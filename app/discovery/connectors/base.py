from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse
import re

from bs4 import BeautifulSoup

from ..keywords import PROCUREMENT_TERMS, CONSULTANCY_TERMS, DOCUMENT_EXTENSIONS, SAUDI_DB_TERMS
from ..utils import clean_text


BLOCKED_HOSTS = {
    'play.google.com', 'apps.apple.com', 'instagram.com', 'www.instagram.com',
    'linkedin.com', 'www.linkedin.com', 'facebook.com', 'www.facebook.com',
    'x.com', 'www.x.com', 'twitter.com', 'www.twitter.com', 'youtube.com', 'www.youtube.com',
    'forms.office.com', 'forms-db.com', 'www.forms-db.com', 'alerts.worldbank.org',
}

# These paths can never represent a live bid opportunity, even when their page wrapper
# contains words such as "tenders" or "procurement" in the header/footer.
HARD_NAVIGATION_PATH_TOKENS = {
    'privacy', 'privacy-policy', 'terms', 'terms-of-use', 'contact', 'contact-us', 'contactus',
    'accessibility', 'sitemap', 'faq', 'about', 'about-us', 'careers', 'career', 'jobs',
    'training', 'annual-report', 'annual-reports', 'history', 'news', 'login', 'register',
    'signup', 'sign-up', 'disclaimer', 'customercharter', 'customer-charter',
}

NAVIGATION_PATH_TOKENS = {
    'eforms', 'process', 'legislation', 'guideline', 'guidelines', 'guide',
    'board-practice', 'sectors', 'prequalified-vendors', 'procurement-plans', 'winning-bids',
    'awarded-tenders', 'archived-tenders', 'opened-bids', 'opening-results', 'live-opening',
    'warranties', 'postponement', 'postponements', 'closing-tenders',
}

NAVIGATION_TEXT_TOKENS = {
    'home', 'overview', 'privacy policy', 'privacy', 'terms of use', 'contact', 'contact us',
    'accessibility', 'sitemap', 'faq', 'general faq', 'supplier faq', 'annual reports', 'news',
    'training courses', 'eforms', 'process', 'prequalified vendors', 'procurement plans',
    'winning bids', 'awarded tenders', 'archived tenders', 'live opening', 'tender opening results',
    'disclaimer', 'customer charter', 'create an account in etendering', 'etendering login',
    'subscribe to receive email alerts', 'skip to content', 'skip to footer',
    'دليل', 'الأخبار', 'اتصل بنا', 'سياسة الخصوصية', 'الشروط', 'الترسيات', 'التأمين الأولي',
    'تأجيل المناقصات', 'فض العطاءات',
}
PAGINATION_TEXT = {'next','previous','prev','first','frist','last','التالي','السابق','الأول','الاول'}


@dataclass(slots=True)
class ExtractedOpportunity:
    url: str
    title: str
    snippet: str = ''
    evidence: str = 'HTML_LINK'


@dataclass(slots=True)
class ConnectorResult:
    items: list[ExtractedOpportunity]
    final_url: str
    http_status: int | None = None
    connector_name: str = 'GENERIC'
    rendered: bool = False


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or '').lower()
    except Exception:
        return ''


def is_blocked_external_host(url: str) -> bool:
    host=_host(url)
    return host in BLOCKED_HOSTS or any(host.endswith('.'+x) for x in BLOCKED_HOSTS if not x.startswith('www.'))


def _path_words(url: str) -> set[str]:
    try:
        path=(urlparse(url).path or '').lower().replace('_','-')
    except Exception:
        return set()
    return {x for x in re.split(r'[^a-z0-9]+',path) if x}


def _without_fragment(url: str) -> str:
    try:
        p=urlparse(url)
        return urlunparse((p.scheme,p.netloc,p.path,p.params,p.query,''))
    except Exception:
        return url.split('#',1)[0]


def looks_like_navigation(url: str, title: str, context: str='') -> bool:
    if is_blocked_external_host(url):
        return True
    low_title=clean_text(title or '').lower().strip()
    if low_title in NAVIGATION_TEXT_TOKENS or low_title in PAGINATION_TEXT or low_title.isdigit():
        return True
    parsed=urlparse(url)
    path=(parsed.path or '').lower()
    if path in {'','/'}:
        return True
    if parsed.fragment:
        return True
    if 'pageindex=' in (parsed.query or '').lower() and (low_title.isdigit() or low_title in PAGINATION_TEXT):
        return True
    if any(token in path for token in HARD_NAVIGATION_PATH_TOKENS):
        return True
    if any(token in path for token in NAVIGATION_PATH_TOKENS):
        # Soft navigation paths can occasionally be part of a real record URL. Only
        # preserve them when the record itself has explicit procurement evidence.
        probe=(low_title+' '+clean_text(context or '').lower())
        if not any(k.lower() in probe for k in PROCUREMENT_TERMS):
            return True
    return False


def slug_title(url: str) -> str:
    try:
        path=(urlparse(url).path or '').rstrip('/')
        slug=path.rsplit('/',1)[-1]
    except Exception:
        return ''
    slug=re.sub(r'[-_]+',' ',slug)
    slug=re.sub(r'\s+',' ',slug).strip()
    if slug.lower() in {'tenders','tender','procurement','opportunities','publictenders'}:
        return ''
    return slug[:500]


def _parent_context(anchor, max_chars: int=2500) -> str:
    # Prefer row/card/article/list item so a generic link label like "View" inherits
    # the actual tender title, reference and authority shown beside it.
    parent=anchor.find_parent(['tr','article','li','section'])
    if parent is None:
        parent=anchor.find_parent(class_=re.compile(r'(card|item|tender|notice|opportun|result|row)',re.I))
    if parent is None:
        parent=anchor.parent
    return clean_text(parent.get_text(' ',strip=True) if parent else '')[:max_chars]


def _signal_counts(text: str) -> tuple[int,int,int]:
    low=(text or '').lower()
    procurement=sum(1 for x in PROCUREMENT_TERMS if x.lower() in low)
    consultancy=sum(1 for x in CONSULTANCY_TERMS if x.lower() in low)
    saudi=sum(1 for x in SAUDI_DB_TERMS if x.lower() in low)
    return procurement,consultancy,saudi


def is_individual_opportunity(url: str, title: str, context: str, *, country: str|None=None) -> bool:
    if looks_like_navigation(url,title,context):
        return False
    clean_title=clean_text(title or '')
    slug=slug_title(url)
    probe=' '.join(x for x in (clean_title,context,slug) if x)
    p,c,s=_signal_counts(probe)
    # A document is only interesting when its name/context carries procurement evidence.
    is_doc=url.lower().split('?',1)[0].endswith(DOCUMENT_EXTENSIONS)
    if is_doc and p == 0:
        return False
    # Procurement evidence is mandatory. Consultancy relevance is validated later using
    # the full page; keeping procurement-only records here allows Saudi D&B/EPC analysis.
    if p == 0:
        return False
    # Reject obvious listing/root pages: they are SourceChannels, not opportunities.
    try:
        path=(urlparse(url).path or '').lower().rstrip('/')
    except Exception:
        path=''
    if path.endswith(('/tenders','/tender','/procurement','/publictenders','/opportunities')):
        return False
    return True


class BaseConnector:
    name='BASE'
    render_js=False

    def extract(self, html: str, base_url: str, *, country: str|None=None) -> list[ExtractedOpportunity]:
        raise NotImplementedError


class PortalHtmlConnector(BaseConnector):
    name='PORTAL_HTML'

    def extract(self, html: str, base_url: str, *, country: str|None=None) -> list[ExtractedOpportunity]:
        soup=BeautifulSoup(html or '','html.parser')
        out=[]; seen=set(); base_no_fragment=_without_fragment(base_url).rstrip('/')
        for a in soup.find_all('a',href=True):
            href=urljoin(base_url,a.get('href') or '')
            if not href.startswith(('http://','https://')) or href in seen:
                continue
            if _without_fragment(href).rstrip('/') == base_no_fragment:
                continue
            title=clean_text(a.get_text(' ',strip=True))
            context=_parent_context(a)
            if not is_individual_opportunity(href,title,context,country=country):
                continue
            if not title or title.lower() in {'view','details','more','read more','click here','عرض','تفاصيل'}:
                # Prefer contextual title; URL slug is a final fallback. Generic labels
                # with no useful surrounding context are not allowed to become records.
                contextual=context
                if contextual and len(contextual)>12 and contextual.lower()!=title.lower():
                    title=contextual[:500]
                else:
                    slug=slug_title(href)
                    if not slug or slug.isdigit():
                        continue
                    title=slug
            out.append(ExtractedOpportunity(url=href,title=title[:500],snippet=context[:3000]))
            seen.add(href)
            if len(out)>=500:
                break
        return out
