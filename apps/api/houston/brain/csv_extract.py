from __future__ import annotations

import csv
import io

from houston.brain.bounds import ExtractionBudget
from houston.brain.errors import ExtractionRejected
from houston.brain.grid import extract_grid
from houston.brain.records import SOURCE_TEXT, ExtractionResult, GridCell

_SEPARATORS = (",", ";", "\t", "|")
_AMBIGUOUS_SEPARATOR = (
    "Le séparateur du CSV est ambigu. Exportez le fichier avec un séparateur unique."
)
_INVALID_CSV = "Le fichier CSV n'est pas exploitable."


def extract_csv(raw: bytes, budget: ExtractionBudget) -> ExtractionResult:
    budget.check_time()
    text = _decode(raw)
    separator = _detect_separator(text)
    rows: list[list[GridCell]] = []
    for physical in csv.reader(io.StringIO(text), delimiter=separator):
        budget.add_row()
        budget.check_columns(len(physical))
        grid_row: list[GridCell] = []
        for value in physical:
            budget.add_cell()
            grid_row.append(GridCell(raw=value, source=SOURCE_TEXT))
        rows.append(grid_row)
    measures, blocks = extract_grid(rows, locate=_locate)
    return ExtractionResult(
        source_format="csv",
        measures=measures,
        qualitative=blocks,
        warnings=[],
    )


def _decode(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1252")
    if "\x00" in text:
        raise ExtractionRejected(code="invalid_csv", message=_INVALID_CSV)
    return text


def _detect_separator(text: str) -> str:
    scored: list[tuple[int, str, list[list[str]]]] = []
    for separator in _SEPARATORS:
        parsed = [
            row
            for row in csv.reader(io.StringIO(text), delimiter=separator)
            if any(cell.strip() for cell in row)
        ]
        if not parsed:
            scored.append((0, separator, parsed))
            continue
        widths = [len(row) for row in parsed]
        mode = max(set(widths), key=widths.count)
        consistent = sum(1 for width in widths if width == mode)
        score = consistent if mode >= 2 else 0
        scored.append((score, separator, parsed))
    best = max(item[0] for item in scored)
    winners = [item for item in scored if item[0] == best and item[0] > 0]
    if len(winners) > 1 and _grids_differ([item[2] for item in winners]):
        raise ExtractionRejected(code="csv_separator_ambiguous", message=_AMBIGUOUS_SEPARATOR)
    if winners:
        return winners[0][1]
    return ","


def _grids_differ(grids: list[list[list[str]]]) -> bool:
    first = grids[0]
    return any(grid != first for grid in grids[1:])


def _locate(row_index: int, column_index: int, header: str | None) -> dict:
    locator = {"format": "csv", "row": row_index + 1, "column": column_index + 1}
    if header:
        locator["header"] = header
    return locator
