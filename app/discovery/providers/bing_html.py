import httpx
from bs4 import BeautifulSoup

from .base import SearchHit
from ..utils import normalize_url, clean_text
from ...config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT


class BingHtmlProvider:
    name='BING_HTML'
    cost_class='FREE_PUBLIC'
    endpoint='https://www.bing.com/search'

    def available(self) -> bool:
        return True

    def search(self, query: str, limit: int=10) -> list[SearchHit]:
        headers={
            'User-Agent':USER_AGENT,
            'Accept-Language':'en-US,en;q=0.8',
            'Accept':'text/html,application/xhtml+xml',
        }
        with httpx.Client(timeout=DISCOVERY_REQUEST_TIMEOUT,follow_redirects=True,headers=headers) as c:
            r=c.get(self.endpoint,params={'q':query,'count':max(10,min(limit,20))})
            r.raise_for_status()
        low=r.text.lower()
        if 'captcha' in low and 'b_algo' not in low:
            raise RuntimeError('BING_BLOCKED_BY_BOT_CHALLENGE')
        soup=BeautifulSoup(r.text,'html.parser')
        hits=[]; seen=set()
        for row in soup.select('li.b_algo'):
            a=row.select_one('h2 a')
            if not a:
                continue
            url=normalize_url(a.get('href',''))
            title=clean_text(a.get_text(' ',strip=True))
            if not title or not url.startswith(('http://','https://')) or url in seen:
                continue
            sn=row.select_one('.b_caption p') or row.select_one('.b_snippet')
            hits.append(SearchHit(
                url=url,title=title,
                snippet=clean_text(sn.get_text(' ',strip=True) if sn else ''),
                rank=len(hits)+1,
            ))
            seen.add(url)
            if len(hits)>=limit:
                break
        if not hits:
            raise RuntimeError('BING_HTML_ZERO_RESULTS_OR_LAYOUT_CHANGED')
        return hits
