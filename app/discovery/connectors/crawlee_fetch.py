from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from ...config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT


@dataclass(slots=True)
class FetchResult:
    html: str
    final_url: str
    http_status: int | None
    engine: str
    rendered: bool = False


async def _crawlee_bs_fetch(url: str) -> FetchResult:
    from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext

    box={}
    crawler=BeautifulSoupCrawler(max_requests_per_crawl=1)

    @crawler.router.default_handler
    async def handler(context: BeautifulSoupCrawlingContext) -> None:
        box['html']=str(context.soup)
        box['url']=context.request.loaded_url or context.request.url

    await crawler.run([url])
    if not box.get('html'):
        raise RuntimeError('CRAWLEE_HTTP_EMPTY_RESPONSE')
    return FetchResult(box['html'],box.get('url') or url,200,'CRAWLEE_BS4',False)


async def _crawlee_playwright_fetch(url: str) -> FetchResult:
    from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext, PlaywrightPreNavCrawlingContext

    box={}
    crawler=PlaywrightCrawler(max_requests_per_crawl=1,headless=True,browser_type='chromium')

    @crawler.pre_navigation_hook
    async def pre_nav(context: PlaywrightPreNavCrawlingContext) -> None:
        # Images/fonts/media are irrelevant for tender extraction and waste bandwidth.
        await context.block_requests(extra_url_patterns=['google-analytics','doubleclick','facebook.net'])

    @crawler.router.default_handler
    async def handler(context: PlaywrightCrawlingContext) -> None:
        try:
            await context.page.wait_for_load_state('networkidle',timeout=10000)
        except Exception:
            pass
        box['html']=await context.page.content()
        box['url']=context.page.url

    await crawler.run([url])
    if not box.get('html'):
        raise RuntimeError('CRAWLEE_PLAYWRIGHT_EMPTY_RESPONSE')
    return FetchResult(box['html'],box.get('url') or url,200,'CRAWLEE_PLAYWRIGHT',True)


def _run(coro):
    # Scanner endpoints are synchronous FastAPI handlers and normally run in a worker
    # thread without an event loop. Keep a deterministic fallback for test environments.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError('ASYNC_EVENT_LOOP_ACTIVE_USE_HTTP_FALLBACK')


def fetch_page(url: str, *, render_js: bool=False) -> FetchResult:
    try:
        if render_js:
            return _run(_crawlee_playwright_fetch(url))
        return _run(_crawlee_bs_fetch(url))
    except Exception as crawlee_error:
        # Crawlee/Chromium is an enhancement, not a single point of failure. Static
        # HTTP fallback keeps the zero-cost system usable if the browser is unavailable.
        r=httpx.get(
            url,timeout=DISCOVERY_REQUEST_TIMEOUT,follow_redirects=True,
            headers={'User-Agent':USER_AGENT,'Accept-Language':'ar,en,fr;q=0.8'},
        )
        r.raise_for_status()
        engine='HTTPX_FALLBACK_AFTER_PLAYWRIGHT' if render_js else 'HTTPX_FALLBACK'
        return FetchResult(r.text,str(r.url),r.status_code,engine,False)
