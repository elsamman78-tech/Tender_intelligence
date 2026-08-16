from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import BASE_DIR
from ..db import get_db
from ..discovery.country_coverage import country_coverage_snapshot
from ..agents.tools import ToolRuntime

router=APIRouter()
templates=Jinja2Templates(directory=str(BASE_DIR / 'app' / 'templates'))


@router.get('/coverage/countries', response_class=HTMLResponse)
def countries_home(request: Request, db: Session=Depends(get_db)):
    return templates.TemplateResponse(request=request,name='country_coverage.html',context={'coverage':country_coverage_snapshot(db)})


@router.post('/coverage/countries/discover')
def discover_country(country: str=Form(...), db: Session=Depends(get_db)):
    runtime=ToolRuntime(db)
    r1=runtime.tool_run_country_discovery(country,'SOURCE_SEARCH',2)
    r2=runtime.tool_run_country_discovery(country,'TENDER_SEARCH',2)
    if not r1.get('ok') and not r2.get('ok'):
        raise HTTPException(400,r1.get('error') or r2.get('error') or 'Country discovery failed')
    return RedirectResponse('/coverage/countries',303)


@router.get('/api/v1/coverage/countries')
def api_country_coverage(db: Session=Depends(get_db)):
    return country_coverage_snapshot(db)
