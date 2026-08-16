from .ddg_html import DuckDuckGoHtmlProvider
from .searxng import SearXNGProvider
from .agent_reach_search import AgentReachSearchProvider


def providers():
    # Free local first, then public zero-key, then optional Agent-Reach upstream.
    p=[SearXNGProvider(), DuckDuckGoHtmlProvider(), AgentReachSearchProvider()]
    return [x for x in p if x.available()]


def provider_status():
    allp=[SearXNGProvider(), DuckDuckGoHtmlProvider(), AgentReachSearchProvider()]
    return [{'name':x.name,'available':bool(x.available()),'cost_class':x.cost_class} for x in allp]
