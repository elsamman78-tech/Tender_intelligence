from __future__ import annotations

from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import httpx

from ..config import RSS_BRIDGE_ENABLED, RSS_BRIDGE_URL, DISCOVERY_REQUEST_TIMEOUT, USER_AGENT
from .utils import clean_text


def available() -> bool:
    return bool(RSS_BRIDGE_ENABLED and RSS_BRIDGE_URL)


def bridge_feed_url(page_url: str) -> str|None:
    if not available() or not page_url.startswith(('http://','https://')):
        return None
    # Generic procurement-link bridge. It is deliberately a fallback; source-specific
    # collectors remain the primary path for dynamic government portals.
    selector='a[href*="tender"],a[href*="procurement"],a[href*="rfp"],a[href*="eoi"],a[href*="bid"],a[href*="notice"]'
    params={
        'action':'display','bridge':'CssSelectorBridge','home_page':page_url,
        'url_selector':selector,'url_pattern':'','content_selector':'',
        'content_cleanup':'','title_cleanup':'','limit':'50','format':'Atom',
    }
    return RSS_BRIDGE_URL.rstrip('/')+'/?'+urlencode(params)


def _parse_feed(content: bytes) -> list[tuple[str,str,str]]:
    out=[]
    try:
        root=ET.fromstring(content)
        for node in root.iter():
            tag=node.tag.rsplit('}',1)[-1].lower()
            if tag not in {'item','entry'}:
                continue
            title=''; link=''; summary=''
            for ch in list(node):
                ct=ch.tag.rsplit('}',1)[-1].lower()
                if ct=='title': title=clean_text(ch.text or '')
                elif ct in {'description','summary','content'}: summary=clean_text(''.join(ch.itertext()))
                elif ct=='link': link=(ch.attrib.get('href') or ch.text or '').strip()
            if link and link.startswith(('http://','https://')):
                out.append((link,title,summary))
            if len(out)>=100: break
    except Exception:
        return []
    return out


def fetch_bridge_items(page_url: str) -> list[tuple[str,str,str]]:
    feed=bridge_feed_url(page_url)
    if not feed:
        return []
    try:
        r=httpx.get(feed,timeout=min(DISCOVERY_REQUEST_TIMEOUT,12),headers={'User-Agent':USER_AGENT},follow_redirects=True)
        r.raise_for_status()
        return _parse_feed(r.content)
    except Exception:
        return []
