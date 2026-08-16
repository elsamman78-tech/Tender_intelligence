from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import DiscoveryCandidate, DocumentRecord
from .keywords import DOCUMENT_EXTENSIONS, FILE_TERMS
from .utils import hash_text

DOC_TYPE_HINTS={
    'RFP':['rfp','request for proposal'], 'TOR':['tor','terms of reference'], 'EOI':['eoi','reoi','expression of interest'],
    'ADDENDUM':['addendum'], 'CLARIFICATION':['clarification'], 'PREQUALIFICATION':['prequalification','pre-qualification'],
    'TENDER':['tender','bid','مناقصة','منافسة']
}

def classify_document(url: str, title: str='') -> str:
    low=(url+' '+(title or '')).lower()
    for k,terms in DOC_TYPE_HINTS.items():
        if any(t in low for t in terms): return k
    return 'OTHER'

def is_document_url(url: str) -> bool:
    return url.lower().split('?',1)[0].endswith(DOCUMENT_EXTENSIONS)

def index_candidate_documents(db: Session, limit: int=200):
    rows=db.scalars(select(DiscoveryCandidate).order_by(DiscoveryCandidate.created_at.desc()).limit(limit)).all()
    added=0
    for c in rows:
        if not is_document_url(c.url): continue
        c.candidate_type='DOCUMENT'
        uh=hash_text(c.url)
        existing=db.scalar(select(DocumentRecord).where(DocumentRecord.url_hash==uh,DocumentRecord.source_url==c.url))
        if not existing:
            filename=Path(c.url.split('?',1)[0]).name[:500] or None
            db.add(DocumentRecord(source_url=c.url,url_hash=uh,filename=filename,document_type=classify_document(c.url,c.title or ''),candidate_id=c.id))
            added+=1
    db.commit(); return {'indexed':added}
