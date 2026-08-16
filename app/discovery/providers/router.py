from .ddg_html import DuckDuckGoHtmlProvider
from .searxng import SearXNGProvider
from .agent_reach_search import AgentReachSearchProvider


def all_providers():
    # Google and Bing are reached through the user's local SearXNG instance.
    # This avoids paid/retired official APIs while keeping them independently measurable.
    return [
        SearXNGProvider('google','SEARXNG_GOOGLE'),
        SearXNGProvider('bing','SEARXNG_BING'),
        SearXNGProvider(None,'SEARXNG_META'),
        DuckDuckGoHtmlProvider(),
        AgentReachSearchProvider(),
    ]


def providers():
    return [x for x in all_providers() if x.available()]


def provider_status():
    return [{'name':x.name,'available':bool(x.available()),'cost_class':x.cost_class} for x in all_providers()]
