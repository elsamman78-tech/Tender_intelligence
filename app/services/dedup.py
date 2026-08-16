import hashlib
import re

def _norm(value: str | None) -> str:
    return re.sub(r'\W+', ' ', (value or '').lower(), flags=re.UNICODE).strip()

def fingerprint(*, title: str, client: str | None, country: str | None, deadline, reference: str | None) -> str:
    base = '|'.join([
        _norm(reference) or '-',
        _norm(title),
        _norm(client),
        _norm(country),
        deadline.isoformat() if deadline else '-'
    ])
    return hashlib.sha256(base.encode('utf-8')).hexdigest()
