from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import BASE_DIR
from ..db import get_db
from ..models import Source
from ..discovery.source_health import audit_all_sources, health_snapshot

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


@router.get('/api/v1/sources/health')
def api_source_health(db: Session=Depends(get_db)):
    return health_snapshot(db)


@router.post('/api/v1/sources/health/audit')
def api_source_health_audit(limit: int=30, db: Session=Depends(get_db)):
    return audit_all_sources(db,max(1,min(int(limit),100)))
