from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Source, DiscoveryCandidate
from ..config import DISCOVERY_QUERY_BATCH
from .source_registry import bootstrap_sources
from .query_engine import bootstrap_queries, run_query_fanout
from .query_expansion import bootstrap_deep_queries, select_balanced_query_batch
from .scanner import scan_source
from .candidates import validate_candidate
from .profiler import profile_source
from .file_discovery import index_candidate_documents


def bootstrap(db: Session):
    source_added=bootstrap_sources(db)
    query_added=bootstrap_queries(db)
    deep_added=bootstrap_deep_queries(db)
    return {'sources_added':source_added,'queries_added':query_added+deep_added,'deep_queries_added':deep_added}


def run_known_sources(db: Session, limit: int|None=None):
    q=select(Source).where(Source.enabled==1, Source.lifecycle_status.in_(['ACTIVE','VERIFIED'])).order_by(Source.priority.asc(),Source.trust_score.desc())
    sources=db.scalars(q).all()
    order={'CRITICAL':0,'HIGH':1,'MEDIUM':2,'LOW':3,'EXPERIMENTAL':4}
    sources=sorted(sources,key=lambda x:(order.get(x.priority,9),-(x.trust_score or 0)))
    if limit: sources=sources[:limit]
    summary={'sources':0,'scans':0,'new_candidates':0,'failed':0}
    for s in sources:
        summary['sources']+=1
        scans=scan_source(db,s); summary['scans']+=len(scans)
        for x in scans:
            summary['new_candidates']+=x.new_candidates or 0
            if x.status=='FAILED': summary['failed']+=1
    return summary


def run_open_discovery(db: Session, limit: int|None=None):
    qs=select_balanced_query_batch(db,limit or DISCOVERY_QUERY_BATCH)
    out={'queries':0,'provider_runs':0,'results':0,'unique_results':0,'new_domains':0,'new_candidates':0,'failed':0,'providers':{},'purposes':{}}
    for q in qs:
        r=run_query_fanout(db,q)
        out['queries']+=1
        out['results']+=r.get('results',0); out['unique_results']+=r.get('unique_results',0)
        out['new_domains']+=r.get('new_domains',0); out['new_candidates']+=r.get('new_candidates',0)
        purpose_bucket=out['purposes'].setdefault(q.purpose,{'queries':0,'results':0,'new_candidates':0})
        purpose_bucket['queries']+=1
        purpose_bucket['results']+=r.get('results',0)
        purpose_bucket['new_candidates']+=r.get('new_candidates',0)
        for pr in r.get('provider_runs',[]):
            out['provider_runs']+=1
            name=pr.get('provider','UNKNOWN')
            bucket=out['providers'].setdefault(name,{'runs':0,'ok':0,'results':0,'new_candidates':0})
            bucket['runs']+=1
            if pr.get('ok'): bucket['ok']+=1
            bucket['results']+=pr.get('results',0); bucket['new_candidates']+=pr.get('new_candidates',0)
        if not r.get('ok'): out['failed']+=1
    return out


def validate_candidates(db: Session, limit: int=50, include_fetch_failed: bool=True):
    statuses=['NEW','FETCH_FAILED'] if include_fetch_failed else ['NEW']
    candidates=db.scalars(select(DiscoveryCandidate).where(DiscoveryCandidate.validation_status.in_(statuses)).order_by(DiscoveryCandidate.confidence.desc()).limit(limit)).all()
    out={'reviewed':0,'promoted':0,'rejected':0,'fetch_failed':0,'social_leads':0}
    for c in candidates:
        r=validate_candidate(db,c); out['reviewed']+=1
        if r['status']=='PROMOTED': out['promoted']+=1
        elif r['status']=='REJECTED': out['rejected']+=1
        elif r['status']=='FETCH_FAILED': out['fetch_failed']+=1
        elif r['status']=='LEAD_REQUIRES_OFFICIAL_SOURCE': out['social_leads']+=1
    return out


def validate_new_candidates_until_idle(db: Session, batch_size: int=50, max_total: int=1000):
    """Drain NEW candidates created by the current discovery cycle.

    FETCH_FAILED records are not retried in this loop to avoid repeatedly hammering a blocked
    portal. They remain available for the explicit manual validation/retry action.
    """
    total={'reviewed':0,'promoted':0,'rejected':0,'fetch_failed':0,'social_leads':0,'batches':0,'remaining_new':0}
    while total['reviewed'] < max_total:
        remaining=max_total-total['reviewed']
        r=validate_candidates(db,min(batch_size,remaining),include_fetch_failed=False)
        if r['reviewed']==0:
            break
        total['batches']+=1
        for key in ('reviewed','promoted','rejected','fetch_failed','social_leads'):
            total[key]+=r.get(key,0)
    total['remaining_new']=db.scalar(select(DiscoveryCandidate).where(DiscoveryCandidate.validation_status=='NEW').with_only_columns(__import__('sqlalchemy').func.count(DiscoveryCandidate.id))) or 0
    return total


def profile_candidates(db: Session, limit: int=20):
    sources=db.scalars(select(Source).where(Source.lifecycle_status=='CANDIDATE',Source.enabled==1).order_by(Source.created_at.desc()).limit(limit)).all()
    out={'profiled':0,'verified':0,'failed':0}
    for s in sources:
        r=profile_source(db,s); out['profiled']+=1
        if r.get('ok'): out['verified']+=1
        else: out['failed']+=1
    return out


def run_full_cycle(db: Session, source_limit: int|None=None, query_limit: int|None=None, candidate_limit: int=50):
    boot=bootstrap(db)
    known=run_known_sources(db,source_limit)
    openr=run_open_discovery(db,query_limit)
    files=index_candidate_documents(db,1000)
    profiles=profile_candidates(db,30)
    valid=validate_new_candidates_until_idle(db,batch_size=max(25,candidate_limit),max_total=1000)
    return {'bootstrap':boot,'known_sources':known,'open_discovery':openr,'file_discovery':files,'source_profiles':profiles,'validation':valid}
