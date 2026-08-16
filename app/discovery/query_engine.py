from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import DiscoveryQuery, SearchRun, SearchResult
from ..config import DISCOVERY_MAX_RESULTS_PER_QUERY, ZERO_COST_MODE
from .providers.router import providers
from .source_registry import get_or_create_discovered_source
from .candidates import upsert_candidate
from .utils import hash_text, domain_of

SEED_QUERIES = [
    ('"engineering consultancy" tender Saudi Arabia','en','Saudi Arabia','TENDER_SEARCH',95),
    ('"project management consultant" RFP Saudi Arabia','en','Saudi Arabia','TENDER_SEARCH',95),
    ('"طلب إبداء اهتمام" استشاري السعودية','ar','Saudi Arabia','TENDER_SEARCH',95),
    ('"منافسة" استشاري تصميم إشراف السعودية','ar','Saudi Arabia','TENDER_SEARCH',90),
    ('"engineering consultancy" tender Egypt','en','Egypt','TENDER_SEARCH',90),
    ('"خدمات استشارية" مناقصة مصر','ar','Egypt','TENDER_SEARCH',95),
    ('"construction supervision consultant" UAE RFP','en','UAE','TENDER_SEARCH',90),
    ('"project management consultant" UAE tender','en','UAE','TENDER_SEARCH',90),
    ('"consulting services" EOI Libya engineering','en','Libya','TENDER_SEARCH',85),
    ('"consulting services" EOI Bangladesh engineering','en','Bangladesh','TENDER_SEARCH',85),
    ('"request for expressions of interest" consultant Africa engineering','en',None,'TENDER_SEARCH',80),
    ('"owner\'s engineer" tender Africa','en',None,'TENDER_SEARCH',80),
    ('"manifestation d\'intérêt" "bureau d\'études" Afrique','fr',None,'TENDER_SEARCH',80),
    ('"mission de contrôle" "appel d\'offres" Afrique','fr',None,'TENDER_SEARCH',75),
    ('filetype:pdf "terms of reference" "consulting services" Africa','en',None,'FILE_SEARCH',75),
    ('filetype:pdf RFP "project management consultant" Middle East','en',None,'FILE_SEARCH',75),
    ('inurl:procurement consultant "Saudi Arabia"','en','Saudi Arabia','SOURCE_SEARCH',70),
    ('inurl:tenders consultant UAE','en','UAE','SOURCE_SEARCH',70),
]

def bootstrap_queries(db: Session):
    added=0
    for text,lang,country,purpose,priority in SEED_QUERIES:
        q=db.scalar(select(DiscoveryQuery).where(DiscoveryQuery.query_text==text))
        if not q:
            db.add(DiscoveryQuery(query_text=text,language=lang,country=country,purpose=purpose,priority=priority)); added+=1
    db.commit(); return added


def run_query(db: Session, q: DiscoveryQuery, provider=None, limit: int|None=None):
    plist=[provider] if provider else providers()
    if not plist:
        return {'ok':False,'error':'NO_ZERO_COST_SEARCH_PROVIDER_AVAILABLE','results':0}
    last_error=''
    for p in plist:
        if ZERO_COST_MODE and getattr(p,'cost_class','UNKNOWN') not in {'FREE_PUBLIC','FREE_LOCAL','FREE_OPTIONAL'}:
            continue
        run=SearchRun(query_id=q.id,provider=p.name,query_text=q.query_text,status='RUNNING'); db.add(run); db.commit(); db.refresh(run)
        try:
            hits=p.search(q.query_text,limit or DISCOVERY_MAX_RESULTS_PER_QUERY)
            new_domains=0; new_candidates=0
            for h in hits:
                uh=hash_text(h.url); dom=domain_of(h.url)
                db.add(SearchResult(run_id=run.id,url=h.url,url_hash=uh,domain=dom,title=h.title[:2000],snippet=h.snippet[:5000],rank=h.rank))
                source,is_new_domain=get_or_create_discovered_source(db,h.url,'OPEN_SEARCH',f'provider={p.name}; query={q.query_text[:300]}')
                new_domains+=1 if is_new_domain else 0
                cand,is_new=upsert_candidate(db,h.url,h.title,h.snippet,source,'OPEN_SEARCH',q.query_text)
                new_candidates+=1 if is_new else 0
            now=datetime.utcnow(); run.completed_at=now; run.status='SUCCESS'; run.result_count=len(hits); run.new_domain_count=new_domains; run.new_candidate_count=new_candidates
            q.run_count=(q.run_count or 0)+1; q.result_count=(q.result_count or 0)+len(hits); q.new_source_count=(q.new_source_count or 0)+new_domains; q.last_run_at=now
            db.commit()
            return {'ok':True,'provider':p.name,'results':len(hits),'new_domains':new_domains,'new_candidates':new_candidates}
        except Exception as e:
            last_error=str(e); run.completed_at=datetime.utcnow(); run.status='FAILED'; run.error=last_error[:1500]; db.commit()
    return {'ok':False,'error':last_error or 'ALL_PROVIDERS_FAILED','results':0}


def select_query_batch(db: Session, limit: int=8):
    return db.scalars(select(DiscoveryQuery).where(DiscoveryQuery.enabled==True).order_by(DiscoveryQuery.priority.desc(),DiscoveryQuery.last_run_at.asc()).limit(limit)).all()
