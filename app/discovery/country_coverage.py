from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..geography import TARGET_COUNTRIES, PRIORITY_COUNTRIES
from ..models import Source, DiscoveryQuery, DiscoveryCandidate, Tender


def country_coverage_snapshot(db: Session) -> dict:
    rows=[]
    for country in TARGET_COUNTRIES:
        sources=db.scalar(select(func.count(Source.id)).where(Source.country==country)) or 0
        verified=db.scalar(select(func.count(Source.id)).where(
            Source.country==country, Source.lifecycle_status.in_(['ACTIVE','VERIFIED']), Source.trust_score>=70
        )) or 0
        healthy=db.scalar(select(func.count(Source.id)).where(Source.country==country,Source.health_status=='HEALTHY')) or 0
        source_queries=db.scalar(select(func.count(DiscoveryQuery.id)).where(DiscoveryQuery.country==country,DiscoveryQuery.purpose=='SOURCE_SEARCH')) or 0
        tender_queries=db.scalar(select(func.count(DiscoveryQuery.id)).where(DiscoveryQuery.country==country,DiscoveryQuery.purpose=='TENDER_SEARCH')) or 0
        candidates=db.scalar(select(func.count(DiscoveryCandidate.id)).where(DiscoveryCandidate.country_guess==country)) or 0
        tenders=db.scalar(select(func.count(Tender.id)).where(Tender.project_country==country)) or 0
        if verified>=2 and healthy>=1: status='COVERED'
        elif verified>=1 or sources>=2: status='PARTIAL'
        else: status='GAP'
        rows.append({'country':country,'priority':100 if country in PRIORITY_COUNTRIES else 70,'status':status,
                     'sources':sources,'verified_sources':verified,'healthy_sources':healthy,
                     'source_queries':source_queries,'tender_queries':tender_queries,
                     'candidates':candidates,'tenders':tenders})
    order={'GAP':0,'PARTIAL':1,'COVERED':2}
    rows.sort(key=lambda x:(order[x['status']],-x['priority'],x['verified_sources'],x['healthy_sources'],x['country']))
    return {
        'countries':rows,
        'counts':{
            'target':len(rows),
            'covered':sum(1 for x in rows if x['status']=='COVERED'),
            'partial':sum(1 for x in rows if x['status']=='PARTIAL'),
            'gaps':sum(1 for x in rows if x['status']=='GAP'),
        }
    }
