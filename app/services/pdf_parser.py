from pathlib import Path
from pypdf import PdfReader


def extract_pdf(path: str | Path) -> dict:
    reader = PdfReader(str(path))
    pages = []
    chunks = []
    for i, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or '').strip()
        pages.append({'page': i, 'text': text})
        if text:
            chunks.append(f"\n--- PAGE {i} ---\n{text}")
    full_text = ''.join(chunks)
    scanned_likely = len(full_text.strip()) < max(120, len(reader.pages) * 40)
    return {'text': full_text, 'pages': pages, 'page_count': len(reader.pages), 'scanned_likely': scanned_likely}
