from datetime import datetime
from hashlib import sha256
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from ..models import Source, SourceChannel, SourceScan
from ..config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT, ZERO_COST_MODE
from .candidates import upsert_candidate
from .keywords import PROCUREMENT_TERMS, CONSULTANCY_TERMS, DOCUMENT_EXTENSIONS
from .utils import clean_text


def _html_items(text: str, base_url: str):
    soup=BeautifulSoup(text,'html.parser'); out=[]
    for a in soup.find_all('a',href=True):
        title=clean_text(a.get_text(' ',strip=True)); href=urljoin(base_url,a['href'])
        probe=(title+' '+href).lower()
        if any(k.lower() in probe for k in PROCUREMENT_TERMS) or any(k.lower() in probe for k in CONSULTANCY_TERMS) or href.lower().endswith(DOCUMENT_EXTENSIONS):
            out.append((href,title,''))
    return out[:500]

def _sitemap_items(text: str):
    out=[]
    try:
        root=ET.fromstring(text)
        for el in root.iter():
            if el.tag.endswith('loc') and el.text:
                u=el.text.strip(); low=u.lower()
                if any(x in low for x in ('tender','procurement','rfp','eoi','consult','notice','bid')):
                    out.append((u,u.rsplit('/',1)[-1].replace('-',' '),''))
    except Exception: pass
    return out[:500]

def _rss_items(content: bytes):
    out=[]
    try:
        root=ET.fromstring(content)
        # RSS item or Atom entry; tolerate namespaces.
        for node in list(root.iter()):
            tag=node.tag.rsplit('}',1)[-1].lower()
            if tag not in {'item','entry'}:
                continue
            title=''; link=''; summary=''
            for ch in list(node):
                ct=ch.tag.rsplit('}',1)[-1].lower()
                if ct=='title': title=clean_text(ch.text or '')
                elif ct in {'description','summary','content'}: summary=clean_text(''.join(ch.itertext()))
                elif ct=='link': link=(ch.attrib.get('href') or ch.text or '').strip()
            if link: out.append((link,title,summary))
            if len(out)>=500: break
    except Exception:
        pass
    return out

def scan_channel(db: Session, source: Source, ch: SourceChannel):
    scan=SourceScan(source_id=source.id,channel_id=ch.id,status='RUNNING'); db.add(scan); db.commit(); db.refresh(scan)
    source.scan_count=(source.scan_count or 0)+1; source.last_scan_at=datetime.utcnow(); ch.last_scan_at=datetime.utcnow()
    if ZERO_COST_MODE and (source.requires_payment or source.cost_class in {'PAID','UNKNOWN'}):
        scan.status='BLOCKED'; scan.error='BLOCKED_BY_COST_POLICY'; source.health_status='BLOCKED_BY_COST_POLICY'; db.commit(); return scan
    try:
        r=httpx.get(ch.url,timeout=DISCOVERY_REQUEST_TIMEOUT,follow_redirects=True,headers={'User-Agent':USER_AGENT,'Accept-Language':'ar,en,fr;q=0.8'})
        scan.http_status=r.status_code; r.raise_for_status()
        content_hash=sha256(r.content).hexdigest()
        if ch.last_content_hash==content_hash:
            items=[]; scan.status='UNCHANGED'
        else:
            if ch.access_method=='RSS': items=_rss_items(r.content)
            elif ch.access_method=='SITEMAP': items=_sitemap_items(r.text)
            else: items=_html_items(r.text,str(r.url))
            new=0
            for u,title,snip in items:
                if not u.startswith(('http://','https://')): continue
                c,is_new=upsert_candidate(db,u,title,snip,source,'KNOWN_SOURCE',f'{ch.purpose}:{ch.access_method}')
                new+=1 if is_new else 0
            scan.items_seen=len(items); scan.new_candidates=new
            source.candidate_count=(source.candidate_count or 0)+new; scan.status='SUCCESS'; ch.last_content_hash=content_hash
        now=datetime.utcnow(); scan.completed_at=now; source.last_success_at=now; source.success_count=(source.success_count or 0)+1
        source.health_status='HEALTHY'; source.last_error=None; ch.health_status='HEALTHY'; ch.last_success_at=now; ch.last_error=None
        if source.lifecycle_status in {'VERIFIED','CANDIDATE','DISCOVERED'}: source.lifecycle_status='ACTIVE'
    except Exception as e:
        scan.status='FAILED'; scan.error=str(e)[:1500]; scan.completed_at=datetime.utcnow(); source.health_status='DEGRADED'; source.last_error=str(e)[:1500]; ch.health_status='FAILED'; ch.last_error=str(e)[:1500]
    db.commit(); return scan

def scan_source(db: Session, source: Source):
    results=[]
    for ch in sorted([c for c in source.channels if c.enabled],key=lambda x:x.priority_order):
        results.append(scan_channel(db,source,ch))
    return results
