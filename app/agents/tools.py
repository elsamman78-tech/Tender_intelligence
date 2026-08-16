from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..geography import TARGET_COUNTRIES, PRIORITY_COUNTRIES, normalize_country, is_target_country
from ..models import Source, DiscoveryQuery, DiscoveryCandidate
from ..discovery.coverage import coverage_snapshot, run_coverage_benchmark
from ..discovery.orchestrator import run_known_sources, run_open_discovery, validate_candidates, profile_candidates
from ..discovery.query_engine import run_query_fanout
from ..discovery.scanner import scan_source
from ..discovery.candidates import validate_candidate
from ..discovery.source_health import audit_all_sources, health_snapshot


TOOL_SCHEMAS = {
    'coverage_snapshot': {
        'type':'function','function':{
            'name':'coverage_snapshot','description':'Read accumulated search-engine coverage metrics without changing data.',
            'parameters':{'type':'object','properties':{}}
        }
    },
    'coverage_gaps': {
        'type':'function','function':{
            'name':'coverage_gaps','description':'Find target countries with the weakest verified/healthy source coverage.',
            'parameters':{'type':'object','properties':{'limit':{'type':'integer','minimum':1,'maximum':30}}}
        }
    },
    'health_snapshot': {
        'type':'function','function':{
            'name':'health_snapshot','description':'Read source health counts such as HEALTHY, DEGRADED, LOGIN_REQUIRED and RATE_LIMITED.',
            'parameters':{'type':'object','properties':{}}
        }
    },
    'audit_sources': {
        'type':'function','function':{
            'name':'audit_sources','description':'Probe a bounded batch of sources and classify access state. Use small batches to avoid hammering sites.',
            'parameters':{'type':'object','properties':{'limit':{'type':'integer','minimum':1,'maximum':100}}}
        }
    },
    'run_known_sources': {
        'type':'function','function':{
            'name':'run_known_sources','description':'Scan a bounded number of known ACTIVE/VERIFIED procurement sources.',
            'parameters':{'type':'object','properties':{'limit':{'type':'integer','minimum':1,'maximum':50}}}
        }
    },
    'run_open_discovery': {
        'type':'function','function':{
            'name':'run_open_discovery','description':'Run a bounded batch of highest-priority open-web discovery queries across all available free search providers.',
            'parameters':{'type':'object','properties':{'query_limit':{'type':'integer','minimum':1,'maximum':20}}}
        }
    },
    'run_country_discovery': {
        'type':'function','function':{
            'name':'run_country_discovery','description':'Run country-specific discovery queries for source, tender, private-sector or social-signal purposes.',
            'parameters':{'type':'object','required':['country'],'properties':{
                'country':{'type':'string'},
                'purpose':{'type':'string','enum':['SOURCE_SEARCH','TENDER_SEARCH','PRIVATE_SOURCE_SEARCH','LINKEDIN_SIGNAL','FACEBOOK_SIGNAL','X_SIGNAL','EARLY_SIGNAL']},
                'query_limit':{'type':'integer','minimum':1,'maximum':10},
            }}
        }
    },
    'profile_source_candidates': {
        'type':'function','function':{
            'name':'profile_source_candidates','description':'Profile newly discovered candidate source domains and look for procurement links, RSS and sitemaps.',
            'parameters':{'type':'object','properties':{'limit':{'type':'integer','minimum':1,'maximum':30}}}
        }
    },
    'validate_candidates': {
        'type':'function','function':{
            'name':'validate_candidates','description':'Validate opportunity candidates and promote qualifying non-social results into the deterministic tender analyzer.',
            'parameters':{'type':'object','properties':{'limit':{'type':'integer','minimum':1,'maximum':100}}}
        }
    },
    'scan_source': {
        'type':'function','function':{
            'name':'scan_source','description':'Scan one known source by database source id.',
            'parameters':{'type':'object','required':['source_id'],'properties':{'source_id':{'type':'integer'}}}
        }
    },
    'validate_candidate': {
        'type':'function','function':{
            'name':'validate_candidate','description':'Validate one opportunity candidate by id using the deterministic verification and analyzer pipeline.',
            'parameters':{'type':'object','required':['candidate_id'],'properties':{'candidate_id':{'type':'integer'}}}
        }
    },
    'coverage_benchmark': {
        'type':'function','function':{
            'name':'coverage_benchmark','description':'Benchmark available search providers on the same bounded set of queries and compare distinct and unique results.',
            'parameters':{'type':'object','properties':{
                'query_limit':{'type':'integer','minimum':1,'maximum':10},
                'result_limit':{'type':'integer','minimum':1,'maximum':20}
            }}
        }
    },
}

ROLE_TOOLS = {
    'SOURCE_DISCOVERY_AGENT':['coverage_gaps','run_country_discovery','profile_source_candidates','audit_sources','health_snapshot'],
    'OPPORTUNITY_DISCOVERY_AGENT':['run_known_sources','run_open_discovery','run_country_discovery','coverage_snapshot'],
    'VERIFICATION_AGENT':['validate_candidates','validate_candidate','audit_sources','health_snapshot'],
    'COVERAGE_AGENT':['coverage_snapshot','coverage_gaps','coverage_benchmark','health_snapshot'],
}


class ToolRuntime:
    def __init__(self, db: Session):
        self.db=db

    def schemas_for_role(self, role: str):
        return [TOOL_SCHEMAS[n] for n in ROLE_TOOLS.get(role,[]) if n in TOOL_SCHEMAS]

    def execute(self, name: str, args: dict | None=None):
        args=args or {}
        fn=getattr(self, f'tool_{name}', None)
        if not fn:
            return {'ok':False,'error':f'UNKNOWN_TOOL:{name}'}
        try:
            return fn(**args)
        except Exception as e:
            return {'ok':False,'error':str(e)[:1500]}

    def tool_coverage_snapshot(self):
        return coverage_snapshot(self.db)

    def tool_health_snapshot(self):
        return health_snapshot(self.db)

    def tool_audit_sources(self, limit: int=20):
        return audit_all_sources(self.db,max(1,min(int(limit),100)))

    def tool_run_known_sources(self, limit: int=10):
        return run_known_sources(self.db,max(1,min(int(limit),50)))

    def tool_run_open_discovery(self, query_limit: int=4):
        return run_open_discovery(self.db,max(1,min(int(query_limit),20)))

    def tool_profile_source_candidates(self, limit: int=10):
        return profile_candidates(self.db,max(1,min(int(limit),30)))

    def tool_validate_candidates(self, limit: int=25):
        return validate_candidates(self.db,max(1,min(int(limit),100)))

    def tool_scan_source(self, source_id: int):
        s=self.db.get(Source,int(source_id))
        if not s: return {'ok':False,'error':'SOURCE_NOT_FOUND'}
        scans=scan_source(self.db,s)
        return {'ok':True,'source_id':s.id,'scans':[{'status':x.status,'items_seen':x.items_seen,'new_candidates':x.new_candidates,'error':x.error} for x in scans]}

    def tool_validate_candidate(self, candidate_id: int):
        c=self.db.get(DiscoveryCandidate,int(candidate_id))
        if not c: return {'ok':False,'error':'CANDIDATE_NOT_FOUND'}
        return validate_candidate(self.db,c)

    def tool_coverage_benchmark(self, query_limit: int=3, result_limit: int=8):
        return run_coverage_benchmark(self.db,max(1,min(int(query_limit),10)),max(1,min(int(result_limit),20)))

    def tool_run_country_discovery(self, country: str, purpose: str='SOURCE_SEARCH', query_limit: int=3):
        c=normalize_country(country)
        if not c or not is_target_country(c):
            return {'ok':False,'error':'COUNTRY_NOT_IN_TARGET_POLICY','country':c or country}
        allowed={'SOURCE_SEARCH','TENDER_SEARCH','PRIVATE_SOURCE_SEARCH','LINKEDIN_SIGNAL','FACEBOOK_SIGNAL','X_SIGNAL','EARLY_SIGNAL'}
        if purpose not in allowed: return {'ok':False,'error':'INVALID_PURPOSE'}
        qs=self.db.scalars(select(DiscoveryQuery).where(
            DiscoveryQuery.enabled==True, DiscoveryQuery.country==c, DiscoveryQuery.purpose==purpose
        ).order_by(DiscoveryQuery.priority.desc(),DiscoveryQuery.last_run_at.asc()).limit(max(1,min(int(query_limit),10)))).all()
        # Some social/regional queries intentionally have no country. If no direct social query exists,
        # create one bounded query record so future runs can learn from it.
        if not qs and purpose in {'LINKEDIN_SIGNAL','FACEBOOK_SIGNAL','X_SIGNAL','PRIVATE_SOURCE_SEARCH','EARLY_SIGNAL'}:
            domain={'LINKEDIN_SIGNAL':'linkedin.com/posts','FACEBOOK_SIGNAL':'facebook.com','X_SIGNAL':'x.com'}.get(purpose)
            if domain:
                text=f'site:{domain} "{c}" (RFP OR EOI OR tender OR procurement OR "expression of interest") (consultant OR consultancy OR "project management")'
            elif purpose=='PRIVATE_SOURCE_SEARCH':
                text=f'"{c}" (developer OR utility OR operator OR bank OR university OR hospital OR infrastructure) (RFP OR EOI OR tender OR procurement) (consultant OR consultancy)'
            else:
                text=f'"{c}" ("procurement plan" OR "general procurement notice" OR prequalification OR EOI) consultant infrastructure'
            q=self.db.scalar(select(DiscoveryQuery).where(DiscoveryQuery.query_text==text))
            if not q:
                q=DiscoveryQuery(query_text=text,language='en',country=c,purpose=purpose,priority=75 if c not in PRIORITY_COUNTRIES else 95)
                self.db.add(q); self.db.commit(); self.db.refresh(q)
            qs=[q]
        results=[]
        for q in qs:
            results.append({'query_id':q.id,'query':q.query_text,'result':run_query_fanout(self.db,q,limit=10)})
        return {'ok':bool(qs),'country':c,'purpose':purpose,'queries_run':len(qs),'runs':results}

    def tool_coverage_gaps(self, limit: int=10):
        out=[]
        for country in TARGET_COUNTRIES:
            total=self.db.scalar(select(func.count(Source.id)).where(Source.country==country)) or 0
            trusted=self.db.scalar(select(func.count(Source.id)).where(
                Source.country==country, Source.lifecycle_status.in_(['ACTIVE','VERIFIED']), Source.trust_score>=70
            )) or 0
            healthy=self.db.scalar(select(func.count(Source.id)).where(Source.country==country,Source.health_status=='HEALTHY')) or 0
            source_queries=self.db.scalar(select(func.count(DiscoveryQuery.id)).where(
                DiscoveryQuery.country==country,DiscoveryQuery.purpose=='SOURCE_SEARCH'
            )) or 0
            score=(trusted*5)+(healthy*3)+min(total,5)+min(source_queries,2)
            out.append({'country':country,'priority':100 if country in PRIORITY_COUNTRIES else 70,
                        'sources':total,'trusted_sources':trusted,'healthy_sources':healthy,'source_queries':source_queries,'coverage_score':score})
        out.sort(key=lambda x:(x['coverage_score'], -x['priority'], x['country']))
        return {'count':min(len(out),max(1,min(int(limit),30))),'gaps':out[:max(1,min(int(limit),30))]}
