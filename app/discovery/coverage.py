from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..models import DiscoveryQuery, SearchRun, SearchResult
from .providers.router import providers, provider_status
from .query_engine import run_query


def coverage_snapshot(db: Session) -> dict:
    rows=db.execute(
        select(
            SearchRun.provider,
            func.count(SearchRun.id),
            func.sum(SearchRun.result_count),
            func.sum(SearchRun.new_domain_count),
            func.sum(SearchRun.new_candidate_count),
        ).group_by(SearchRun.provider)
    ).all()
    stats=[]
    for provider,runs,results,new_domains,new_candidates in rows:
        failed=db.scalar(select(func.count(SearchRun.id)).where(SearchRun.provider==provider,SearchRun.status=='FAILED')) or 0
        stats.append({
            'provider':provider,'runs':runs or 0,'successful_runs':(runs or 0)-failed,'failed_runs':failed,
            'results':results or 0,'new_domains':new_domains or 0,'new_candidates':new_candidates or 0,
        })
    stats.sort(key=lambda x:(x['new_candidates'],x['new_domains'],x['results']),reverse=True)
    return {'providers':provider_status(),'stats':stats}


def run_coverage_benchmark(db: Session, query_limit: int=5, result_limit: int=10) -> dict:
    ps=providers()
    qs=db.scalars(
        select(DiscoveryQuery).where(
            DiscoveryQuery.enabled==True,
            DiscoveryQuery.purpose.in_(['TENDER_SEARCH','SOURCE_SEARCH','PRIVATE_SOURCE_SEARCH'])
        ).order_by(DiscoveryQuery.priority.desc(),DiscoveryQuery.last_run_at.asc()).limit(query_limit)
    ).all()
    by_provider=defaultdict(lambda:{'runs':0,'ok':0,'results':0,'new_domains':0,'new_candidates':0,'urls':set(),'domains':set()})
    for q in qs:
        for p in ps:
            r=run_query(db,q,provider=p,limit=result_limit)
            b=by_provider[p.name]; b['runs']+=1
            if r.get('ok'): b['ok']+=1
            b['results']+=r.get('results',0); b['new_domains']+=r.get('new_domains',0); b['new_candidates']+=r.get('new_candidates',0)
            for u in r.get('urls',[]): b['urls'].add(u)
            run_id=r.get('run_id')
            if run_id:
                for d in db.scalars(select(SearchResult.domain).where(SearchResult.run_id==run_id)).all():
                    if d: b['domains'].add(d)
    all_sets={k:v['urls'] for k,v in by_provider.items()}
    union=set().union(*all_sets.values()) if all_sets else set()
    comparison=[]
    for name,b in by_provider.items():
        others=set().union(*(s for n,s in all_sets.items() if n!=name)) if len(all_sets)>1 else set()
        unique_to_provider=b['urls']-others
        comparison.append({
            'provider':name,'runs':b['runs'],'ok_runs':b['ok'],'results':b['results'],
            'distinct_urls':len(b['urls']),'distinct_domains':len(b['domains']),
            'unique_urls_vs_others':len(unique_to_provider),'new_domains':b['new_domains'],
            'new_candidates':b['new_candidates'],
            'share_of_union_pct':round((len(b['urls'])/len(union)*100),1) if union else 0.0,
        })
    comparison.sort(key=lambda x:(x['unique_urls_vs_others'],x['new_candidates'],x['distinct_urls']),reverse=True)
    return {'queries_tested':len(qs),'providers_tested':len(ps),'union_distinct_urls':len(union),'comparison':comparison}
