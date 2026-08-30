import httpx
from bs4 import BeautifulSoup
from .base import SearchHit
from ..utils import normalize_url, clean_text
from ...config import DDG_HTML_ENABLED, DISCOVERY_REQUEST_TIMEOUT, USER_AGENT


class DuckDuckGoHtmlProvider:
    name = 'DDG_HTML'
    cost_class = 'FREE_PUBLIC'
    endpoint = 'https://html.duckduckgo.com/html/'
    lite_endpoint = 'https://lite.duckduckgo.com/lite/'

    def available(self) -> bool:
        return DDG_HTML_ENABLED

    def _parse(self, html: str, limit: int) -> list[SearchHit]:
        low=(html or '').lower()
        if 'anomaly-modal' in low or 'captcha' in low or 'select all squares containing a duck' in low:
            raise RuntimeError('DDG_BLOCKED_BY_BOT_CHALLENGE')
        soup=BeautifulSoup(html or '', 'html.parser')
        hits=[]; seen=set()

        # Standard no-JS HTML endpoint.
        for result in soup.select('.result'):
            a=result.select_one('a.result__a') or result.select_one('.result__title a')
            if not a:
                continue
            url=normalize_url(a.get('href',''),base='https://duckduckgo.com')
            if not url.startswith(('http://','https://')) or url in seen:
                continue
            sn=result.select_one('.result__snippet')
            hits.append(SearchHit(
                url=url,
                title=clean_text(a.get_text(' ',strip=True)),
                snippet=clean_text(sn.get_text(' ',strip=True) if sn else ''),
                rank=len(hits)+1,
            ))
            seen.add(url)
            if len(hits)>=limit:
                return hits

        # Lite endpoint / minor HTML variations.
        for a in soup.select('a.result-link, a.result__a'):
            url=normalize_url(a.get('href',''),base='https://duckduckgo.com')
            title=clean_text(a.get_text(' ',strip=True))
            if not title or not url.startswith(('http://','https://')) or url in seen:
                continue
            parent=a.find_parent(['tr','div'])
            snippet=clean_text(parent.get_text(' ',strip=True) if parent else '')
            hits.append(SearchHit(url=url,title=title,snippet=snippet[:2000],rank=len(hits)+1))
            seen.add(url)
            if len(hits)>=limit:
                break
        return hits

    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        if not self.available():
            return []
        headers={
            'User-Agent':USER_AGENT,
            'Accept-Language':'en-US,en;q=0.8',
            'Accept':'text/html,application/xhtml+xml',
        }
        errors=[]
        attempts=[
            ('GET',self.endpoint,{'params':{'q':query,'kl':'us-en'}}),
            ('POST',self.endpoint,{'data':{'q':query,'kl':'us-en'}}),
            ('GET',self.lite_endpoint,{'params':{'q':query}}),
        ]
        with httpx.Client(timeout=DISCOVERY_REQUEST_TIMEOUT,follow_redirects=True,headers=headers) as c:
            for method,url,kwargs in attempts:
                try:
                    r=c.request(method,url,**kwargs)
                    r.raise_for_status()
                    hits=self._parse(r.text,limit)
                    if hits:
                        return hits
                    errors.append(f'{method}:{url}:ZERO_RESULTS')
                except Exception as e:
                    errors.append(str(e))
        raise RuntimeError('DDG_NO_RESULTS_OR_BLOCKED: '+' | '.join(errors[-3:]))
