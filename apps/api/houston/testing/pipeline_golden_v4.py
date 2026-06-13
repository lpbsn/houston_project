from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from houston.establishments.models import ActivitySubject, BusinessUnit, Establishment
from houston.signals.models import Signal

CORPUS_PATH = Path(__file__).with_name("pipeline_golden_v4_corpus.json")


@lru_cache(maxsize=1)
def load_pipeline_golden_v4_corpus() -> dict[str, Any]:
    with CORPUS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_pipeline_golden_v4_case(case_id: str) -> dict[str, Any]:
    corpus = load_pipeline_golden_v4_corpus()
    for case in corpus["cases"]:
        if case["id"] == case_id:
            return case
    raise KeyError(f"Unknown pipeline golden v4 case: {case_id}")


def list_pipeline_golden_v4_case_ids() -> list[str]:
    return [case["id"] for case in load_pipeline_golden_v4_corpus()["cases"]]


def setup_taxonomy_from_fixture(
    *,
    establishment: Establishment,
    fixture: dict[str, Any],
) -> tuple[dict[str, BusinessUnit], dict[str, ActivitySubject]]:
    from houston.testing.taxonomy import create_activity_subject, create_business_unit

    business_units: dict[str, BusinessUnit] = {}
    for unit_spec in fixture.get("business_units", []):
        business_units[unit_spec["key"]] = create_business_unit(
            establishment=establishment,
            key=unit_spec["key"],
            label=unit_spec.get("label", unit_spec["key"]),
            description=unit_spec.get("description", ""),
            unit_type=unit_spec.get("unit_type", BusinessUnit.UnitType.DEDICATED),
        )

    activity_subjects: dict[str, ActivitySubject] = {}
    for subject_spec in fixture.get("activity_subjects", []):
        business_unit = business_units[subject_spec["business_unit_key"]]
        subject = create_activity_subject(
            establishment=establishment,
            business_unit=business_unit,
            label=subject_spec["label"],
            description=subject_spec.get("description", ""),
        )
        activity_subjects[subject.normalized_name] = subject

    return business_units, activity_subjects


def setup_active_signals_from_fixture(
    *,
    establishment: Establishment,
    setup: list[dict[str, Any]],
    business_units: dict[str, BusinessUnit],
    activity_subjects: dict[str, ActivitySubject],
) -> dict[str, Signal]:
    from houston.signals.services import normalize_issue_focus
    from houston.testing.taxonomy import create_v3_signal

    signals: dict[str, Signal] = {}
    for signal_spec in setup:
        affected = business_units[signal_spec["affected_business_unit_key"]]
        responsible = business_units[signal_spec["responsible_business_unit_key"]]
        subject = activity_subjects[signal_spec["activity_subject_key"]]
        signals[signal_spec["ref"]] = create_v3_signal(
            establishment,
            affected_business_unit=affected,
            responsible_business_unit=responsible,
            activity_subject=subject,
            title=signal_spec["title"],
            structured_summary=signal_spec.get(
                "structured_summary",
                "Structured summary for golden corpus setup.",
            ),
            location_text=signal_spec.get("location_text", ""),
            issue_focus=normalize_issue_focus(signal_spec.get("issue_focus", "")),
            status=signal_spec.get("status", Signal.Status.OPEN),
        )
    return signals
