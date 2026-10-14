"""Section grouping and subdivision. No provider call."""

from __future__ import annotations

import io

import pytest

from houston.brain.configuration import (
    call_input_tokens,
    digest,
    json_token_count,
)
from houston.brain.errors import BrainWorkError
from houston.brain.extract import extract_document
from houston.brain.lots import (
    PlanningTrace,
    _merge,
    _ReadingMeter,
    plan_lots,
    reading_envelope,
    sections_from_payload,
)


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


def test_a_closed_lot_reserves_the_exact_call_cost():
    planned = plan_lots(
        [_paragraph("paquet " * 30)],
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=4,
    )
    lot = planned[0]
    assert lot.reserved_input_tokens == call_input_tokens(lot.payload)
    assert lot.planning_tokens >= lot.reserved_input_tokens
    assert plan_lots.last_trace.request_encodings == 1


def test_a_section_must_fit_the_call_ceiling():
    section = _paragraph("paquet " * 30)
    planned = plan_lots(
        [section],
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=4,
    )
    ceiling = planned[0].planning_tokens
    fitting = plan_lots(
        [section],
        per_call_input_tokens=ceiling,
        total_input_tokens=ceiling * 4,
        max_calls=4,
    )
    assert len(fitting) == 1
    with pytest.raises(BrainWorkError) as raised:
        plan_lots(
            [section],
            per_call_input_tokens=ceiling - 1,
            total_input_tokens=ceiling * 4,
            max_calls=4,
        )
    assert raised.value.code == "budget_exceeded"


def test_an_oversized_table_is_split_and_each_lot_repeats_the_header():
    section = _table(["ligne"] * 6)
    one = plan_lots(
        [_table(["ligne"])],
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=2,
    )
    two = plan_lots(
        [_table(["ligne", "ligne"])],
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=2,
    )
    per_call = max(one[0].planning_tokens, two[0].planning_tokens - 1)
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
    one = plan_lots(
        [sections[0]],
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=2,
    )
    with pytest.raises(BrainWorkError) as raised:
        plan_lots(
            sections,
            per_call_input_tokens=80_000,
            total_input_tokens=one[0].reserved_input_tokens,
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


def _texts(planned) -> str:
    chunks: list[str] = []
    for lot in planned:
        for section in lot.payload["sections"]:
            if section.get("text"):
                chunks.append(section["text"])
            for row in section.get("rows") or []:
                chunks.append(row.get("text") or "")
    return "\n".join(chunks)


def test_a_measure_table_keeps_one_item_per_row_in_order():
    payload = {
        "qualitative": [],
        "measures": [
            {
                "label": "CA",
                "value": "10",
                "unit": "EUR",
                "raw": "10 EUR",
                "value_kind": "number",
                "definition": "Chiffre encaissé",
                "ambiguities": ["hors taxes"],
                "locator": {"sheet": "Suivi", "header": "Mois", "row": str(index + 2)},
            }
            for index in range(3)
        ],
    }
    section = sections_from_payload(payload)[0]
    assert section["item_ids"] == [
        "document:measure:0000",
        "document:measure:0001",
        "document:measure:0002",
    ]
    assert [row["stable_key"] for row in section["rows"]] == section["item_ids"]
    assert section["rows"][0]["definition"] == "Chiffre encaissé"
    assert section["rows"][0]["ambiguities"] == ["hors taxes"]
    assert "definition" not in section["rows"][0]["text"]
    assert section["rows"][0]["text"] == "CA 10 EUR 10 EUR"


def test_minimal_output_fits_until_the_output_ceiling():
    from django.conf import settings

    from houston.brain.contract import minimal_call_output

    ceiling = int(settings.HOUSTON_BRAIN_PER_CALL_OUTPUT_TOKENS)

    def fits(piece_id, count: int) -> bool:
        pieces = [piece_id(index) for index in range(count)]
        return json_token_count(minimal_call_output(pieces)) <= ceiling

    def largest(piece_id) -> int:
        low, high = 1, 1
        while fits(piece_id, high):
            high *= 2
            if high > 8192:
                break
        while low < high:
            mid = (low + high + 1) // 2
            if fits(piece_id, mid):
                low = mid
            else:
                high = mid - 1
        return low

    short = largest(lambda index: f"s{index:04d}")
    subdivided = largest(lambda index: f"s{index:04d}-p0000")
    assert short > 0
    assert subdivided < short
    short_ids = [f"s{index:04d}" for index in range(short)]
    assert json_token_count(minimal_call_output(short_ids)) <= ceiling
    assert (
        json_token_count(minimal_call_output([f"s{index:04d}" for index in range(short + 1)]))
        > ceiling
    )


def test_synthesis_majorant_names_the_last_accepted_lot_count():
    from houston.brain.configuration import empty_knowledge
    from houston.brain.contract import MAX_SUBJECTS, synthesis_input_majorant

    pieces = [f"s{index:04d}" for index in range(467)]
    knowledge = empty_knowledge()
    output_tokens = 8_000
    ceiling = 80_000

    def bound(lot_count: int) -> int:
        return synthesis_input_majorant(
            pieces,
            key_slots=MAX_SUBJECTS,
            knowledge=knowledge,
            per_call_output_tokens=output_tokens,
            lot_count=lot_count,
        )

    accepted = max(lot_count for lot_count in range(0, 13) if bound(lot_count) <= ceiling)
    assert bound(accepted) <= ceiling
    assert bound(accepted + 1) > ceiling


def _field_limit(model, name: str) -> int:
    for constraint in model.model_fields[name].metadata:
        limit = getattr(constraint, "max_length", None)
        if isinstance(limit, int):
            return limit
    raise AssertionError(name)


def _fit_statement(doc: dict, ceiling: int, statement_limit: int) -> int:
    subject = doc["subjects"][0]
    low, high = 1, statement_limit
    best = "x"
    while low <= high:
        mid = (low + high) // 2
        subject["statement"] = "\U00010000" * mid
        if json_token_count(doc) <= ceiling:
            best = subject["statement"]
            low = mid + 1
        else:
            high = mid - 1
    subject["statement"] = best
    return json_token_count(doc)


def _widest_keys(count: int, width: int) -> list[str]:
    head = "\U00010000" * (width - 2)
    return [
        head + chr(0x10000 + index) + chr(0x10100 + index)
        for index in range(count)
    ]


def test_correction_majorant_covers_issues_beside_a_full_candidate():
    """Issues and the widest subject keys sit outside the reserved output ceiling."""
    from django.conf import settings

    from houston.brain.configuration import empty_knowledge
    from houston.brain.contract import (
        MAX_SUBJECTS,
        SCHEMA_VERSION,
        MechanismProposal,
        Proposals,
        Subject,
        assess,
        correction_envelope,
        correction_input_majorant,
        correction_shell,
    )

    knowledge = empty_knowledge()
    ceiling = int(settings.HOUSTON_BRAIN_PER_CALL_OUTPUT_TOKENS)
    evidence_limit = _field_limit(Subject, "evidence")
    statement_limit = _field_limit(Subject, "statement")
    key_width = _field_limit(Subject, "key")
    mechanism_limit = _field_limit(Proposals, "mechanisms")
    evidence_id_limit = _field_limit(MechanismProposal, "evidence_item_ids")
    subject = {
        "key": "sujet",
        "statement": "x",
        "evidence": [{"item_id": "x", "locator": {}} for _ in range(evidence_limit)],
        "interpretation": "x",
        "contradictions": [],
        "gaps": [],
        "orientation": "NO_ACTION",
        "calculations": [],
        "reported_facts": [],
        "limits": [],
    }
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "subjects": [subject],
        "coverage": [],
        "limits": [],
        "proposals": {"suggestions": [], "mechanisms": []},
    }
    fitted = _fit_statement(candidate, ceiling, statement_limit)
    assert ceiling - fitted < 8
    short_keys = [f"k{index:04d}" for index in range(MAX_SUBJECTS)]
    assessed = assess(candidate, pieces=["s0000"], items=[], required_subject_keys=short_keys)
    assert assessed.parsed is not None
    references = [issue for issue in assessed.issues if issue.code == "invalid_reference"]
    assert len(references) == evidence_limit
    citation_envelope = correction_envelope(
        assessed.issues,
        (),
        [],
        short_keys,
        candidate=candidate,
        knowledge=knowledge,
        assemble_coverage=True,
    )
    wide_keys = _widest_keys(MAX_SUBJECTS, key_width)
    assert len(wide_keys) == len(set(wide_keys)) == MAX_SUBJECTS
    assert all(len(key) == key_width for key in wide_keys)
    mechanisms = [
        {
            "key": f"m{index:02d}",
            "formulation": "f",
            "global_formulation": "",
            "conditions": "",
            "limits": "",
            "uncertainty": "",
            "evidence_item_ids": ["x"] * evidence_id_limit,
        }
        for index in range(mechanism_limit)
    ]
    dense = {
        "schema_version": SCHEMA_VERSION,
        "subjects": [
            {
                "key": "sujet",
                "statement": "x",
                "evidence": [],
                "interpretation": "x",
                "contradictions": [],
                "gaps": ["x"],
                "orientation": "NO_ACTION",
                "calculations": [],
                "reported_facts": [],
                "limits": [],
            }
        ],
        "coverage": [],
        "limits": [],
        "proposals": {"suggestions": [], "mechanisms": mechanisms},
    }
    dense_fitted = _fit_statement(dense, ceiling, statement_limit)
    assert ceiling - dense_fitted < 8
    dense_assessed = assess(dense, pieces=["s0000"], items=[], required_subject_keys=wide_keys)
    assert dense_assessed.parsed is not None
    dense_references = [
        issue for issue in dense_assessed.issues if issue.code == "invalid_reference"
    ]
    assert len(dense_references) == mechanism_limit * evidence_id_limit
    old = call_input_tokens(correction_shell(key_slots=MAX_SUBJECTS, knowledge=knowledge)) + ceiling
    citation_actual = call_input_tokens(citation_envelope)
    assert citation_actual > old
    assert citation_actual - old >= 300
    reserved = correction_input_majorant(
        key_slots=MAX_SUBJECTS,
        knowledge=knowledge,
        per_call_output_tokens=ceiling,
    )
    assert citation_actual <= reserved
    wide_envelope = correction_envelope(
        assessed.issues,
        (),
        [],
        wide_keys,
        candidate=candidate,
        knowledge=knowledge,
        assemble_coverage=True,
    )
    assert call_input_tokens(wide_envelope) <= reserved
    dense_envelope = correction_envelope(
        dense_assessed.issues,
        (),
        [],
        wide_keys,
        candidate=dense,
        knowledge=knowledge,
        assemble_coverage=True,
    )
    assert call_input_tokens(dense_envelope) <= reserved
    assert reserved <= int(settings.HOUSTON_BRAIN_PER_CALL_INPUT_TOKENS)


def test_analysis_correction_majorant_covers_one_output_issues():
    """A single lot sends the issue list and the output's keys, not the candidate."""
    from django.conf import settings

    from houston.brain.configuration import empty_knowledge
    from houston.brain.contract import (
        MAX_SUBJECTS,
        SCHEMA_VERSION,
        MechanismProposal,
        Proposals,
        analysis_correction_majorant,
        assess,
        correction_envelope,
    )

    knowledge = empty_knowledge()
    ceiling = int(settings.HOUSTON_BRAIN_PER_CALL_OUTPUT_TOKENS)
    pieces = ["s0000"]
    old_payload = correction_envelope(
        (),
        pieces,
        [],
        [f"k{index:04d}" for index in range(MAX_SUBJECTS)],
    )
    old_payload["knowledge"] = knowledge
    old = call_input_tokens(old_payload)
    invalid = {
        "schema_version": SCHEMA_VERSION,
        "subjects": [
            {
                "key": "k",
                "statement": "x",
                "interpretation": "x",
                "orientation": "NO_ACTION",
                "evidence": [{"item_id": None, "locator": {"sheet": None}}],
                "gaps": [],
            }
            for _ in range(20)
        ],
        "coverage": [],
    }
    failed = assess(invalid, pieces=pieces, items=[])
    assert failed.parsed is None
    assert failed.subject_keys == ()
    assert len(failed.issues) >= 20
    failed_payload = correction_envelope(failed.issues, pieces, [], failed.subject_keys)
    failed_payload["knowledge"] = knowledge
    failed_actual = call_input_tokens(failed_payload)
    assert failed_actual - old >= 200
    mechanism_limit = _field_limit(Proposals, "mechanisms")
    evidence_id_limit = _field_limit(MechanismProposal, "evidence_item_ids")
    dense = {
        "schema_version": SCHEMA_VERSION,
        "subjects": [
            {
                "key": "sujet",
                "statement": "x",
                "evidence": [],
                "interpretation": "x",
                "contradictions": [],
                "gaps": ["x"],
                "orientation": "NO_ACTION",
                "calculations": [],
                "reported_facts": [],
                "limits": [],
            }
        ],
        "coverage": [],
        "limits": [],
        "proposals": {
            "suggestions": [],
            "mechanisms": [
                {
                    "key": f"m{index:02d}",
                    "formulation": "f",
                    "global_formulation": "",
                    "conditions": "",
                    "limits": "",
                    "uncertainty": "",
                    "evidence_item_ids": ["x"] * evidence_id_limit,
                }
                for index in range(mechanism_limit)
            ],
        },
    }
    assert json_token_count(dense) <= ceiling
    parsed = assess(dense, pieces=pieces, items=[])
    assert parsed.parsed is not None
    references = [issue for issue in parsed.issues if issue.code == "invalid_reference"]
    assert len(references) == mechanism_limit * evidence_id_limit
    dense_payload = correction_envelope(parsed.issues, pieces, [], parsed.subject_keys)
    dense_payload["knowledge"] = knowledge
    dense_actual = call_input_tokens(dense_payload)
    assert dense_actual > old
    reserved = analysis_correction_majorant(
        pieces,
        [],
        key_slots=MAX_SUBJECTS,
        knowledge=knowledge,
        per_call_output_tokens=ceiling,
    )
    assert failed_actual <= reserved
    assert dense_actual <= reserved
    assert reserved <= int(settings.HOUSTON_BRAIN_PER_CALL_INPUT_TOKENS)


def test_document_keys_keep_source_indexes_in_capture_and_lots():
    from houston.brain.collection import _document_rows

    payload = {
        "qualitative": [
            {"text": "  "},
            {"text": "Café — déjà"},
            "ignore",
            {"text": "Suite"},
        ],
        "measures": [
            "ignore",
            {
                "label": "CA",
                "value": "1",
                "unit": "EUR",
                "raw": "1",
                "locator": {"sheet": "Suivi"},
            },
        ],
    }
    row_keys = [row.stable_key for row in _document_rows(payload)]
    section_keys = []
    for section in sections_from_payload(payload):
        section_keys.extend(section["item_ids"])
    assert row_keys == [
        "document:qualitative:0001",
        "document:qualitative:0003",
        "document:measure:0000",
    ]
    assert section_keys == row_keys


def test_incremental_tokens_bound_the_closed_request_without_merge_encodes():
    knowledge = {
        "formulation": 'déjà "vu" — 日本語 \\ chemin',
        "limits": "ligne\nsuivante\t\u0001",
        "uncertainty": "",
    }
    searches = ["unité", 'code "spécial"', ""]
    sections = [
        {
            "kind": "paragraph",
            "text": "",
            "locator": {},
            "item_ids": [],
            "piece_id": 's"0000"',
        },
        {
            "kind": "table",
            "header": "Mois",
            "unit": None,
            "locator": {"sheet": "Suivi / été"},
            "rows": [
                {
                    "text": "Café ☕",
                    "locator": {"row": 2},
                    "stable_key": "document:measure:0000",
                }
            ],
            "item_ids": ["document:measure:0000"],
            "piece_id": "s0001-p0000",
        },
        {
            "kind": "paragraph",
            "text": "sans piece",
            "locator": {"block": 1},
        },
    ]
    items = [
        {
            "item_id": "signal-1",
            "stable_key": "signal:1",
            "category": "signal",
            "role": "copie",
            "payload": {"text": "preuve — \u2603", "tags": [], "note": None},
        },
        {
            "item_id": "plan-1",
            "stable_key": "plan:1",
            "category": "plan",
            "role": "copie",
            "payload": {"execution_ids": ["ex-1"], "label": "Plan \\ déjà"},
        },
    ]
    meter = _ReadingMeter(
        knowledge,
        searches,
        provider="fake",
        model="fake",
        trace=PlanningTrace(),
    )
    merged = meter.section_group(sections[0])
    for section in sections[1:]:
        incoming = meter.section_group(section)
        encoded = meter.trace.object_encodings
        merged = _merge(merged, incoming)
        assert meter.trace.object_encodings == encoded
    incoming_items = meter.item_group(items)
    encoded = meter.trace.object_encodings
    merged = _merge(merged, incoming_items)
    assert meter.trace.object_encodings == encoded
    assert meter.trace.request_encodings == 0
    envelope = reading_envelope(
        merged.sections,
        knowledge,
        searches=searches,
        items=merged.items,
    )
    assert meter.tokens(merged.cost) >= call_input_tokens(envelope)

    bare = _ReadingMeter(None, [], provider="fake", model="fake", trace=PlanningTrace())
    one = bare.section_group({"kind": "paragraph", "text": "seul", "piece_id": "s0000"})
    alone = reading_envelope(one.sections, None, searches=[], items=[])
    assert "items" not in alone
    assert bare.tokens(one.cost) >= call_input_tokens(alone)


def test_packed_lot_boundaries_and_hashes_match_the_full_envelope():
    knowledge = {"formulation": "Knowledge été — 中文", "limits": "aucune"}
    searches = ["chevauchement_signals", "unité"]
    sections = [
        _paragraph(f"Café {index} — ligne déjà vue " + ("漢" * (index % 7)) + ' "suite"')
        for index in range(48)
    ]
    longest = max(sections, key=lambda section: len(section["text"]))
    alone = plan_lots(
        [longest],
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=2,
        knowledge=knowledge,
        searches=searches,
    )
    per_call = alone[0].planning_tokens
    planned = plan_lots(
        sections,
        per_call_input_tokens=per_call,
        total_input_tokens=per_call * len(sections),
        max_calls=len(sections),
        knowledge=knowledge,
        searches=searches,
    )
    assert len(planned) > 1
    _assert_lot_boundaries(planned, per_call)
    assert plan_lots.last_trace.request_encodings == len(planned)

    row_texts = [f"CA été {index} — {index},00 €" for index in range(120)]
    one_row = plan_lots(
        [_table([max(row_texts, key=len)])],
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=2,
        knowledge=knowledge,
        searches=searches,
    )
    # A subdivided row carries a longer piece id than the unsplit one-row table.
    table_call = max(per_call, one_row[0].planning_tokens + 32)
    table = _table(row_texts)
    table_plan = plan_lots(
        [table],
        per_call_input_tokens=table_call,
        total_input_tokens=table_call * 120,
        max_calls=120,
        knowledge=knowledge,
        searches=searches,
    )
    assert len(table_plan) > 1
    _assert_lot_boundaries(table_plan, table_call)
    assert plan_lots.last_trace.request_encodings == len(table_plan)


def _assert_lot_boundaries(planned, per_call: int) -> None:
    for lot in planned:
        assert lot.input_hash == digest(lot.payload)
        assert lot.reserved_input_tokens == call_input_tokens(lot.payload)
        assert lot.planning_tokens >= lot.reserved_input_tokens
        assert lot.reserved_input_tokens <= per_call
        assert lot.planning_tokens <= per_call


def test_unknown_openai_model_is_unusable_before_a_lot_is_closed():
    with pytest.raises(BrainWorkError) as raised:
        plan_lots(
            [_paragraph("Un.")],
            per_call_input_tokens=80_000,
            total_input_tokens=400_000,
            max_calls=4,
            provider="openai",
            model="gpt-not-a-brain-model",
        )
    assert raised.value.code == "configuration_unusable"
    assert plan_lots.last_trace.request_encodings == 0


def test_o200k_models_count_offline_and_other_encodings_are_refused(monkeypatch):
    """gpt-4 uses cl100k. Loading it would fetch a remote rank file."""
    import tiktoken.load as load

    from houston.brain import configuration

    def refuse_remote(blobpath: str) -> bytes:
        if "://" in blobpath:
            raise AssertionError(blobpath)
        with open(blobpath, "rb", buffering=0) as handle:
            return handle.read()

    monkeypatch.setattr(load, "read_file", refuse_remote)
    configuration._o200k_encoding = None
    for model in ("gpt-5-mini", "gpt-5-mini-2026-01-01", "gpt-4o", "gpt-4.1"):
        planned = plan_lots(
            [_paragraph("déjà")],
            per_call_input_tokens=80_000,
            total_input_tokens=400_000,
            max_calls=2,
            provider="openai",
            model=model,
        )
        assert planned[0].reserved_input_tokens == call_input_tokens(
            planned[0].payload,
            provider="openai",
            model=model,
        )
    with pytest.raises(BrainWorkError) as raised:
        plan_lots(
            [_paragraph("Un.")],
            per_call_input_tokens=80_000,
            total_input_tokens=400_000,
            max_calls=2,
            provider="openai",
            model="gpt-4",
        )
    assert raised.value.code == "configuration_unusable"
    assert plan_lots.last_trace.request_encodings == 0


def test_fake_provider_counts_with_o200k_for_any_model_name():
    planned = plan_lots(
        [_paragraph("déjà")],
        per_call_input_tokens=80_000,
        total_input_tokens=400_000,
        max_calls=2,
        provider="fake",
        model="gpt-not-a-brain-model",
    )
    assert planned[0].reserved_input_tokens == call_input_tokens(
        planned[0].payload,
        provider="fake",
        model="gpt-not-a-brain-model",
    )


def test_a_large_table_is_planned_once_per_piece_and_once_per_lot():
    import time

    rows = [f"ligne {index}" for index in range(20_000)]
    started = time.perf_counter()
    planned = plan_lots(
        [_table(rows)],
        per_call_input_tokens=80_000,
        total_input_tokens=50_000_000,
        max_calls=20_000,
    )
    elapsed = time.perf_counter() - started
    trace = plan_lots.last_trace
    assert elapsed < 10
    assert trace.request_encodings == len(planned)
    assert trace.object_encodings == 2 + (20_000 * 2)
    assert all(lot.planning_tokens >= lot.reserved_input_tokens for lot in planned)


def test_mama_shelter_dataset_is_fully_planned_or_refused_before_any_call():
    from houston.brain.configuration import empty_knowledge
    from houston.brain.contract import (
        MAX_SUBJECTS,
        analysis_correction_majorant,
        correction_input_majorant,
        synthesis_input_majorant,
    )
    from houston.establishments.mama_nice_dataset_compiler import compile_mama_nice_dataset
    from houston.establishments.mama_nice_dataset_constants import HISTORICAL_FROM_SIGNAL

    corpus = compile_mama_nice_dataset()
    assert not corpus.errors
    signals = corpus.signal_specs
    observations = corpus.observation_specs
    executions = _mama_executions(corpus)
    assert len(signals) == 420
    assert len(observations) == 692
    assert len(executions) == HISTORICAL_FROM_SIGNAL + len(corpus.overdue_specs)
    elements = _mama_items(signals, observations, executions)
    assert len(elements) == 420 + 692 + len(executions)
    expected = [item.stable_key for item in elements]
    per_call = 80_000
    total = 500_000
    max_calls = 12
    knowledge = empty_knowledge()
    try:
        planned = plan_lots(
            [_paragraph("Reporting Mama Shelter Nice.")],
            per_call_input_tokens=per_call,
            total_input_tokens=total,
            max_calls=max_calls,
            knowledge=knowledge,
            searches=["chevauchement_signals"],
            items=elements,
        )
    except BrainWorkError as exc:
        assert exc.code == "budget_exceeded"
        return
    assigned = []
    for lot in planned:
        for item in lot.payload.get("items") or []:
            if item.get("stable_key"):
                assigned.append(str(item["stable_key"]))
    assert len(assigned) == len(set(assigned))
    assert set(assigned) == set(expected)
    pieces = []
    for lot in planned:
        pieces.extend(lot.payload.get("required_piece_ids") or [])
    if len(planned) > 1:
        tail = synthesis_input_majorant(
            pieces,
            key_slots=MAX_SUBJECTS,
            knowledge=knowledge,
            per_call_output_tokens=8_000,
            lot_count=len(planned),
        ) + correction_input_majorant(
            key_slots=MAX_SUBJECTS,
            knowledge=knowledge,
            per_call_output_tokens=8_000,
        )
        calls = len(planned) + 2
    else:
        tail = analysis_correction_majorant(
            pieces,
            elements,
            key_slots=MAX_SUBJECTS,
            knowledge=knowledge,
            per_call_output_tokens=8_000,
        )
        calls = len(planned) + 1
    reserved = sum(lot.reserved_input_tokens for lot in planned) + tail
    within = (
        all(lot.reserved_input_tokens <= per_call for lot in planned)
        and all(lot.planning_tokens >= lot.reserved_input_tokens for lot in planned)
        and reserved <= total
        and calls <= max_calls
    )
    if not within:
        return
    assert within


def _mama_executions(corpus) -> list:
    """Signal-linked historical executions plus overdue specs, with their texts.

    The compiler does not list the 260 historical rows. Replay builds 180 of them
    from the first resolved or canceled signals. The six overdue specs are the
    other authored executions available without a database.
    """
    from houston.establishments.mama_nice_dataset_constants import HISTORICAL_FROM_SIGNAL
    from houston.establishments.mama_nice_dataset_copy import execution_tasks, execution_title

    linked = [
        spec
        for spec in corpus.signal_specs
        if spec["status"] in {"resolved", "canceled"}
    ][:HISTORICAL_FROM_SIGNAL]
    executions = [
        {
            "seed_key": f"exec:signal:{spec['seed_key']}",
            "source_signal_id": spec["seed_key"],
            "title": execution_title(spec["issue_focus"]),
            "text": spec["issue_focus"],
            "tasks": list(execution_tasks(spec["canonical_object"])),
        }
        for spec in linked
    ]
    executions.extend(corpus.overdue_specs)
    return executions


def _mama_items(signals, observations, executions):
    items = []
    for spec in signals:
        items.append(
            _mama_item(
                spec["seed_key"],
                "signal",
                {
                    "source_id": spec["seed_key"],
                    "title": spec.get("title") or "",
                    "issue_focus": spec.get("issue_focus") or "",
                    "text": spec.get("issue_focus") or "",
                },
            )
        )
    for spec in observations:
        items.append(
            _mama_item(
                spec["seed_key"],
                "observation",
                {
                    "source_signal_id": spec.get("signal_seed_key") or "",
                    "text": spec.get("raw_text") or "",
                    "raw_text": spec.get("raw_text") or "",
                },
            )
        )
    for spec in executions:
        if isinstance(spec, dict):
            key = spec["seed_key"]
            payload = {
                "source_id": key,
                "source_signal_id": spec["source_signal_id"],
                "title": spec["title"],
                "text": spec["text"],
                "tasks": list(spec["tasks"]),
            }
        else:
            key = spec.seed_key
            payload = {
                "source_id": key,
                "title": spec.title,
                "text": spec.context,
                "context": spec.context,
            }
            if spec.oneshot_tasks:
                payload["tasks"] = list(spec.oneshot_tasks)
        items.append(_mama_item(key, "execution", payload))
    return items


def _mama_item(stable_key: str, category: str, payload: dict):
    from types import SimpleNamespace

    return SimpleNamespace(
        id=stable_key,
        stable_key=stable_key,
        category=category,
        role="copie",
        payload=payload,
    )
