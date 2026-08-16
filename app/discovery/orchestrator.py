from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Source, DiscoveryCandidate
from ..config import DISCOVERY_QUERY_BATCH
from .source_registry import bootstrap_sources
from .query_engine import bootstrap_queries, select_query_batch, run_query
from .scanner import scan_source
from .candidates import validate_candidate
from .profiler import profile_source
from .file_discovery import index_candidate_documents


def bootstrap(db: Session):
    return {'sources_added':bootstrap_sources(db),'queries_added':bootstrap_queries(db)}

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
    qs=select_query_batch(db,limit or DISCOVERY_QUERY_BATCH)
    out={'queries':0,'results':0,'new_domains':0,'new_candidates':0,'failed':0,'providers':{}}
    for q in qs:
        r=run_query(db,q); out['queries']+=1; out['results']+=r.get('results',0); out['new_domains']+=r.get('new_domains',0); out['new_candidates']+=r.get('new_candidates',0)
        if not r.get('ok'): out['failed']+=1
        if r.get('provider'): out['providers'][r['provider']]=out['providers'].get(r['provider'],0)+1
    return out

def validate_candidates(db: Session, limit: int=50):
    candidates=db.scalars(select(DiscoveryCandidate).where(DiscoveryCandidate.validation_status.in_(['NEW','FETCH_FAILED'])).order_by(DiscoveryCandidate.confidence.desc()).limit(limit)).all()
    out={'reviewed':0,'promoted':0,'rejected':0,'fetch_failed':0}
    for c in candidates:
        r=validate_candidate(db,c); out['reviewed']+=1
        if r['status']=='PROMOTED': out['promoted']+=1
        elif r['status']=='REJECTED': out['rejected']+=1
        elif r['status']=='FETCH_FAILED': out['fetch_failed']+=1
    return out

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
    files=index_candidate_documents(db,500)
    profiles=profile_candidates(db,20)
    valid=validate_candidates(db,candidate_limit)
    return {'bootstrap':boot,'known_sources':known,'open_discovery':openr,'file_discovery':files,'source_profiles':profiles,'validation':valid}
