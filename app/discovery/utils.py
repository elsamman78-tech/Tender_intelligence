from urllib.parse import urljoin, urlparse, parse_qs, unquote
from hashlib import sha256
import re


def hash_text(value: str) -> str:
    return sha256((value or '').encode('utf-8', errors='ignore')).hexdigest()


def normalize_url(url: str, base: str | None = None) -> str:
    if base:
        url = urljoin(base, url)
    url = (url or '').strip()
    if not url:
        return ''
    # DuckDuckGo wraps outbound URLs in /l/?uddg=
    try:
        p = urlparse(url)
        if 'duckduckgo.com' in p.netloc and p.path.startswith('/l/'):
            uddg = parse_qs(p.query).get('uddg', [''])[0]
            if uddg:
                url = unquote(uddg)
    except Exception:
        pass
    return url.split('#',1)[0]


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().split(':')[0]
    except Exception:
        return ''


def clean_text(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '')).strip()


def keyword_score(text: str, terms: list[str]) -> int:
    low = (text or '').lower()
    score = 0
    for term in terms:
        if term.lower() in low:
            score += 12 if len(term) > 4 else 6
    return min(score, 100)
