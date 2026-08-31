from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..geography import PRIORITY_COUNTRIES, TARGET_COUNTRIES
from ..models import DiscoveryQuery


# A full cycle must cover different evidence channels. Pure priority sorting previously
# starved FILE_SEARCH and NEWS_GAZETTE_SEARCH because high-priority tender queries always
# occupied the small query batch first.
PURPOSE_SEQUENCE = (
    'TENDER_SEARCH',
    'FILE_SEARCH',
    'NEWS_GAZETTE_SEARCH',
    'SOURCE_SEARCH',
    'SAUDI_DB_SEARCH',
    'FILE_SEARCH',
    'NEWS_GAZETTE_SEARCH',
    'TENDER_SEARCH',
)


def bootstrap_deep_queries(db: Session) -> int:
    """Add country-specific PDF discovery queries.

    Newspaper/gazette queries already exist for every target country in query_engine.
    PDF discovery used to have only two broad region queries, which was far too weak.
    """
    added = 0
    for country in TARGET_COUNTRIES:
        priority = 92 if country in PRIORITY_COUNTRIES else 70
        text = (
            f'filetype:pdf "{country}" '
            f'(RFP OR EOI OR REOI OR "terms of reference" OR "request for proposal") '
            f'("engineering consultancy" OR "consulting services" OR "construction supervision" '
            f'OR "detailed design" OR "project management consultant")'
        )
        q = db.scalar(select(DiscoveryQuery).where(DiscoveryQuery.query_text == text))
        if q is None:
            db.add(DiscoveryQuery(
                query_text=text,
                language='en',
                country=country,
                purpose='FILE_SEARCH',
                priority=priority,
                enabled=True,
            ))
            added += 1
        else:
            q.enabled = True
            q.purpose = 'FILE_SEARCH'
            q.priority = priority
    db.commit()
    return added


def _next_for_purpose(db: Session, purpose: str, excluded_ids: list[int]):
    stmt = select(DiscoveryQuery).where(
        DiscoveryQuery.enabled == True,
        DiscoveryQuery.purpose == purpose,
    )
    if excluded_ids:
        stmt = stmt.where(~DiscoveryQuery.id.in_(excluded_ids))
    # Never-run queries first, then rotate the least-recently-run query. Priority breaks ties.
    stmt = stmt.order_by(
        DiscoveryQuery.last_run_at.is_(None).desc(),
        DiscoveryQuery.last_run_at.asc(),
        DiscoveryQuery.priority.desc(),
    ).limit(1)
    return db.scalar(stmt)


def select_balanced_query_batch(db: Session, limit: int = 8):
    if limit <= 0:
        return []

    selected = []
    selected_ids: list[int] = []
    sequence = list(PURPOSE_SEQUENCE)

    # If a caller requests more than eight queries, keep repeating the balanced pattern.
    while len(sequence) < limit:
        sequence.extend(PURPOSE_SEQUENCE)

    for purpose in sequence[:limit]:
        q = _next_for_purpose(db, purpose, selected_ids)
        if q is not None:
            selected.append(q)
            selected_ids.append(q.id)

    # Fill any missing slots from the global queue without losing the balanced picks.
    if len(selected) < limit:
        stmt = select(DiscoveryQuery).where(DiscoveryQuery.enabled == True)
        if selected_ids:
            stmt = stmt.where(~DiscoveryQuery.id.in_(selected_ids))
        stmt = stmt.order_by(
            DiscoveryQuery.last_run_at.is_(None).desc(),
            DiscoveryQuery.last_run_at.asc(),
            DiscoveryQuery.priority.desc(),
        ).limit(limit - len(selected))
        for q in db.scalars(stmt).all():
            selected.append(q)

    return selected[:limit]
