from datetime import datetime, date
from urllib.parse import urlparse
import re
import httpx
from bs4 import BeautifulSoup
from trafilatura import extract as trafilatura_extract
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import DiscoveryCandidate, Tender, Source
from ..config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT, AUTO_PROMOTE_TENDERS
from ..services.analysis import run_analysis
from ..services.participation import analyze_participation
from ..services.dedup import fingerprint as make_fingerprint
from ..geography import infer_country_from_text, is_excluded_country, is_target_country, normalize_country
from .utils import hash_text, clean_text, keyword_score
from .document_ocr import extract_pdf_text
from .keywords import (
    PROCUREMENT_TERMS, CONSULTANCY_TERMS, ENGINEERING_DOMAIN_TERMS, NOISE_TERMS, DOCUMENT_EXTENSIONS,
    ACTIONABLE_NOTICE_TERMS, SAUDI_DB_TERMS,
)

SOCIAL_DOMAINS={'linkedin.com','www.linkedin.com','facebook.com','www.facebook.com','x.com','www.x.com','twitter.com','www.twitter.com'}
MONTHS={
    'jan':1,'january':1,'feb':2,'february':2,'mar':3,'march':3,'apr':4,'april':4,'may':5,
    'jun':6,'june':6,'jul':7,'july':7,'aug':8,'august':8,'sep':9,'sept':9,'september':9,
    'oct':10,'october':10,'nov':11,'november':11,'dec':12,'december':12,
}


def infer_country(text: str, source: Source|None=None):
    guessed=infer_country_from_text(text or '')
    if guessed: return normalize_country(guessed)
    return normalize_country(source.country) if source and source.country else None


def opportunity_type(text: str):
    low=(text or '').lower()
    mapping=[
        ('AWARD',['contract award','award notice','contract awarded','ترسية','إسناد العقد']),
        ('ADDENDUM',['addendum','clarification','تمديد','ملحق']),
        ('EOI',['expression of interest','eoi','reoi','إبداء اهتمام','ابداء اهتمام','manifestation d’intérêt',"manifestation d'interet"]),
        ('RFP',['request for proposal','rfp','طلب عروض','طلب تقديم عروض']),
        ('PREQUALIFICATION',['prequalification','pre-qualification','تأهيل']),
        ('GPN',['general procurement notice','gpn']),
        ('TENDER',['tender','مناقصة','منافسة','appel d’offres',"appel d'offres"]),
    ]
    for kind,terms in mapping:
        if any(t in low for t in terms): return kind
    return 'OPPORTUNITY'


def score_candidate(title: str, snippet: str=''):
    text=clean_text((title or '')+' '+(snippet or ''))
    p=keyword_score(text,PROCUREMENT_TERMS); c=keyword_score(text,CONSULTANCY_TERMS)
    noise=keyword_score(text,NOISE_TERMS)
    if noise: p=max(0,p-noise); c=max(0,c-noise)
    return p,c,min(1.0,(p*0.45+c*0.55)/100)


def has_engineering_domain(text: str) -> bool:
    low=(text or '').lower()
    return any(term.lower() in low for term in ENGINEERING_DOMAIN_TERMS)


def _is_social_url(url: str) -> bool:
    try:
        host=(urlparse(url).hostname or '').lower()
        return host in SOCIAL_DOMAINS or any(host.endswith('.'+d) for d in {'linkedin.com','facebook.com','x.com','twitter.com'})
    except Exception: return False


def _is_saudi_db(text: str, country: str|None) -> bool:
    if normalize_country(country)!='Saudi Arabia': return False
    low=(text or '').lower()
    return any(t in low for t in SAUDI_DB_TERMS) and (
        any(t in low for t in CONSULTANCY_TERMS) or any(t in low for t in ['design','engineering','bim','تصميم','هندسي','مخططات'])
    )


def _actionable_notice(text: str, country: str|None) -> bool:
    low=(text or '').lower()
    if opportunity_type(low) in {'AWARD','ADDENDUM'}: return False
    if _is_saudi_db(low,country): return True
    signals=sum(1 for term in ACTIONABLE_NOTICE_TERMS if term in low)
    procurement=sum(1 for term in PROCUREMENT_TERMS if term in low)
    consultancy=sum(1 for term in CONSULTANCY_TERMS if term in low)
    return procurement>=1 and consultancy>=1 and signals>=1 and has_engineering_domain(low)


def upsert_candidate(db: Session, url: str, title: str='', snippet: str='', source: Source|None=None, method: str='UNKNOWN', detail: str=''):
    h=hash_text(url); c=db.scalar(select(DiscoveryCandidate).where(DiscoveryCandidate.url_hash==h))
    p,cs,conf=score_candidate(title,snippet)
    country=infer_country(title or '',source if source and source.country else None)
    if not country and (not source or source.country): country=infer_country(snippet or '',source)
    if c:
        c.last_seen_at=datetime.utcnow(); c.title=c.title or title; c.snippet=c.snippet or snippet
        c.procurement_score=max(c.procurement_score,p); c.consultancy_score=max(c.consultancy_score,cs); c.confidence=max(c.confidence,conf)
        c.country_guess=c.country_guess or country
        if _is_social_url(c.url):
            c.candidate_type='NOISE'; c.validation_status='REJECTED'; c.rejection_reason='SOCIAL_SOURCE_BLOCKED'
        db.commit(); return c,False
    blocked_social=_is_social_url(url) or (source and source.source_type=='SOCIAL_SIGNAL')
    candidate_type='NOISE' if blocked_social else ('DOCUMENT' if url.lower().split('?',1)[0].endswith(DOCUMENT_EXTENSIONS) else 'OPPORTUNITY')
    c=DiscoveryCandidate(
        candidate_type=candidate_type,url=url,url_hash=h,title=title[:1000] or None,snippet=snippet[:4000] or None,
        source_id=source.id if source else None,discovery_method=method,discovery_detail=detail,country_guess=country,
        opportunity_type_guess=opportunity_type((title or '')+' '+(snippet or '')),
        procurement_score=p,consultancy_score=cs,confidence=conf,
    )
    if blocked_social:
        c.validation_status='REJECTED'; c.rejection_reason='SOCIAL_SOURCE_BLOCKED'
    elif is_excluded_country(country) or (country and not is_target_country(country)):
        c.validation_status='REJECTED'; c.rejection_reason='EXCLUDED_GEOGRAPHY'
    db.add(c); db.commit(); db.refresh(c); return c,True


def _extract_main_html_text(html: str, final_url: str) -> str:
    try:
        main=trafilatura_extract(html or '',url=final_url,include_comments=False,include_tables=True,favor_recall=True,output_format='txt')
        if main and len(clean_text(main))>=80: return clean_text(main)[:300000]
    except Exception: pass
    soup=BeautifulSoup(html or '','html.parser')
    for bad in soup(['script','style','noscript','nav','footer']): bad.decompose()
    return clean_text(soup.get_text(' ',strip=True))[:300000]


def fetch_candidate_text(c: DiscoveryCandidate):
    r=httpx.get(c.url,timeout=DISCOVERY_REQUEST_TIMEOUT,follow_redirects=True,headers={'User-Agent':USER_AGENT})
    r.raise_for_status(); ctype=r.headers.get('content-type','').lower()
    is_pdf='application/pdf' in ctype or str(r.url).lower().split('?',1)[0].endswith('.pdf')
    if is_pdf:
        text,_engine=extract_pdf_text(r.content)
        return text[:300000],str(r.url)
    if c.candidate_type=='DOCUMENT' and not ('html' in ctype or 'text/' in ctype):
        raise RuntimeError('DOCUMENT_INDEXED_PARSING_NOT_YET_ENABLED_FOR_THIS_FORMAT')
    return _extract_main_html_text(r.text,str(r.url)),str(r.url)


def _two_or_four_digit_year(raw: str) -> int:
    y=int(raw)
    if y<100: return 2000+y if y<70 else 1900+y
    return y


def _parse_date_window(window: str):
    patterns=[
        (r'(20\d{2})[-/](\d{1,2})[-/](\d{1,2})','ymd'),
        (r'(\d{1,2})[-/](\d{1,2})[-/](20\d{2})','dmy'),
        (r'(\d{1,2})[-\s/](Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[-\s/](\d{2,4})','dmony'),
        (r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:,)?\s+(\d{2,4})','mondy'),
    ]
    for pattern,kind in patterns:
        m=re.search(pattern,window,re.I)
        if not m: continue
        try:
            if kind=='ymd': return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
            if kind=='dmy': return date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
            if kind=='dmony': return date(_two_or_four_digit_year(m.group(3)),MONTHS[m.group(2).lower()[:3]],int(m.group(1)))
            return date(_two_or_four_digit_year(m.group(3)),MONTHS[m.group(1).lower()[:3]],int(m.group(2)))
        except Exception: pass
    return None


def _extract_date_near(text: str, labels: list[str]):
    if not text: return None
    label='|'.join(re.escape(x) for x in labels)
    for m in re.finditer(rf'(?:{label})',text,re.I):
        parsed=_parse_date_window(text[m.end():m.end()+120])
        if parsed: return parsed
    return None


def _extract_deadline(text: str):
    return _extract_date_near(text,['deadline','closing date','submission deadline','bid closing','proposal due','آخر موعد','الموعد النهائي','موعد تقديم العروض','إقفال المناقصة','اغلاق المناقصة'])


def _extract_publication_date(text: str):
    return _extract_date_near(text,['publication date','published on','date published','notice date','issue date','posted','تاريخ النشر','تاريخ الإعلان','تاريخ الاعلان','تاريخ الطرح'])


def _evidence_type(c: DiscoveryCandidate, final_url: str) -> str:
    method=(c.discovery_method or '').upper()
    if 'NEWS_GAZETTE' in method: return 'NEWSPAPER_NOTICE'
    if final_url.lower().split('?',1)[0].endswith('.pdf'): return 'PDF_NOTICE'
    return 'WEB_NOTICE'


def validate_candidate(db: Session, c: DiscoveryCandidate, auto_promote: bool=AUTO_PROMOTE_TENDERS):
    source=db.get(Source,c.source_id) if c.source_id else None
    if c.candidate_type=='NOISE' or _is_social_url(c.url):
        c.validation_status='REJECTED'; c.rejection_reason='SOCIAL_SOURCE_BLOCKED'; db.commit(); return {'status':'REJECTED'}
    if is_excluded_country(c.country_guess) or (c.country_guess and not is_target_country(c.country_guess)):
        c.validation_status='REJECTED'; c.rejection_reason='EXCLUDED_GEOGRAPHY'; db.commit(); return {'status':'REJECTED'}
    preliminary=(c.title or '')+' '+(c.snippet or ''); saudi_db=_is_saudi_db(preliminary,c.country_guess)
    if c.procurement_score<6 or (c.consultancy_score<10 and not saudi_db):
        c.validation_status='REJECTED'; c.rejection_reason='LOW_RELEVANCE'; db.commit(); return {'status':'REJECTED'}
    try: text,final_url=fetch_candidate_text(c)
    except Exception as e:
        c.validation_status='FETCH_FAILED'; c.rejection_reason=str(e)[:120]; db.commit(); return {'status':'FETCH_FAILED'}
    combined=(c.title or '')+' '+text[:150000]
    p,cs,conf=score_candidate(combined,'')
    c.procurement_score=max(c.procurement_score,p); c.consultancy_score=max(c.consultancy_score,cs); c.confidence=max(c.confidence,conf)
    title_country=infer_country(c.title or '',source if source and source.country else None)
    body_country=infer_country(text,source if source and source.country else None)
    c.country_guess=title_country or body_country or c.country_guess; c.opportunity_type_guess=opportunity_type(combined)
    if is_excluded_country(c.country_guess) or (c.country_guess and not is_target_country(c.country_guess)):
        c.validation_status='REJECTED'; c.rejection_reason='EXCLUDED_GEOGRAPHY'; db.commit(); return {'status':'REJECTED'}
    if c.opportunity_type_guess in {'AWARD','ADDENDUM'}:
        c.validation_status='REJECTED'; c.rejection_reason='NOT_A_NEW_BID_OPPORTUNITY'; db.commit(); return {'status':'REJECTED'}
    if not has_engineering_domain(combined) and not _is_saudi_db(combined,c.country_guess):
        c.validation_status='REJECTED'; c.rejection_reason='NO_ENGINEERING_DOMAIN_EVIDENCE'; db.commit(); return {'status':'REJECTED'}
    if not _actionable_notice(combined,c.country_guess):
        c.validation_status='REJECTED'; c.rejection_reason='NON_ACTIONABLE_NEWS_OR_PAGE'; db.commit(); return {'status':'REJECTED'}
    if p<12 or (cs<12 and not _is_saudi_db(combined,c.country_guess)):
        c.validation_status='REJECTED'; c.rejection_reason='CONTENT_NOT_ENGINEERING_PROCUREMENT'; db.commit(); return {'status':'REJECTED'}
    deadline=_extract_deadline(combined); publication_date=_extract_publication_date(combined)
    result=run_analysis(c.country_guess or None,deadline,text,use_ai=False,publication_date=publication_date)
    if result['hard_reject']:
        c.validation_status='REJECTED'; c.rejection_reason=result['hard_reject_reason'] or 'HARD_RULE_REJECT'; db.commit(); return {'status':'REJECTED','reason':c.rejection_reason}
    participation=analyze_participation(c.country_guess,text)
    if participation['eligibility_status'] in {'NOT_ELIGIBLE_LANGUAGE','LOCAL_RESTRICTION'}:
        c.validation_status='REJECTED'; c.rejection_reason=participation['eligibility_status']; db.commit(); return {'status':'REJECTED','reason':c.rejection_reason}
    c.validation_status='VALIDATED'; c.rejection_reason=None
    if auto_promote:
        title=clean_text(c.title or '')[:500] or clean_text(text[:180])[:500] or 'Discovered engineering opportunity'
        fp=make_fingerprint(title=title,client='',country=c.country_guess or '',deadline=deadline,reference='')
        t=db.scalar(select(Tender).where(Tender.fingerprint==fp))
        if not t:
            needs_review=(deadline is None or publication_date is None or participation['eligibility_status']=='ELIGIBILITY_TO_VERIFY')
            t=Tender(
                title=title,fingerprint=fp,project_country=c.country_guess,source_url=final_url,
                publication_date=publication_date,submission_deadline=deadline,raw_text=text[:1000000],
                tender_status='REVIEW_REQUIRED' if needs_review else 'QUALIFIED',discovery_candidate_id=c.id,discovery_method=c.discovery_method,
                bid_route=participation['bid_route'],eligibility_status=participation['eligibility_status'],partner_requirement=participation['partner_requirement'],
                submission_language=participation['submission_language'],language_status=participation['language_status'],participation_notes=participation['notes'],
                source_evidence_type=_evidence_type(c,final_url),**{k:v for k,v in result.items() if k!='hard_reject'}
            )
            db.add(t); db.flush()
        c.tender_id=t.id; c.validation_status='PROMOTED'
        if source: source.useful_count=(source.useful_count or 0)+1
    db.commit(); return {'status':c.validation_status,'tender_id':c.tender_id}
