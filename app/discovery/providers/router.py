from .ddg_html import DuckDuckGoHtmlProvider
from .bing_html import BingHtmlProvider
from .searxng import SearXNGProvider
from .agent_reach_search import AgentReachSearchProvider


def all_providers():
    # Google and Bing via local SearXNG remain preferred when available. Public HTML
    # fallbacks keep zero-cost discovery functional when SearXNG is not installed.
    return [
        SearXNGProvider('google','SEARXNG_GOOGLE'),
        SearXNGProvider('bing','SEARXNG_BING'),
        SearXNGProvider(None,'SEARXNG_META'),
        DuckDuckGoHtmlProvider(),
        BingHtmlProvider(),
        AgentReachSearchProvider(),
    ]


def providers():
    return [x for x in all_providers() if x.available()]


def provider_status():
    return [{'name':x.name,'available':bool(x.available()),'cost_class':x.cost_class} for x in all_providers()]
