import httpx
from .base import SearchHit
from ...config import SEARXNG_URL, DISCOVERY_REQUEST_TIMEOUT, USER_AGENT


class SearXNGProvider:
    cost_class='FREE_LOCAL'

    def __init__(self, engine: str|None=None, name: str|None=None):
        self.engine=engine
        self.name=name or ('SEARXNG_'+engine.upper() if engine else 'SEARXNG_META')

    def available(self):
        return bool(SEARXNG_URL)

    def search(self, query: str, limit: int=10):
        if not self.available(): return []
        base=SEARXNG_URL.rstrip('/')
        params={'q':query,'format':'json'}
        if self.engine:
            params['engines']=self.engine
        r=httpx.get(base+'/search', params=params, timeout=DISCOVERY_REQUEST_TIMEOUT, headers={'User-Agent':USER_AGENT})
        r.raise_for_status()
        out=[]
        for i,item in enumerate(r.json().get('results',[])[:limit],1):
            url=item.get('url','') or ''
            if not url.startswith(('http://','https://')):
                continue
            out.append(SearchHit(url=url, title=item.get('title','') or '', snippet=item.get('content','') or '', rank=i))
        return out
