import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import Source, SourceChannel
from ..config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT, ZERO_COST_MODE
from .source_registry import procurement_links


def profile_source(db: Session, source: Source) -> dict:
    if ZERO_COST_MODE and (source.requires_payment or source.cost_class in {'PAID','UNKNOWN'}):
        source.lifecycle_status='BLOCKED'; source.health_status='BLOCKED_BY_COST_POLICY'; db.commit()
        return {'ok':False,'reason':'BLOCKED_BY_COST_POLICY'}
    url=source.base_url or (source.channels[0].url if source.channels else None)
    if not url: return {'ok':False,'reason':'NO_URL'}
    try:
        r=httpx.get(url,timeout=DISCOVERY_REQUEST_TIMEOUT,follow_redirects=True,headers={'User-Agent':USER_AGENT})
        r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        anchors=[(a.get('href',''),a.get_text(' ',strip=True)) for a in soup.find_all('a',href=True)]
        found=procurement_links(str(r.url),anchors)
        existing_urls={x.url for x in source.channels}
        for u,t in found[:10]:
            if u not in existing_urls:
                db.add(SourceChannel(source_id=source.id,purpose='DISCOVERY',url=u,access_method='HTML',priority_order=5))
        # Common public discovery endpoints.
        for path,method,purpose in [('/sitemap.xml','SITEMAP','DISCOVERY'),('/feed','RSS','DISCOVERY'),('/rss','RSS','DISCOVERY')]:
            u=urljoin(str(r.url),path)
            if u not in existing_urls:
                try:
                    rr=httpx.get(u,timeout=8,follow_redirects=True,headers={'User-Agent':USER_AGENT})
                    if rr.status_code==200 and len(rr.content)>30:
                        ctype=rr.headers.get('content-type','').lower()
                        if method=='SITEMAP' and ('xml' in ctype or '<urlset' in rr.text[:1000].lower()):
                            db.add(SourceChannel(source_id=source.id,purpose=purpose,url=u,access_method=method,priority_order=4))
                        elif method=='RSS' and ('xml' in ctype or '<rss' in rr.text[:1000].lower() or '<feed' in rr.text[:1000].lower()):
                            db.add(SourceChannel(source_id=source.id,purpose=purpose,url=u,access_method=method,priority_order=3))
                except Exception: pass
        source.health_status='HEALTHY'; source.last_error=None
        if source.lifecycle_status in {'DISCOVERED','CANDIDATE','VALIDATING'} and found:
            source.lifecycle_status='VERIFIED'
        db.commit()
        return {'ok':True,'procurement_links':len(found)}
    except Exception as e:
        source.health_status='DEGRADED'; source.last_error=str(e)[:1000]; db.commit()
        return {'ok':False,'reason':str(e)}
