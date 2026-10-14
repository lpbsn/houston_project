from __future__ import annotations

from houston.brain.bounds import ExtractionBudget
from houston.brain.csv_extract import extract_csv
from houston.brain.docx_extract import extract_docx
from houston.brain.errors import ExtractionRejected
from houston.brain.pdf_extract import extract_pdf
from houston.brain.records import ExtractionResult
from houston.brain.xlsx_extract import extract_xlsx

_EMPTY = "Le fichier ne contient pas de contenu analysable."


def extract_document(
    raw: bytes,
    source_format: str,
    budget: ExtractionBudget | None = None,
) -> ExtractionResult:
    budget = budget or ExtractionBudget()
    if source_format == "csv":
        result = extract_csv(raw, budget)
    elif source_format == "xlsx":
        result = extract_xlsx(raw, budget)
    elif source_format == "pdf":
        result = extract_pdf(raw, budget)
    elif source_format == "docx":
        result = extract_docx(raw, budget)
    else:
        raise ExtractionRejected(
            code="unsupported_format",
            message="Ce format n'est pas pris en charge.",
        )
    if not result.analyzable():
        raise ExtractionRejected(code="empty_document", message=_empty_message(result))
    return result


def _empty_message(result: ExtractionResult) -> str:
    codes = {warning["code"] for warning in result.warnings}
    if "macros_not_executed" in codes:
        return f"{_EMPTY} Les macros ne sont pas exécutées."
    if "text_boxes_not_extracted" in codes:
        return f"{_EMPTY} Les zones de texte ne sont pas lues."
    if "header_footer_not_extracted" in codes:
        return f"{_EMPTY} L'en-tête et le pied de page ne sont pas extraits."
    if "charts_not_interpreted" in codes:
        return (
            f"{_EMPTY} Les graphiques ne sont pas lus. "
            "Exportez les valeurs en XLSX ou en CSV."
        )
    return _EMPTY
