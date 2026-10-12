"""Section grouping and subdivision. No provider call."""

from __future__ import annotations

import io

import pytest

from houston.brain.configuration import estimate_tokens
from houston.brain.errors import BrainWorkError
from houston.brain.extract import extract_document
from houston.brain.lots import plan_lots, sections_from_payload


def _paragraph(text: str) -> dict:
    return {"kind": "paragraph", "text": text, "locator": {"block": text[:12]}}


def _table(rows: list[str]) -> dict:
    return {
        "kind": "table",
        "header": "Mois",
        "unit": "EUR",
        "locator": {"sheet": "Suivi"},
        "rows": [{"text": row, "locator": {"row": index + 1}} for index, row in enumerate(rows)],
    }


def test_three_short_sections_form_one_lot():
    sections = [_paragraph("un"), _paragraph("deux"), _paragraph("trois")]
    planned = plan_lots(
        sections,
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=12,
    )
    assert len(planned) == 1
    texts = [section["text"] for section in planned[0].payload["sections"]]
    assert texts == ["un", "deux", "trois"]


def test_an_oversized_table_is_split_and_each_lot_repeats_the_header():
    section = _table(["ligne"] * 6)
    one = estimate_tokens({"sections": [_table_piece(section, 1)]})
    two = estimate_tokens({"sections": [_table_piece(section, 2)]})
    per_call = max(one, two - 1)
    planned = plan_lots(
        [section],
        per_call_input_tokens=per_call,
        total_input_tokens=per_call * 20,
        max_calls=12,
    )
    assert len(planned) > 1
    headers = [
        part["header"] == "Mois" and part["unit"] == "EUR"
        for lot in planned
        for part in lot.payload["sections"]
    ]
    parents = [
        part["locator"]["sheet"] == "Suivi"
        for lot in planned
        for part in lot.payload["sections"]
    ]
    assert headers
    assert all(headers)
    assert all(parents)


def test_one_row_above_the_call_ceiling_fails_before_any_lot():
    section = _table(["x" * 400])
    with pytest.raises(BrainWorkError) as raised:
        plan_lots(
            [section],
            per_call_input_tokens=1,
            total_input_tokens=400_000,
            max_calls=12,
        )
    assert raised.value.code == "budget_exceeded"


def test_reserved_lots_above_the_total_fail():
    sections = [_paragraph(f"section {index} " * 30) for index in range(4)]
    one = estimate_tokens({"sections": [sections[0]]})
    with pytest.raises(BrainWorkError) as raised:
        plan_lots(
            sections,
            per_call_input_tokens=one,
            total_input_tokens=one,
            max_calls=12,
        )
    assert raised.value.code == "budget_exceeded"


def test_extracted_docx_paragraph_and_xlsx_text_are_in_the_lot_payload():
    from docx import Document
    from openpyxl import Workbook

    document = Document()
    document.add_paragraph("Le service du soir a été lent.")
    docx_buffer = io.BytesIO()
    document.save(docx_buffer)
    docx = extract_document(docx_buffer.getvalue(), "docx")
    book = Workbook()
    sheet = book.active
    sheet.title = "Mars"
    sheet["A1"] = "Commentaire salle"
    xlsx_buffer = io.BytesIO()
    book.save(xlsx_buffer)
    xlsx = extract_document(xlsx_buffer.getvalue(), "xlsx")

    docx_lots = plan_lots(
        sections_from_payload(docx.as_payload()),
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=12,
    )
    xlsx_lots = plan_lots(
        sections_from_payload(xlsx.as_payload()),
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=12,
    )
    assert "Le service du soir a été lent." in _texts(docx_lots)
    assert "Commentaire salle" in _texts(xlsx_lots)


def _table_piece(section: dict, count: int) -> dict:
    return {
        "kind": "table",
        "header": section["header"],
        "unit": section["unit"],
        "locator": section["locator"],
        "rows": section["rows"][:count],
    }


def _texts(planned) -> str:
    chunks: list[str] = []
    for lot in planned:
        for section in lot.payload["sections"]:
            if section.get("text"):
                chunks.append(section["text"])
            for row in section.get("rows") or []:
                chunks.append(row.get("text") or "")
    return "\n".join(chunks)
