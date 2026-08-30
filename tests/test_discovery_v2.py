from io import BytesIO
import zipfile

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Source, SourceChannel, DiscoveryCandidate, Tender, DocumentRecord, DiscoveryQuery
from app.discovery.source_registry import bootstrap_sources
from app.discovery.query_engine import bootstrap_queries, run_query
from app.discovery.candidates import upsert_candidate, validate_candidate
from app.discovery.file_discovery import index_candidate_documents
from app.discovery.scanner import scan_channel
from app.discovery.connectors.base import PortalHtmlConnector, ConnectorResult, ExtractedOpportunity
from app.evaluation_report import build_evaluation_zip


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


def test_portal_connector_blocks_navigation_external_apps_and_awards():
    html='''<html>
      <a href="https://play.google.com/store/apps/details?id=com.om.esnad">ESNAD Mobile App</a>
      <a href="https://www.instagram.com/tenderboard_bh/">Instagram</a>
      <a href="/PrivacyPolicy/">Privacy Policy</a>
      <a href="/FAQ/GeneralFAQ/">General FAQ</a>
      <a href="/About/News/">News</a>
      <a href="/Tenders/ArchivedTenders/">Archived Tenders</a>
      <a href="/Tenders/AwardedTenders/">Awarded Tenders</a>
      <a href="/Tenders/PublicTenders/">Published Tenders</a>
      <a href="/Tenders/Details/12345">RFP Engineering Consultancy for Detailed Design and Supervision</a>
    </html>'''
    items=PortalHtmlConnector().extract(html,'https://www.tenderboard.gov.bh/tenders/publictenders/',country='Bahrain')
    assert len(items)==1
    assert 'Engineering Consultancy' in items[0].title
    assert '/Tenders/Details/12345' in items[0].url


def test_portal_connector_recovers_title_from_view_card():
    html='''<html><article class="tender-card">
      <h3>Harouge Oil Operations - Open Invitation to Tender No. TS-C-07-2026 - Engineering Design Consultancy</h3>
      <p>Consulting services for detailed engineering design and supervision.</p>
      <a href="/en/tenders/harouge-oil-operations-an-open-invitation-to-tender-no-ts-c-07-2026/">View</a>
    </article></html>'''
    items=PortalHtmlConnector().extract(html,'https://noc.ly/en/tenders/',country='Libya')
    assert len(items)==1
    assert items[0].title != 'View'
    assert 'Harouge Oil Operations' in items[0].title
    assert 'Engineering Design Consultancy' in items[0].title


def test_generic_scanner_uses_connector_result(monkeypatch):
    db=make_db()
    s=Source(name='Authority',domain='authority.gov',base_url='https://authority.gov',source_type='GOVERNMENT_PORTAL',country='Saudi Arabia',cost_class='FREE_PUBLIC',lifecycle_status='ACTIVE')
    db.add(s); db.flush()
    ch=SourceChannel(source_id=s.id,purpose='TENDERS',url='https://authority.gov/tenders',access_method='HTML')
    db.add(ch); db.commit()
    fake=ConnectorResult(
        items=[ExtractedOpportunity('https://authority.gov/rfp/123','RFP Engineering Consultancy for Project Management and Supervision','consulting services')],
        final_url=ch.url,http_status=200,connector_name='TEST_CONNECTOR',rendered=False,
    )
    monkeypatch.setattr('app.discovery.scanner.scan_url',lambda *a,**k:fake)
    scan=scan_channel(db,s,ch)
    assert scan.status=='SUCCESS' and scan.new_candidates==1
    c=db.scalar(select(DiscoveryCandidate))
    assert c and c.consultancy_score>0 and 'TEST_CONNECTOR' in (c.discovery_detail or '')


def test_award_channel_health_checks_without_creating_tender_candidates():
    db=make_db()
    s=Source(name='Awards Test',domain='award.gov',base_url='https://award.gov',source_type='GOVERNMENT_PORTAL',country='Egypt',cost_class='FREE_PUBLIC',lifecycle_status='ACTIVE')
    db.add(s); db.flush()
    ch=SourceChannel(source_id=s.id,purpose='AWARDS',url='https://award.gov/awards',access_method='HTML')
    db.add(ch); db.commit()
    scan=scan_channel(db,s,ch)
    assert scan.status in {'SUCCESS','UNCHANGED'}
    assert scan.new_candidates==0
    assert db.scalars(select(DiscoveryCandidate)).all()==[]


def test_source_search_does_not_create_tender_candidate(monkeypatch):
    db=make_db()
    q=DiscoveryQuery(query_text='Oman procurement portal',country='Oman',purpose='SOURCE_SEARCH',priority=90,enabled=True)
    db.add(q); db.commit()

    class Hit:
        url='https://play.google.com/store/apps/details?id=com.om.esnad'
        title='ESNAD - Oman government eTendering mobile app'
        snippet='Official e-tendering application for government procurement'
        rank=1

    class Provider:
        name='TEST'; cost_class='FREE_PUBLIC'
        def search(self,query,limit): return [Hit()]

    r=run_query(db,q,provider=Provider(),limit=5)
    assert r['ok'] is True
    assert db.scalars(select(DiscoveryCandidate)).all()==[]
    assert len(db.scalars(select(Source)).all())==1


def test_tender_search_prefilter_drops_non_consultancy_result(monkeypatch):
    db=make_db()
    q=DiscoveryQuery(query_text='engineering consultancy tender Oman',country='Oman',purpose='TENDER_SEARCH',priority=90,enabled=True)
    db.add(q); db.commit()

    class Hit:
        url='https://example.org/about/transport'
        title='Transport sector overview'
        snippet='General information about transport sector development'
        rank=1

    class Provider:
        name='TEST'; cost_class='FREE_PUBLIC'
        def search(self,query,limit): return [Hit()]

    r=run_query(db,q,provider=Provider(),limit=5)
    assert r['ok'] is True
    assert r['new_candidates']==0
    assert r['noise']==1
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


def test_evaluation_zip_contains_review_files():
    db=make_db()
    s=Source(name='Official Source',domain='official.gov',base_url='https://official.gov',source_type='GOVERNMENT_PORTAL',country='UAE',cost_class='FREE_PUBLIC',lifecycle_status='ACTIVE',health_status='HEALTHY')
    db.add(s); db.commit()
    upsert_candidate(db,'https://official.gov/rfp/1','RFP Engineering Consultancy','consulting services',s,'KNOWN_SOURCE')
    body,filename=build_evaluation_zip(db)
    assert filename.startswith('Tender_Intelligence_Evaluation_') and filename.endswith('.zip')
    with zipfile.ZipFile(BytesIO(body),'r') as z:
        names=set(z.namelist())
        assert {'README_EVALUATION.md','evaluation_report.json','sources.csv','candidates.csv','tenders.csv','coverage.csv','queries.csv','search_runs.csv'} <= names
        summary=z.read('README_EVALUATION.md').decode('utf-8')
        assert 'Snapshot' in summary and 'Sources: 1' in summary


def test_zero_cost_blocks_paid_source():
    db=make_db()
    s=Source(name='Paid',domain='paid.test',base_url='https://paid.test',cost_class='PAID',requires_payment=1,lifecycle_status='ACTIVE')
    db.add(s); db.flush(); ch=SourceChannel(source_id=s.id,purpose='TENDERS',url='https://paid.test/tenders',access_method='HTML'); db.add(ch); db.commit()
    scan=scan_channel(db,s,ch)
    assert scan.status=='BLOCKED'
    assert s.health_status=='BLOCKED_BY_COST_POLICY'
