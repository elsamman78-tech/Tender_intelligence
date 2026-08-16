from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_dashboard_template_renders():
    r = client.get('/')
    assert r.status_code == 200
    assert r.template.name == 'dashboard.html'
    assert 'request' in r.context


def test_new_tender_template_renders():
    r = client.get('/tenders/new')
    assert r.status_code == 200
    assert r.template.name == 'new_tender.html'
    assert 'request' in r.context


def test_discovery_template_renders():
    r = client.get('/discovery')
    assert r.status_code == 200
    assert r.template.name == 'discovery.html'
    assert 'request' in r.context


def test_sources_template_renders():
    r = client.get('/sources')
    assert r.status_code == 200
    assert r.template.name == 'sources.html'
    assert 'request' in r.context
