from __future__ import annotations

from urllib.parse import urlparse

from ..connectors.base import ConnectorResult
from .etimad import EtimadCollector


_COLLECTORS = [EtimadCollector()]


def collect_special_source(url: str, *, country: str|None=None) -> ConnectorResult|None:
    try:
        host=(urlparse(url).hostname or '').lower()
    except Exception:
        host=''
    for collector in _COLLECTORS:
        if collector.matches(host,url):
            return collector.scan(url,country=country)
    return None
