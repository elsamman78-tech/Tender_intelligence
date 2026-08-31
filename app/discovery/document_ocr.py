from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

from pypdf import PdfReader

from ..config import OCR_ENABLED, OCR_DOCKER_FALLBACK, OCR_LANGUAGES, OCR_MIN_TEXT_CHARS, OCR_DOCKER_IMAGE
from .utils import clean_text


def _pypdf_text(data: bytes) -> str:
    reader=PdfReader(BytesIO(data))
    return clean_text('\n'.join((p.extract_text() or '') for p in reader.pages[:250]))[:300000]


def _run(cmd: list[str], timeout: int=240) -> bool:
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,shell=False)
        return p.returncode==0
    except Exception:
        return False


def _local_ocr(input_path: Path, output_path: Path) -> bool:
    exe=shutil.which('ocrmypdf')
    if not exe:
        return False
    langs=[OCR_LANGUAGES,'eng'] if OCR_LANGUAGES!='eng' else ['eng']
    for lang in langs:
        cmd=[exe,'--skip-text','--rotate-pages','--deskew','-l',lang,str(input_path),str(output_path)]
        if _run(cmd) and output_path.exists():
            return True
    return False


def _docker_ocr(input_path: Path, output_path: Path) -> bool:
    if not OCR_DOCKER_FALLBACK or not shutil.which('docker'):
        return False
    try:
        if subprocess.run(['docker','info'],capture_output=True,timeout=8).returncode!=0:
            return False
    except Exception:
        return False
    mount=str(input_path.parent.resolve())
    langs=[OCR_LANGUAGES,'eng'] if OCR_LANGUAGES!='eng' else ['eng']
    for lang in langs:
        cmd=[
            'docker','run','--rm','-v',f'{mount}:/data',OCR_DOCKER_IMAGE,
            '--skip-text','--rotate-pages','--deskew','-l',lang,
            '/data/input.pdf','/data/output.pdf'
        ]
        if _run(cmd) and output_path.exists():
            return True
    return False


def extract_pdf_text(data: bytes) -> tuple[str,str]:
    """Extract searchable text, escalating to OCR only for image/scanned PDFs."""
    text=_pypdf_text(data)
    if len(text)>=OCR_MIN_TEXT_CHARS or not OCR_ENABLED:
        return text,'PYPDF'
    with TemporaryDirectory(prefix='tender_ocr_') as tmp:
        root=Path(tmp); inp=root/'input.pdf'; out=root/'output.pdf'; inp.write_bytes(data)
        ok=_local_ocr(inp,out) or _docker_ocr(inp,out)
        if ok and out.exists():
            try:
                ocr_text=_pypdf_text(out.read_bytes())
                if len(ocr_text)>len(text):
                    return ocr_text,'OCR'
            except Exception:
                pass
    return text,'PYPDF_LOW_TEXT'
