"""Compare title-wording smoke archives without calling a provider.

Each live run creates a new establishment, so routing keys embed a fresh id.
Comparison resolves those keys inside the taxonomy archived for that run and
compares the business identity (catalog, specific name, subject label).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

TITLE_WRITING_CRITERIA_PROMPT_VERSION = "ai_observation_pipeline_v6_5"

_NUMBER_RE = re.compile(r"\d+")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def title_archive_kind(prompt_version: str) -> str:
    """Filename prefix kept distinct per prompt version by write_smoke_archive."""
    return f"title-wording-{prompt_version}"


def title_writing_criteria_apply(prompt_version: str) -> bool:
    return prompt_version == TITLE_WRITING_CRITERIA_PROMPT_VERSION


def routing_context_from_taxonomy(routing_taxonomy: dict[str, Any]) -> dict[str, Any]:
    """Stable join context for one run. Keys stay run-local; labels do not."""
    business_units: list[dict[str, Any]] = []
    for unit in routing_taxonomy.get("business_units") or []:
        subjects = [
            {
                "routing_key": subject.get("routing_key"),
                "label": subject.get("label") or "",
                "catalog_key": subject.get("catalog_key"),
            }
            for subject in unit.get("activity_subjects") or []
        ]
        business_units.append(
            {
                "routing_key": unit.get("routing_key"),
                "catalog_key": unit.get("catalog_key") or "",
                "specific_name": unit.get("specific_name") or "",
                "activity_subjects": subjects,
            }
        )
    operational_units = [
        {"key": unit.get("key"), "label": unit.get("label") or ""}
        for unit in routing_taxonomy.get("operational_units") or []
    ]
    return {
        "business_units": business_units,
        "operational_units": operational_units,
    }


def business_routing_for_candidate(
    candidate: dict[str, Any],
    routing_context: dict[str, Any],
) -> dict[str, Any]:
    units = {
        unit["routing_key"]: unit
        for unit in routing_context.get("business_units") or []
        if unit.get("routing_key")
    }
    subjects: dict[str, dict[str, Any]] = {}
    for unit in routing_context.get("business_units") or []:
        for subject in unit.get("activity_subjects") or []:
            if subject.get("routing_key"):
                subjects[subject["routing_key"]] = subject
    operational_units = {
        unit["key"]: unit
        for unit in routing_context.get("operational_units") or []
        if unit.get("key")
    }
    return {
        "affected_business_unit": _unit_identity(
            candidate.get("affected_business_unit_routing_key"),
            units,
        ),
        "responsible_business_unit": _unit_identity(
            candidate.get("responsible_business_unit_routing_key"),
            units,
        ),
        "activity_subject": _subject_identity(
            candidate.get("activity_subject_routing_key"),
            subjects,
        ),
        "operational_unit": _operational_unit_identity(
            candidate.get("operational_unit_key"),
            operational_units,
        ),
    }


def compare_title_wording_archives(
    *,
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    """Classify archive differences. Routing keys are never compared as text."""
    regressions: list[dict[str, str]] = []
    fluctuations: list[dict[str, str]] = []
    before_by_id = {item["id"]: item for item in before.get("scenarios") or []}
    after_by_id = {item["id"]: item for item in after.get("scenarios") or []}
    scenario_ids = list(dict.fromkeys([*before_by_id.keys(), *after_by_id.keys()]))

    for scenario_id in scenario_ids:
        before_scenario = before_by_id.get(scenario_id)
        after_scenario = after_by_id.get(scenario_id)
        if before_scenario is None or after_scenario is None:
            regressions.append(
                {
                    "scenario_id": scenario_id,
                    "code": "scenario_mismatch",
                    "detail": "Scenario present on only one side.",
                }
            )
            continue
        _compare_scenario(
            scenario_id=scenario_id,
            before_scenario=before_scenario,
            after_scenario=after_scenario,
            regressions=regressions,
            fluctuations=fluctuations,
        )

    return {"regressions": regressions, "fluctuations": fluctuations}


def _compare_scenario(
    *,
    scenario_id: str,
    before_scenario: dict[str, Any],
    after_scenario: dict[str, Any],
    regressions: list[dict[str, str]],
    fluctuations: list[dict[str, str]],
) -> None:
    before_context = before_scenario.get("routing_context")
    after_context = after_scenario.get("routing_context")
    if not before_context or not after_context:
        fluctuations.append(
            {
                "scenario_id": scenario_id,
                "code": "routing_context_missing",
                "detail": "Routing keys are not comparable without each run's taxonomy.",
            }
        )
        context_matches = False
    else:
        context_matches = _context_fingerprint(before_context) == _context_fingerprint(
            after_context
        )
        if not context_matches:
            fluctuations.append(
                {
                    "scenario_id": scenario_id,
                    "code": "routing_context",
                    "detail": "Available poles or subjects differ between runs.",
                }
            )

    before_candidates = list(before_scenario.get("candidates") or [])
    after_candidates = list(after_scenario.get("candidates") or [])
    if len(before_candidates) != len(after_candidates):
        regressions.append(
            {
                "scenario_id": scenario_id,
                "code": "candidate_count",
                "detail": (f"{len(before_candidates)} candidate(s) vs {len(after_candidates)}."),
            }
        )

    pairs, unmatched_before, unmatched_after = _pair_candidates(
        before_candidates,
        after_candidates,
    )
    for _candidate in unmatched_before + unmatched_after:
        regressions.append(
            {
                "scenario_id": scenario_id,
                "code": "candidate_mismatch",
                "detail": "A candidate has no counterpart on the other side.",
            }
        )

    observation = str(before_scenario.get("text") or after_scenario.get("text") or "")
    for before_candidate, after_candidate in pairs:
        _compare_pair(
            scenario_id=scenario_id,
            observation=observation,
            before_candidate=before_candidate,
            after_candidate=after_candidate,
            before_context=before_context,
            after_context=after_context,
            context_matches=context_matches,
            regressions=regressions,
            fluctuations=fluctuations,
        )


def _compare_pair(
    *,
    scenario_id: str,
    observation: str,
    before_candidate: dict[str, Any],
    after_candidate: dict[str, Any],
    before_context: dict[str, Any] | None,
    after_context: dict[str, Any] | None,
    context_matches: bool,
    regressions: list[dict[str, str]],
    fluctuations: list[dict[str, str]],
) -> None:
    if before_candidate.get("signal_kind") != after_candidate.get("signal_kind"):
        regressions.append(
            {
                "scenario_id": scenario_id,
                "code": "signal_kind",
                "detail": (
                    f"{before_candidate.get('signal_kind')} vs "
                    f"{after_candidate.get('signal_kind')}."
                ),
            }
        )

    _compare_wording_field(
        scenario_id=scenario_id,
        field="issue_focus",
        before_value=before_candidate.get("issue_focus"),
        after_value=after_candidate.get("issue_focus"),
        regressions=regressions,
        fluctuations=fluctuations,
        disjoint_code="issue_focus",
        close_code="issue_focus_wording",
    )
    _compare_wording_field(
        scenario_id=scenario_id,
        field="canonical_object",
        before_value=before_candidate.get("canonical_object"),
        after_value=after_candidate.get("canonical_object"),
        regressions=regressions,
        fluctuations=fluctuations,
        disjoint_code="canonical_object",
        close_code="canonical_object_wording",
    )
    _compare_expected_action(
        scenario_id=scenario_id,
        before_value=before_candidate.get("expected_action"),
        after_value=after_candidate.get("expected_action"),
        regressions=regressions,
        fluctuations=fluctuations,
    )
    _compare_information_type(
        scenario_id=scenario_id,
        before_value=before_candidate.get("information_type"),
        after_value=after_candidate.get("information_type"),
        fluctuations=fluctuations,
    )
    _compare_location(
        scenario_id=scenario_id,
        before_value=before_candidate.get("location_text"),
        after_value=after_candidate.get("location_text"),
        regressions=regressions,
        fluctuations=fluctuations,
    )
    _compare_narrative(
        scenario_id=scenario_id,
        observation=observation,
        field="title",
        before_value=before_candidate.get("title"),
        after_value=after_candidate.get("title"),
        regressions=regressions,
        fluctuations=fluctuations,
        lost_code="title_discriminant",
        wording_code="title_wording",
    )
    _compare_narrative(
        scenario_id=scenario_id,
        observation=observation,
        field="structured_summary",
        before_value=before_candidate.get("structured_summary"),
        after_value=after_candidate.get("structured_summary"),
        regressions=regressions,
        fluctuations=fluctuations,
        lost_code="summary_detail",
        wording_code="summary_wording",
        lost_is_regression=False,
    )
    if before_context and after_context:
        _compare_routing(
            scenario_id=scenario_id,
            before_candidate=before_candidate,
            after_candidate=after_candidate,
            before_context=before_context,
            after_context=after_context,
            context_matches=context_matches,
            regressions=regressions,
            fluctuations=fluctuations,
        )


def _compare_routing(
    *,
    scenario_id: str,
    before_candidate: dict[str, Any],
    after_candidate: dict[str, Any],
    before_context: dict[str, Any],
    after_context: dict[str, Any],
    context_matches: bool,
    regressions: list[dict[str, str]],
    fluctuations: list[dict[str, str]],
) -> None:
    before_routing = business_routing_for_candidate(before_candidate, before_context)
    after_routing = business_routing_for_candidate(after_candidate, after_context)
    for slot in (
        "affected_business_unit",
        "responsible_business_unit",
        "activity_subject",
        "operational_unit",
    ):
        code = _routing_slot_code(
            before_routing[slot],
            after_routing[slot],
            context_matches=context_matches,
        )
        if code is None:
            continue
        entry = {
            "scenario_id": scenario_id,
            "code": code,
            "detail": f"{slot}: {_routing_label(before_routing[slot])} vs "
            f"{_routing_label(after_routing[slot])}.",
        }
        if code in {"routing_changed", "routing_unknown_key"}:
            regressions.append(entry)
        else:
            fluctuations.append(entry)


def _routing_slot_code(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    context_matches: bool,
) -> str | None:
    if before["status"] == "unknown_key" or after["status"] == "unknown_key":
        return "routing_unknown_key"
    if before["status"] == "absent" and after["status"] == "absent":
        return None
    if before["status"] == "resolved" and after["status"] == "resolved":
        if _routing_identity(before) == _routing_identity(after):
            return None
        return "routing_changed" if context_matches else "routing_context"
    return "routing_uncertain" if context_matches else "routing_context"


def _compare_wording_field(
    *,
    scenario_id: str,
    field: str,
    before_value: Any,
    after_value: Any,
    regressions: list[dict[str, str]],
    fluctuations: list[dict[str, str]],
    disjoint_code: str,
    close_code: str,
) -> None:
    if _fold(str(before_value or "")) == _fold(str(after_value or "")):
        return
    if _texts_are_close(before_value, after_value):
        fluctuations.append(
            {
                "scenario_id": scenario_id,
                "code": close_code,
                "detail": f"{field} paraphrase.",
            }
        )
        return
    regressions.append(
        {
            "scenario_id": scenario_id,
            "code": disjoint_code,
            "detail": f"{field} no longer describes the same fact.",
        }
    )


def _compare_expected_action(
    *,
    scenario_id: str,
    before_value: Any,
    after_value: Any,
    regressions: list[dict[str, str]],
    fluctuations: list[dict[str, str]],
) -> None:
    if before_value == after_value:
        return
    if before_value in (None, "") or after_value in (None, ""):
        fluctuations.append(
            {
                "scenario_id": scenario_id,
                "code": "expected_action_uncertain",
                "detail": f"{before_value} vs {after_value}.",
            }
        )
        return
    regressions.append(
        {
            "scenario_id": scenario_id,
            "code": "expected_action",
            "detail": f"{before_value} vs {after_value}.",
        }
    )


def _compare_information_type(
    *,
    scenario_id: str,
    before_value: Any,
    after_value: Any,
    fluctuations: list[dict[str, str]],
) -> None:
    if _fold(str(before_value or "")) == _fold(str(after_value or "")):
        return
    fluctuations.append(
        {
            "scenario_id": scenario_id,
            "code": "information_type",
            "detail": "Free information_type wording differs.",
        }
    )


def _compare_location(
    *,
    scenario_id: str,
    before_value: Any,
    after_value: Any,
    regressions: list[dict[str, str]],
    fluctuations: list[dict[str, str]],
) -> None:
    before_text = str(before_value or "").strip()
    after_text = str(after_value or "").strip()
    if _fold(before_text) == _fold(after_text):
        return
    if not before_text or not after_text or _texts_are_close(before_text, after_text):
        fluctuations.append(
            {
                "scenario_id": scenario_id,
                "code": "location_wording",
                "detail": "Location wording differs or one side omitted it.",
            }
        )
        return
    regressions.append(
        {
            "scenario_id": scenario_id,
            "code": "location_text",
            "detail": "Location names a different place.",
        }
    )


def _compare_narrative(
    *,
    scenario_id: str,
    observation: str,
    field: str,
    before_value: Any,
    after_value: Any,
    regressions: list[dict[str, str]],
    fluctuations: list[dict[str, str]],
    lost_code: str,
    wording_code: str,
    lost_is_regression: bool = True,
) -> None:
    before_text = str(before_value or "")
    after_text = str(after_value or "")
    observed_numbers = set(_NUMBER_RE.findall(observation))
    before_numbers = set(_NUMBER_RE.findall(before_text))
    after_numbers = set(_NUMBER_RE.findall(after_text))
    lost = (observed_numbers & before_numbers) ^ (observed_numbers & after_numbers)
    invented = (before_numbers | after_numbers) - observed_numbers
    if lost or invented:
        entry = {
            "scenario_id": scenario_id,
            "code": lost_code,
            "detail": f"{field} number set differs from the observation.",
        }
        if lost_is_regression:
            regressions.append(entry)
        else:
            fluctuations.append(entry)
    if _fold(before_text) != _fold(after_text):
        fluctuations.append(
            {
                "scenario_id": scenario_id,
                "code": wording_code,
                "detail": f"{field} wording differs.",
            }
        )


def _pair_candidates(
    before_candidates: list[dict[str, Any]],
    after_candidates: list[dict[str, Any]],
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    remaining = set(range(len(after_candidates)))
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    unmatched_before: list[dict[str, Any]] = []
    for before in before_candidates:
        best_index: int | None = None
        best_score = 0.0
        for index in sorted(remaining):
            score = _match_score(before, after_candidates[index])
            if score > best_score:
                best_score = score
                best_index = index
        if best_index is None:
            unmatched_before.append(before)
            continue
        remaining.remove(best_index)
        pairs.append((before, after_candidates[best_index]))
    unmatched_after = [after_candidates[index] for index in sorted(remaining)]
    return pairs, unmatched_before, unmatched_after


def _match_score(before: dict[str, Any], after: dict[str, Any]) -> float:
    score = 6.0 * _jaccard(before.get("issue_focus"), after.get("issue_focus"))
    score += 2.0 * _jaccard(before.get("canonical_object"), after.get("canonical_object"))
    if before.get("signal_kind") and before.get("signal_kind") == after.get("signal_kind"):
        score += 5.0
    return score


def _unit_identity(routing_key: Any, units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not routing_key:
        return {"status": "absent"}
    unit = units.get(routing_key)
    if unit is None:
        return {"status": "unknown_key"}
    return {
        "status": "resolved",
        "catalog_key": unit.get("catalog_key") or "",
        "specific_name": unit.get("specific_name") or "",
    }


def _subject_identity(routing_key: Any, subjects: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not routing_key:
        return {"status": "absent"}
    subject = subjects.get(routing_key)
    if subject is None:
        return {"status": "unknown_key"}
    return {
        "status": "resolved",
        "label": subject.get("label") or "",
        "catalog_key": subject.get("catalog_key") or "",
    }


def _operational_unit_identity(
    unit_key: Any,
    operational_units: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not unit_key:
        return {"status": "absent"}
    unit = operational_units.get(unit_key)
    if unit is None:
        return {"status": "unknown_key"}
    return {"status": "resolved", "label": unit.get("label") or "", "key": unit_key}


def _routing_identity(identity: dict[str, Any]) -> tuple[str, str]:
    if "specific_name" in identity:
        return (identity.get("catalog_key") or "", identity.get("specific_name") or "")
    if "label" in identity:
        return (identity.get("label") or "", identity.get("catalog_key") or "")
    return (identity.get("label") or "", identity.get("key") or "")


def _routing_label(identity: dict[str, Any]) -> str:
    if identity["status"] != "resolved":
        return identity["status"]
    catalog_key, name = _routing_identity(identity)
    return " / ".join(part for part in (catalog_key, name) if part) or "resolved"


def _context_fingerprint(context: dict[str, Any]) -> tuple[Any, ...]:
    units = []
    for unit in context.get("business_units") or []:
        subjects = tuple(
            sorted(
                (subject.get("label") or "", subject.get("catalog_key") or "")
                for subject in unit.get("activity_subjects") or []
            )
        )
        units.append((unit.get("catalog_key") or "", unit.get("specific_name") or "", subjects))
    operational_units = tuple(
        sorted(
            (unit.get("label") or "",)
            for unit in context.get("operational_units") or []
        )
    )
    return (tuple(sorted(units, key=lambda item: (item[0], item[1], item[2]))), operational_units)


def _texts_are_close(before_value: Any, after_value: Any) -> bool:
    before = _fold(str(before_value or ""))
    after = _fold(str(after_value or ""))
    if not before or not after:
        return False
    if before in after or after in before:
        return True
    return _jaccard(before, after) >= 0.5


def _jaccard(before_value: Any, after_value: Any) -> float:
    before_tokens = set(_TOKEN_RE.findall(_fold(str(before_value or ""))))
    after_tokens = set(_TOKEN_RE.findall(_fold(str(after_value or ""))))
    if not before_tokens and not after_tokens:
        return 1.0
    if not before_tokens or not after_tokens:
        return 0.0
    return len(before_tokens & after_tokens) / len(before_tokens | after_tokens)


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")
