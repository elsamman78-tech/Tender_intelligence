from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..geography import TARGET_COUNTRIES, PRIORITY_COUNTRIES
from ..models import Source, DiscoveryQuery, DiscoveryCandidate, Tender


def _counts(rows):
    return {k or '': int(v or 0) for k,v in rows}


def country_coverage_snapshot(db: Session) -> dict:
    source_counts=_counts(db.execute(select(Source.country,func.count(Source.id)).where(Source.country.is_not(None)).group_by(Source.country)).all())
    verified_counts=_counts(db.execute(select(Source.country,func.count(Source.id)).where(
        Source.country.is_not(None),Source.lifecycle_status.in_(['ACTIVE','VERIFIED']),Source.trust_score>=70
    ).group_by(Source.country)).all())
    healthy_counts=_counts(db.execute(select(Source.country,func.count(Source.id)).where(
        Source.country.is_not(None),Source.health_status=='HEALTHY'
    ).group_by(Source.country)).all())
    query_rows=db.execute(select(DiscoveryQuery.country,DiscoveryQuery.purpose,func.count(DiscoveryQuery.id)).where(
        DiscoveryQuery.country.is_not(None)
    ).group_by(DiscoveryQuery.country,DiscoveryQuery.purpose)).all()
    query_counts={(country,purpose):int(count or 0) for country,purpose,count in query_rows}
    candidate_counts=_counts(db.execute(select(DiscoveryCandidate.country_guess,func.count(DiscoveryCandidate.id)).where(
        DiscoveryCandidate.country_guess.is_not(None)
    ).group_by(DiscoveryCandidate.country_guess)).all())
    tender_counts=_counts(db.execute(select(Tender.project_country,func.count(Tender.id)).where(
        Tender.project_country.is_not(None)
    ).group_by(Tender.project_country)).all())

    rows=[]
    for country in TARGET_COUNTRIES:
        sources=source_counts.get(country,0); verified=verified_counts.get(country,0); healthy=healthy_counts.get(country,0)
        source_queries=query_counts.get((country,'SOURCE_SEARCH'),0); tender_queries=query_counts.get((country,'TENDER_SEARCH'),0)
        candidates=candidate_counts.get(country,0); tenders=tender_counts.get(country,0)
        if verified>=2 and healthy>=1: status='COVERED'
        elif verified>=1 or sources>=2: status='PARTIAL'
        else: status='GAP'
        rows.append({'country':country,'priority':100 if country in PRIORITY_COUNTRIES else 70,'status':status,
                     'sources':sources,'verified_sources':verified,'healthy_sources':healthy,
                     'source_queries':source_queries,'tender_queries':tender_queries,
                     'candidates':candidates,'tenders':tenders})
    order={'GAP':0,'PARTIAL':1,'COVERED':2}
    rows.sort(key=lambda x:(order[x['status']],-x['priority'],x['verified_sources'],x['healthy_sources'],x['country']))
    return {'countries':rows,'counts':{
        'target':len(rows),'covered':sum(1 for x in rows if x['status']=='COVERED'),
        'partial':sum(1 for x in rows if x['status']=='PARTIAL'),'gaps':sum(1 for x in rows if x['status']=='GAP')
    }}
