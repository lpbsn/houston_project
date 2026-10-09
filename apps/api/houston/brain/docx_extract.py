from __future__ import annotations

import io

from houston.brain.bounds import ExtractionBudget, zip_entry_names
from houston.brain.errors import ExtractionRejected
from houston.brain.grid import extract_grid
from houston.brain.records import ExtractionResult, GridCell, QualitativeBlock

_INVALID = "Le fichier DOCX n'est pas exploitable."


def extract_docx(raw: bytes, budget: ExtractionBudget) -> ExtractionResult:
    budget.check_time()
    names = zip_entry_names(raw, invalid_code="invalid_docx", invalid_message=_INVALID)
    warnings = _package_warnings(names)
    document = _open(raw)
    if _has_text_boxes(document):
        warnings.append(
            {
                "code": "text_boxes_not_extracted",
                "message": (
                    "Les zones de texte ne sont pas lues. "
                    "Placez ce contenu dans les paragraphes ou les tableaux."
                ),
            }
        )
    if _header_or_footer_has_text(document):
        warnings.append(
            {
                "code": "header_footer_not_extracted",
                "message": (
                    "L'en-tête et le pied de page ne sont pas extraits. "
                    "Placez ce contenu dans le corps du document."
                ),
            }
        )
    measures = []
    blocks: list[QualitativeBlock] = []
    block_index = 0
    for block in _iter_blocks(document):
        budget.check_time()
        block_index += 1
        budget.check_count(
            block_index,
            limit=budget.max_blocks,
            code="extraction_block_limit",
            label="blocs",
        )
        if block.__class__.__name__ == "Paragraph":
            text = block.text.strip()
            if not text:
                continue
            kind = "heading" if _is_heading(block) else "paragraph"
            blocks.append(
                QualitativeBlock(
                    kind=kind,
                    text=text,
                    locator={"format": "docx", "block": block_index},
                )
            )
            continue
        grid: list[list[GridCell]] = []
        for row in block.rows:
            budget.add_row()
            budget.check_columns(len(row.cells))
            grid_row = []
            for cell in row.cells:
                budget.add_cell()
                grid_row.append(GridCell(raw=cell.text))
            grid.append(grid_row)
        current = block_index

        def locate(row_index: int, column_index: int, header: str | None, *, table_block=current):
            locator = {
                "format": "docx",
                "block": table_block,
                "table": table_block,
                "row": row_index + 1,
                "column": column_index + 1,
            }
            if header:
                locator["header"] = header
            return locator

        found_measures, found_blocks = extract_grid(grid, locate=locate)
        measures.extend(found_measures)
        blocks.extend(found_blocks)
    return ExtractionResult(
        source_format="docx",
        measures=measures,
        qualitative=blocks,
        warnings=warnings,
    )


def _package_warnings(names: list[str]) -> list[dict]:
    warnings = []
    if any(name.endswith("vbaProject.bin") for name in names):
        warnings.append(
            {
                "code": "macros_not_executed",
                "message": "Les macros du document ne sont pas exécutées.",
            }
        )
    if any("/embeddings/" in f"/{name}" for name in names):
        warnings.append(
            {
                "code": "embedded_objects_ignored",
                "message": "Les objets incorporés ne sont pas ouverts.",
            }
        )
    return warnings


def _open(raw: bytes):
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError

    try:
        return Document(io.BytesIO(raw))
    except (PackageNotFoundError, OSError, ValueError) as exc:
        raise ExtractionRejected(code="invalid_docx", message=_INVALID) from exc


def _iter_blocks(document):
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _is_heading(paragraph) -> bool:
    style = paragraph.style
    name = (style.name or "") if style is not None else ""
    folded = name.casefold()
    if folded.startswith("heading") or folded.startswith("titre"):
        return True
    properties = paragraph._p.pPr
    return properties is not None and properties.outlineLvl is not None


def _has_text_boxes(document) -> bool:
    return any(element.tag.endswith("txbxContent") for element in document.element.iter())


def _header_or_footer_has_text(document) -> bool:
    for section in document.sections:
        for container in (section.header, section.footer):
            try:
                if any(paragraph.text.strip() for paragraph in container.paragraphs):
                    return True
            except Exception:
                continue
    return False
