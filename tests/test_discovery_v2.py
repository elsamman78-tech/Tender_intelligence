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


def test_tender_portal_navigation_noise_is_blocked_at_ingress(monkeypatch):
    db=make_db()
    s=Source(name='Bahrain Tender Board Test',domain='tenderboard.gov.bh',base_url='https://www.tenderboard.gov.bh/',source_type='GOVERNMENT_PORTAL',country='Bahrain',cost_class='FREE_PUBLIC',lifecycle_status='ACTIVE')
    db.add(s); db.flush()
    ch=SourceChannel(source_id=s.id,purpose='TENDERS',url='https://www.tenderboard.gov.bh/tenders/publictenders/',access_method='HTML')
    db.add(ch); db.commit()
    html='''<html>
      <a href="/PrivacyPolicy/">Privacy Policy</a>
      <a href="/FAQ/GeneralFAQ/">General FAQ</a>
      <a href="/About/News/">News</a>
      <a href="/Tenders/ArchivedTenders/">Archived Tenders</a>
      <a href="/Tenders/AwardedTenders/">Awarded Tenders</a>
      <a href="/MediaHandler/GenericHandler/Pdf/guide/Vision2030.pdf">Vision 2030</a>
      <a href="/tenders/publictenders/#menu">Menu</a>
      <a href="/Tenders/Details/12345">RFP Engineering Consultancy for Detailed Design and Supervision</a>
    </html>'''
    class R:
        status_code=200
        content=html.encode()
        text=html
        url='https://www.tenderboard.gov.bh/tenders/publictenders/'
        def raise_for_status(self): pass
    monkeypatch.setattr('app.discovery.scanner.httpx.get',lambda *a,**k:R())
    scan=scan_channel(db,s,ch)
    candidates=db.scalars(select(DiscoveryCandidate)).all()
    assert scan.status=='SUCCESS'
    assert scan.items_seen==1
    assert scan.new_candidates==1
    assert len(candidates)==1
    assert 'Engineering Consultancy' in candidates[0].title


def test_award_channel_health_checks_without_creating_tender_candidates(monkeypatch):
    db=make_db()
    s=Source(name='Awards Test',domain='award.gov',base_url='https://award.gov',source_type='GOVERNMENT_PORTAL',country='Egypt',cost_class='FREE_PUBLIC',lifecycle_status='ACTIVE')
    db.add(s); db.flush()
    ch=SourceChannel(source_id=s.id,purpose='AWARDS',url='https://award.gov/awards',access_method='HTML')
    db.add(ch); db.commit()
    class R:
        status_code=200
        content=b'<html><a href="/award/1">Contract Award - Engineering Consultant</a></html>'
        text=content.decode()
        url='https://award.gov/awards'
        def raise_for_status(self): pass
    monkeypatch.setattr('app.discovery.scanner.httpx.get',lambda *a,**k:R())
    scan=scan_channel(db,s,ch)
    assert scan.status=='SUCCESS'
    assert scan.new_candidates==0
    assert db.scalars(select(DiscoveryCandidate)).all()==[]


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
