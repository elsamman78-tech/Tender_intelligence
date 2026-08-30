from datetime import datetime
from hashlib import sha256
from urllib.parse import urljoin, urlparse, urldefrag
import xml.etree.ElementTree as ET
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from ..models import Source, SourceChannel, SourceScan
from ..config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT, ZERO_COST_MODE
from .candidates import upsert_candidate
from .keywords import PROCUREMENT_TERMS, CONSULTANCY_TERMS, DOCUMENT_EXTENSIONS
from .utils import clean_text

# These are site-navigation / information surfaces, not bid opportunities.
NOISE_LINK_TERMS = {
    'accessibility', 'privacy policy', 'privacy', 'sitemap', 'customer charter', 'disclaimer',
    'terms of use', 'contact', 'contact us', 'home', 'faq', 'frequently asked', 'annual report',
    'annual reports', 'news', 'training', 'training courses', 'eforms', 'e-forms', 'process',
    'supplier faq', 'general faq', 'about us', 'careers', 'jobs', 'media', 'legislation',
    'guideline', 'guidelines', 'supplier guide', 'contractor guide', 'partnership guide',
    'vision 2030', 'standard electronic report', 'standard electronic request template',
    'prequalified vendors', 'live opening', 'tender opening results', 'opened bids',
    'archived tenders', 'awarded tenders', 'contract awards', 'procurement plans',
    'to be opened this week', 'site map',
}

NOISE_PATH_PARTS = {
    '/accessibility', '/privacypolicy', '/privacy', '/sitemap', '/customercharter', '/disclaimer',
    '/terms', '/contactus', '/faq/', '/about/news', '/about/annualreports', '/services/training',
    '/services/eforms', '/services/process', '/legislation/', '/archivedtenders', '/awardedtenders',
    '/openedbids', '/prequalifiedvendors', '/liveopening', '/procurementplans', '/tobeopened',
}

# Only these channel purposes may create opportunity candidates. Other channels can still be
# health-checked, but awards/early-signal pages do not pollute the tender validation queue.
OPPORTUNITY_CHANNEL_PURPOSES = {
    'TENDERS', 'EOI', 'RFP', 'RFQ', 'PREQUALIFICATION', 'ANNOUNCEMENTS', 'OPPORTUNITIES'
}


def _clean_url(url: str) -> str:
    return urldefrag(url)[0].rstrip('/')


def _is_noise_link(title: str, href: str, base_url: str) -> bool:
    t = clean_text(title or '').lower().strip()
    parsed = urlparse(href)
    path = (parsed.path or '').lower().rstrip('/')
    base_clean = _clean_url(base_url)
    target_clean = _clean_url(href)

    # Same-page anchors/navigation are never opportunities.
    if target_clean == base_clean:
        return True

    if t in NOISE_LINK_TERMS or any(term in t for term in NOISE_LINK_TERMS if len(term) >= 5):
        return True
    if any(part in path for part in NOISE_PATH_PARTS):
        return True

    # Bare home/navigation links.
    if path in {'', '/'} and t in {'', 'home', 'الرئيسية', 'الصفحة الرئيسية'}:
        return True
    return False


def _opportunity_probe(title: str, href: str) -> str:
    """Build a relevance probe without the hostname.

    The old scanner included the hostname, so every link on tenderboard.gov.bh contained
    the word 'tender' and was incorrectly promoted as a candidate.
    """
    parsed = urlparse(href)
    path_query = f'{parsed.path} {parsed.query}'.replace('-', ' ').replace('_', ' ')
    return clean_text(f'{title or ""} {path_query}').lower()


def _looks_like_opportunity(title: str, href: str, base_url: str) -> bool:
    if _is_noise_link(title, href, base_url):
        return False

    probe = _opportunity_probe(title, href)
    has_procurement = any(k.lower() in probe for k in PROCUREMENT_TERMS)
    has_consultancy = any(k.lower() in probe for k in CONSULTANCY_TERMS)

    # A document is not interesting just because it is a PDF/DOC; filename/title must also
    # carry procurement or consultancy evidence (blocks Vision2030.pdf and generic guides).
    parsed = urlparse(href)
    is_document = parsed.path.lower().endswith(DOCUMENT_EXTENSIONS)
    if is_document:
        return has_procurement or has_consultancy

    return has_procurement or has_consultancy


def _html_items(text: str, base_url: str):
    soup = BeautifulSoup(text, 'html.parser')
    out = []
    seen = set()
    for a in soup.find_all('a', href=True):
        title = clean_text(a.get_text(' ', strip=True))
        href = urljoin(base_url, a['href'])
        if not href.startswith(('http://', 'https://')):
            continue
        href = urldefrag(href)[0]
        if not href or href in seen:
            continue
        if _looks_like_opportunity(title, href, base_url):
            seen.add(href)
            out.append((href, title, ''))
    return out[:500]


def _sitemap_items(text: str):
    out = []
    try:
        root = ET.fromstring(text)
        for el in root.iter():
            if el.tag.endswith('loc') and el.text:
                u = el.text.strip()
                parsed = urlparse(u)
                low = (parsed.path + ' ' + parsed.query).lower()
                if any(x in low for x in ('tender', 'procurement', 'rfp', 'eoi', 'consult', 'notice', 'bid')):
                    if not _is_noise_link('', u, ''):
                        out.append((u, u.rsplit('/', 1)[-1].replace('-', ' '), ''))
    except Exception:
        pass
    return out[:500]


def _rss_items(content: bytes):
    out = []
    try:
        root = ET.fromstring(content)
        for node in list(root.iter()):
            tag = node.tag.rsplit('}', 1)[-1].lower()
            if tag not in {'item', 'entry'}:
                continue
            title = ''; link = ''; summary = ''
            for ch in list(node):
                ct = ch.tag.rsplit('}', 1)[-1].lower()
                if ct == 'title':
                    title = clean_text(ch.text or '')
                elif ct in {'description', 'summary', 'content'}:
                    summary = clean_text(''.join(ch.itertext()))
                elif ct == 'link':
                    link = (ch.attrib.get('href') or ch.text or '').strip()
            if link and _looks_like_opportunity(title + ' ' + summary, link, ''):
                out.append((link, title, summary))
            if len(out) >= 500:
                break
    except Exception:
        pass
    return out


def scan_channel(db: Session, source: Source, ch: SourceChannel):
    scan = SourceScan(source_id=source.id, channel_id=ch.id, status='RUNNING')
    db.add(scan); db.commit(); db.refresh(scan)
    source.scan_count = (source.scan_count or 0) + 1
    source.last_scan_at = datetime.utcnow(); ch.last_scan_at = datetime.utcnow()
    if ZERO_COST_MODE and (source.requires_payment or source.cost_class in {'PAID', 'UNKNOWN'}):
        scan.status = 'BLOCKED'; scan.error = 'BLOCKED_BY_COST_POLICY'
        source.health_status = 'BLOCKED_BY_COST_POLICY'; db.commit(); return scan
    try:
        r = httpx.get(ch.url, timeout=DISCOVERY_REQUEST_TIMEOUT, follow_redirects=True,
                      headers={'User-Agent': USER_AGENT, 'Accept-Language': 'ar,en,fr;q=0.8'})
        scan.http_status = r.status_code; r.raise_for_status()
        content_hash = sha256(r.content).hexdigest()
        if ch.last_content_hash == content_hash:
            items = []; scan.status = 'UNCHANGED'
        else:
            if ch.purpose not in OPPORTUNITY_CHANNEL_PURPOSES:
                # Keep source/channel health current, but do not feed awards or early-signal
                # navigation into the tender candidate queue.
                items = []
            elif ch.access_method == 'RSS':
                items = _rss_items(r.content)
            elif ch.access_method == 'SITEMAP':
                items = _sitemap_items(r.text)
            else:
                items = _html_items(r.text, str(r.url))
            new = 0
            for u, title, snip in items:
                if not u.startswith(('http://', 'https://')):
                    continue
                c, is_new = upsert_candidate(db, u, title, snip, source, 'KNOWN_SOURCE', f'{ch.purpose}:{ch.access_method}')
                new += 1 if is_new else 0
            scan.items_seen = len(items); scan.new_candidates = new
            source.candidate_count = (source.candidate_count or 0) + new
            scan.status = 'SUCCESS'; ch.last_content_hash = content_hash
        now = datetime.utcnow(); scan.completed_at = now; source.last_success_at = now
        source.success_count = (source.success_count or 0) + 1
        source.health_status = 'HEALTHY'; source.last_error = None
        ch.health_status = 'HEALTHY'; ch.last_success_at = now; ch.last_error = None
        if source.lifecycle_status in {'VERIFIED', 'CANDIDATE', 'DISCOVERED'}:
            source.lifecycle_status = 'ACTIVE'
    except Exception as e:
        scan.status = 'FAILED'; scan.error = str(e)[:1500]; scan.completed_at = datetime.utcnow()
        source.health_status = 'DEGRADED'; source.last_error = str(e)[:1500]
        ch.health_status = 'FAILED'; ch.last_error = str(e)[:1500]
    db.commit(); return scan


def scan_source(db: Session, source: Source):
    results = []
    for ch in sorted([c for c in source.channels if c.enabled], key=lambda x: x.priority_order):
        results.append(scan_channel(db, source, ch))
    return results
