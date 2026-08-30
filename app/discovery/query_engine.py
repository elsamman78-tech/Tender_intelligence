from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import DiscoveryQuery, SearchRun, SearchResult
from ..config import DISCOVERY_MAX_RESULTS_PER_QUERY, ZERO_COST_MODE
from ..geography import TARGET_COUNTRIES, PRIORITY_COUNTRIES
from .providers.router import providers
from .source_registry import get_or_create_discovered_source
from .candidates import upsert_candidate, score_candidate
from .utils import hash_text, domain_of

SEED_QUERIES = [
    ('"engineering consultancy" tender Saudi Arabia','en','Saudi Arabia','TENDER_SEARCH',100),
    ('"project management consultant" RFP Saudi Arabia','en','Saudi Arabia','TENDER_SEARCH',100),
    ('("design and build" OR EPC OR turnkey) (engineering OR design) tender Saudi Arabia','en','Saudi Arabia','SAUDI_DB_SEARCH',100),
    ('("تصميم وتنفيذ" OR "تصميم وبناء") (منافسة OR مناقصة) السعودية','ar','Saudi Arabia','SAUDI_DB_SEARCH',100),
    ('"طلب إبداء اهتمام" استشاري السعودية','ar','Saudi Arabia','TENDER_SEARCH',100),
    ('"خدمات استشارية" مناقصة مصر','ar','Egypt','TENDER_SEARCH',100),
    ('"engineering consultancy" tender Egypt','en','Egypt','TENDER_SEARCH',100),
    ('"construction supervision consultant" UAE RFP','en','UAE','TENDER_SEARCH',100),
    ('"consulting services" EOI Libya engineering','en','Libya','TENDER_SEARCH',98),
    ('"consulting services" EOI Yemen engineering','en','Yemen','TENDER_SEARCH',96),
    ('"request for expressions of interest" consultant Africa engineering','en',None,'TENDER_SEARCH',90),
    ('"owner\'s engineer" tender Africa','en',None,'TENDER_SEARCH',90),
    ('filetype:pdf "terms of reference" "consulting services" Africa','en',None,'FILE_SEARCH',88),
    ('filetype:pdf RFP "project management consultant" "Middle East"','en',None,'FILE_SEARCH',88),
    ('(newspaper OR gazette OR e-paper) (tender OR RFP OR EOI) "engineering consultant" Africa','en',None,'NEWS_GAZETTE_SEARCH',84),
    ('(جريدة OR صحيفة) (مناقصة OR "إبداء اهتمام" OR "طلب عروض") (استشاري OR تصميم OR إشراف)','ar',None,'NEWS_GAZETTE_SEARCH',84),
    ('"procurement plan" consultant infrastructure Africa','en',None,'EARLY_SIGNAL',70),
    ('"general procurement notice" consulting services Africa','en',None,'EARLY_SIGNAL',70),
]

REGION_PACKS = ['Africa','North Africa','Sub-Saharan Africa','Middle East','GCC','Gulf Cooperation Council']
DEPRECATED_PURPOSES = {'LINKEDIN_SIGNAL','FACEBOOK_SIGNAL','X_SIGNAL','SOCIAL_SIGNAL'}
SOURCE_ONLY_PURPOSES = {'SOURCE_SEARCH','PRIVATE_SOURCE_SEARCH','EARLY_SIGNAL'}
OPPORTUNITY_PURPOSES = {'TENDER_SEARCH','SAUDI_DB_SEARCH','FILE_SEARCH','NEWS_GAZETTE_SEARCH'}


def generated_queries():
    out=[]
    for country in TARGET_COUNTRIES:
        pr=96 if country in PRIORITY_COUNTRIES else 72
        out.append((f'("engineering consultancy" OR "consulting services" OR "project management consultant" OR "construction supervision") (tender OR RFP OR EOI OR procurement) "{country}"','en',country,'TENDER_SEARCH',pr))
        out.append((f'"{country}" ("government procurement" OR "e-procurement" OR "tender portal" OR "procurement opportunities") (consultant OR engineering)','en',country,'SOURCE_SEARCH',pr-4))
        out.append((f'"{country}" (newspaper OR gazette OR "tender notice" OR "procurement notice") (consultant OR consultancy OR engineering)','en',country,'NEWS_GAZETTE_SEARCH',max(64,pr-10)))
    for region in REGION_PACKS:
        out.append((f'"{region}" (developer OR utility OR operator OR bank OR university OR hospital OR infrastructure) (RFP OR EOI OR tender OR procurement) (consultant OR consultancy OR engineering)','en',None,'PRIVATE_SOURCE_SEARCH',80))
        out.append((f'"{region}" ("procurement portal" OR "tender portal" OR "business opportunities") engineering consultant','en',None,'SOURCE_SEARCH',78))
        out.append((f'"{region}" (gazette OR newspaper OR "procurement notice" OR "tender notice") (consultant OR consultancy OR engineering)','en',None,'NEWS_GAZETTE_SEARCH',76))
    out.extend([
        ('("مناقصة" OR "منافسة" OR "إبداء اهتمام" OR "طلب عروض") (استشاري OR "خدمات استشارية" OR إشراف OR تصميم) أفريقيا','ar',None,'TENDER_SEARCH',88),
        ('("مناقصة" OR "منافسة" OR "إبداء اهتمام" OR "طلب عروض") (استشاري OR "خدمات استشارية" OR إشراف OR تصميم) "الشرق الأوسط"','ar',None,'TENDER_SEARCH',88),
        ('("appel d’offres" OR "manifestation d’intérêt") (consultant OR "bureau d’études" OR supervision) Afrique','fr',None,'TENDER_SEARCH',82),
    ])
    return out


def bootstrap_queries(db: Session):
    for old in db.scalars(select(DiscoveryQuery).where(DiscoveryQuery.purpose.in_(DEPRECATED_PURPOSES))).all():
        old.enabled=False
    added=0
    for text,lang,country,purpose,priority in SEED_QUERIES + generated_queries():
        q=db.scalar(select(DiscoveryQuery).where(DiscoveryQuery.query_text==text))
        if not q:
            db.add(DiscoveryQuery(query_text=text,language=lang,country=country,purpose=purpose,priority=priority)); added+=1
        else:
            q.enabled=True; q.priority=priority; q.purpose=purpose
    db.commit(); return added


def _opportunity_hit_ok(q: DiscoveryQuery, title: str, snippet: str) -> bool:
    p,c,_=score_candidate(title or '',snippet or '')
    if q.purpose=='SAUDI_DB_SEARCH':
        return p>=6 and (c>=4 or any(x in ((title or '')+' '+(snippet or '')).lower() for x in ('design','engineering','epc','turnkey','تصميم','هندسي')))
    return p>=6 and c>=6


def run_query(db: Session, q: DiscoveryQuery, provider=None, limit: int|None=None):
    if q.purpose in DEPRECATED_PURPOSES or not q.enabled:
        return {'ok':True,'skipped':True,'reason':'DEPRECATED_OR_DISABLED_QUERY','results':0}
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
            new_domains=0; new_candidates=0; noise=0; urls=[]
            for h in hits:
                uh=hash_text(h.url); dom=domain_of(h.url)
                db.add(SearchResult(run_id=run.id,url=h.url,url_hash=uh,domain=dom,title=h.title[:2000],snippet=h.snippet[:5000],rank=h.rank))
                urls.append(h.url)

                if q.purpose in SOURCE_ONLY_PURPOSES:
                    # Source discovery enriches the source graph only. A portal/app/article
                    # discovered here is not a tender candidate.
                    _,is_new_domain=get_or_create_discovered_source(db,h.url,'OPEN_SOURCE_SEARCH',f'provider={p.name}; purpose={q.purpose}; query={q.query_text[:300]}')
                    new_domains+=1 if is_new_domain else 0
                    continue

                if q.purpose not in OPPORTUNITY_PURPOSES or not _opportunity_hit_ok(q,h.title,h.snippet):
                    noise+=1
                    continue

                source,is_new_domain=get_or_create_discovered_source(db,h.url,'OPEN_OPPORTUNITY_SEARCH',f'provider={p.name}; purpose={q.purpose}; query={q.query_text[:300]}')
                new_domains+=1 if is_new_domain else 0
                _,is_new=upsert_candidate(db,h.url,h.title,h.snippet,source,f'{p.name}:{q.purpose}',q.query_text)
                new_candidates+=1 if is_new else 0

            now=datetime.utcnow(); run.completed_at=now; run.status='SUCCESS'; run.result_count=len(hits); run.new_domain_count=new_domains; run.new_candidate_count=new_candidates
            q.run_count=(q.run_count or 0)+1; q.result_count=(q.result_count or 0)+len(hits); q.new_source_count=(q.new_source_count or 0)+new_domains; q.noise_count=(q.noise_count or 0)+noise; q.last_run_at=now
            db.commit()
            return {'ok':True,'provider':p.name,'run_id':run.id,'results':len(hits),'new_domains':new_domains,'new_candidates':new_candidates,'noise':noise,'urls':urls}
        except Exception as e:
            last_error=str(e); run.completed_at=datetime.utcnow(); run.status='FAILED'; run.error=last_error[:1500]; db.commit()
            if provider is not None:
                return {'ok':False,'provider':p.name,'run_id':run.id,'error':last_error,'results':0}
    return {'ok':False,'error':last_error or 'ALL_PROVIDERS_FAILED','results':0}


def run_query_fanout(db: Session, q: DiscoveryQuery, limit: int|None=None):
    results=[]
    for p in providers(): results.append(run_query(db,q,provider=p,limit=limit))
    ok=[r for r in results if r.get('ok')]; all_urls=set()
    for r in ok: all_urls.update(r.get('urls',[]))
    return {'ok':bool(ok),'provider_runs':results,'providers_ok':len(ok),'providers_total':len(results),'results':sum(r.get('results',0) for r in ok),'unique_results':len(all_urls),'new_domains':sum(r.get('new_domains',0) for r in ok),'new_candidates':sum(r.get('new_candidates',0) for r in ok),'noise':sum(r.get('noise',0) for r in ok)}


def select_query_batch(db: Session, limit: int=8):
    return db.scalars(select(DiscoveryQuery).where(DiscoveryQuery.enabled==True).order_by(DiscoveryQuery.priority.desc(),DiscoveryQuery.last_run_at.asc()).limit(limit)).all()
