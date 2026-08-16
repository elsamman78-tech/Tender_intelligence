import json, shlex, subprocess
from .base import SearchHit
from ...config import AGENT_REACH_ENABLED, AGENT_REACH_SEARCH_COMMAND
from ..agent_reach import doctor

class AgentReachSearchProvider:
    """Actual optional Agent-Reach/upstream adapter.

    Agent-Reach currently health-checks/routes upstream tools rather than exposing one universal
    search wrapper. If AGENT_REACH_SEARCH_COMMAND is configured, this adapter executes that
    zero-cost upstream command. The command template must contain {query}; JSON-lines or a JSON
    list with url/title/snippet fields is accepted.
    """
    name='AGENT_REACH_UPSTREAM'
    cost_class='FREE_OPTIONAL'
    def available(self):
        if not AGENT_REACH_ENABLED or not AGENT_REACH_SEARCH_COMMAND:
            return False
        d=doctor(timeout=5)
        return d.installed and d.ok
    def search(self, query: str, limit: int=10):
        if not self.available(): return []
        cmd=AGENT_REACH_SEARCH_COMMAND.replace('{query}', query)
        p=subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=60)
        if p.returncode!=0:
            raise RuntimeError(p.stderr.strip() or 'Agent-Reach upstream search failed')
        raw=p.stdout.strip()
        if not raw: return []
        items=[]
        try:
            data=json.loads(raw)
            if isinstance(data,dict): data=data.get('results',[])
            if isinstance(data,list): items=data
        except Exception:
            for line in raw.splitlines():
                try: items.append(json.loads(line))
                except Exception: pass
        out=[]
        for i,x in enumerate(items[:limit],1):
            if isinstance(x,dict) and x.get('url'):
                out.append(SearchHit(url=x['url'],title=x.get('title',''),snippet=x.get('snippet') or x.get('content',''),rank=i))
        return out
