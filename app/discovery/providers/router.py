from .ddg_html import DuckDuckGoHtmlProvider
from .bing_html import BingHtmlProvider
from .searxng import SearXNGProvider
from .agent_reach_search import AgentReachSearchProvider
from .gdelt_news import GdeltNewsProvider


def all_providers():
    return [
        SearXNGProvider('google','SEARXNG_GOOGLE'),
        SearXNGProvider('bing','SEARXNG_BING'),
        SearXNGProvider(None,'SEARXNG_META'),
        DuckDuckGoHtmlProvider(),
        BingHtmlProvider(),
        GdeltNewsProvider(),
        AgentReachSearchProvider(),
    ]


def providers():
    return [x for x in all_providers() if x.available()]


def provider_status():
    return [{'name':x.name,'available':bool(x.available()),'cost_class':x.cost_class} for x in all_providers()]
