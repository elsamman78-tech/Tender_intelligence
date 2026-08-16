from sqlalchemy import inspect, text
from .db import engine

# Lightweight additive migration support for upgrading an existing V1 SQLite DB.
SOURCE_COLUMNS = {
    'base_url': 'TEXT', 'languages': 'VARCHAR(120)', 'lifecycle_status': "VARCHAR(40) DEFAULT 'DISCOVERED'",
    'priority': "VARCHAR(30) DEFAULT 'EXPERIMENTAL'", 'relevance_score': 'INTEGER DEFAULT 50',
    'discovery_value': 'INTEGER DEFAULT 50', 'cost_class': "VARCHAR(40) DEFAULT 'FREE_PUBLIC'",
    'requires_login': 'INTEGER DEFAULT 0', 'discovered_by': 'VARCHAR(80)', 'discovery_detail': 'TEXT',
    'last_success_at': 'DATETIME', 'last_error': 'TEXT', 'scan_count': 'INTEGER DEFAULT 0',
    'success_count': 'INTEGER DEFAULT 0', 'candidate_count': 'INTEGER DEFAULT 0', 'useful_count': 'INTEGER DEFAULT 0',
    'updated_at': 'DATETIME'
}
TENDER_COLUMNS = {
    'discovery_candidate_id': 'INTEGER', 'discovery_method': 'VARCHAR(60)'
}


def _add_columns(table: str, cols: dict[str, str]):
    if engine.dialect.name != 'sqlite':
        return
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    existing = {c['name'] for c in inspector.get_columns(table)}
    with engine.begin() as conn:
        for name, ddl in cols.items():
            if name not in existing:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))


def migrate_additive():
    _add_columns('sources', SOURCE_COLUMNS)
    _add_columns('tenders', TENDER_COLUMNS)
