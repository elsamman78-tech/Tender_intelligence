from __future__ import annotations

from datetime import datetime
import time
import httpx

from ..config import CHANGEDETECTION_ENABLED, CHANGEDETECTION_URL, CHANGEDETECTION_API_KEY, DISCOVERY_REQUEST_TIMEOUT

_CACHE={'at':0.0,'watches':{}}


def available() -> bool:
    return bool(CHANGEDETECTION_ENABLED and CHANGEDETECTION_URL)


def _headers() -> dict[str,str]:
    return {'x-api-key':CHANGEDETECTION_API_KEY} if CHANGEDETECTION_API_KEY else {}


def _base() -> str:
    return CHANGEDETECTION_URL.rstrip('/')


def list_watches(force: bool=False) -> dict:
    if not available():
        return {}
    now=time.time()
    if not force and now-_CACHE['at'] < 60:
        return _CACHE['watches']
    try:
        r=httpx.get(_base()+'/api/v1/watch',headers=_headers(),timeout=min(DISCOVERY_REQUEST_TIMEOUT,8))
        r.raise_for_status(); data=r.json()
        if not isinstance(data,dict): data={}
        _CACHE['at']=now; _CACHE['watches']=data
        return data
    except Exception:
        return {}


def ensure_watch(url: str) -> str|None:
    if not available() or not url.startswith(('http://','https://')):
        return None
    watches=list_watches()
    for uuid,item in watches.items():
        if isinstance(item,dict) and (item.get('url') or '').rstrip('/')==url.rstrip('/'):
            return uuid
    try:
        r=httpx.post(_base()+'/api/v1/watch',json={'url':url},headers=_headers(),timeout=min(DISCOVERY_REQUEST_TIMEOUT,8))
        if r.status_code not in {200,201}:
            return None
        uuid=(r.json() or {}).get('uuid')
        _CACHE['at']=0
        return uuid
    except Exception:
        return None


def _as_datetime(value) -> datetime|None:
    if value in {None,'',0,'0'}:
        return None
    if isinstance(value,(int,float)):
        try: return datetime.utcfromtimestamp(float(value))
        except Exception: return None
    s=str(value).strip()
    try:
        if s.replace('.','',1).isdigit(): return datetime.utcfromtimestamp(float(s))
        return datetime.fromisoformat(s.replace('Z','+00:00')).replace(tzinfo=None)
    except Exception:
        return None


def should_scan(url: str, last_scan_at: datetime|None) -> bool|None:
    """Return False only when ChangeDetection has authoritative evidence of no change.

    True means it changed since our last scan. None means the helper is unavailable or has
    insufficient history, in which case normal discovery proceeds without depending on it.
    """
    if not available() or not last_scan_at:
        if available(): ensure_watch(url)
        return None
    uuid=ensure_watch(url)
    if not uuid:
        return None
    item=list_watches().get(uuid) or {}
    last_changed=_as_datetime(item.get('last_changed'))
    last_checked=_as_datetime(item.get('last_checked'))
    if not last_checked or last_checked <= last_scan_at:
        return None
    if not last_changed:
        return None
    return last_changed > last_scan_at


def sync_urls(urls: list[str]) -> dict:
    if not available():
        return {'available':False,'created_or_present':0}
    count=0
    for url in dict.fromkeys(u for u in urls if u.startswith(('http://','https://'))):
        if ensure_watch(url): count+=1
    return {'available':True,'created_or_present':count}
