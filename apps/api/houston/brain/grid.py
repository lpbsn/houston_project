from __future__ import annotations

from houston.brain.numbers import (
    decimal_text,
    interpret_label,
    merge_ambiguities,
    parse_cell,
)
from houston.brain.records import (
    SOURCE_ABSENT,
    SOURCE_ERROR,
    SOURCE_EXCEL_NUMBER,
    VALUE_ABSENT,
    VALUE_EMPTY,
    VALUE_ERROR,
    VALUE_UNINTERPRETABLE,
    VALUE_ZERO,
    GridCell,
    Measure,
    QualitativeBlock,
)


def extract_grid(
    rows: list[list[GridCell]],
    *,
    locate,
    preamble_kind: str = "text_cell",
) -> tuple[list[Measure], list[QualitativeBlock]]:
    header_at = _header_index(rows)
    measures: list[Measure] = []
    blocks: list[QualitativeBlock] = []
    labels = _header_labels(rows[header_at]) if header_at is not None else []
    numeric_columns = _numeric_columns(rows, header_at)
    for row_index, row in enumerate(rows):
        if header_at is not None and row_index < header_at:
            blocks.extend(_preamble(row, row_index, locate, preamble_kind))
            continue
        if header_at is not None and row_index == header_at:
            blocks.extend(_header_blocks(row, row_index, locate))
            continue
        if all(cell.is_empty() for cell in row):
            continue
        scope = _row_scope(row)
        for column_index, cell in enumerate(row):
            if cell.omit:
                continue
            header = labels[column_index] if column_index < len(labels) else None
            locator = _located(
                locate,
                row_index,
                column_index,
                header.label if header else None,
                cell,
            )
            if cell.source == SOURCE_ABSENT:
                measures.append(
                    _measure(
                        header,
                        locator,
                        scope if column_index else None,
                        value=None,
                        value_kind=VALUE_ABSENT,
                        raw=None,
                        extra_flags=(),
                        cell_unit=None,
                    )
                )
                continue
            if cell.source == SOURCE_ERROR:
                measures.append(
                    _measure(
                        header,
                        locator,
                        scope if column_index else None,
                        value=None,
                        value_kind=VALUE_ERROR,
                        raw=cell.raw,
                        extra_flags=(),
                        cell_unit=None,
                    )
                )
                continue
            if cell.source == SOURCE_EXCEL_NUMBER and cell.number is not None:
                kind = VALUE_ZERO if cell.number == 0 else "number"
                measures.append(
                    _measure(
                        header,
                        locator,
                        scope if column_index else None,
                        value=decimal_text(cell.number),
                        value_kind=kind,
                        raw=decimal_text(cell.number),
                        extra_flags=(),
                        cell_unit=None,
                    )
                )
                continue
            if cell.is_empty():
                if column_index in numeric_columns:
                    measures.append(
                        _measure(
                            header,
                            locator,
                            scope if column_index else None,
                            value=None,
                            value_kind=VALUE_EMPTY,
                            raw="",
                            extra_flags=(),
                            cell_unit=None,
                        )
                    )
                continue
            parsed = parse_cell(cell.raw)
            if parsed.kind == "formula":
                blocks.append(
                    QualitativeBlock(kind="text_cell", text=parsed.raw, locator=locator)
                )
                continue
            if parsed.kind in {"number", "zero"}:
                measures.append(
                    _measure(
                        header,
                        locator,
                        scope if column_index else None,
                        value=decimal_text(parsed.value) if parsed.value is not None else None,
                        value_kind=VALUE_ZERO if parsed.kind == "zero" else "number",
                        raw=parsed.raw,
                        extra_flags=parsed.ambiguities,
                        cell_unit=parsed.unit,
                    )
                )
                continue
            if parsed.kind == "uninterpretable":
                measures.append(
                    _measure(
                        header,
                        locator,
                        scope if column_index else None,
                        value=None,
                        value_kind=VALUE_UNINTERPRETABLE,
                        raw=parsed.raw,
                        extra_flags=parsed.ambiguities,
                        cell_unit=parsed.unit,
                    )
                )
                continue
            if parsed.kind == "error":
                measures.append(
                    _measure(
                        header,
                        locator,
                        scope if column_index else None,
                        value=None,
                        value_kind=VALUE_ERROR,
                        raw=parsed.raw,
                        extra_flags=(),
                        cell_unit=None,
                    )
                )
                continue
            if parsed.kind == "text" and parsed.raw:
                blocks.append(
                    QualitativeBlock(kind="text_cell", text=parsed.raw, locator=locator)
                )
    return measures, blocks


def _measure(
    header,
    locator: dict,
    scope: str | None,
    *,
    value: str | None,
    value_kind: str,
    raw: str | None,
    extra_flags: tuple[str, ...],
    cell_unit: str | None,
) -> Measure:
    label = header.label if header else None
    unit = header.unit if header else None
    flags = header.ambiguities if header else ()
    if cell_unit and unit and cell_unit != unit:
        if {cell_unit, unit} <= {"EUR", "kEUR"}:
            extra_flags = (*extra_flags, "euro_scale")
            unit = None
        elif {cell_unit, unit} <= {"percent", "points"}:
            extra_flags = (*extra_flags, "percent_points")
            unit = None
    elif cell_unit:
        unit = cell_unit
    return Measure(
        label=label,
        value=value,
        value_kind=value_kind,
        unit=unit,
        period=header.period if header else None,
        scope=scope,
        definition=header.definition if header else None,
        locator=locator,
        ambiguities=merge_ambiguities(flags, extra_flags),
        raw=raw,
    )


def _header_index(rows: list[list[GridCell]]) -> int | None:
    for index, row in enumerate(rows[:-1]):
        if not _row_is_textual(row):
            continue
        follower = _next_nonempty(rows, index)
        if follower is not None and any(_is_numeric_like(cell) for cell in rows[follower]):
            return index
    return None


def _next_nonempty(rows: list[list[GridCell]], index: int) -> int | None:
    for follower in range(index + 1, len(rows)):
        if any(not cell.is_empty() for cell in rows[follower]):
            return follower
    return None


def _row_is_textual(row: list[GridCell]) -> bool:
    nonempty = [cell for cell in row if not cell.is_empty()]
    if not nonempty:
        return False
    return all(_is_textual(cell) for cell in nonempty)


def _is_textual(cell: GridCell) -> bool:
    if cell.source != "text":
        return False
    parsed = parse_cell(cell.raw)
    return parsed.kind in {"text", "formula"}


def _is_numeric_like(cell: GridCell) -> bool:
    if cell.source in {SOURCE_EXCEL_NUMBER, SOURCE_ABSENT, SOURCE_ERROR}:
        return True
    if cell.source != "text":
        return False
    return parse_cell(cell.raw).kind in {"number", "zero", "uninterpretable", "error"}


def _header_labels(row: list[GridCell]):
    labels = []
    for cell in row:
        if cell.horizontal_continuation and labels:
            labels.append(labels[-1])
            continue
        if cell.omit:
            labels.append(None)
            continue
        text = (cell.raw or "").strip()
        labels.append(interpret_label(text) if text else None)
    return labels


def _numeric_columns(rows: list[list[GridCell]], header_at: int | None) -> set[int]:
    start = 0 if header_at is None else header_at + 1
    columns: set[int] = set()
    for row in rows[start:]:
        for index, cell in enumerate(row):
            if _is_numeric_like(cell):
                columns.add(index)
    return columns


def _preamble(row, row_index: int, locate, kind: str) -> list[QualitativeBlock]:
    blocks = []
    for column_index, cell in enumerate(row):
        if cell.omit:
            continue
        text = (cell.raw or "").strip()
        if not text:
            continue
        blocks.append(
            QualitativeBlock(
                kind=kind,
                text=text,
                locator=_located(locate, row_index, column_index, None, cell),
            )
        )
    return blocks


def _header_blocks(row, row_index: int, locate) -> list[QualitativeBlock]:
    blocks = []
    for column_index, cell in enumerate(row):
        if cell.omit:
            continue
        text = (cell.raw or "").strip()
        if not text:
            continue
        blocks.append(
            QualitativeBlock(
                kind="label",
                text=text,
                locator=_located(locate, row_index, column_index, text, cell),
            )
        )
    return blocks


def _located(locate, row_index: int, column_index: int, header: str | None, cell: GridCell) -> dict:
    locator = locate(row_index, column_index, header)
    if cell.column_span > 1:
        locator["column_span"] = cell.column_span
    if cell.row_span > 1:
        locator["row_span"] = cell.row_span
    return locator


def _row_scope(row: list[GridCell]) -> str | None:
    if not row or row[0].is_empty():
        return None
    if row[0].source != "text":
        return None
    parsed = parse_cell(row[0].raw)
    if parsed.kind == "text":
        return parsed.raw
    return None
