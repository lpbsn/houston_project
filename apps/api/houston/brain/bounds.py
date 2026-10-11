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


def limits_from_settings() -> dict:
    return {
        "timeout_seconds": int(settings.HOUSTON_BRAIN_EXTRACTION_TIMEOUT_SECONDS),
        "memory_bytes": int(settings.HOUSTON_BRAIN_MAX_EXTRACTION_MEMORY_BYTES),
        "max_rows": int(settings.HOUSTON_BRAIN_MAX_ROWS),
        "max_columns": int(settings.HOUSTON_BRAIN_MAX_COLUMNS),
        "max_cells": int(settings.HOUSTON_BRAIN_MAX_CELLS),
        "max_sheets": int(settings.HOUSTON_BRAIN_MAX_SHEETS),
        "max_pages": int(settings.HOUSTON_BRAIN_MAX_PDF_PAGES),
        "max_blocks": int(settings.HOUSTON_BRAIN_MAX_DOCX_BLOCKS),
        "max_uncompressed": int(settings.HOUSTON_BRAIN_MAX_XLSX_UNCOMPRESSED_BYTES),
        "max_zip_entries": int(settings.HOUSTON_BRAIN_MAX_ZIP_ENTRIES),
    }


class ExtractionBudget:
    def __init__(self, limits: dict | None = None):
        values = limits_from_settings()
        if limits:
            values.update(limits)
        seconds = int(values["timeout_seconds"])
        now = time.monotonic()
        self.deadline = now - 1 if seconds <= 0 else now + seconds
        self.timeout_seconds = seconds
        self.memory_bytes = int(values["memory_bytes"])
        self.max_rows = int(values["max_rows"])
        self.max_columns = int(values["max_columns"])
        self.max_cells = int(values["max_cells"])
        self.max_sheets = int(values["max_sheets"])
        self.max_pages = int(values["max_pages"])
        self.max_blocks = int(values["max_blocks"])
        self.max_uncompressed = int(values["max_uncompressed"])
        self.max_zip_entries = int(values["max_zip_entries"])
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


def zip_entry_names(
    raw: bytes,
    budget: ExtractionBudget,
    *,
    invalid_code: str,
    invalid_message: str,
) -> list[str]:
    """Count inflated bytes while reading. Declared size cannot skip the stream cap."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) > budget.max_zip_entries:
                raise ExtractionLimit(
                    code="ooxml_entry_limit",
                    message=(
                        "Le fichier contient trop d'éléments compressés. "
                        "Aucune extraction partielle n'a été conservée."
                    ),
                )
            total = 0
            names: list[str] = []
            for info in infos:
                budget.check_time()
                if info.file_size < 0:
                    raise ExtractionRejected(code=invalid_code, message=invalid_message)
                remaining = budget.max_uncompressed - total
                if remaining <= 0 or info.file_size > remaining:
                    raise ExtractionLimit(
                        code="ooxml_uncompressed_too_large",
                        message=_UNCOMPRESSED_MESSAGE,
                    )
                produced = _inflated_size(
                    archive,
                    info,
                    budget,
                    remaining,
                    invalid_code=invalid_code,
                    invalid_message=invalid_message,
                )
                total += produced
                if total > budget.max_uncompressed:
                    raise ExtractionLimit(
                        code="ooxml_uncompressed_too_large",
                        message=_UNCOMPRESSED_MESSAGE,
                    )
                names.append(info.filename)
    except zipfile.BadZipFile as exc:
        raise ExtractionRejected(code=invalid_code, message=invalid_message) from exc
    return names


def _inflated_size(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    budget: ExtractionBudget,
    remaining: int,
    *,
    invalid_code: str,
    invalid_message: str,
) -> int:
    """Inflate one member, stopping once the bytes still allowed are exceeded."""
    declared = info.file_size
    # Zip readers stop at the declared size. Lift that ceiling one byte past the
    # bytes still allowed so an understated header cannot hide the rest.
    info.file_size = max(declared, remaining + 1)
    produced = 0
    try:
        with archive.open(info, "r") as handle:
            handle._expected_crc = None
            while True:
                budget.check_time()
                chunk = handle.read(256 * 1024)
                if not chunk:
                    break
                produced += len(chunk)
                if produced > remaining:
                    raise ExtractionLimit(
                        code="ooxml_uncompressed_too_large",
                        message=_UNCOMPRESSED_MESSAGE,
                    )
    except ExtractionLimit:
        raise
    except (zipfile.BadZipFile, OSError, RuntimeError, EOFError) as exc:
        raise ExtractionRejected(code=invalid_code, message=invalid_message) from exc
    finally:
        info.file_size = declared
    return produced
