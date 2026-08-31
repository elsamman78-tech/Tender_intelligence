from pathlib import Path

from app.discovery.collectors.etimad import EtimadCollector
from app.discovery import document_ocr
from app.discovery import feed_bridge
from app.discovery.change_detection import _as_datetime


def test_etimad_collector_parses_real_listing_shape():
    html='''<html><body>
    <div class="col-12 col-md-12 mb-4">
      <span class="badge badge-primary">منافسة عامة</span>
      <h3>خدمات استشارية هندسية للإشراف على مشروع طرق</h3>
      <p>وزارة النقل والخدمات اللوجستية</p>
      <span>2026-08-30</span>
      <a href="/Tender/DetailsForVisitor?STenderId=abc123">التفاصيل</a>
    </div></body></html>'''
    items=EtimadCollector.parse_page(html,'https://tenders.etimad.sa/Tender/')
    assert len(items)==1
    assert 'خدمات استشارية هندسية' in items[0].title
    assert items[0].url.startswith('https://tenders.etimad.sa/Tender/DetailsForVisitor')
    assert 'Publication Date 2026-08-30' in items[0].snippet
    assert 'وزارة النقل' in items[0].snippet


def test_etimad_date_parser_is_strict():
    assert str(EtimadCollector._parse_date('نشر 2026-08-31'))=='2026-08-31'
    assert EtimadCollector._parse_date('بدون تاريخ') is None


def test_ocr_escalates_when_pdf_has_almost_no_text(monkeypatch,tmp_path):
    calls={'n':0}
    def fake_text(data):
        calls['n']+=1
        return '' if calls['n']==1 else 'Engineering consultancy request for proposal '*20
    def fake_local(inp: Path,out: Path):
        out.write_bytes(b'ocr-pdf')
        return True
    monkeypatch.setattr(document_ocr,'_pypdf_text',fake_text)
    monkeypatch.setattr(document_ocr,'_local_ocr',fake_local)
    monkeypatch.setattr(document_ocr,'OCR_ENABLED',True)
    monkeypatch.setattr(document_ocr,'OCR_MIN_TEXT_CHARS',180)
    text,engine=document_ocr.extract_pdf_text(b'input-pdf')
    assert engine=='OCR'
    assert 'Engineering consultancy' in text


def test_rss_bridge_builds_procurement_css_feed(monkeypatch):
    monkeypatch.setattr(feed_bridge,'RSS_BRIDGE_ENABLED',True)
    monkeypatch.setattr(feed_bridge,'RSS_BRIDGE_URL','http://127.0.0.1:3000')
    url=feed_bridge.bridge_feed_url('https://example.gov/procurement')
    assert 'CssSelectorBridge' in url
    assert 'home_page=https%3A%2F%2Fexample.gov%2Fprocurement' in url
    assert 'format=Atom' in url


def test_changedetection_timestamps_accept_epoch_and_iso():
    assert _as_datetime(1700000000) is not None
    assert _as_datetime('2026-08-31T10:00:00Z').year==2026
