from __future__ import annotations

import httpx

from .base import SearchHit
from ...config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT


class GdeltNewsProvider:
    """Free GDELT DOC 2.0 index dedicated to newspaper/gazette discovery."""
    name='GDELT_NEWS'
    cost_class='FREE_PUBLIC'
    news_only=True
    endpoint='https://api.gdeltproject.org/api/v2/doc/doc'

    def available(self):
        return True

    def search(self,query: str,limit: int=10):
        low=(query or '').lower()
        news_markers=('newspaper','gazette','e-paper','tender notice','procurement notice','صحيفة','جريدة')
        if not any(x in low for x in news_markers):
            return []
        params={
            'query':query,
            'mode':'ArtList',
            'maxrecords':max(1,min(int(limit),75)),
            'format':'json',
            'sort':'HybridRel',
        }
        r=httpx.get(self.endpoint,params=params,timeout=DISCOVERY_REQUEST_TIMEOUT,headers={'User-Agent':USER_AGENT})
        r.raise_for_status(); data=r.json()
        articles=data.get('articles',[]) if isinstance(data,dict) else []
        out=[]
        for i,item in enumerate(articles[:limit],1):
            url=item.get('url') or ''
            if not url.startswith(('http://','https://')): continue
            meta=' | '.join(str(x) for x in [item.get('domain'),item.get('sourcecountry'),item.get('language'),item.get('seendate')] if x)
            out.append(SearchHit(url=url,title=item.get('title') or '',snippet=meta,rank=i))
        return out
