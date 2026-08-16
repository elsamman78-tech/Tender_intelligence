from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import Source, SourceChannel, DiscoveryCandidate, Tender, DocumentRecord
from app.discovery.source_registry import bootstrap_sources
from app.discovery.query_engine import bootstrap_queries
from app.discovery.candidates import upsert_candidate, validate_candidate
from app.discovery.file_discovery import index_candidate_documents
from app.discovery.scanner import scan_channel


def make_db():
    e=create_engine('sqlite+pysqlite:///:memory:',future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e,future=True)()


def test_bootstrap_sources_and_queries():
    db=make_db()
    assert bootstrap_sources(db) >= 10
    assert bootstrap_queries(db) >= 18
    assert len(db.scalars(select(Source)).all()) >= 10


def test_candidate_dedup_and_scoring():
    db=make_db()
    s=Source(name='X',domain='x.gov',base_url='https://x.gov',source_type='GOVERNMENT_PORTAL',country='UAE',cost_class='FREE_PUBLIC')
    db.add(s); db.commit()
    title='Request for Expression of Interest - Engineering Consultancy and Construction Supervision'
    c1,new1=upsert_candidate(db,'https://x.gov/eoi/1',title,'consulting services',s,'KNOWN_SOURCE')
    c2,new2=upsert_candidate(db,'https://x.gov/eoi/1',title,'consulting services',s,'OPEN_SEARCH')
    assert new1 is True and new2 is False
    assert c1.id==c2.id and c1.procurement_score>0 and c1.consultancy_score>0


def test_file_discovery_index():
    db=make_db()
    c,_=upsert_candidate(db,'https://x.gov/docs/RFP_Consultancy.pdf','RFP Consultancy','',None,'FILE_SEARCH')
    r=index_candidate_documents(db)
    assert r['indexed']==1
    doc=db.scalar(select(DocumentRecord))
    assert doc and doc.document_type=='RFP'


def test_generic_html_scanner_creates_candidate(monkeypatch):
    db=make_db()
    s=Source(name='Authority',domain='authority.gov',base_url='https://authority.gov',source_type='GOVERNMENT_PORTAL',country='Saudi Arabia',cost_class='FREE_PUBLIC',lifecycle_status='ACTIVE')
    db.add(s); db.flush()
    ch=SourceChannel(source_id=s.id,purpose='TENDERS',url='https://authority.gov/tenders',access_method='HTML')
    db.add(ch); db.commit()
    class R:
        status_code=200
        content=b'<html><a href="/rfp/123">RFP Engineering Consultancy for Project Management and Supervision</a></html>'
        text=content.decode()
        url='https://authority.gov/tenders'
        def raise_for_status(self): pass
    monkeypatch.setattr('app.discovery.scanner.httpx.get',lambda *a,**k:R())
    scan=scan_channel(db,s,ch)
    assert scan.status=='SUCCESS' and scan.new_candidates==1
    c=db.scalar(select(DiscoveryCandidate))
    assert c and c.consultancy_score>0


def test_valid_candidate_promotes_to_existing_analyzer(monkeypatch):
    db=make_db()
    s=Source(name='Official',domain='official.gov',base_url='https://official.gov',source_type='GOVERNMENT_PORTAL',country='UAE',cost_class='FREE_PUBLIC',lifecycle_status='ACTIVE')
    db.add(s); db.commit()
    c,_=upsert_candidate(db,'https://official.gov/rfp/5','RFP Engineering Consultancy - Project Management Consultant PMC','consulting services construction supervision',s,'KNOWN_SOURCE')
    text=('Request for Proposal RFP. Engineering consultancy services. Project Management Consultant PMC. '
          'Construction supervision and design review. Submission deadline 2026-09-30. United Arab Emirates.')
    monkeypatch.setattr('app.discovery.candidates.fetch_candidate_text',lambda cand:(text,cand.url))
    r=validate_candidate(db,c,auto_promote=True)
    assert r['status']=='PROMOTED'
    t=db.scalar(select(Tender))
    assert t and t.discovery_candidate_id==c.id and t.discovery_method=='KNOWN_SOURCE'


def test_zero_cost_blocks_paid_source(monkeypatch):
    db=make_db()
    s=Source(name='Paid',domain='paid.test',base_url='https://paid.test',cost_class='PAID',requires_payment=1,lifecycle_status='ACTIVE')
    db.add(s); db.flush(); ch=SourceChannel(source_id=s.id,purpose='TENDERS',url='https://paid.test/tenders',access_method='HTML'); db.add(ch); db.commit()
    scan=scan_channel(db,s,ch)
    assert scan.status=='BLOCKED'
    assert s.health_status=='BLOCKED_BY_COST_POLICY'
