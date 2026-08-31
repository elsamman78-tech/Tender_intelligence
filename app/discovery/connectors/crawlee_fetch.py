from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from ...config import DISCOVERY_REQUEST_TIMEOUT, USER_AGENT


@dataclass(slots=True)
class FetchResult:
    html: str
    final_url: str
    http_status: int | None
    engine: str
    rendered: bool = False


class AccessBlockedError(RuntimeError):
    """Remote source is reachable but denies anonymous automated access."""


class LoginRequiredError(RuntimeError):
    """Remote source redirects public traffic to an authentication page."""


def _looks_like_login(url: str, html: str='') -> bool:
    low_url=(url or '').lower()
    if any(x in low_url for x in ('/login','/signin','/sign-in','/usr/login','returnurl=')):
        return True
    sample=(html or '')[:12000].lower()
    signals=(
        'sign in','log in','login','username','password',
        'تسجيل الدخول','اسم المستخدم','كلمة المرور',
    )
    return sum(1 for x in signals if x in sample) >= 2


def _headers() -> dict[str,str]:
    return {
        'User-Agent':USER_AGENT,
        'Accept-Language':'ar,en,fr;q=0.8',
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }


def _httpx_fetch(url: str) -> FetchResult:
    # No crawler/session pool here: one bounded request, no hidden retry loop.
    timeout=min(float(DISCOVERY_REQUEST_TIMEOUT),20.0)
    with httpx.Client(timeout=timeout,follow_redirects=True,headers=_headers()) as client:
        r=client.get(url)
    if r.status_code in {401,403}:
        raise AccessBlockedError(f'ACCESS_BLOCKED_HTTP_{r.status_code}')
    r.raise_for_status()
    final_url=str(r.url)
    if _looks_like_login(final_url,r.text):
        raise LoginRequiredError('LOGIN_REQUIRED')
    return FetchResult(r.text,final_url,r.status_code,'HTTPX',False)


def _playwright_fetch(url: str) -> FetchResult:
    # Synchronous Playwright is deliberate: scan routes are synchronous FastAPI
    # handlers running in worker threads. This avoids cross-event-loop locks.
    from playwright.sync_api import sync_playwright

    timeout_ms=max(5000,min(int(float(DISCOVERY_REQUEST_TIMEOUT)*1000),20000))
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(
            user_agent=USER_AGENT,
            locale='en-US',
            extra_http_headers={'Accept-Language':'ar,en,fr;q=0.8'},
        )
        page=context.new_page()
        page.set_default_timeout(timeout_ms)
        page.set_default_navigation_timeout(timeout_ms)
        # Reduce bandwidth without affecting tender text/links.
        def route_handler(route):
            if route.request.resource_type in {'image','media','font'}:
                route.abort()
            else:
                route.continue_()
        page.route('**/*',route_handler)
        try:
            response=page.goto(url,wait_until='domcontentloaded',timeout=timeout_ms)
            status=response.status if response else None
            if status in {401,403}:
                raise AccessBlockedError(f'ACCESS_BLOCKED_HTTP_{status}')
            try:
                page.wait_for_load_state('networkidle',timeout=min(timeout_ms,7000))
            except Exception:
                pass
            html=page.content()
            final_url=page.url
            if _looks_like_login(final_url,html):
                raise LoginRequiredError('LOGIN_REQUIRED')
            return FetchResult(html,final_url,status or 200,'PLAYWRIGHT',True)
        finally:
            context.close()
            browser.close()


def fetch_page(url: str, *, render_js: bool=False) -> FetchResult:
    if not render_js:
        return _httpx_fetch(url)

    try:
        return _playwright_fetch(url)
    except (AccessBlockedError,LoginRequiredError):
        # These are source access states, not browser failures; do not retry/fallback.
        raise
    except Exception:
        # Browser unavailable / JS failure: one bounded HTTP fallback only.
        result=_httpx_fetch(url)
        result.engine='HTTPX_FALLBACK_AFTER_PLAYWRIGHT'
        return result
