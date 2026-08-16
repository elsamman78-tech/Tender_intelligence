from __future__ import annotations

from datetime import datetime
import json
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import OLLAMA_URL, OLLAMA_MODEL, ZERO_COST_MODE
from ..agent_models import AgentRun, AgentStep
from .tools import ToolRuntime

ROLES = ['COVERAGE_AGENT','SOURCE_DISCOVERY_AGENT','OPPORTUNITY_DISCOVERY_AGENT','VERIFICATION_AGENT','COVERAGE_AGENT']

ROLE_PROMPTS = {
    'COVERAGE_AGENT': '''You are the Coverage Agent for a zero-cost engineering consultancy tender intelligence system.
Measure coverage; do not invent sources. Use tools to identify weak countries and compare providers. Prefer small bounded benchmarks. Never change geography policy or scoring rules.''',
    'SOURCE_DISCOVERY_AGENT': '''You are the Source Discovery Agent. Your job is to find and profile new public procurement, government, MDB, developer, infrastructure operator, bank, university, healthcare and other legitimate opportunity sources.
Use coverage gaps first, then search weak countries. Social networks are lead-generation only. Do not bypass login, CAPTCHA, paywalls, robots protections or paid access. Keep calls bounded.''',
    'OPPORTUNITY_DISCOVERY_AGENT': '''You are the Opportunity Discovery Agent. Find engineering consultancy opportunities: detailed design, supervision, PMC, cost management, feasibility, master planning and owner's engineer.
Use known-source monitoring plus open discovery. Search providers are complementary. Do not make BID/NO-BID decisions. Keep calls bounded and let deterministic validation/scoring decide.''',
    'VERIFICATION_AGENT': '''You are the Verification Agent. Validate discovered candidates using deterministic tools. Social posts are never final evidence by themselves. Prefer official tender documents and procuring-entity pages. Do not bypass access controls or paywalls. Never override hard geography, scope, deduplication or scoring rules.''',
}


def _json_safe(value):
    try:
        return json.loads(json.dumps(value,default=str))
    except Exception:
        return {'value':str(value)[:10000]}


def agent_health() -> dict:
    try:
        r=httpx.get(f'{OLLAMA_URL}/api/tags',timeout=3)
        if r.status_code!=200:
            return {'ok':False,'model':OLLAMA_MODEL,'detail':f'HTTP {r.status_code}'}
        models=[(x.get('name') or x.get('model') or '') for x in r.json().get('models',[])]
        base=OLLAMA_MODEL.split(':',1)[0]
        installed=any(m==OLLAMA_MODEL or m.split(':',1)[0]==base for m in models)
        return {'ok':installed,'server_ok':True,'model':OLLAMA_MODEL,'installed_models':models[:30],
                'detail':None if installed else f'Model {OLLAMA_MODEL} is not installed'}
    except Exception as e:
        return {'ok':False,'server_ok':False,'model':OLLAMA_MODEL,'detail':str(e)}


def _log_step(db: Session, run_id: int, cycle_no: int, role: str, step_no: int, action: str,
              tool_name: str|None=None, input_json=None, output_json=None, status='DONE', rationale: str|None=None):
    s=AgentStep(run_id=run_id,cycle_no=cycle_no,agent_name=role,step_no=step_no,action=action,
                tool_name=tool_name,input_json=_json_safe(input_json) if input_json is not None else None,
                output_json=_json_safe(output_json) if output_json is not None else None,status=status,
                rationale=(rationale or '')[:4000] or None)
    db.add(s); db.commit(); return s


def _ollama_role_loop(db: Session, run: AgentRun, cycle_no: int, role: str, goal: str, max_turns: int=5) -> dict:
    runtime=ToolRuntime(db); tools=runtime.schemas_for_role(role)
    messages=[
        {'role':'system','content':ROLE_PROMPTS[role] + '\nZero-cost mode is ' + str(ZERO_COST_MODE) + '. Stop when you have taken enough bounded actions for this cycle.'},
        {'role':'user','content':goal},
    ]
    outputs=[]; tool_calls_total=0; final_text=''
    for turn in range(1,max_turns+1):
        payload={'model':OLLAMA_MODEL,'messages':messages,'tools':tools,'stream':False,'think':False,
                 'options':{'temperature':0.1}}
        try:
            r=httpx.post(f'{OLLAMA_URL}/api/chat',json=payload,timeout=180)
            r.raise_for_status(); msg=r.json().get('message') or {}
        except Exception as e:
            _log_step(db,run.id,cycle_no,role,turn,'MODEL_ERROR',status='FAILED',rationale=str(e))
            return {'ok':False,'mode':'OLLAMA_TOOLS','role':role,'error':str(e),'outputs':outputs}
        messages.append(msg)
        calls=msg.get('tool_calls') or []
        if not calls:
            final_text=(msg.get('content') or '')[:6000]
            _log_step(db,run.id,cycle_no,role,turn,'ROLE_COMPLETE',output_json={'content':final_text},rationale='Model stopped requesting tools.')
            return {'ok':True,'mode':'OLLAMA_TOOLS','role':role,'tool_calls':tool_calls_total,'final':final_text,'outputs':outputs}
        for call in calls[:4]:
            fn=(call.get('function') or {})
            name=fn.get('name') or ''
            args=fn.get('arguments') or {}
            if isinstance(args,str):
                try: args=json.loads(args)
                except Exception: args={}
            result=runtime.execute(name,args)
            tool_calls_total+=1; outputs.append({'tool':name,'result':_json_safe(result)})
            _log_step(db,run.id,cycle_no,role,tool_calls_total,'TOOL_CALL',tool_name=name,input_json=args,output_json=result,
                      status='DONE' if result.get('ok',True) else 'FAILED')
            messages.append({'role':'tool','tool_name':name,'content':json.dumps(_json_safe(result),ensure_ascii=False)[:30000]})
            if tool_calls_total>=8:
                _log_step(db,run.id,cycle_no,role,tool_calls_total+1,'BOUNDED_STOP',rationale='Per-role tool-call safety limit reached.')
                return {'ok':True,'mode':'OLLAMA_TOOLS','role':role,'tool_calls':tool_calls_total,'bounded_stop':True,'outputs':outputs}
    return {'ok':True,'mode':'OLLAMA_TOOLS','role':role,'tool_calls':tool_calls_total,'max_turns_reached':True,'outputs':outputs}


def _fallback_role(db: Session, run: AgentRun, cycle_no: int, role: str) -> dict:
    """Deterministic fallback preserves useful automation when Ollama is unavailable."""
    runtime=ToolRuntime(db); outputs=[]
    def call(name,args=None):
        result=runtime.execute(name,args or {}); outputs.append({'tool':name,'result':_json_safe(result)})
        _log_step(db,run.id,cycle_no,role,len(outputs),'FALLBACK_TOOL',tool_name=name,input_json=args or {},output_json=result,
                  status='DONE' if result.get('ok',True) else 'FAILED',rationale='Deterministic bounded fallback because local Ollama tool model is unavailable.')
        return result
    if role=='COVERAGE_AGENT':
        call('coverage_snapshot'); call('coverage_gaps',{'limit':8})
    elif role=='SOURCE_DISCOVERY_AGENT':
        gaps=call('coverage_gaps',{'limit':3}).get('gaps',[])
        for g in gaps[:2]: call('run_country_discovery',{'country':g['country'],'purpose':'SOURCE_SEARCH','query_limit':1})
        call('profile_source_candidates',{'limit':8}); call('audit_sources',{'limit':12})
    elif role=='OPPORTUNITY_DISCOVERY_AGENT':
        call('run_known_sources',{'limit':8}); call('run_open_discovery',{'query_limit':3})
    elif role=='VERIFICATION_AGENT':
        call('validate_candidates',{'limit':20}); call('audit_sources',{'limit':12})
    return {'ok':True,'mode':'DETERMINISTIC_FALLBACK','role':role,'outputs':outputs}


def run_role(db: Session, run: AgentRun, cycle_no: int, role: str, goal: str) -> dict:
    h=agent_health()
    if h.get('ok'):
        return _ollama_role_loop(db,run,cycle_no,role,goal)
    return _fallback_role(db,run,cycle_no,role)


def run_discovery_supervisor(db: Session, goal: str='Improve worldwide engineering consultancy tender coverage and verify high-value opportunities.', cycles: int=1) -> dict:
    cycles=max(1,min(int(cycles),3))
    h=agent_health(); mode='OLLAMA_TOOLS' if h.get('ok') else 'DETERMINISTIC_FALLBACK'
    run=AgentRun(goal=goal[:6000],status='RUNNING',mode=mode,model=OLLAMA_MODEL,cycles_requested=cycles)
    db.add(run); db.commit(); db.refresh(run)
    summaries=[]
    try:
        for cycle in range(1,cycles+1):
            cycle_out={'cycle':cycle,'roles':[]}
            for role in ROLES:
                role_goal=(
                    f'Cycle {cycle}/{cycles}. Overall goal: {goal}. '
                    'Use only the tools you need. Prefer measurable coverage gain, official-source verification, and bounded network load.'
                )
                cycle_out['roles'].append(run_role(db,run,cycle,role,role_goal))
            run.cycles_completed=cycle; db.commit(); summaries.append(cycle_out)
        runtime=ToolRuntime(db)
        final={'agent_health':h,'cycles':summaries,'coverage':runtime.tool_coverage_snapshot(),
               'source_health':runtime.tool_health_snapshot(),'coverage_gaps':runtime.tool_coverage_gaps(10)}
        run.status='COMPLETED'; run.summary_json=_json_safe(final); run.completed_at=datetime.utcnow(); db.commit()
        return {'ok':True,'run_id':run.id,'mode':mode,'summary':final}
    except Exception as e:
        run.status='FAILED'; run.error=str(e)[:3000]; run.completed_at=datetime.utcnow(); db.commit()
        return {'ok':False,'run_id':run.id,'mode':mode,'error':str(e)}


def recent_agent_runs(db: Session, limit: int=10) -> list[dict]:
    rows=db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(max(1,min(limit,30)))).all()
    return [{'id':x.id,'status':x.status,'mode':x.mode,'model':x.model,'cycles_completed':x.cycles_completed,
             'cycles_requested':x.cycles_requested,'started_at':x.started_at,'completed_at':x.completed_at,'error':x.error} for x in rows]


def agent_run_detail(db: Session, run_id: int) -> dict | None:
    run=db.get(AgentRun,run_id)
    if not run: return None
    steps=db.scalars(select(AgentStep).where(AgentStep.run_id==run_id).order_by(AgentStep.cycle_no,AgentStep.id)).all()
    return {'id':run.id,'goal':run.goal,'status':run.status,'mode':run.mode,'model':run.model,
            'cycles_requested':run.cycles_requested,'cycles_completed':run.cycles_completed,
            'summary':run.summary_json,'error':run.error,'started_at':run.started_at,'completed_at':run.completed_at,
            'steps':[{'id':s.id,'cycle':s.cycle_no,'agent':s.agent_name,'action':s.action,'tool':s.tool_name,
                      'input':s.input_json,'output':s.output_json,'status':s.status,'rationale':s.rationale,'created_at':s.created_at} for s in steps]}
