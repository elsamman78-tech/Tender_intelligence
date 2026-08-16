import re
import httpx
from html import unescape


def read_url(url: str) -> str:
    if not url.lower().startswith(('http://','https://')):
        raise ValueError('Only http/https URLs are allowed')
    headers = {'User-Agent':'TenderIntelligenceZeroCost/1.0 (+local research tool)'}
    r = httpx.get(url, headers=headers, follow_redirects=True, timeout=20)
    r.raise_for_status()
    ctype = r.headers.get('content-type','')
    if 'text/html' not in ctype and 'text/plain' not in ctype:
        raise ValueError(f'Unsupported content-type: {ctype}')
    text = re.sub(r'(?is)<script.*?>.*?</script>', ' ', r.text)
    text = re.sub(r'(?is)<style.*?>.*?</style>', ' ', text)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    text = unescape(text)
    return re.sub(r'\s+', ' ', text).strip()
