import httpx
from .base import SearchHit
from ...config import SEARXNG_URL, DISCOVERY_REQUEST_TIMEOUT, USER_AGENT

class SearXNGProvider:
    name='SEARXNG_LOCAL'
    cost_class='FREE_LOCAL'
    def available(self): return bool(SEARXNG_URL)
    def search(self, query: str, limit: int=10):
        if not self.available(): return []
        base=SEARXNG_URL.rstrip('/')
        r=httpx.get(base+'/search', params={'q':query,'format':'json'}, timeout=DISCOVERY_REQUEST_TIMEOUT, headers={'User-Agent':USER_AGENT})
        r.raise_for_status()
        out=[]
        for i,item in enumerate(r.json().get('results',[])[:limit],1):
            out.append(SearchHit(url=item.get('url',''), title=item.get('title',''), snippet=item.get('content',''), rank=i))
        return out
