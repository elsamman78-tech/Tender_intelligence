from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse
import re
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import DiscoveryCandidate, Tender, Source
from ..config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT, AUTO_PROMOTE_TENDERS
from ..services.analysis import run_analysis
from ..services.dedup import fingerprint as make_fingerprint
from .utils import hash_text, clean_text, keyword_score
from .keywords import PROCUREMENT_TERMS, CONSULTANCY_TERMS, NOISE_TERMS, DOCUMENT_EXTENSIONS

COUNTRIES = {
    'saudi arabia':['saudi arabia','kingdom of saudi arabia','السعودية','المملكة العربية السعودية'],
    'egypt':['egypt','arab republic of egypt','مصر'],
    'uae':['united arab emirates','uae','الإمارات','الامارات'],
    'libya':['libya','ليبيا'],
    'bangladesh':['bangladesh','بنغلاديش'],
}

def infer_country(text: str, source: Source|None=None):
    low=(text or '').lower()
    for canonical, aliases in COUNTRIES.items():
        if any(a.lower() in low for a in aliases):
            return {'saudi arabia':'Saudi Arabia','egypt':'Egypt','uae':'UAE','libya':'Libya','bangladesh':'Bangladesh'}[canonical]
    return source.country if source and source.country else None

def opportunity_type(text: str):
    low=(text or '').lower()
    mapping=[('ADDENDUM',['addendum','clarification','تمديد']),('EOI',['expression of interest','eoi','reoi','إبداء اهتمام','ابداء اهتمام','manifestation d’intérêt',"manifestation d'interet"]),
             ('RFP',['request for proposal','rfp','طلب عروض']),('PREQUALIFICATION',['prequalification','pre-qualification','تأهيل']),('GPN',['general procurement notice','gpn']),('AWARD',['contract award','award notice','ترسية']),('TENDER',['tender','مناقصة','منافسة','appel d’offres',"appel d'offres"])]
    for kind,terms in mapping:
        if any(t in low for t in terms): return kind
    return 'OPPORTUNITY'

def score_candidate(title: str, snippet: str=''):
    text=clean_text((title or '')+' '+(snippet or ''))
    p=keyword_score(text,PROCUREMENT_TERMS); c=keyword_score(text,CONSULTANCY_TERMS)
    noise=keyword_score(text,NOISE_TERMS)
    if noise: p=max(0,p-noise); c=max(0,c-noise)
    conf=min(1.0,(p*0.45+c*0.55)/100)
    return p,c,conf

def upsert_candidate(db: Session, url: str, title: str='', snippet: str='', source: Source|None=None, method: str='UNKNOWN', detail: str=''):
    h=hash_text(url)
    c=db.scalar(select(DiscoveryCandidate).where(DiscoveryCandidate.url_hash==h))
    p,cs,conf=score_candidate(title,snippet)
    if c:
        c.last_seen_at=datetime.utcnow(); c.title=c.title or title; c.snippet=c.snippet or snippet
        c.procurement_score=max(c.procurement_score,p); c.consultancy_score=max(c.consultancy_score,cs); c.confidence=max(c.confidence,conf)
        db.commit(); return c,False
    candidate_type='DOCUMENT' if url.lower().split('?',1)[0].endswith(DOCUMENT_EXTENSIONS) else 'OPPORTUNITY'
    c=DiscoveryCandidate(candidate_type=candidate_type,url=url,url_hash=h,title=title[:1000] or None,snippet=snippet[:4000] or None,source_id=source.id if source else None,
                         discovery_method=method,discovery_detail=detail,country_guess=infer_country((title or '')+' '+(snippet or ''),source),
                         opportunity_type_guess=opportunity_type((title or '')+' '+(snippet or '')),procurement_score=p,consultancy_score=cs,confidence=conf)
    db.add(c); db.commit(); db.refresh(c); return c,True

def fetch_candidate_text(c: DiscoveryCandidate):
    r=httpx.get(c.url,timeout=DISCOVERY_REQUEST_TIMEOUT,follow_redirects=True,headers={'User-Agent':USER_AGENT})
    r.raise_for_status()
    ctype=r.headers.get('content-type','').lower()
    is_pdf='application/pdf' in ctype or str(r.url).lower().split('?',1)[0].endswith('.pdf')
    if is_pdf:
        reader=PdfReader(BytesIO(r.content))
        text='\n'.join((p.extract_text() or '') for p in reader.pages[:250])
        return clean_text(text)[:300000],str(r.url)
    if c.candidate_type=='DOCUMENT' and not ('html' in ctype or 'text/' in ctype):
        raise RuntimeError('DOCUMENT_INDEXED_PARSING_NOT_YET_ENABLED_FOR_THIS_FORMAT')
    soup=BeautifulSoup(r.text,'html.parser')
    for bad in soup(['script','style','noscript']): bad.decompose()
    return clean_text(soup.get_text(' ',strip=True))[:300000], str(r.url)

def _extract_deadline(text: str):
    # Conservative ISO/date extraction near deadline words. Returns None if ambiguous.
    patterns=[r'(?:deadline|closing date|submission deadline)[^\d]{0,30}(20\d{2})[-/](\d{1,2})[-/](\d{1,2})',
              r'(?:deadline|closing date|submission deadline)[^\d]{0,30}(\d{1,2})[-/](\d{1,2})[-/](20\d{2})']
    from datetime import date
    for idx,p in enumerate(patterns):
        m=re.search(p,text,re.I)
        if m:
            try:
                if idx==0: return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
                return date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
            except Exception: pass
    return None

def validate_candidate(db: Session, c: DiscoveryCandidate, auto_promote: bool=AUTO_PROMOTE_TENDERS):
    source=db.get(Source,c.source_id) if c.source_id else None
    if c.procurement_score<6 or c.consultancy_score<10:
        c.validation_status='REJECTED'; c.rejection_reason='LOW_RELEVANCE'; db.commit(); return {'status':'REJECTED'}
    try:
        text,final_url=fetch_candidate_text(c)
    except Exception as e:
        c.validation_status='FETCH_FAILED'; c.rejection_reason=str(e)[:120]; db.commit(); return {'status':'FETCH_FAILED'}
    combined=(c.title or '')+' '+text[:100000]
    p,cs,conf=score_candidate(combined,'')
    c.procurement_score=max(c.procurement_score,p); c.consultancy_score=max(c.consultancy_score,cs); c.confidence=max(c.confidence,conf)
    c.country_guess=infer_country(combined,source) or c.country_guess
    c.opportunity_type_guess=opportunity_type(combined)
    if p<12 or cs<12:
        c.validation_status='REJECTED'; c.rejection_reason='CONTENT_NOT_CONSULTANCY_PROCUREMENT'; db.commit(); return {'status':'REJECTED'}
    c.validation_status='VALIDATED'; c.rejection_reason=None
    if auto_promote and c.opportunity_type_guess not in {'AWARD','ADDENDUM'}:
        deadline=_extract_deadline(text)
        title=clean_text(c.title or '')[:500] or clean_text(text[:180])[:500] or 'Discovered consultancy opportunity'
        fp=make_fingerprint(title=title,client='',country=c.country_guess or '',deadline=deadline,reference='')
        t=db.scalar(select(Tender).where(Tender.fingerprint==fp))
        if not t:
            result=run_analysis(c.country_guess or None,deadline,text,use_ai=False)
            status='HARD_REJECTED' if result['hard_reject'] else ('EXPIRED' if result['urgency_level']=='EXPIRED' else 'QUALIFIED')
            t=Tender(title=title,fingerprint=fp,project_country=c.country_guess,source_url=final_url,submission_deadline=deadline,
                     raw_text=text[:1000000],tender_status=status,discovery_candidate_id=c.id,discovery_method=c.discovery_method,
                     **{k:v for k,v in result.items() if k!='hard_reject'})
            db.add(t); db.flush()
        c.tender_id=t.id; c.validation_status='PROMOTED'
        if source: source.useful_count=(source.useful_count or 0)+1
    db.commit()
    return {'status':c.validation_status,'tender_id':c.tender_id}
