from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Source, SourceChannel, DiscoveryCandidate
from app.discovery.candidates import (
    upsert_candidate, validate_candidate, _extract_deadline, _extract_publication_date,
)
from app.discovery.scanner import scan_channel
from app.discovery.connectors.base import PortalHtmlConnector, ConnectorResult, ExtractedOpportunity


def make_db():
    e=create_engine('sqlite+pysqlite:///:memory:',future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e,future=True)()


def test_undp_structured_country_wins_over_neighbouring_yemen_snippet():
    db=make_db()
    s=Source(name='UNDP',domain='procurement-notices.undp.org',base_url='https://procurement-notices.undp.org/',source_type='UN',cost_class='FREE_PUBLIC')
    db.add(s); db.commit()
    title=('Title Consultancy notice Ref No UNDP-COL-03385 UNDP Office/Country '
           'UNDP-COL/COLOMBIA Process RFP - Request for proposal Deadline 10-Sep-26')
    snippet='Neighbouring listing row Yemen engineering consultancy tender'
    c,_=upsert_candidate(db,'https://procurement-notices.undp.org/view_negotiation.cfm?nego_id=1',title,snippet,s,'KNOWN_SOURCE')
    assert c.country_guess.upper()=='COLOMBIA'
    assert c.validation_status=='REJECTED'
    assert c.rejection_reason=='EXCLUDED_GEOGRAPHY'


def test_undp_target_country_is_normalized_from_structured_title():
    db=make_db()
    s=Source(name='UNDP',domain='procurement-notices.undp.org',base_url='https://procurement-notices.undp.org/',source_type='UN',cost_class='FREE_PUBLIC')
    db.add(s); db.commit()
    title=('RFP Engineering Consultancy Ref No UNDP-TUN-01114 UNDP Office/Country '
           'UNDP-TUN/TUNISIA Process RFP - Request for proposal')
    c,_=upsert_candidate(db,'https://procurement-notices.undp.org/view_negotiation.cfm?nego_id=2',title,'',s,'KNOWN_SOURCE')
    assert c.country_guess=='Tunisia'
    assert c.validation_status=='NEW'


def test_undp_short_month_dates_are_extracted_from_listing_text():
    text=('Title Engineering Consultancy Ref No UNDP-TUN-01114 Process RFP '
          'Deadline 11-Sep-26 06:00 PM (New York time) Posted 21-Aug-26')
    assert str(_extract_deadline(text))=='2026-09-11'
    assert str(_extract_publication_date(text))=='2026-08-21'


def test_privacy_path_is_blocked_even_when_page_context_mentions_tenders():
    html='''<html><section>
      <h2>Tenders</h2><p>Explore procurement and tender opportunities.</p>
      <a href="/en/privacy-policy/">Privacy Policy</a>
      <a href="/en/tenders/rfp-engineering-123/">RFP Engineering Consultancy for Detailed Design</a>
    </section></html>'''
    items=PortalHtmlConnector().extract(html,'https://noc.ly/en/tenders/',country='Libya')
    assert len(items)==1
    assert 'privacy' not in items[0].url.lower()
    assert 'rfp-engineering-123' in items[0].url


def test_global_un_listing_prefilter_drops_capacity_building_but_keeps_engineering(monkeypatch):
    db=make_db()
    s=Source(name='UNDP',domain='procurement-notices.undp.org',base_url='https://procurement-notices.undp.org/',source_type='UN',cost_class='FREE_PUBLIC',lifecycle_status='ACTIVE')
    db.add(s); db.flush()
    ch=SourceChannel(source_id=s.id,purpose='TENDERS',url='https://procurement-notices.undp.org/',access_method='HTML')
    db.add(ch); db.commit()
    fake=ConnectorResult(items=[
        ExtractedOpportunity(
            'https://procurement-notices.undp.org/view_negotiation.cfm?nego_id=10',
            'Consulting firm to design and deliver capacity building program - UNDP Office/Country UNDP-HQ/MOZAMBIQUE Process RFQ',
            'Request for quotation deadline 09-Sep-26 consulting services capacity building training',
        ),
        ExtractedOpportunity(
            'https://procurement-notices.undp.org/view_negotiation.cfm?nego_id=11',
            'RFP Engineering Consultancy for Detailed Design - UNDP Office/Country UNDP-TUN/TUNISIA Process RFP',
            'construction supervision and design review deadline 30-Sep-26',
        ),
    ],final_url=ch.url,http_status=200,connector_name='TEST',rendered=False)
    monkeypatch.setattr('app.discovery.scanner.scan_url',lambda *a,**k:fake)
    scan=scan_channel(db,s,ch)
    rows=db.scalars(select(DiscoveryCandidate)).all()
    assert scan.new_candidates==1
    assert len(rows)==1
    assert 'Engineering Consultancy' in rows[0].title


def test_capacity_building_consultancy_is_not_promoted_as_engineering(monkeypatch):
    db=make_db()
    s=Source(name='UNDP',domain='procurement-notices.undp.org',base_url='https://procurement-notices.undp.org/',source_type='UN',country=None,cost_class='FREE_PUBLIC')
    db.add(s); db.commit()
    title=('Consulting firm to design and deliver capacity building program Ref No UNDP-HQ-02295 '
           'UNDP Office/Country UNDP-HQ/MOZAMBIQUE Process RFQ - Request for quotation Deadline 09-Sep-26 Posted 28-Aug-26')
    c,_=upsert_candidate(db,'https://procurement-notices.undp.org/view_negotiation.cfm?nego_id=12',title,'consulting services request for quotation deadline',s,'KNOWN_SOURCE')
    text=('Request for quotation. Consulting firm to design and deliver a capacity building program. '
          'Training curriculum, workshops and institutional capacity development. Deadline 09-Sep-26. Posted 28-Aug-26.')
    monkeypatch.setattr('app.discovery.candidates.fetch_candidate_text',lambda cand:(text,cand.url))
    r=validate_candidate(db,c,auto_promote=True)
    assert r['status']=='REJECTED'
    assert c.rejection_reason=='NO_ENGINEERING_DOMAIN_EVIDENCE'
