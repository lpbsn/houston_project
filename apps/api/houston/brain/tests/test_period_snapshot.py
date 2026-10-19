"""Period snapshot and first-reading selection. No provider call."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import pytest

from houston.brain.configuration import json_token_count
from houston.brain.investigation import (
    QUALIFICATION_COMPLETE,
    QUALIFICATION_REFUSED,
    InvestigationFacts,
    SubjectFinding,
    qualify,
)
from houston.brain.period import (
    LIMIT_PERIOD_EXCEEDS_CALL,
    MemoryDossier,
    PeriodCopy,
    PeriodSnapshotError,
    PeriodSource,
    freeze_period_snapshot,
    reading_input_tokens,
    select_first_reading,
    stored_view,
)

CAPTURE_AT = datetime(2026, 4, 1, 12, tzinfo=UTC)
PERIOD = (date(2026, 3, 1), date(2026, 3, 8))
WEEK = (date(2026, 3, 1), date(2026, 3, 8))
PARTIAL = (date(2026, 3, 1), date(2026, 3, 2))


def reporting() -> dict:
    return {
        "source_id": "R-01",
        "title": "Reporting restauration",
        "period_start": "2026-03-01",
        "period_end": "2026-03-08",
        "measures": [{"label": "frequentation", "value": "-12%"}],
    }


def series() -> tuple[dict, ...]:
    return (
        {
            "series_key": "frequentation",
            "label": "frequentation",
            "unit": "couverts",
            "scope": "restauration",
        },
    )


def field(
    source_id: str,
    *,
    pole: str,
    summary: str,
    start: date,
    end: date,
    category: str = "signal",
    title: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    linked: tuple[str, ...] = (),
    series_key: str = "",
    payload_extra: dict | None = None,
) -> PeriodSource:
    payload = {
        "source_id": source_id,
        "title": title or source_id,
        "structured_summary": summary,
        "business_units": {"affected": {"id": pole, "name": pole}},
        "status_at_period_start": {"value": "open"},
        "status_at_period_end": {"value": "open"},
    }
    if payload_extra:
        payload.update(payload_extra)
    return PeriodSource(
        source_id=source_id,
        category=category,
        pole=pole,
        start=start,
        end=end,
        created_at=created_at or (CAPTURE_AT - timedelta(days=1)),
        updated_at=updated_at or CAPTURE_AT,
        payload=payload,
        linked_source_ids=linked,
        series_key=series_key,
    )


def restaurant_week() -> tuple:
    """S-01 is last and has the full overlap. Fillers only cover the first day."""
    fillers = tuple(
        field(
            source_id,
            pole="restauration",
            title="Incident partiel",
            summary="REMPLISSAGE-RESTAURATION",
            start=PARTIAL[0],
            end=PARTIAL[1],
        )
        for source_id in ("R-01", "R-02", "R-03")
    )
    drowned = field(
        "S-01",
        pole="restauration",
        title="Service salle",
        summary="PREUVE-NOYEE",
        start=WEEK[0],
        end=WEEK[1],
    )
    other_pole = field(
        "S-02",
        pole="hebergement",
        title="Clients heberges",
        summary="PISTE-HEBERGEMENT",
        start=WEEK[0],
        end=WEEK[1],
    )
    other_extra = field(
        "H-99",
        pole="hebergement",
        title="Autre hebergement",
        summary="AUTRE-HEBERGEMENT",
        start=PARTIAL[0],
        end=PARTIAL[1],
    )
    sources = (*fillers, other_extra, drowned, other_pole)
    snapshot = freeze_period_snapshot(
        capture_at=CAPTURE_AT,
        period_start=PERIOD[0],
        period_end=PERIOD[1],
        reporting=reporting(),
        series=series(),
        sources=sources,
    )
    return snapshot, drowned.payload


def _select(snapshot, budget: int):
    return select_first_reading(
        snapshot,
        subject_pole="restauration",
        subject_start=WEEK[0],
        subject_end=WEEK[1],
        input_token_budget=budget,
    )


def _copy(snapshot, source_id: str):
    return next(item for item in snapshot.copies if item.source_id == source_id)


def test_s02_stays_while_same_pole_fillers_are_left_unread():
    snapshot, _source = restaurant_week()
    opened = _select(snapshot, 10**9)

    assert opened.representative_ids == ("S-01", "S-02")
    assert "R-01" not in opened.representative_ids
    budget = reading_input_tokens(snapshot, opened.representative_ids)
    assert budget < reading_input_tokens(snapshot, (*opened.representative_ids, "R-01"))
    reading = _select(snapshot, budget)
    blob = json.dumps(reading.payload)
    discovered = [item.source_id for item in reading.discovered_not_examined]

    assert reading.launched is True
    assert reading.limit is None
    assert reading.competing_period_lead_excluded is False
    assert reading.examined_ids == ("S-01", "S-02")
    assert "PREUVE-NOYEE" in blob
    assert "PISTE-HEBERGEMENT" in blob
    assert "REMPLISSAGE-RESTAURATION" not in blob
    assert "AUTRE-HEBERGEMENT" not in blob
    assert "index" not in reading.payload
    assert discovered == ["R-01", "R-02", "R-03", "H-99"]
    assert discovered.index("R-01") < discovered.index("H-99")
    assert "S-02" not in discovered
    assert all(item.pole == "restauration" for item in reading.discovered_not_examined[:3])
    assert "REMPLISSAGE-RESTAURATION" in _copy(snapshot, "R-01").payload["structured_summary"]
    assert "structured_summary" not in next(
        entry.as_record() for entry in snapshot.index if entry.source_id == "R-01"
    )
    search = json.dumps(reading.search_record())
    assert "REMPLISSAGE-RESTAURATION" not in search
    assert "PISTE-HEBERGEMENT" not in search


def test_a_window_that_holds_one_signal_does_not_omit_s02():
    snapshot, _source = restaurant_week()
    representatives = _select(snapshot, 10**9).representative_ids
    one_signal = reading_input_tokens(snapshot, (representatives[0],))
    both_poles = reading_input_tokens(snapshot, representatives)
    assert one_signal < both_poles

    reading = _select(snapshot, one_signal)
    result = qualify(
        InvestigationFacts(
            subjects=(
                SubjectFinding(
                    key="S-01",
                    examined=True,
                    affirmative=True,
                    verified_analytical=True,
                    cause_established=True,
                ),
            ),
            competing_period_lead_excluded=reading.competing_period_lead_excluded,
        )
    )
    search = json.dumps(reading.search_record())

    assert reading.launched is False
    assert reading.payload is None
    assert reading.examined_ids == ()
    assert reading.limit == LIMIT_PERIOD_EXCEEDS_CALL
    assert reading.competing_period_lead_excluded is True
    assert any(
        item.source_id == "S-02" and item.pole == "hebergement"
        for item in reading.discovered_not_examined
    )
    assert "PISTE-HEBERGEMENT" not in search
    assert "PREUVE-NOYEE" not in search
    assert result.qualification == QUALIFICATION_REFUSED
    assert result.qualification != QUALIFICATION_COMPLETE
    assert result.blocked_finding_keys == ("S-01",)
    assert result.investigation_succeeded is False


def test_resume_reloads_frozen_copies_and_does_not_rewrite_them():
    snapshot, source_payload = restaurant_week()
    source_payload["title"] = "APRES"
    source_payload["structured_summary"] = "APRES"
    assert _copy(snapshot, "S-01").payload["structured_summary"] == "PREUVE-NOYEE"

    dossier = MemoryDossier()
    dossier.save(snapshot)
    _copy(snapshot, "S-01").payload["structured_summary"] = "APRES"
    with pytest.raises(PeriodSnapshotError) as duplicate:
        dossier.add_copies(
            (
                PeriodCopy(
                    source_id="S-01",
                    category="signal",
                    pole="restauration",
                    role="chevauchement",
                    title="APRES",
                    start=WEEK[0],
                    end=WEEK[1],
                    payload={
                        "source_id": "S-01",
                        "title": "APRES",
                        "structured_summary": "APRES",
                    },
                ),
            )
        )
    assert duplicate.value.code == "copy_already_frozen"

    resumed = dossier.load()
    resumed_copy = _copy(resumed, "S-01")
    resumed_copy.payload["structured_summary"] = "APRES"
    reloaded = dossier.load()
    reading = _select(reloaded, reading_input_tokens(reloaded, ("S-01", "S-02")))
    blob = json.dumps(stored_view(reloaded)) + json.dumps(reading.payload)

    assert _copy(reloaded, "S-01").payload["title"] == "Service salle"
    assert _copy(reloaded, "S-01").payload["structured_summary"] == "PREUVE-NOYEE"
    assert "APRES" not in blob
    assert "PISTE-HEBERGEMENT" in blob
    assert reading.examined_ids == ("S-01", "S-02")
    with pytest.raises(PeriodSnapshotError) as sealed:
        dossier.save(snapshot)
    assert sealed.value.code == "dossier_already_frozen"


def test_period_snapshot_keeps_the_period_and_drops_forbidden_text():
    late = field(
        "L-01",
        pole="restauration",
        title="Declaration tardive",
        summary="Vu le 2026-03-04 au matin.",
        start=date(2026, 3, 9),
        end=date(2026, 3, 10),
        created_at=datetime(2026, 3, 9, 8, tzinfo=UTC),
        updated_at=datetime(2026, 3, 9, 8, tzinfo=UTC),
    )
    ancient = field(
        "D-01",
        pole="restauration",
        title="Ancien",
        summary="ANCIEN-DISTRACTEUR",
        start=date(2024, 1, 1),
        end=date(2024, 1, 8),
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )
    changed = field(
        "H-04",
        pole="restauration",
        title="APRES",
        summary="APRES",
        start=WEEK[0],
        end=WEEK[1],
        updated_at=CAPTURE_AT + timedelta(minutes=1),
    )
    raw = field(
        "RAW-01",
        pole="restauration",
        title="Signal sale",
        summary="RESUME AUTORISE",
        start=WEEK[0],
        end=WEEK[1],
        payload_extra={"raw_text": "OBSERVATION BRUTE", "observation": {"body": "brut"}},
    )
    opened = field(
        "E-04",
        pole="cuisine",
        title="Statut historique",
        summary="OUVERT PENDANT LA PERIODE",
        start=WEEK[0],
        end=WEEK[1],
        payload_extra={
            "events": [
                {"occurred_at": CAPTURE_AT - timedelta(days=3), "event_type": "opened"},
                {"occurred_at": CAPTURE_AT + timedelta(days=2), "event_type": "resolved"},
            ]
        },
    )
    execution = field(
        "E-02",
        pole="hebergement",
        category="execution",
        title="Execution hebergement",
        summary="EXECUTION-HEBERGEMENT",
        start=WEEK[0],
        end=WEEK[1],
    )
    raw_execution = field(
        "E-RAW",
        pole="hebergement",
        category="execution",
        title="Execution sale",
        summary="EXECUTION",
        start=WEEK[0],
        end=WEEK[1],
        payload_extra={"description": "OBSERVATION BRUTE"},
    )
    plan = PeriodSource(
        source_id="P-01",
        category="plan",
        pole="restauration",
        start=WEEK[0],
        end=WEEK[1],
        created_at=CAPTURE_AT - timedelta(days=1),
        updated_at=CAPTURE_AT,
        linked_source_ids=("E-04",),
        payload={
            "source_id": "P-01",
            "title": "Plan fin de periode",
            "source_signal_ids": ["E-04"],
            "catalog_status": "active",
        },
    )
    orphan_plan = PeriodSource(
        source_id="P-99",
        category="plan",
        pole="restauration",
        start=date(2024, 1, 1),
        end=date(2024, 1, 8),
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        linked_source_ids=("D-01",),
        payload={"source_id": "P-99", "title": "PLAN-ANCIEN"},
    )
    matched = PeriodSource(
        source_id="O-01",
        category="objective",
        pole="",
        start=WEEK[0],
        end=WEEK[1],
        created_at=CAPTURE_AT - timedelta(days=10),
        updated_at=CAPTURE_AT,
        series_key="frequentation",
        payload={
            "source_id": "O-01",
            "series_key": "frequentation",
            "indicator": "frequentation",
            "unit": "couverts",
            "scope": "restauration",
            "target": "stable",
            "period_start": "2026-03-01",
            "period_end": "2026-03-08",
        },
    )
    unmatched = PeriodSource(
        source_id="O-99",
        category="objective",
        pole="",
        start=WEEK[0],
        end=WEEK[1],
        created_at=CAPTURE_AT - timedelta(days=10),
        updated_at=CAPTURE_AT,
        series_key="spa",
        payload={
            "source_id": "O-99",
            "series_key": "spa",
            "indicator": "OBJECTIF-HORS-SERIE",
            "target": "invente",
        },
    )
    snapshot = freeze_period_snapshot(
        capture_at=CAPTURE_AT,
        period_start=PERIOD[0],
        period_end=PERIOD[1],
        reporting=reporting(),
        series=series(),
        sources=(
            late,
            ancient,
            changed,
            raw,
            opened,
            execution,
            raw_execution,
            plan,
            orphan_plan,
            matched,
            unmatched,
        ),
    )
    view = json.dumps(stored_view(snapshot))
    codes = {item.source_id: item.code for item in snapshot.omissions}
    kept = {item.source_id for item in snapshot.copies}
    indexed = {entry.source_id: entry for entry in snapshot.index}
    opened = select_first_reading(
        snapshot,
        subject_pole="restauration",
        subject_start=WEEK[0],
        subject_end=WEEK[1],
        input_token_budget=10**9,
    )
    reading = select_first_reading(
        snapshot,
        subject_pole="restauration",
        subject_start=WEEK[0],
        subject_end=WEEK[1],
        input_token_budget=reading_input_tokens(snapshot, opened.representative_ids),
    )

    assert "L-01" in kept
    assert _copy(snapshot, "L-01").role == "declaration_tardive"
    assert "D-01" not in kept
    assert "ANCIEN-DISTRACTEUR" not in view
    assert "PLAN-ANCIEN" not in view
    assert codes["D-01"] == "outside_period"
    assert codes["H-04"] == "modified_after_capture"
    assert "APRES" not in view
    assert codes["RAW-01"] == "copy_boundary"
    assert codes["E-RAW"] == "copy_boundary"
    assert "OBSERVATION BRUTE" not in view
    assert "resolved" not in view
    assert "opened" in view
    assert "P-01" in kept
    assert codes["P-99"] == "unlinked_plan"
    assert codes["O-99"] == "series_mismatch"
    assert "OBJECTIF-HORS-SERIE" not in view
    assert snapshot.objectives[0]["indicator"] == "frequentation"
    assert "D-01" not in indexed
    assert indexed["E-02"].pole == "hebergement"
    assert "structured_summary" not in indexed["E-02"].as_record()
    assert indexed["E-02"].text_tokens == json_token_count(
        {"title": "Execution hebergement", "structured_summary": "EXECUTION-HEBERGEMENT"}
    )
    assert opened.representative_ids == ("L-01", "E-04", "E-02")
    assert "P-01" not in opened.representative_ids
    assert reading.launched is True
    assert reading.examined_ids == opened.representative_ids
    assert "E-02" in reading.examined_ids
    assert "EXECUTION-HEBERGEMENT" in json.dumps(reading.payload)
    assert "P-01" not in reading.examined_ids
    assert reading.competing_period_lead_excluded is False


def test_a_reporting_observation_is_refused_without_its_text():
    dirty = reporting()
    dirty["raw_text"] = "OBSERVATION BRUTE"
    with pytest.raises(PeriodSnapshotError) as raised:
        freeze_period_snapshot(
            capture_at=CAPTURE_AT,
            period_start=PERIOD[0],
            period_end=PERIOD[1],
            reporting=dirty,
        )
    assert raised.value.code == "reporting_forbidden"
    assert "OBSERVATION BRUTE" not in str(raised.value)
