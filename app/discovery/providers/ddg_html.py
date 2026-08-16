import httpx
from bs4 import BeautifulSoup
from .base import SearchHit
from ..utils import normalize_url, clean_text
from ...config import DDG_HTML_ENABLED, DISCOVERY_REQUEST_TIMEOUT, USER_AGENT

class DuckDuckGoHtmlProvider:
    name = 'DDG_HTML'
    cost_class = 'FREE_PUBLIC'
    endpoint = 'https://html.duckduckgo.com/html/'

    def available(self) -> bool:
        return DDG_HTML_ENABLED

    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        if not self.available():
            return []
        headers = {'User-Agent': USER_AGENT, 'Accept-Language': 'en-US,en;q=0.8'}
        with httpx.Client(timeout=DISCOVERY_REQUEST_TIMEOUT, follow_redirects=True, headers=headers) as c:
            r = c.post(self.endpoint, data={'q': query})
            r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        hits=[]
        for i, result in enumerate(soup.select('.result'), start=1):
            a = result.select_one('.result__a')
            if not a:
                continue
            url = normalize_url(a.get('href',''))
            if not url.startswith(('http://','https://')):
                continue
            sn = result.select_one('.result__snippet')
            hits.append(SearchHit(url=url, title=clean_text(a.get_text(' ', strip=True)), snippet=clean_text(sn.get_text(' ', strip=True) if sn else ''), rank=i))
            if len(hits)>=limit:
                break
        return hits
