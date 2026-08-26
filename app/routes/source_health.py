import json
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import BASE_DIR
from ..db import get_db
from ..models import Source
from ..discovery.source_health import audit_all_sources, health_snapshot
from ..system_diagnostics import run_and_build_full_diagnostic

router=APIRouter()
templates=Jinja2Templates(directory=str(BASE_DIR / 'app' / 'templates'))


@router.get('/system/source-health', response_class=HTMLResponse)
def source_health_home(request: Request, db: Session=Depends(get_db)):
    rows=db.scalars(select(Source).order_by(Source.health_status,Source.priority,Source.trust_score.desc())).all()
    return templates.TemplateResponse(request=request,name='source_health.html',context={'snapshot':health_snapshot(db),'sources':rows})


@router.post('/system/source-health/audit')
def source_health_audit(limit: int=Form(30), db: Session=Depends(get_db)):
    audit_all_sources(db,max(1,min(int(limit),100)))
    return RedirectResponse('/system/source-health',303)


@router.post('/system/full-diagnostic/export')
def full_diagnostic_export(
    source_limit: int=Form(10), candidate_limit: int=Form(20), db: Session=Depends(get_db)
):
    report=run_and_build_full_diagnostic(
        db,
        source_limit=max(1,min(int(source_limit),20)),
        candidate_limit=max(1,min(int(candidate_limit),50)),
    )
    stamp=datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename=f'tender_intelligence_full_diagnostic_{stamp}.json'
    body=json.dumps(report,ensure_ascii=False,indent=2,default=str)
    return Response(
        content=body,
        media_type='application/json; charset=utf-8',
        headers={'Content-Disposition':f'attachment; filename="{filename}"'},
    )


@router.get('/api/v1/sources/health')
def api_source_health(db: Session=Depends(get_db)):
    return health_snapshot(db)


@router.post('/api/v1/sources/health/audit')
def api_source_health_audit(limit: int=30, db: Session=Depends(get_db)):
    return audit_all_sources(db,max(1,min(int(limit),100)))


@router.post('/api/v1/system/full-diagnostic')
def api_full_diagnostic(source_limit:int=10,candidate_limit:int=20,db:Session=Depends(get_db)):
    return run_and_build_full_diagnostic(
        db,
        source_limit=max(1,min(int(source_limit),20)),
        candidate_limit=max(1,min(int(candidate_limit),50)),
    )
