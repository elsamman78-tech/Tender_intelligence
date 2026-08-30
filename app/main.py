from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .config import APP_NAME, BASE_DIR, UPLOAD_DIR, ZERO_COST_MODE, MAX_UPLOAD_MB, DISCOVERY_ENABLED
from .db import Base, engine, get_db
from .models import Tender, Source, SourceChannel, SourceScan, DiscoveryCandidate, DiscoveryQuery, SearchRun
from .migrations import migrate_additive
from .services.pdf_parser import extract_pdf
from .services.analysis import run_analysis
from .services.participation import analyze_participation
from .services.web_reader import read_url
from .services.dedup import fingerprint as make_fingerprint
from .geography import geography_policy_summary
from .discovery.agent_reach import doctor as agent_reach_doctor
from .services.ollama import health as ollama_health
from .discovery.orchestrator import bootstrap as discovery_bootstrap, run_known_sources, run_open_discovery, validate_candidates, profile_candidates, run_full_cycle
from .discovery.candidates import validate_candidate
from .discovery.profiler import profile_source
from .discovery.scanner import scan_source
from .discovery.scheduler import start_scheduler, stop_scheduler
from .discovery.providers.router import provider_status
from .discovery.coverage import coverage_snapshot, run_coverage_benchmark
from .routes.agents import router as agents_router
from .routes.source_health import router as source_health_router

Base.metadata.create_all(bind=engine)
migrate_additive()
Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME)
templates = Jinja2Templates(directory=str(BASE_DIR / 'app' / 'templates'))
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'app' / 'static')), name='static')
app.include_router(agents_router)
app.include_router(source_health_router)

@app.on_event('startup')
def _startup():
    if DISCOVERY_ENABLED:
        start_scheduler()

@app.on_event('shutdown')
def _shutdown():
    stop_scheduler()

@app.get('/', response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    discovery_bootstrap(db)
    visible_statuses=['QUALIFIED','REVIEW_REQUIRED']
    tenders = db.scalars(
        select(Tender).where(Tender.tender_status.in_(visible_statuses)).order_by(Tender.created_at.desc()).limit(100)
    ).all()
    total = db.scalar(select(func.count(Tender.id)).where(Tender.tender_status.in_(visible_statuses))) or 0
    direct = db.scalar(select(func.count(Tender.id)).where(Tender.tender_status.in_(visible_statuses), Tender.bid_route.in_(['DIRECT','DIRECT_LOCAL']))) or 0
    partner = db.scalar(select(func.count(Tender.id)).where(Tender.tender_status.in_(visible_statuses), Tender.bid_route.in_(['JV','LOCAL_ASSOCIATION','SUBCONSULTANT','SAUDI_DB_PARTNER']))) or 0
    saudi_db = db.scalar(select(func.count(Tender.id)).where(Tender.tender_status.in_(visible_statuses), Tender.bid_route=='SAUDI_DB_PARTNER')) or 0
    review = db.scalar(select(func.count(Tender.id)).where(Tender.tender_status=='REVIEW_REQUIRED')) or 0
    urgent = db.scalar(select(func.count(Tender.id)).where(Tender.tender_status.in_(visible_statuses), Tender.urgency_level.in_(['URGENT','CRITICAL']))) or 0
    return templates.TemplateResponse(request=request, name='dashboard.html', context={
        'tenders':tenders,
        'kpis':{'total':total,'direct':direct,'partner':partner,'saudi_db':saudi_db,'review':review,'urgent':urgent},
        'zero_cost':ZERO_COST_MODE,
        'geography':geography_policy_summary(),
    })

@app.get('/tenders/new', response_class=HTMLResponse)
def new_tender(request: Request):
    return templates.TemplateResponse(request=request, name='new_tender.html', context={})

@app.post('/tenders/new')
async def create_tender(
    request: Request,
    title: str = Form(...), client_name: str = Form(''), project_country: str = Form(''), source_url: str = Form(''),
    external_reference: str = Form(''), submission_deadline: str = Form(''), pasted_text: str = Form(''),
    use_ai: bool = Form(False), file: UploadFile | None = File(None), db: Session = Depends(get_db)
):
    text = pasted_text.strip(); document_name = None
    if source_url and not text:
        try: text = read_url(source_url)[:200000]
        except Exception as e: text = f'[URL fetch failed: {e}]'
    if file and file.filename:
        suffix = Path(file.filename).suffix.lower()
        if suffix != '.pdf': raise HTTPException(400, 'Manual upload currently accepts PDF only; discovery can index other document links.')
        dest = UPLOAD_DIR / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{Path(file.filename).name}"
        size = 0
        with dest.open('wb') as out:
            while chunk := await file.read(1024*1024):
                size += len(chunk)
                if size > MAX_UPLOAD_MB * 1024 * 1024:
                    out.close(); dest.unlink(missing_ok=True); raise HTTPException(413, 'File too large')
                out.write(chunk)
        document_name = file.filename; parsed = extract_pdf(dest); text = (text + '\n' + parsed['text']).strip()
    deadline = None
    if submission_deadline:
        try: deadline = datetime.strptime(submission_deadline, '%Y-%m-%d').date()
        except ValueError: raise HTTPException(400, 'Invalid deadline')
    fp = make_fingerprint(title=title, client=client_name, country=project_country, deadline=deadline, reference=external_reference)
    existing = db.scalar(select(Tender).where(Tender.fingerprint == fp))
    if existing: return RedirectResponse(f'/tenders/{existing.id}', status_code=303)
    result = run_analysis(project_country or None, deadline, text, use_ai=use_ai)
    participation = analyze_participation(project_country or None, text)
    disallowed = participation['eligibility_status'] in {'NOT_ELIGIBLE_LANGUAGE','LOCAL_RESTRICTION'}
    status = 'HARD_REJECTED' if (result['hard_reject'] or disallowed) else ('REVIEW_REQUIRED' if deadline is None or participation['eligibility_status']=='ELIGIBILITY_TO_VERIFY' else 'QUALIFIED')
    tender = Tender(
        title=title.strip(), fingerprint=fp, client_name=client_name.strip() or None, project_country=project_country.strip() or None,
        source_url=source_url.strip() or None, external_reference=external_reference.strip() or None, submission_deadline=deadline,
        raw_text=text[:1000000] or None, document_name=document_name, tender_status=status,
        bid_route=participation['bid_route'],eligibility_status=participation['eligibility_status'],
        partner_requirement=participation['partner_requirement'],submission_language=participation['submission_language'],
        language_status=participation['language_status'],participation_notes=participation['notes'],source_evidence_type='MANUAL',
        **{k:v for k,v in result.items() if k != 'hard_reject'}
    )
    db.add(tender); db.commit(); db.refresh(tender)
    return RedirectResponse(f'/tenders/{tender.id}', status_code=303)

@app.get('/tenders/{tender_id}', response_class=HTMLResponse)
def tender_detail(tender_id: int, request: Request, db: Session = Depends(get_db)):
    t = db.get(Tender, tender_id)
    if not t: raise HTTPException(404)
    return templates.TemplateResponse(request=request, name='detail.html', context={'t':t})

@app.post('/tenders/{tender_id}/decision')
def set_decision(tender_id: int, decision: str = Form(...), db: Session = Depends(get_db)):
    if decision not in {'BID','NO_BID','HOLD','UNDECIDED'}: raise HTTPException(400)
    t = db.get(Tender, tender_id)
    if not t: raise HTTPException(404)
    t.bd_decision = decision; db.commit(); return RedirectResponse(f'/tenders/{tender_id}', status_code=303)

# ---------------- Discovery V4 ----------------
@app.get('/discovery', response_class=HTMLResponse)
def discovery_home(request: Request, db: Session = Depends(get_db)):
    discovery_bootstrap(db)
    noise_reasons=['SOCIAL_SOURCE_BLOCKED','NON_ACTIONABLE_NEWS_OR_PAGE','LOW_RELEVANCE','CONTENT_NOT_ENGINEERING_PROCUREMENT']
    k={
        'sources':db.scalar(select(func.count(Source.id))) or 0,
        'healthy':db.scalar(select(func.count(Source.id)).where(Source.health_status=='HEALTHY')) or 0,
        'source_candidates':db.scalar(select(func.count(Source.id)).where(Source.lifecycle_status=='CANDIDATE')) or 0,
        'candidates':db.scalar(select(func.count(DiscoveryCandidate.id))) or 0,
        'new_candidates':db.scalar(select(func.count(DiscoveryCandidate.id)).where(DiscoveryCandidate.validation_status=='NEW')) or 0,
        'promoted':db.scalar(select(func.count(DiscoveryCandidate.id)).where(DiscoveryCandidate.validation_status=='PROMOTED')) or 0,
        'noise_rejected':db.scalar(select(func.count(DiscoveryCandidate.id)).where(DiscoveryCandidate.rejection_reason.in_(noise_reasons))) or 0,
        'queries':db.scalar(select(func.count(DiscoveryQuery.id)).where(DiscoveryQuery.enabled==True)) or 0,
        'runs':db.scalar(select(func.count(SearchRun.id))) or 0,
    }
    recent=db.scalars(
        select(DiscoveryCandidate).where(DiscoveryCandidate.candidate_type!='NOISE').order_by(DiscoveryCandidate.created_at.desc()).limit(30)
    ).all()
    return templates.TemplateResponse(request=request, name='discovery.html', context={
        'k':k,'recent':recent,'zero_cost':ZERO_COST_MODE,'enabled':DISCOVERY_ENABLED,
        'providers':provider_status(),'coverage':coverage_snapshot(db),'geography':geography_policy_summary()
    })

@app.post('/discovery/bootstrap')
def discovery_bootstrap_route(db: Session=Depends(get_db)):
    discovery_bootstrap(db); return RedirectResponse('/discovery',303)

@app.post('/discovery/run-known')
def run_known_route(db: Session=Depends(get_db)):
    run_known_sources(db); return RedirectResponse('/discovery',303)

@app.post('/discovery/run-open')
def run_open_route(db: Session=Depends(get_db)):
    run_open_discovery(db); return RedirectResponse('/discovery',303)

@app.post('/discovery/validate')
def validate_route(db: Session=Depends(get_db)):
    validate_candidates(db,50); return RedirectResponse('/discovery',303)

@app.post('/discovery/run-full')
def run_full_route(db: Session=Depends(get_db)):
    run_full_cycle(db,source_limit=20,query_limit=8,candidate_limit=50); return RedirectResponse('/discovery',303)

@app.post('/discovery/coverage/run')
def coverage_run_route(db: Session=Depends(get_db)):
    run_coverage_benchmark(db,query_limit=5,result_limit=10)
    return RedirectResponse('/discovery',303)

@app.get('/sources', response_class=HTMLResponse)
def sources_list(request: Request, db: Session=Depends(get_db)):
    discovery_bootstrap(db)
    rows=db.scalars(select(Source).order_by(Source.trust_score.desc(),Source.created_at.desc())).all()
    return templates.TemplateResponse(request=request, name='sources.html', context={'sources':rows,'zero_cost':ZERO_COST_MODE})

@app.get('/sources/{source_id}', response_class=HTMLResponse)
def source_detail(source_id:int,request:Request,db:Session=Depends(get_db)):
    s=db.get(Source,source_id)
    if not s: raise HTTPException(404)
    scans=db.scalars(select(SourceScan).where(SourceScan.source_id==source_id).order_by(SourceScan.started_at.desc()).limit(30)).all()
    return templates.TemplateResponse(request=request, name='source_detail.html', context={'s':s,'scans':scans})

@app.post('/sources/{source_id}/profile')
def source_profile_route(source_id:int,db:Session=Depends(get_db)):
    s=db.get(Source,source_id)
    if not s: raise HTTPException(404)
    profile_source(db,s); return RedirectResponse(f'/sources/{source_id}',303)

@app.post('/sources/{source_id}/scan')
def source_scan_route(source_id:int,db:Session=Depends(get_db)):
    s=db.get(Source,source_id)
    if not s: raise HTTPException(404)
    scan_source(db,s); return RedirectResponse(f'/sources/{source_id}',303)

@app.post('/sources/{source_id}/decision')
def source_decision(source_id:int,decision:str=Form(...),db:Session=Depends(get_db)):
    s=db.get(Source,source_id)
    if not s: raise HTTPException(404)
    if decision=='APPROVE': s.lifecycle_status='ACTIVE'; s.enabled=1
    elif decision=='REJECT': s.lifecycle_status='REJECTED'; s.enabled=0
    elif decision=='PAUSE': s.lifecycle_status='PAUSED'; s.enabled=0
    else: raise HTTPException(400)
    db.commit(); return RedirectResponse(f'/sources/{source_id}',303)

@app.post('/candidates/{candidate_id}/validate')
def candidate_validate(candidate_id:int,db:Session=Depends(get_db)):
    c=db.get(DiscoveryCandidate,candidate_id)
    if not c: raise HTTPException(404)
    validate_candidate(db,c) if c.validation_status in {'NEW','FETCH_FAILED'} else None
    return RedirectResponse('/discovery',303)

@app.get('/api/v1/discovery/status')
def discovery_status(db:Session=Depends(get_db)):
    return {
        'enabled':DISCOVERY_ENABLED,'zero_cost_mode':ZERO_COST_MODE,'geography':geography_policy_summary(),'providers':provider_status(),
        'sources':db.scalar(select(func.count(Source.id))) or 0,
        'source_candidates':db.scalar(select(func.count(Source.id)).where(Source.lifecycle_status=='CANDIDATE')) or 0,
        'opportunity_candidates':db.scalar(select(func.count(DiscoveryCandidate.id))) or 0,
        'promoted':db.scalar(select(func.count(DiscoveryCandidate.id)).where(DiscoveryCandidate.validation_status=='PROMOTED')) or 0
    }

@app.post('/api/v1/discovery/run')
def discovery_run_api(db:Session=Depends(get_db)):
    return run_full_cycle(db,source_limit=20,query_limit=8,candidate_limit=50)

@app.get('/api/v1/discovery/coverage')
def discovery_coverage_api(db:Session=Depends(get_db)):
    return coverage_snapshot(db)

@app.post('/api/v1/discovery/coverage/benchmark')
def discovery_coverage_benchmark_api(query_limit:int=5,result_limit:int=10,db:Session=Depends(get_db)):
    return run_coverage_benchmark(db,max(1,min(query_limit,20)),max(1,min(result_limit,30)))

# ---------------- System ----------------
@app.get('/system/doctor', response_class=HTMLResponse)
def doctor(request: Request):
    ar = agent_reach_doctor(); ollama = ollama_health()
    return templates.TemplateResponse(request=request, name='doctor.html', context={'agent_reach':ar,'ollama':ollama,'zero_cost':ZERO_COST_MODE,'discovery_enabled':DISCOVERY_ENABLED,'providers':provider_status()})

@app.get('/api/v1/health')
def api_health():
    ar = agent_reach_doctor(timeout=8)
    return JSONResponse({'ok':True,'zero_cost_mode':ZERO_COST_MODE,'discovery_enabled':DISCOVERY_ENABLED,'providers':provider_status(),'geography':geography_policy_summary(),'ollama':ollama_health(),'agent_reach':{'installed':ar.installed,'enabled':ar.enabled,'ok':ar.ok}})
