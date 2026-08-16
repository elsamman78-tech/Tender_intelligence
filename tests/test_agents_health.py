from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Source, SourceChannel
from app.agent_models import AgentRun, AgentStep
from app.discovery.source_health import audit_source, health_snapshot
from app.discovery.query_engine import bootstrap_queries
from app.agents.tools import ToolRuntime


def make_db():
    e=create_engine('sqlite+pysqlite:///:memory:',future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e,future=True)()


def test_source_health_detects_login_required_on_procurement_channel(monkeypatch):
    db=make_db()
    s=Source(name='Portal',domain='portal.test',base_url='https://portal.test',source_type='GOVERNMENT_PORTAL',country='Egypt',lifecycle_status='ACTIVE',cost_class='FREE_PUBLIC')
    db.add(s); db.flush()
    db.add(SourceChannel(source_id=s.id,purpose='TENDERS',url='https://portal.test/login',access_method='HTML'))
    db.commit()
    def fake_probe(url):
        if url.endswith('/login'): return ('LOGIN_REQUIRED','login page',200)
        return ('HEALTHY',None,200)
    monkeypatch.setattr('app.discovery.source_health._probe',fake_probe)
    r=audit_source(db,s)
    assert r['state']=='LOGIN_REQUIRED'
    assert s.health_status=='LOGIN_REQUIRED' and s.requires_login==1
    assert health_snapshot(db)['states']['LOGIN_REQUIRED']==1


def test_agent_gap_tool_is_bounded_and_respects_country_matrix():
    db=make_db(); bootstrap_queries(db)
    runtime=ToolRuntime(db)
    r=runtime.tool_coverage_gaps(5)
    assert r['count']==5 and len(r['gaps'])==5
    assert all('country' in x and 'coverage_score' in x for x in r['gaps'])


def test_agent_country_tool_rejects_excluded_country_without_network():
    db=make_db(); bootstrap_queries(db)
    runtime=ToolRuntime(db)
    r=runtime.tool_run_country_discovery('United States','SOURCE_SEARCH',1)
    assert r['ok'] is False and r['error']=='COUNTRY_NOT_IN_TARGET_POLICY'


def test_agent_audit_models_are_registered():
    db=make_db()
    run=AgentRun(goal='test',status='COMPLETED')
    db.add(run); db.commit(); db.refresh(run)
    db.add(AgentStep(run_id=run.id,cycle_no=1,agent_name='COVERAGE_AGENT',step_no=1,action='ROLE_COMPLETE'))
    db.commit()
    assert db.scalar(select(AgentRun).where(AgentRun.id==run.id)) is not None
