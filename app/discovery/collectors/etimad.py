from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urljoin
import re

from bs4 import BeautifulSoup

from ..connectors.base import ConnectorResult, ExtractedOpportunity
from ..connectors.crawlee_fetch import fetch_page
from ..utils import clean_text


class EtimadCollector:
    key='SAUDI_ETIMAD_COLLECTOR'
    domains=('tenders.etimad.sa',)
    page_size=24
    max_pages=12
    stale_days=35

    def matches(self, host: str, url: str='') -> bool:
        h=(host or '').lower()
        return any(h==d or h.endswith('.'+d) for d in self.domains)

    def _page_url(self,page_number: int) -> str:
        return (
            'https://tenders.etimad.sa/Tender/AllTendersForVisitor?'
            '&MultipleSearch=&TenderCategory=&ReferenceNumber=&TenderNumber=&agency='
            '&ConditionaBookletRange=&PublishDate=&LastOfferPresentationDate='
            '&TenderAreasIdString=&TenderTypeId=NaN&TenderSubActivityId=&AgencyCode='
            '&FromLastOfferPresentationDateString=&ToLastOfferPresentationDateString='
            '&SortDirection=DESC&Sort=SubmitionDate&PageSize=24&IsSearch=true'
            '&ConditionaBookletRange=&PublishDate=undefined&PageNumber={}'
        ).format(page_number)

    @staticmethod
    def _parse_date(text: str) -> date|None:
        m=re.search(r'\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b',text or '')
        if not m:
            return None
        try:
            return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
        except Exception:
            return None

    @staticmethod
    def parse_page(html: str, base_url: str) -> list[ExtractedOpportunity]:
        soup=BeautifulSoup(html or '','html.parser')
        cards=soup.select('div.col-12.col-md-12.mb-4')
        out=[]; seen=set()
        for card in cards:
            title_el=card.find('h3')
            title=clean_text(title_el.get_text(' ',strip=True) if title_el else '')
            if not title:
                continue
            href=''
            for a in card.find_all('a',href=True):
                raw=(a.get('href') or '').strip()
                low=raw.lower()
                if '/tender/' in low and 'alltendersforvisitor' not in low:
                    href=urljoin(base_url,raw); break
            if not href:
                a=card.find('a',href=True)
                if a:
                    href=urljoin(base_url,(a.get('href') or '').strip())
            if not href or href in seen:
                continue
            text=clean_text(card.get_text(' ',strip=True))
            published=EtimadCollector._parse_date(text)
            type_el=card.select_one('span.badge')
            tender_type=clean_text(type_el.get_text(' ',strip=True) if type_el else '')
            authority=''
            for p in card.find_all('p'):
                t=clean_text(p.get_text(' ',strip=True))
                if t and t not in title and len(t)>3:
                    authority=t; break
            snippet_parts=[]
            if published: snippet_parts.append(f'Publication Date {published.isoformat()}')
            if tender_type: snippet_parts.append(f'Tender Type {tender_type}')
            if authority: snippet_parts.append(f'Tendering Authority {authority}')
            snippet_parts.append(text[:1800])
            out.append(ExtractedOpportunity(
                url=href,title=title[:500],snippet=' | '.join(snippet_parts)[:3000],evidence='ETIMAD_LISTING'
            ))
            seen.add(href)
        return out

    def scan(self, url: str, *, country: str|None=None) -> ConnectorResult:
        all_items=[]; seen=set(); final_url=url; http_status=None; rendered=False
        today=date.today(); stale_pages=0
        for page in range(1,self.max_pages+1):
            page_url=self._page_url(page)
            fetched=fetch_page(page_url,render_js=True)
            final_url=fetched.final_url; http_status=fetched.http_status; rendered=rendered or fetched.rendered
            items=self.parse_page(fetched.html,fetched.final_url)
            if not items:
                if page==1:
                    # Preserve generic diagnostics when Etimad changes its markup.
                    raise RuntimeError('ETIMAD_LAYOUT_CHANGED_OR_EMPTY')
                break
            page_dates=[]
            for item in items:
                d=self._parse_date(item.snippet)
                if d: page_dates.append(d)
                if item.url not in seen:
                    all_items.append(item); seen.add(item.url)
            if page_dates and all((today-d).days > self.stale_days for d in page_dates):
                stale_pages+=1
            else:
                stale_pages=0
            if stale_pages>=1:
                break
        return ConnectorResult(
            items=all_items,final_url=final_url,http_status=http_status,
            connector_name=self.key,rendered=rendered,
        )
