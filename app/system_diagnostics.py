from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .agent_models import AgentRun, AgentStep
from .config import (
    APP_NAME, ZERO_COST_MODE, DISCOVERY_ENABLED, AUTO_PROMOTE_TENDERS,
    DISCOVERY_SCAN_INTERVAL_MINUTES, OPEN_DISCOVERY_INTERVAL_MINUTES,
    SOURCE_HEALTH_AUDIT_INTERVAL_MINUTES, AUTONOMOUS_AGENTS_ENABLED,
    AUTONOMOUS_AGENT_INTERVAL_MINUTES,
)
from .models import Tender, Source, SourceScan, DiscoveryCandidate, DiscoveryQuery, SearchRun
from .discovery.orchestrator import run_known_sources, validate_candidates
from .discovery.source_health import audit_all_sources, health_snapshot
from .discovery.providers.router import provider_status
from .geography import geography_policy_summary
from .discovery import scheduler as scheduler_module

SENSITIVE_KEYS = ('token','secret','password','passwd','api_key','apikey','authorization','cookie','credential')


def _safe(value: Any):
    if isinstance(value, dict):
        out={}
        for k,v in value.items():
            out[k] = '[REDACTED]' if any(x in str(k).lower() for x in SENSITIVE_KEYS) else _safe(v)
        return out
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _source_productivity(db: Session):
    sources=db.scalars(select(Source).order_by(Source.priority, Source.trust_score.desc())).all()
    scans=db.scalars(select(SourceScan).order_by(SourceScan.started_at.desc())).all()
    by_source={}
    for scan in scans:
        bucket=by_source.setdefault(scan.source_id, {'scans':0,'items_seen':0,'new_candidates':0,'failures':0,'last_scan':None})
        bucket['scans']+=1
        bucket['items_seen']+=scan.items_seen or 0
        bucket['new_candidates']+=scan.new_candidates or 0
        bucket['failures']+=1 if scan.status=='FAILED' else 0
        if bucket['last_scan'] is None:
            bucket['last_scan']=scan.started_at.isoformat() if scan.started_at else None
    rows=[]
    for s in sources:
        m=by_source.get(s.id, {'scans':0,'items_seen':0,'new_candidates':0,'failures':0,'last_scan':None})
        if (s.useful_count or 0)>0:
            classification='PRODUCTIVE'
        elif m['items_seen']>0 or (s.candidate_count or 0)>0:
            classification='EMPTY_OR_UNQUALIFIED'
        elif s.health_status in {'FAILED','DEGRADED','BLOCKED','BLOCKED_BY_COST_POLICY','LOGIN_REQUIRED','RATE_LIMITED'}:
            classification='BROKEN_OR_BLOCKED'
        elif s.health_status=='HEALTHY':
            classification='REACHABLE_NOT_PRODUCTIVE'
        else:
            classification='UNKNOWN'
        rows.append({
            'source_id':s.id,'name':s.name,'domain':s.domain,'country':s.country,'source_type':s.source_type,
            'priority':s.priority,'health_status':s.health_status,'classification':classification,
            'scan_count':s.scan_count or 0,'success_count':s.success_count or 0,
            'candidate_count':s.candidate_count or 0,'useful_count':s.useful_count or 0,
            'observed_scans':m['scans'],'items_seen':m['items_seen'],'new_candidates':m['new_candidates'],
            'scan_failures':m['failures'],'last_scan':m['last_scan'],'last_error':(s.last_error or '')[:500] or None,
        })
    return rows


def _candidate_funnel(db: Session):
    candidates=db.scalars(select(DiscoveryCandidate)).all()
    status=Counter((c.validation_status or 'UNKNOWN') for c in candidates)
    rejected=Counter((c.rejection_reason or 'UNSPECIFIED') for c in candidates if c.validation_status in {'REJECTED','FETCH_FAILED'})
    evidence=[]
    recent=sorted(candidates,key=lambda c:c.created_at or datetime.min,reverse=True)[:50]
    for c in recent:
        evidence.append({
            'id':c.id,'title':c.title,'url':c.url,'source_id':c.source_id,'candidate_type':c.candidate_type,
            'discovery_method':c.discovery_method,'country_guess':c.country_guess,
            'opportunity_type':c.opportunity_type_guess,'procurement_score':c.procurement_score,
            'consultancy_score':c.consultancy_score,'confidence':c.confidence,
            'validation_status':c.validation_status,'rejection_reason':c.rejection_reason,'tender_id':c.tender_id,
            'created_at':c.created_at.isoformat() if c.created_at else None,
        })
    promoted=status.get('PROMOTED',0)
    validated=status.get('VALIDATED',0)+promoted
    return {
        'total_discovered':len(candidates),
        'new':status.get('NEW',0),
        'fetch_failed':status.get('FETCH_FAILED',0),
        'rejected':status.get('REJECTED',0),
        'social_leads':status.get('LEAD_REQUIRES_OFFICIAL_SOURCE',0),
        'validated_or_promoted':validated,
        'promoted':promoted,
        'saved_to_tenders':db.scalar(select(func.count(Tender.id)).where(Tender.discovery_candidate_id.is_not(None))) or 0,
        'status_counts':dict(status),'rejection_reasons':dict(rejected),'evidence':evidence,
    }


def _queries(db: Session):
    rows=db.scalars(select(DiscoveryQuery).order_by(DiscoveryQuery.last_run_at.desc().nullslast()).limit(100)).all()
    return [{
        'id':q.id,'query':q.query_text,'country':q.country,'sector':q.sector,'service':q.service,'purpose':q.purpose,
        'priority':q.priority,'enabled':q.enabled,'run_count':q.run_count,'result_count':q.result_count,
        'new_source_count':q.new_source_count,'valid_tender_count':q.valid_tender_count,'noise_count':q.noise_count,
        'last_run_at':q.last_run_at.isoformat() if q.last_run_at else None,
    } for q in rows]


def _search_runs(db: Session):
    rows=db.scalars(select(SearchRun).order_by(SearchRun.started_at.desc()).limit(50)).all()
    return [{
        'id':r.id,'provider':r.provider,'query':r.query_text,'status':r.status,'result_count':r.result_count,
        'new_domain_count':r.new_domain_count,'new_candidate_count':r.new_candidate_count,'error':(r.error or '')[:500] or None,
        'started_at':r.started_at.isoformat() if r.started_at else None,'completed_at':r.completed_at.isoformat() if r.completed_at else None,
    } for r in rows]


def _agents(db: Session):
    runs=db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(20)).all()
    steps=db.scalars(select(AgentStep).order_by(AgentStep.created_at.desc()).limit(100)).all()
    return {
        'runs':[{'id':r.id,'supervisor':r.supervisor,'goal':r.goal,'status':r.status,'mode':r.mode,'model':r.model,
                 'cycles_requested':r.cycles_requested,'cycles_completed':r.cycles_completed,'error':r.error,
                 'started_at':r.started_at.isoformat() if r.started_at else None,'completed_at':r.completed_at.isoformat() if r.completed_at else None}
                for r in runs],
        'recent_steps':[{'run_id':s.run_id,'agent_name':s.agent_name,'action':s.action,'tool_name':s.tool_name,'status':s.status,
                         'created_at':s.created_at.isoformat() if s.created_at else None} for s in steps]
    }


def _database_counts(db: Session):
    return {
        'sources':db.scalar(select(func.count(Source.id))) or 0,
        'source_scans':db.scalar(select(func.count(SourceScan.id))) or 0,
        'discovery_candidates':db.scalar(select(func.count(DiscoveryCandidate.id))) or 0,
        'queries':db.scalar(select(func.count(DiscoveryQuery.id))) or 0,
        'search_runs':db.scalar(select(func.count(SearchRun.id))) or 0,
        'tenders':db.scalar(select(func.count(Tender.id))) or 0,
        'qualified_tenders':db.scalar(select(func.count(Tender.id)).where(Tender.tender_status=='QUALIFIED')) or 0,
        'hard_rejected_tenders':db.scalar(select(func.count(Tender.id)).where(Tender.tender_status=='HARD_REJECTED')) or 0,
        'expired_tenders':db.scalar(select(func.count(Tender.id)).where(Tender.tender_status=='EXPIRED')) or 0,
        'auto_discovered_tenders':db.scalar(select(func.count(Tender.id)).where(Tender.discovery_candidate_id.is_not(None))) or 0,
    }


def _diagnostic_summary(report):
    db=report['database']
    funnel=report['pipeline_funnel']
    productivity=report['source_productivity']
    productive=sum(1 for s in productivity if s['classification']=='PRODUCTIVE')
    reachable_unproductive=sum(1 for s in productivity if s['classification']=='REACHABLE_NOT_PRODUCTIVE')
    broken=sum(1 for s in productivity if s['classification']=='BROKEN_OR_BLOCKED')
    if funnel['total_discovered']==0:
        bottleneck='DISCOVERY_NOT_PRODUCING_CANDIDATES'
        severity='CRITICAL'
    elif funnel['promoted']==0 and funnel['rejected']+funnel['fetch_failed']>0:
        bottleneck='VALIDATION_OR_FETCH_FILTERING_ALL_CANDIDATES'
        severity='CRITICAL'
    elif funnel['promoted']>0 and db['auto_discovered_tenders']==0:
        bottleneck='PROMOTION_TO_DATABASE_MISMATCH'
        severity='CRITICAL'
    elif db['auto_discovered_tenders']>0 and db['tenders']>0:
        bottleneck='NO_SINGLE_CRITICAL_BOTTLENECK_IDENTIFIED'
        severity='WARN' if productive==0 else 'OK'
    else:
        bottleneck='INSUFFICIENT_EVIDENCE'
        severity='WARN'
    return {
        'overall_status':severity,'main_bottleneck':bottleneck,'productive_sources':productive,
        'reachable_not_productive_sources':reachable_unproductive,'broken_or_blocked_sources':broken,
        'discovered_candidates':funnel['total_discovered'],'promoted_candidates':funnel['promoted'],
        'auto_discovered_tenders':db['auto_discovered_tenders'],'total_tenders':db['tenders'],
    }


def run_and_build_full_diagnostic(db: Session, source_limit: int=10, candidate_limit: int=20):
    started=datetime.utcnow()
    live={'health_audit':None,'known_source_scan':None,'validation':None,'errors':[]}
    try:
        live['health_audit']=audit_all_sources(db,max(1,min(source_limit,20)))
    except Exception as e:
        live['errors'].append(f'health_audit: {e}')
    try:
        live['known_source_scan']=run_known_sources(db,max(1,min(source_limit,20)))
    except Exception as e:
        live['errors'].append(f'known_source_scan: {e}')
    try:
        live['validation']=validate_candidates(db,max(1,min(candidate_limit,50)))
    except Exception as e:
        live['errors'].append(f'validation: {e}')

    scheduler_thread=getattr(scheduler_module,'_thread',None)
    report={
        'meta':{'report_type':'TENDER_INTELLIGENCE_FULL_DIAGNOSTIC','generated_at':datetime.utcnow().isoformat(),
                'app_name':APP_NAME,'zero_cost_mode':ZERO_COST_MODE,'discovery_enabled':DISCOVERY_ENABLED,
                'auto_promote_tenders':AUTO_PROMOTE_TENDERS,'live_run_started_at':started.isoformat()},
        'executive_summary':{},
        'live_diagnostic_run':live,
        'health_snapshot':health_snapshot(db),
        'source_productivity':_source_productivity(db),
        'pipeline_funnel':_candidate_funnel(db),
        'database':_database_counts(db),
        'queries':_queries(db),
        'search_runs':_search_runs(db),
        'agents':_agents(db),
        'scheduler':{
            'thread_alive':bool(scheduler_thread and scheduler_thread.is_alive()),
            'discovery_scan_interval_minutes':DISCOVERY_SCAN_INTERVAL_MINUTES,
            'open_discovery_interval_minutes':OPEN_DISCOVERY_INTERVAL_MINUTES,
            'source_health_audit_interval_minutes':SOURCE_HEALTH_AUDIT_INTERVAL_MINUTES,
            'autonomous_agents_enabled':AUTONOMOUS_AGENTS_ENABLED,
            'autonomous_agent_interval_minutes':AUTONOMOUS_AGENT_INTERVAL_MINUTES,
        },
        'providers':provider_status(),
        'geography_policy':geography_policy_summary(),
        'security':{'secrets_exported':False,'redaction_policy':'keys containing token/secret/password/api_key/authorization/cookie/credential are redacted'},
    }
    report['executive_summary']=_diagnostic_summary(report)
    return _safe(report)
