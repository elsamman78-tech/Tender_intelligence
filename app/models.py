from datetime import datetime, date
from sqlalchemy import String, Integer, Date, DateTime, Text, Float, JSON, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Tender(Base):
    __tablename__ = 'tenders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    project_country: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    publication_age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submission_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    business_days_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    urgency_level: Mapped[str] = mapped_column(String(40), default='UNKNOWN')
    tender_status: Mapped[str] = mapped_column(String(40), default='NEW', index=True)
    bd_decision: Mapped[str] = mapped_column(String(40), default='UNDECIDED')
    hard_reject_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scope_classification: Mapped[str | None] = mapped_column(String(80), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_status: Mapped[str] = mapped_column(String(40), default='NOT_RUN')
    analysis_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    score_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    recommendation: Mapped[str | None] = mapped_column(String(60), nullable=True)
    discovery_candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    discovery_method: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # V4 commercial participation / evidence fields.
    bid_route: Mapped[str] = mapped_column(String(60), default='DIRECT', index=True)
    eligibility_status: Mapped[str] = mapped_column(String(60), default='ELIGIBILITY_TO_VERIFY', index=True)
    partner_requirement: Mapped[str] = mapped_column(String(100), default='NONE')
    submission_language: Mapped[str] = mapped_column(String(40), default='UNKNOWN')
    language_status: Mapped[str] = mapped_column(String(40), default='UNKNOWN')
    participation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_evidence_type: Mapped[str] = mapped_column(String(50), default='WEB', index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Source(Base):
    __tablename__ = 'sources'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True)
    domain: Mapped[str | None] = mapped_column(String(250), nullable=True, index=True)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(60), default='OPEN_WEB', index=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    languages: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(40), default='DISCOVERED', index=True)
    priority: Mapped[str] = mapped_column(String(30), default='EXPERIMENTAL', index=True)
    trust_score: Mapped[int] = mapped_column(Integer, default=50)
    relevance_score: Mapped[int] = mapped_column(Integer, default=50)
    discovery_value: Mapped[int] = mapped_column(Integer, default=50)
    health_status: Mapped[str] = mapped_column(String(50), default='UNKNOWN', index=True)
    cost_class: Mapped[str] = mapped_column(String(40), default='FREE_PUBLIC', index=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    requires_payment: Mapped[int] = mapped_column(Integer, default=0)
    requires_login: Mapped[int] = mapped_column(Integer, default=0)
    discovered_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    discovery_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    scan_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    useful_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    channels = relationship('SourceChannel', back_populates='source', cascade='all, delete-orphan')


class SourceChannel(Base):
    __tablename__ = 'source_channels'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('sources.id'), index=True)
    purpose: Mapped[str] = mapped_column(String(60), default='TENDERS')
    url: Mapped[str] = mapped_column(Text)
    access_method: Mapped[str] = mapped_column(String(40), default='HTML')
    priority_order: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    health_status: Mapped[str] = mapped_column(String(40), default='UNKNOWN')
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source = relationship('Source', back_populates='channels')


class SourceScan(Base):
    __tablename__ = 'source_scans'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('sources.id'), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey('source_channels.id'), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default='RUNNING', index=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_seen: Mapped[int] = mapped_column(Integer, default=0)
    new_candidates: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class DiscoveryQuery(Base):
    __tablename__ = 'discovery_queries'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_text: Mapped[str] = mapped_column(Text, unique=True)
    language: Mapped[str] = mapped_column(String(20), default='en')
    country: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    service: Mapped[str | None] = mapped_column(String(120), nullable=True)
    purpose: Mapped[str] = mapped_column(String(50), default='TENDER_SEARCH', index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    new_source_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_tender_count: Mapped[int] = mapped_column(Integer, default=0)
    noise_count: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SearchRun(Base):
    __tablename__ = 'search_runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int | None] = mapped_column(ForeignKey('discovery_queries.id'), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    query_text: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default='RUNNING')
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    new_domain_count: Mapped[int] = mapped_column(Integer, default=0)
    new_candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class SearchResult(Base):
    __tablename__ = 'search_results'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('search_runs.id'), index=True)
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), index=True)
    domain: Mapped[str | None] = mapped_column(String(250), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DiscoveryCandidate(Base):
    __tablename__ = 'discovery_candidates'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_type: Mapped[str] = mapped_column(String(40), default='OPPORTUNITY', index=True)
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey('sources.id'), nullable=True, index=True)
    discovery_method: Mapped[str] = mapped_column(String(60), default='UNKNOWN', index=True)
    discovery_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_guess: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country_guess: Mapped[str | None] = mapped_column(String(120), nullable=True)
    opportunity_type_guess: Mapped[str | None] = mapped_column(String(60), nullable=True)
    procurement_score: Mapped[int] = mapped_column(Integer, default=0)
    consultancy_score: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    validation_status: Mapped[str] = mapped_column(String(40), default='NEW', index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tender_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DocumentRecord(Base):
    __tablename__ = 'document_records'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), index=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_type: Mapped[str] = mapped_column(String(60), default='OTHER')
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey('discovery_candidates.id'), nullable=True, index=True)
    tender_id: Mapped[int | None] = mapped_column(ForeignKey('tenders.id'), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
