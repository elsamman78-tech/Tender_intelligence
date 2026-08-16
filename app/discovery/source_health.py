from __future__ import annotations

from datetime import datetime
import re
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT, ZERO_COST_MODE
from ..models import Source, SourceChannel

LOGIN_HINTS = [
    r'\bsign[ -]?in\b', r'\blog[ -]?in\b', r'username', r'password', r'otp',
    r'تسجيل الدخول', r'اسم المستخدم', r'كلمة المرور',
]
CAPTCHA_HINTS = [r'captcha', r'recaptcha', r'cloudflare challenge', r'verify you are human', r'checking your browser']
PAYMENT_HINTS = [r'payment required', r'subscription required', r'paywall', r'purchase access', r'اشتراك مدفوع']


def _classify_response(r: httpx.Response) -> tuple[str, str | None]:
    status=r.status_code
    text=(r.text or '')[:20000].lower()
    final_url=str(r.url).lower()
    if status == 429:
        return 'RATE_LIMITED', 'HTTP 429'
    if status in {401, 407}:
        return 'LOGIN_REQUIRED', f'HTTP {status}'
    if status == 402:
        return 'BLOCKED_BY_COST_POLICY', 'HTTP 402'
    if status == 403:
        if any(re.search(p,text,re.I) for p in CAPTCHA_HINTS):
            return 'DEGRADED', 'HTTP 403 / anti-bot challenge'
        if any(re.search(p,text,re.I) for p in LOGIN_HINTS) or 'login' in final_url or 'signin' in final_url:
            return 'LOGIN_REQUIRED', 'HTTP 403 / login required'
        return 'DEGRADED', 'HTTP 403'
    if status in {404, 410}:
        return 'FAILED', f'HTTP {status}'
    if status >= 500:
        return 'DEGRADED', f'HTTP {status}'
    if status >= 400:
        return 'DEGRADED', f'HTTP {status}'
    if any(re.search(p,text,re.I) for p in PAYMENT_HINTS):
        return 'BLOCKED_BY_COST_POLICY', 'Page indicates paid/subscription access'
    if ('login' in final_url or 'signin' in final_url) and any(re.search(p,text,re.I) for p in LOGIN_HINTS):
        return 'LOGIN_REQUIRED', 'Redirected to login page'
    if any(re.search(p,text,re.I) for p in CAPTCHA_HINTS):
        return 'DEGRADED', 'Anti-bot/CAPTCHA page detected'
    return 'HEALTHY', None


def _probe(url: str) -> tuple[str, str | None, int | None]:
    try:
        r=httpx.get(url,timeout=min(DISCOVERY_REQUEST_TIMEOUT,15),follow_redirects=True,
                    headers={'User-Agent':USER_AGENT,'Accept-Language':'en,ar;q=0.8,fr;q=0.6'})
        state,detail=_classify_response(r)
        return state,detail,r.status_code
    except httpx.TimeoutException:
        return 'DEGRADED','Timeout',None
    except httpx.RequestError as e:
        return 'FAILED',str(e)[:500],None
    except Exception as e:
        return 'FAILED',str(e)[:500],None


def audit_source(db: Session, source: Source, channel_limit: int=3) -> dict:
    now=datetime.utcnow()
    if not source.enabled:
        source.health_status='DISABLED'; source.last_scan_at=now; db.commit()
        return {'source_id':source.id,'state':'DISABLED','probes':[]}
    if ZERO_COST_MODE and (source.requires_payment or source.cost_class in {'PAID','UNKNOWN'}):
        source.health_status='BLOCKED_BY_COST_POLICY'; source.last_scan_at=now; db.commit()
        return {'source_id':source.id,'state':'BLOCKED_BY_COST_POLICY','probes':[]}

    urls=[]
    if source.base_url: urls.append(('BASE',source.base_url,None))
    channels=db.scalars(select(SourceChannel).where(SourceChannel.source_id==source.id,SourceChannel.enabled==True)
                        .order_by(SourceChannel.priority_order.asc()).limit(channel_limit)).all()
    for ch in channels:
        if ch.url and ch.url not in {u for _,u,_ in urls}: urls.append((ch.purpose,ch.url,ch))
    if not urls:
        source.health_status='FAILED'; source.last_error='NO_URL'; source.last_scan_at=now; db.commit()
        return {'source_id':source.id,'state':'FAILED','probes':[],'error':'NO_URL'}

    probes=[]
    for purpose,url,ch in urls:
        state,detail,http_status=_probe(url)
        probes.append({'purpose':purpose,'url':url,'state':state,'detail':detail,'http_status':http_status})
        if ch is not None:
            ch.health_status=state; ch.last_scan_at=now; ch.last_error=detail
            if state=='HEALTHY': ch.last_success_at=now

    states=[p['state'] for p in probes]
    precedence=['HEALTHY','LOGIN_REQUIRED','RATE_LIMITED','DEGRADED','BLOCKED_BY_COST_POLICY','FAILED']
    final=next((x for x in precedence if x in states),'FAILED')
    # If a public base page is healthy but every procurement channel requires login,
    # retain LOGIN_REQUIRED so the source doctor exposes the real procurement access state.
    channel_states=[p['state'] for p in probes if p['purpose']!='BASE']
    if channel_states and 'HEALTHY' not in channel_states:
        if all(x=='LOGIN_REQUIRED' for x in channel_states): final='LOGIN_REQUIRED'
        elif 'RATE_LIMITED' in channel_states: final='RATE_LIMITED'

    source.health_status=final; source.last_scan_at=now
    source.requires_login=1 if final=='LOGIN_REQUIRED' else source.requires_login
    source.last_error='; '.join(filter(None,(p['detail'] for p in probes)))[:1000] or None
    if final=='HEALTHY':
        source.last_success_at=now; source.success_count=(source.success_count or 0)+1; source.last_error=None
    source.scan_count=(source.scan_count or 0)+1
    db.commit()
    return {'source_id':source.id,'name':source.name,'state':final,'probes':probes}


def audit_all_sources(db: Session, limit: int=0) -> dict:
    q=select(Source).order_by(Source.priority.asc(),Source.trust_score.desc(),Source.last_scan_at.asc())
    rows=db.scalars(q).all()
    if limit and limit > 0: rows=rows[:limit]
    summary={'audited':0,'states':{},'results':[]}
    for s in rows:
        r=audit_source(db,s); summary['audited']+=1
        state=r['state']; summary['states'][state]=summary['states'].get(state,0)+1
        summary['results'].append({'source_id':s.id,'name':s.name,'state':state})
    return summary


def health_snapshot(db: Session) -> dict:
    rows=db.scalars(select(Source)).all()
    states={}
    for s in rows:
        states[s.health_status]=states.get(s.health_status,0)+1
    return {'total':len(rows),'states':states}
