from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import BASE_DIR, AUTONOMOUS_AGENTS_ENABLED, AUTONOMOUS_AGENT_MAX_CYCLES, AUTONOMOUS_AGENT_INTERVAL_MINUTES
from ..db import get_db
from ..agents.loop import agent_health, run_discovery_supervisor, recent_agent_runs, agent_run_detail

router=APIRouter()
templates=Jinja2Templates(directory=str(BASE_DIR / 'app' / 'templates'))


@router.get('/agents', response_class=HTMLResponse)
def agents_home(request: Request, db: Session=Depends(get_db)):
    return templates.TemplateResponse(request=request,name='agents.html',context={
        'enabled':AUTONOMOUS_AGENTS_ENABLED,
        'agent_health':agent_health(),
        'max_cycles':AUTONOMOUS_AGENT_MAX_CYCLES,
        'interval_minutes':AUTONOMOUS_AGENT_INTERVAL_MINUTES,
        'runs':recent_agent_runs(db,15),
    })


@router.post('/agents/run')
def agents_run(goal: str=Form('Improve worldwide engineering consultancy tender coverage and verify high-value opportunities.'),
               cycles: int=Form(1), db: Session=Depends(get_db)):
    if not AUTONOMOUS_AGENTS_ENABLED:
        raise HTTPException(409,'Autonomous agents are disabled by configuration.')
    result=run_discovery_supervisor(db,goal,max(1,min(cycles,AUTONOMOUS_AGENT_MAX_CYCLES)))
    if not result.get('run_id'):
        raise HTTPException(500,result.get('error','Agent run failed'))
    return RedirectResponse(f"/agents/{result['run_id']}",303)


@router.get('/agents/{run_id}', response_class=HTMLResponse)
def agents_detail(run_id: int, request: Request, db: Session=Depends(get_db)):
    detail=agent_run_detail(db,run_id)
    if not detail: raise HTTPException(404,'Agent run not found')
    return templates.TemplateResponse(request=request,name='agent_run.html',context={'run':detail})


@router.get('/api/v1/agents/health')
def api_agent_health():
    return {'enabled':AUTONOMOUS_AGENTS_ENABLED,'interval_minutes':AUTONOMOUS_AGENT_INTERVAL_MINUTES,'health':agent_health()}


@router.post('/api/v1/agents/run')
def api_agent_run(cycles: int=1, goal: str='Improve worldwide engineering consultancy tender coverage and verify high-value opportunities.', db: Session=Depends(get_db)):
    if not AUTONOMOUS_AGENTS_ENABLED:
        raise HTTPException(409,'Autonomous agents are disabled by configuration.')
    return run_discovery_supervisor(db,goal,max(1,min(cycles,AUTONOMOUS_AGENT_MAX_CYCLES)))


@router.get('/api/v1/agents/runs/{run_id}')
def api_agent_run_detail(run_id: int, db: Session=Depends(get_db)):
    detail=agent_run_detail(db,run_id)
    if not detail: raise HTTPException(404,'Agent run not found')
    return detail
