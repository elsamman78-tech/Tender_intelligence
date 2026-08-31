from __future__ import annotations

from urllib.parse import urlparse

from .base import PortalHtmlConnector, ConnectorResult, ExtractedOpportunity
from .crawlee_fetch import fetch_page
from .profiles import profile_for_host, PortalProfile


class ProfiledPortalConnector(PortalHtmlConnector):
    def __init__(self, profile: PortalProfile|None=None):
        self.profile=profile
        self.name=profile.key if profile else 'GENERIC_PORTAL'
        self.render_js=bool(profile and profile.render_js)

    def extract(self, html: str, base_url: str, *, country: str|None=None):
        items=super().extract(html,base_url,country=country)
        if not self.profile:
            return items
        blocked=tuple(x.lower() for x in self.profile.blocked_path_contains)
        if not blocked:
            return items
        out=[]
        for item in items:
            low=item.url.lower()
            if any(x in low for x in blocked):
                continue
            out.append(item)
        return out

    def scan(self, url: str, *, country: str|None=None) -> ConnectorResult:
        fetched=fetch_page(url,render_js=self.render_js)
        items=self.extract(fetched.html,fetched.final_url,country=country)
        return ConnectorResult(
            items=items,final_url=fetched.final_url,http_status=fetched.http_status,
            connector_name=f'{self.name}:{fetched.engine}',rendered=fetched.rendered,
        )


def connector_for_url(url: str) -> ProfiledPortalConnector:
    try:
        host=(urlparse(url).hostname or '').lower()
    except Exception:
        host=''
    return ProfiledPortalConnector(profile_for_host(host))


def scan_url(url: str, *, country: str|None=None) -> ConnectorResult:
    return connector_for_url(url).scan(url,country=country)
