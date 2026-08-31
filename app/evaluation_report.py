from __future__ import annotations

from collections import Counter
from datetime import datetime
from io import BytesIO, StringIO
import csv
import json
import zipfile

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Tender, Source, SourceScan, DiscoveryCandidate, DiscoveryQuery, SearchRun
from .discovery.country_coverage import country_coverage_snapshot
from .discovery.providers.router import provider_status
from .geography import geography_policy_summary


def _dt(v):
    return v.isoformat() if v else None


def _sources(db: Session):
    rows=db.scalars(select(Source).order_by(Source.priority,Source.trust_score.desc())).all()
    return [{
        'id':s.id,'name':s.name,'domain':s.domain,'country':s.country,'source_type':s.source_type,
        'lifecycle_status':s.lifecycle_status,'health_status':s.health_status,'priority':s.priority,
        'trust_score':s.trust_score,'enabled':s.enabled,'requires_login':s.requires_login,
        'scan_count':s.scan_count,'success_count':s.success_count,'candidate_count':s.candidate_count,
        'useful_count':s.useful_count,'last_scan_at':_dt(s.last_scan_at),'last_success_at':_dt(s.last_success_at),
        'last_error':(s.last_error or '')[:1000] or None,'base_url':s.base_url,
    } for s in rows]


def _scans(db: Session):
    rows=db.scalars(select(SourceScan).order_by(SourceScan.started_at.desc()).limit(500)).all()
    return [{
        'id':x.id,'source_id':x.source_id,'channel_id':x.channel_id,'status':x.status,'http_status':x.http_status,
        'items_seen':x.items_seen,'new_candidates':x.new_candidates,'error':(x.error or '')[:1000] or None,
        'started_at':_dt(x.started_at),'completed_at':_dt(x.completed_at),
    } for x in rows]


def _candidates(db: Session):
    rows=db.scalars(select(DiscoveryCandidate).order_by(DiscoveryCandidate.created_at.desc()).limit(1000)).all()
    return [{
        'id':c.id,'title':c.title,'url':c.url,'source_id':c.source_id,'country':c.country_guess,
        'candidate_type':c.candidate_type,'opportunity_type':c.opportunity_type_guess,
        'method':c.discovery_method,'detail':c.discovery_detail,'procurement_score':c.procurement_score,
        'consultancy_score':c.consultancy_score,'confidence':c.confidence,'validation_status':c.validation_status,
        'rejection_reason':c.rejection_reason,'tender_id':c.tender_id,'created_at':_dt(c.created_at),
    } for c in rows]


def _tenders(db: Session):
    rows=db.scalars(select(Tender).order_by(Tender.created_at.desc()).limit(1000)).all()
    return [{
        'id':t.id,'title':t.title,'client':t.client_name,'country':t.project_country,'reference':t.external_reference,
        'publication_date':str(t.publication_date) if t.publication_date else None,'publication_age_days':t.publication_age_days,
        'deadline':str(t.submission_deadline) if t.submission_deadline else None,'business_days_remaining':t.business_days_remaining,
        'status':t.tender_status,'scope':t.scope_classification,'bid_route':t.bid_route,'eligibility':t.eligibility_status,
        'partner_requirement':t.partner_requirement,'submission_language':t.submission_language,
        'evidence_type':t.source_evidence_type,'discovery_method':t.discovery_method,'score':t.overall_score,
        'recommendation':t.recommendation,'hard_reject_reason':t.hard_reject_reason,'source_url':t.source_url,
        'created_at':_dt(t.created_at),
    } for t in rows]


def _queries(db: Session):
    rows=db.scalars(select(DiscoveryQuery).order_by(DiscoveryQuery.priority.desc())).all()
    return [{
        'id':q.id,'query':q.query_text,'country':q.country,'purpose':q.purpose,'priority':q.priority,'enabled':q.enabled,
        'run_count':q.run_count,'result_count':q.result_count,'new_source_count':q.new_source_count,
        'valid_tender_count':q.valid_tender_count,'noise_count':q.noise_count,'last_run_at':_dt(q.last_run_at),
    } for q in rows]


def _search_runs(db: Session):
    rows=db.scalars(select(SearchRun).order_by(SearchRun.started_at.desc()).limit(300)).all()
    return [{
        'id':r.id,'provider':r.provider,'query':r.query_text,'status':r.status,'result_count':r.result_count,
        'new_domain_count':r.new_domain_count,'new_candidate_count':r.new_candidate_count,'error':(r.error or '')[:1000] or None,
        'started_at':_dt(r.started_at),'completed_at':_dt(r.completed_at),
    } for r in rows]


def build_evaluation_snapshot(db: Session) -> dict:
    sources=_sources(db); scans=_scans(db); candidates=_candidates(db); tenders=_tenders(db)
    rejection_counts=Counter(x['rejection_reason'] or 'NONE' for x in candidates if x['validation_status'] in {'REJECTED','FETCH_FAILED'})
    candidate_status=Counter(x['validation_status'] or 'UNKNOWN' for x in candidates)
    source_health=Counter(x['health_status'] or 'UNKNOWN' for x in sources)
    tender_status=Counter(x['status'] or 'UNKNOWN' for x in tenders)
    report={
        'meta':{
            'report_type':'TENDER_INTELLIGENCE_EVALUATION_SNAPSHOT_V1',
            'generated_at':datetime.utcnow().isoformat(),
            'snapshot_only':True,
            'note':'No scan/search/validation is triggered by this export.',
        },
        'summary':{
            'sources':len(sources),'candidates':len(candidates),'tenders':len(tenders),
            'qualified':tender_status.get('QUALIFIED',0),'review_required':tender_status.get('REVIEW_REQUIRED',0),
            'promoted_candidates':candidate_status.get('PROMOTED',0),'rejected_candidates':candidate_status.get('REJECTED',0),
            'fetch_failed_candidates':candidate_status.get('FETCH_FAILED',0),'source_health':dict(source_health),
            'candidate_status':dict(candidate_status),'rejection_reasons':dict(rejection_counts),
        },
        'providers':provider_status(),
        'geography_policy':geography_policy_summary(),
        'coverage':country_coverage_snapshot(db),
        'sources':sources,'source_scans':scans,'candidates':candidates,'tenders':tenders,
        'queries':_queries(db),'search_runs':_search_runs(db),
        'privacy':{'secrets_included':False,'raw_tender_text_included':False,'environment_variables_included':False},
    }
    return report


def _csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b''
    fields=[]
    for row in rows:
        for k in row.keys():
            if k not in fields: fields.append(k)
    s=StringIO(newline='')
    w=csv.DictWriter(s,fieldnames=fields,extrasaction='ignore'); w.writeheader()
    for row in rows: w.writerow(row)
    return s.getvalue().encode('utf-8-sig')


def _summary_markdown(report: dict) -> str:
    s=report['summary']; cov=report['coverage']['counts']
    rejection=s.get('rejection_reasons',{})
    top_rejections=sorted(rejection.items(),key=lambda x:x[1],reverse=True)[:12]
    lines=[
        '# Tender Intelligence - Evaluation Snapshot', '',
        f"Generated: {report['meta']['generated_at']} UTC", '',
        '## Executive numbers',
        f"- Sources: {s['sources']}",f"- Candidates: {s['candidates']}",f"- Tenders: {s['tenders']}",
        f"- Qualified: {s['qualified']}",f"- Review required: {s['review_required']}",
        f"- Promoted candidates: {s['promoted_candidates']}",f"- Rejected candidates: {s['rejected_candidates']}",
        f"- Fetch failed: {s['fetch_failed_candidates']}", '',
        '## Country coverage',
        f"- Target: {cov['target']}",f"- Covered: {cov['covered']}",f"- Partial: {cov['partial']}",f"- Gaps: {cov['gaps']}", '',
        '## Top rejection reasons',
    ]
    if top_rejections:
        lines.extend(f'- {k}: {v}' for k,v in top_rejections)
    else:
        lines.append('- None yet')
    lines += ['', '## Files in this bundle',
              '- evaluation_report.json: complete structured snapshot',
              '- sources.csv / source_scans.csv: source health and productivity evidence',
              '- candidates.csv: discovered candidates, scores and rejection reasons',
              '- tenders.csv: promoted/qualified opportunities and participation route',
              '- coverage.csv: country-by-country coverage',
              '- queries.csv / search_runs.csv: discovery performance and provider errors',
              '', 'This export does not run a new scan and does not include secrets or raw tender text.']
    return '\n'.join(lines)+'\n'


def build_evaluation_zip(db: Session) -> tuple[bytes,str]:
    report=build_evaluation_snapshot(db)
    stamp=datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename=f'Tender_Intelligence_Evaluation_{stamp}.zip'
    buf=BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('README_EVALUATION.md',_summary_markdown(report).encode('utf-8'))
        z.writestr('evaluation_report.json',json.dumps(report,ensure_ascii=False,indent=2,default=str).encode('utf-8'))
        z.writestr('sources.csv',_csv_bytes(report['sources']))
        z.writestr('source_scans.csv',_csv_bytes(report['source_scans']))
        z.writestr('candidates.csv',_csv_bytes(report['candidates']))
        z.writestr('tenders.csv',_csv_bytes(report['tenders']))
        z.writestr('coverage.csv',_csv_bytes(report['coverage']['countries']))
        z.writestr('queries.csv',_csv_bytes(report['queries']))
        z.writestr('search_runs.csv',_csv_bytes(report['search_runs']))
    return buf.getvalue(),filename
