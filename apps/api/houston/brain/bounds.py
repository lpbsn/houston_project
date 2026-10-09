from __future__ import annotations

import io
import time
import zipfile

from django.conf import settings

from houston.brain.errors import ExtractionLimit, ExtractionRejected

_UNCOMPRESSED_MESSAGE = (
    "Le fichier décompressé dépasse la taille maximale acceptée. "
    "Aucune extraction partielle n'a été conservée."
)


class ExtractionBudget:
    def __init__(self):
        seconds = int(settings.HOUSTON_BRAIN_EXTRACTION_TIMEOUT_SECONDS)
        now = time.monotonic()
        self.deadline = now - 1 if seconds <= 0 else now + seconds
        self.max_rows = int(settings.HOUSTON_BRAIN_MAX_ROWS)
        self.max_columns = int(settings.HOUSTON_BRAIN_MAX_COLUMNS)
        self.max_cells = int(settings.HOUSTON_BRAIN_MAX_CELLS)
        self.max_sheets = int(settings.HOUSTON_BRAIN_MAX_SHEETS)
        self.max_pages = int(settings.HOUSTON_BRAIN_MAX_PDF_PAGES)
        self.max_blocks = int(settings.HOUSTON_BRAIN_MAX_DOCX_BLOCKS)
        self.rows = 0
        self.cells = 0

    def check_time(self) -> None:
        if time.monotonic() >= self.deadline:
            raise ExtractionLimit(
                code="extraction_timeout",
                message=(
                    "L'extraction a dépassé le temps imparti. "
                    "Aucun contenu n'a été tronqué."
                ),
            )

    def add_row(self) -> None:
        self.check_time()
        self.rows += 1
        if self.rows > self.max_rows:
            raise ExtractionLimit(
                code="extraction_row_limit",
                message=(
                    "Le fichier dépasse le nombre maximal de lignes. "
                    "Aucune extraction partielle n'a été conservée."
                ),
            )

    def add_cell(self) -> None:
        self.check_time()
        self.cells += 1
        if self.cells > self.max_cells:
            raise ExtractionLimit(
                code="extraction_cell_limit",
                message=(
                    "Le fichier dépasse le nombre maximal de cellules. "
                    "Aucune extraction partielle n'a été conservée."
                ),
            )

    def check_columns(self, count: int) -> None:
        if count > self.max_columns:
            raise ExtractionLimit(
                code="extraction_column_limit",
                message=(
                    "Le fichier dépasse le nombre maximal de colonnes. "
                    "Aucune extraction partielle n'a été conservée."
                ),
            )

    def check_count(self, count: int, *, limit: int, code: str, label: str) -> None:
        if count > limit:
            raise ExtractionLimit(
                code=code,
                message=(
                    f"Le fichier dépasse le nombre maximal de {label}. "
                    "Aucune extraction partielle n'a été conservée."
                ),
            )


def zip_entry_names(raw: bytes, *, invalid_code: str, invalid_message: str) -> list[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
    except zipfile.BadZipFile as exc:
        raise ExtractionRejected(code=invalid_code, message=invalid_message) from exc
    if len(infos) > int(settings.HOUSTON_BRAIN_MAX_ZIP_ENTRIES):
        raise ExtractionLimit(
            code="ooxml_entry_limit",
            message=(
                "Le fichier contient trop d'éléments compressés. "
                "Aucune extraction partielle n'a été conservée."
            ),
        )
    total = 0
    ceiling = int(settings.HOUSTON_BRAIN_MAX_XLSX_UNCOMPRESSED_BYTES)
    names: list[str] = []
    for info in infos:
        if info.file_size < 0:
            raise ExtractionRejected(code=invalid_code, message=invalid_message)
        total += info.file_size
        if total > ceiling:
            raise ExtractionLimit(
                code="ooxml_uncompressed_too_large",
                message=_UNCOMPRESSED_MESSAGE,
            )
        names.append(info.filename)
    return names
