from urllib.parse import urljoin
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Source, SourceChannel
from .seeds.default_sources import SEED_SOURCES
from .utils import domain_of
from .keywords import PROCUREMENT_PATH_HINTS

SOCIAL_DOMAINS={'linkedin.com','facebook.com','x.com','twitter.com'}


def _source_type_for_domain(domain: str|None) -> tuple[str,int,int,str]:
    d=(domain or '').lower()
    social=next((x for x in SOCIAL_DOMAINS if d==x or d.endswith('.'+x)),None)
    if social:
        return 'SOCIAL_SIGNAL',25,35,'SOCIAL_SIGNAL'
    return 'OPEN_WEB',30,50,'DISCOVERY'


def bootstrap_sources(db: Session) -> int:
    added=0
    for seed in SEED_SOURCES:
        source=db.scalar(select(Source).where(Source.name==seed['name']))
        if not source:
            source=Source(
                name=seed['name'],domain=seed['domain'],base_url=seed['base_url'],source_type=seed['source_type'],country=seed.get('country'),
                languages=seed.get('languages'),lifecycle_status='ACTIVE',priority=seed['priority'],trust_score=seed['trust_score'],
                relevance_score=seed['relevance_score'],discovery_value=seed['discovery_value'],health_status='UNKNOWN',cost_class='FREE_PUBLIC',
                requires_payment=0,discovered_by='SEED_LIBRARY',discovery_detail='Verified public seed source'
            )
            db.add(source); db.flush(); added+=1
        for purpose,url,method in seed.get('channels',[]):
            exists=db.scalar(select(SourceChannel).where(SourceChannel.source_id==source.id, SourceChannel.url==url))
            if not exists:
                db.add(SourceChannel(source_id=source.id,purpose=purpose,url=url,access_method=method,priority_order=1))
    db.commit()
    return added


def get_or_create_discovered_source(db: Session, url: str, discovered_by: str, detail: str='') -> tuple[Source,bool]:
    domain=domain_of(url)
    existing=db.scalar(select(Source).where(Source.domain==domain)) if domain else None
    if existing:
        return existing,False
    source_type,trust,discovery_value,purpose=_source_type_for_domain(domain)
    src=Source(name=domain or url[:240],domain=domain or None,base_url=f'https://{domain}/' if domain else url,source_type=source_type,
               lifecycle_status='CANDIDATE',priority='EXPERIMENTAL',trust_score=trust,relevance_score=30,discovery_value=discovery_value,
               health_status='UNKNOWN',cost_class='FREE_PUBLIC',requires_payment=0,discovered_by=discovered_by,discovery_detail=detail)
    db.add(src); db.flush()
    db.add(SourceChannel(source_id=src.id,purpose=purpose,url=url,access_method='HTML',priority_order=1))
    db.commit(); db.refresh(src)
    return src,True


def procurement_links(base_url: str, anchors: list[tuple[str,str]]) -> list[tuple[str,str]]:
    out=[]; seen=set()
    for href,text in anchors:
        u=urljoin(base_url,href or '')
        combined=(u+' '+(text or '')).lower()
        if any(h in combined for h in PROCUREMENT_PATH_HINTS) and u not in seen:
            seen.add(u); out.append((u,text))
    return out[:30]
