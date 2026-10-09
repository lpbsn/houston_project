from __future__ import annotations

import io
import re

from houston.brain.bounds import ExtractionBudget
from houston.brain.errors import ExtractionRejected
from houston.brain.grid import extract_grid
from houston.brain.records import ExtractionResult, GridCell, QualitativeBlock

_INVALID = "Le fichier PDF n'est pas exploitable."
_ENCRYPTED = "Ce PDF est chiffré. Exportez un PDF textuel sans mot de passe."
_NO_TEXT = (
    "Ce PDF ne contient pas de texte exploitable. Les images ne sont pas lues. "
    "Exportez un PDF textuel, un DOCX, un CSV ou un XLSX."
)
_EMPTY = "Le fichier ne contient pas de contenu analysable."
_IMAGES = (
    "Les images ne sont pas lues. Si un chiffre n'existe que dans une image, "
    "exportez un PDF textuel, un DOCX, un CSV ou un XLSX."
)


def extract_pdf(raw: bytes, budget: ExtractionBudget) -> ExtractionResult:
    budget.check_time()
    reader = _open(raw)
    if reader.is_encrypted:
        raise ExtractionRejected(code="pdf_encrypted", message=_ENCRYPTED)
    budget.check_count(
        len(reader.pages),
        limit=budget.max_pages,
        code="extraction_page_limit",
        label="pages",
    )
    warnings: list[dict] = []
    if _has_javascript(reader):
        warnings.append(
            {
                "code": "embedded_instructions_ignored",
                "message": "Les instructions embarquées du PDF sont ignorées.",
            }
        )
    measures = []
    blocks: list[QualitativeBlock] = []
    image_only_pages: list[int] = []
    saw_image = False
    for index, page in enumerate(reader.pages, start=1):
        budget.check_time()
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            text = page.extract_text() or ""
        except KeyError:
            text = ""
        except Exception as exc:
            raise ExtractionRejected(code="invalid_pdf", message=_INVALID) from exc
        has_image = _page_has_image(page)
        saw_image = saw_image or has_image
        if not text.strip():
            if has_image:
                image_only_pages.append(index)
            continue
        page_measures, page_blocks = _page_content(text, index, budget)
        measures.extend(page_measures)
        blocks.extend(page_blocks)
    if saw_image:
        warnings.append({"code": "images_not_interpreted", "message": _IMAGES})
        for page_number in image_only_pages:
            warnings.append(
                {
                    "code": "pdf_page_without_text",
                    "message": "Cette page ne contient pas de texte. Les images ne sont pas lues.",
                    "locator": {"format": "pdf", "page": page_number},
                }
            )
    result = ExtractionResult(
        source_format="pdf",
        measures=measures,
        qualitative=blocks,
        warnings=warnings,
    )
    if result.analyzable():
        return result
    if saw_image:
        raise ExtractionRejected(code="pdf_text_unavailable", message=_NO_TEXT)
    raise ExtractionRejected(code="empty_document", message=_EMPTY)


def _page_content(text: str, page: int, budget: ExtractionBudget):
    measures = []
    blocks: list[QualitativeBlock] = []
    fragment = 0
    paragraph: list[str] = []
    table: list[list[str]] = []

    def flush_paragraph() -> None:
        nonlocal fragment
        joined = " ".join(part.strip() for part in paragraph if part.strip())
        paragraph.clear()
        if not joined:
            return
        blocks.append(
            QualitativeBlock(
                kind="paragraph",
                text=joined,
                locator={"format": "pdf", "page": page, "fragment": fragment},
            )
        )
        fragment += 1

    def flush_table() -> None:
        nonlocal fragment
        if not table:
            return
        grid = [[GridCell(raw=value) for value in row] for row in table]
        table.clear()
        start = fragment

        def locate(row_index: int, column_index: int, header: str | None) -> dict:
            locator = {
                "format": "pdf",
                "page": page,
                "fragment": start,
                "row": row_index + 1,
                "column": column_index + 1,
            }
            if header:
                locator["header"] = header
            return locator

        found_measures, found_blocks = extract_grid(grid, locate=locate)
        measures.extend(found_measures)
        blocks.extend(found_blocks)
        fragment += 1

    for line in text.splitlines():
        budget.check_time()
        if not line.strip():
            flush_table()
            flush_paragraph()
            continue
        cells = re.split(r"\s{2,}", line.strip())
        if len(cells) >= 2:
            flush_paragraph()
            budget.add_row()
            budget.check_columns(len(cells))
            for _cell in cells:
                budget.add_cell()
            table.append(cells)
            continue
        flush_table()
        paragraph.append(line)
    flush_table()
    flush_paragraph()
    return measures, blocks


def _open(raw: bytes):
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        return PdfReader(io.BytesIO(raw))
    except (PdfReadError, OSError, ValueError) as exc:
        raise ExtractionRejected(code="invalid_pdf", message=_INVALID) from exc


def _has_javascript(reader) -> bool:
    try:
        root = reader.trailer["/Root"].get_object()
    except Exception:
        return False
    if "/OpenAction" in root or "/AA" in root:
        return True
    names = root.get("/Names")
    if names is None:
        return False
    try:
        return "/JavaScript" in names.get_object()
    except Exception:
        return False


def _page_has_image(page) -> bool:
    try:
        resources = page.get("/Resources")
        if resources is None:
            return False
        xobjects = resources.get_object().get("/XObject")
        if xobjects is None:
            return False
        for value in xobjects.get_object().values():
            if value.get_object().get("/Subtype") == "/Image":
                return True
    except Exception:
        return False
    return False
