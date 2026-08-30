from datetime import datetime
from hashlib import sha256
import xml.etree.ElementTree as ET

import httpx
from sqlalchemy.orm import Session

from ..models import Source, SourceChannel, SourceScan
from ..config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT, ZERO_COST_MODE
from .candidates import upsert_candidate
from .utils import clean_text
from .connectors import scan_url

OPPORTUNITY_CHANNEL_PURPOSES = {
    'TENDERS','EOI','RFP','RFQ','PREQUALIFICATION','ANNOUNCEMENTS','OPPORTUNITIES'
}


def _sitemap_items(text: str):
    out=[]
    try:
        root=ET.fromstring(text)
        for el in root.iter():
            if el.tag.endswith('loc') and el.text:
                u=el.text.strip(); low=u.lower()
                if any(x in low for x in ('tender','procurement','rfp','eoi','consult','notice','bid')):
                    out.append((u,u.rsplit('/',1)[-1].replace('-',' '),''))
    except Exception:
        pass
    return out[:500]


def _rss_items(content: bytes):
    out=[]
    try:
        root=ET.fromstring(content)
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


def _hash_items(items) -> str:
    body='\n'.join('|'.join((str(x[0]),str(x[1]),str(x[2]))) for x in items)
    return sha256(body.encode('utf-8','ignore')).hexdigest()


def scan_channel(db: Session, source: Source, ch: SourceChannel):
    scan=SourceScan(source_id=source.id,channel_id=ch.id,status='RUNNING')
    db.add(scan); db.commit(); db.refresh(scan)
    source.scan_count=(source.scan_count or 0)+1
    source.last_scan_at=datetime.utcnow(); ch.last_scan_at=datetime.utcnow()
    if ZERO_COST_MODE and (source.requires_payment or source.cost_class in {'PAID','UNKNOWN'}):
        scan.status='BLOCKED'; scan.error='BLOCKED_BY_COST_POLICY'
        source.health_status='BLOCKED_BY_COST_POLICY'; db.commit(); return scan

    try:
        if ch.purpose not in OPPORTUNITY_CHANNEL_PURPOSES:
            # Source metadata / award / early-signal channels are health-checked elsewhere;
            # they never feed the tender candidate queue.
            items=[]; connector_name=f'NON_OPPORTUNITY:{ch.access_method}'
            scan.http_status=None
        elif ch.access_method=='RSS':
            r=httpx.get(ch.url,timeout=DISCOVERY_REQUEST_TIMEOUT,follow_redirects=True,headers={'User-Agent':USER_AGENT,'Accept-Language':'ar,en,fr;q=0.8'})
            scan.http_status=r.status_code; r.raise_for_status(); items=_rss_items(r.content)
            connector_name='RSS'
        elif ch.access_method=='SITEMAP':
            r=httpx.get(ch.url,timeout=DISCOVERY_REQUEST_TIMEOUT,follow_redirects=True,headers={'User-Agent':USER_AGENT,'Accept-Language':'ar,en,fr;q=0.8'})
            scan.http_status=r.status_code; r.raise_for_status(); items=_sitemap_items(r.text)
            connector_name='SITEMAP'
        else:
            result=scan_url(ch.url,country=source.country)
            scan.http_status=result.http_status
            connector_name=result.connector_name
            items=[(x.url,x.title,x.snippet) for x in result.items]

        content_hash=_hash_items(items)
        if ch.last_content_hash==content_hash:
            scan.status='UNCHANGED'; scan.items_seen=len(items)
        else:
            new=0
            for u,title,snip in items:
                if not u.startswith(('http://','https://')):
                    continue
                _,is_new=upsert_candidate(
                    db,u,title,snip,source,'KNOWN_SOURCE',f'{ch.purpose}:{connector_name}'
                )
                new+=1 if is_new else 0
            scan.items_seen=len(items); scan.new_candidates=new
            source.candidate_count=(source.candidate_count or 0)+new
            scan.status='SUCCESS'; ch.last_content_hash=content_hash

        now=datetime.utcnow(); scan.completed_at=now
        source.last_success_at=now; source.success_count=(source.success_count or 0)+1
        source.health_status='HEALTHY'; source.last_error=None
        ch.health_status='HEALTHY'; ch.last_success_at=now; ch.last_error=None
        if source.lifecycle_status in {'VERIFIED','CANDIDATE','DISCOVERED'}:
            source.lifecycle_status='ACTIVE'
    except Exception as e:
        scan.status='FAILED'; scan.error=str(e)[:1500]; scan.completed_at=datetime.utcnow()
        source.health_status='DEGRADED'; source.last_error=str(e)[:1500]
        ch.health_status='FAILED'; ch.last_error=str(e)[:1500]
    db.commit(); return scan


def scan_source(db: Session, source: Source):
    results=[]
    for ch in sorted([c for c in source.channels if c.enabled],key=lambda x:x.priority_order):
        results.append(scan_channel(db,source,ch))
    return results
