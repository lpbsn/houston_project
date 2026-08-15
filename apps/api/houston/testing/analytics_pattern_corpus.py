from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CORPUS_PATH = Path(__file__).with_name("analytics_pattern_corpus.json")
CORPUS_SCHEMA_VERSION = "analytics_pattern_corpus_v1"

FORBIDDEN_CORPUS_KEYS = frozenset(
    {
        "raw_text",
        "observation_raw_text",
        "media",
        "media_path",
        "photo",
        "audio",
        "comment",
        "comments",
        "action_plan",
        "action_plans",
        "author",
        "submitted_by",
        "submitted_at",
        "created_at",
        "updated_at",
        "status",
        "lifecycle",
        "prompt",
        "output",
        "private_path",
    }
)

REQUIRED_SIGNAL_FIELDS = frozenset(
    {
        "ref",
        "title",
        "structured_summary",
        "issue_focus",
        "activity_subject_key",
        "affected_business_unit_key",
        "responsible_business_unit_key",
    }
)


class AnalyticsPatternCorpusValidationError(ValueError):
    """Raised when Analytics pattern corpus artifacts fail strict validation."""


@lru_cache(maxsize=1)
def load_analytics_pattern_corpus() -> dict[str, Any]:
    with CORPUS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def list_analytics_pattern_scenario_ids() -> list[str]:
    return [scenario["id"] for scenario in load_analytics_pattern_corpus()["scenarios"]]


def get_analytics_pattern_scenario(scenario_id: str) -> dict[str, Any]:
    for scenario in load_analytics_pattern_corpus()["scenarios"]:
        if scenario["id"] == scenario_id:
            return scenario
    raise KeyError(f"Unknown Analytics pattern scenario: {scenario_id}")


def validate_analytics_pattern_corpus(corpus: dict[str, Any] | None = None) -> list[str]:
    data = corpus if corpus is not None else load_analytics_pattern_corpus()
    errors: list[str] = []
    _require(
        data.get("schema_version") == CORPUS_SCHEMA_VERSION,
        f"corpus schema_version must be {CORPUS_SCHEMA_VERSION}",
        errors,
    )
    _validate_forbidden_keys("corpus", data, errors)

    scenarios = data.get("scenarios")
    _require(
        isinstance(scenarios, list) and bool(scenarios),
        "corpus.scenarios must be a non-empty list",
        errors,
    )
    if not isinstance(scenarios, list):
        return errors

    seen_scenario_ids: set[str] = set()
    for scenario in scenarios:
        _validate_scenario(scenario, seen_scenario_ids, errors)

    return errors


def normalized_pair(pair: list[str] | tuple[str, str]) -> tuple[str, str]:
    first, second = pair
    return tuple(sorted((first, second)))  # type: ignore[return-value]


def _validate_scenario(
    scenario: Any,
    seen_scenario_ids: set[str],
    errors: list[str],
) -> None:
    _require(isinstance(scenario, dict), "scenario must be an object", errors)
    if not isinstance(scenario, dict):
        return
    _validate_forbidden_keys("scenario", scenario, errors)

    scenario_id = scenario.get("id")
    _require(
        isinstance(scenario_id, str) and bool(scenario_id.strip()),
        "scenario missing id",
        errors,
    )
    if not isinstance(scenario_id, str):
        return
    label = f"scenario {scenario_id}"
    _require(scenario_id not in seen_scenario_ids, f"duplicate scenario id: {scenario_id}", errors)
    seen_scenario_ids.add(scenario_id)

    business_units = scenario.get("business_units")
    _require(
        isinstance(business_units, list) and bool(business_units),
        f"{label}: business_units required",
        errors,
    )
    business_unit_keys = _unique_keys(
        label=f"{label}.business_units",
        items=business_units if isinstance(business_units, list) else [],
        key_name="key",
        errors=errors,
    )

    activity_subjects = scenario.get("activity_subjects")
    _require(
        isinstance(activity_subjects, list) and bool(activity_subjects),
        f"{label}: activity_subjects required",
        errors,
    )
    activity_subject_keys = _unique_keys(
        label=f"{label}.activity_subjects",
        items=activity_subjects if isinstance(activity_subjects, list) else [],
        key_name="key",
        errors=errors,
    )
    for subject in activity_subjects if isinstance(activity_subjects, list) else []:
        business_unit_key = subject.get("business_unit_key")
        _require(
            business_unit_key in business_unit_keys,
            f"{label}: activity subject {subject.get('key')!r} references unknown business unit",
            errors,
        )

    operational_units = scenario.get("operational_units", [])
    _require(
        isinstance(operational_units, list),
        f"{label}: operational_units must be a list",
        errors,
    )
    operational_unit_keys = _unique_keys(
        label=f"{label}.operational_units",
        items=operational_units if isinstance(operational_units, list) else [],
        key_name="key",
        errors=errors,
    )

    initial_patterns = scenario.get("initial_patterns", [])
    _require(
        isinstance(initial_patterns, list),
        f"{label}: initial_patterns must be a list",
        errors,
    )
    pattern_keys = _unique_keys(
        label=f"{label}.initial_patterns",
        items=initial_patterns if isinstance(initial_patterns, list) else [],
        key_name="pattern_key",
        errors=errors,
    )

    signals = scenario.get("signals")
    _require(isinstance(signals, list) and bool(signals), f"{label}: signals required", errors)
    signal_refs = _unique_keys(
        label=f"{label}.signals",
        items=signals if isinstance(signals, list) else [],
        key_name="ref",
        errors=errors,
    )
    for signal in signals if isinstance(signals, list) else []:
        _validate_signal(
            label=label,
            signal=signal,
            business_unit_keys=business_unit_keys,
            activity_subject_keys=activity_subject_keys,
            operational_unit_keys=operational_unit_keys,
            pattern_keys=pattern_keys,
            errors=errors,
        )

    fake_responses = scenario.get("fake_responses")
    _require(isinstance(fake_responses, dict), f"{label}: fake_responses must be an object", errors)
    if isinstance(fake_responses, dict):
        _require(
            set(fake_responses) == signal_refs,
            f"{label}: fake_responses must cover exactly scenario signal refs",
            errors,
        )
        for signal_ref, response in fake_responses.items():
            _validate_fake_response(
                label=label,
                signal_ref=signal_ref,
                response=response,
                pattern_keys=pattern_keys,
                errors=errors,
            )

    must_link = _validate_pairs(
        label=label,
        field_name="must_link",
        raw_pairs=scenario.get("must_link", []),
        signal_refs=signal_refs,
        errors=errors,
    )
    must_not_link = _validate_pairs(
        label=label,
        field_name="must_not_link",
        raw_pairs=scenario.get("must_not_link", []),
        signal_refs=signal_refs,
        errors=errors,
    )
    overlap = must_link & must_not_link
    for pair in sorted(overlap):
        errors.append(f"{label}: pair {pair!r} cannot be both must_link and must_not_link")


def _validate_signal(
    *,
    label: str,
    signal: Any,
    business_unit_keys: set[str],
    activity_subject_keys: set[str],
    operational_unit_keys: set[str],
    pattern_keys: set[str],
    errors: list[str],
) -> None:
    _require(isinstance(signal, dict), f"{label}: signal must be an object", errors)
    if not isinstance(signal, dict):
        return
    _validate_forbidden_keys(f"{label}.signal {signal.get('ref')!r}", signal, errors)
    missing = REQUIRED_SIGNAL_FIELDS - set(signal)
    for field in sorted(missing):
        errors.append(f"{label}: signal {signal.get('ref')!r} missing {field}")
    for field in ("ref", "title", "structured_summary", "issue_focus"):
        _require(
            isinstance(signal.get(field), str) and bool(signal.get(field, "").strip()),
            f"{label}: signal {signal.get('ref')!r} field {field} must be non-empty",
            errors,
        )
    for field in ("affected_business_unit_key", "responsible_business_unit_key"):
        _require(
            signal.get(field) in business_unit_keys,
            f"{label}: signal {signal.get('ref')!r} references unknown {field}",
            errors,
        )
    _require(
        signal.get("activity_subject_key") in activity_subject_keys,
        f"{label}: signal {signal.get('ref')!r} references unknown activity_subject_key",
        errors,
    )
    operational_unit_key = signal.get("operational_unit_key")
    _require(
        operational_unit_key is None or operational_unit_key in operational_unit_keys,
        f"{label}: signal {signal.get('ref')!r} references unknown operational_unit_key",
        errors,
    )
    expected_pattern_key = signal.get("expected_pattern_key")
    expected_new_label = signal.get("expected_new_pattern_label")
    if expected_pattern_key is not None:
        _require(
            expected_pattern_key in pattern_keys,
            f"{label}: signal {signal.get('ref')!r} references unknown expected_pattern_key",
            errors,
        )
    if expected_new_label is not None:
        _require(
            isinstance(expected_new_label, str) and bool(expected_new_label.strip()),
            f"{label}: signal {signal.get('ref')!r} expected_new_pattern_label must be non-empty",
            errors,
        )
    _require(
        expected_pattern_key is not None or expected_new_label is not None,
        f"{label}: signal {signal.get('ref')!r} requires "
        "expected_pattern_key or expected_new_pattern_label",
        errors,
    )


def _validate_fake_response(
    *,
    label: str,
    signal_ref: str,
    response: Any,
    pattern_keys: set[str],
    errors: list[str],
) -> None:
    _require(
        isinstance(response, dict),
        f"{label}: fake response {signal_ref!r} must be an object",
        errors,
    )
    if not isinstance(response, dict):
        return
    _require(
        isinstance(response.get("canonical_label"), str)
        and bool(response.get("canonical_label", "").strip()),
        f"{label}: fake response {signal_ref!r} requires canonical_label",
        errors,
    )
    _require(
        "result_type" not in response and "pattern_key" not in response,
        f"{label}: fake response {signal_ref!r} must use Label-First V2 shape",
        errors,
    )
    _validate_duplicate_guard_response(
        label=label,
        signal_ref=signal_ref,
        response=response.get("duplicate_guard_response"),
        pattern_keys=pattern_keys,
        errors=errors,
    )


def _validate_duplicate_guard_response(
    *,
    label: str,
    signal_ref: str,
    response: Any,
    pattern_keys: set[str],
    errors: list[str],
) -> None:
    if response is None:
        return
    _require(
        isinstance(response, dict),
        f"{label}: duplicate guard response {signal_ref!r} must be an object",
        errors,
    )
    if not isinstance(response, dict):
        return
    result_type = response.get("result_type")
    if result_type == "reuse_existing_pattern":
        _require(
            response.get("pattern_key") in pattern_keys,
            f"{label}: duplicate guard response {signal_ref!r} references unknown pattern_key",
            errors,
        )
        return
    if result_type == "create_new_pattern":
        _require(
            "pattern_key" not in response,
            f"{label}: create_new_pattern duplicate guard response {signal_ref!r} "
            "must not include pattern_key",
            errors,
        )
        return
    errors.append(
        f"{label}: duplicate guard response {signal_ref!r} has invalid result_type"
    )


def _validate_pairs(
    *,
    label: str,
    field_name: str,
    raw_pairs: Any,
    signal_refs: set[str],
    errors: list[str],
) -> set[tuple[str, str]]:
    _require(isinstance(raw_pairs, list), f"{label}: {field_name} must be a list", errors)
    pairs: set[tuple[str, str]] = set()
    if not isinstance(raw_pairs, list):
        return pairs
    for raw_pair in raw_pairs:
        if not (
            isinstance(raw_pair, list)
            and len(raw_pair) == 2
            and all(isinstance(item, str) for item in raw_pair)
        ):
            errors.append(f"{label}: {field_name} pair must contain two signal refs")
            continue
        pair = normalized_pair(raw_pair)
        if pair[0] == pair[1]:
            errors.append(f"{label}: {field_name} pair {pair!r} cannot self-reference")
            continue
        if pair[0] not in signal_refs or pair[1] not in signal_refs:
            errors.append(f"{label}: {field_name} pair {pair!r} references unknown signal")
            continue
        if pair in pairs:
            errors.append(f"{label}: duplicate {field_name} pair {pair!r}")
            continue
        pairs.add(pair)
    return pairs


def _unique_keys(
    *,
    label: str,
    items: list[Any],
    key_name: str,
    errors: list[str],
) -> set[str]:
    keys: set[str] = set()
    for item in items:
        _require(isinstance(item, dict), f"{label}: item must be an object", errors)
        if not isinstance(item, dict):
            continue
        _validate_forbidden_keys(label, item, errors)
        key = item.get(key_name)
        _require(
            isinstance(key, str) and bool(key.strip()),
            f"{label}: item missing {key_name}",
            errors,
        )
        if not isinstance(key, str):
            continue
        if key in keys:
            errors.append(f"{label}: duplicate {key_name}: {key}")
        keys.add(key)
    return keys


def _validate_forbidden_keys(label: str, value: Any, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_CORPUS_KEYS:
                errors.append(f"{label}: forbidden key {key!r}")
            _validate_forbidden_keys(f"{label}.{key}", child, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_forbidden_keys(f"{label}[{index}]", child, errors)


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)
