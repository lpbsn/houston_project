from __future__ import annotations

import io
import zipfile
from pathlib import Path

from houston.brain.errors import ReportingRejected

_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_DOC = (
    "Le format DOC n'est pas pris en charge. Exportez le document en DOCX ou en PDF textuel."
)
_UNSUPPORTED = (
    "Ce format n'est pas pris en charge. Exportez un CSV, un XLSX, un DOCX ou un PDF textuel."
)
_IMAGE = (
    "Les images ne sont pas lues. Exportez un CSV, un XLSX, un DOCX ou un PDF textuel."
)
_INVALID_XLSX = "Le fichier XLSX n'est pas exploitable."
_INVALID_DOCX = "Le fichier DOCX n'est pas exploitable."
_INVALID_PDF = "Le fichier PDF n'est pas exploitable."


def sniff_format(filename: str, raw: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()
    if raw.startswith(b"%PDF"):
        return "pdf"
    if raw.startswith(b"PK"):
        kind = _zip_kind(raw)
        if kind is not None:
            return kind
        raise ReportingRejected(code="unsupported_format", message=_UNSUPPORTED)
    if raw.startswith(_OLE) or suffix == ".doc":
        if suffix in {".doc", ".docx"} or b"WordDocument" in raw:
            raise ReportingRejected(code="doc_not_supported", message=_DOC)
        raise ReportingRejected(code="unsupported_format", message=_UNSUPPORTED)
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"} or raw.startswith(
        (b"\x89PNG", b"\xff\xd8\xff", b"GIF8")
    ):
        raise ReportingRejected(code="image_not_supported", message=_IMAGE)
    if suffix in {".xlsx", ".xlsm"}:
        raise ReportingRejected(code="invalid_xlsx", message=_INVALID_XLSX)
    if suffix == ".docx":
        raise ReportingRejected(code="invalid_docx", message=_INVALID_DOCX)
    if suffix == ".pdf":
        raise ReportingRejected(code="invalid_pdf", message=_INVALID_PDF)
    if suffix in {"", ".csv", ".txt"} or _looks_textual(raw):
        return "csv"
    raise ReportingRejected(code="unsupported_format", message=_UNSUPPORTED)


def _zip_kind(raw: bytes) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return None
    if "xl/workbook.xml" in names:
        return "xlsx"
    if "word/document.xml" in names:
        return "docx"
    return None


def _looks_textual(raw: bytes) -> bool:
    if not raw:
        return False
    sample = raw[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            sample.decode("cp1252")
        except UnicodeDecodeError:
            return False
    return True
