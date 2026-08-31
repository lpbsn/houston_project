from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from houston.ai.observation_pipeline_schema import PipelineCandidateOutput
from houston.establishments.konoha_dataset_actors import (
    ESTABLISHMENT_AKATSUKI,
    ESTABLISHMENT_ANBU,
    KONOHA_DATASET_SEATS,
    NARUTO_EMAIL,
    POLE_BASIC_FIT,
    POLE_COMMERCE,
    POLE_COMMUNICATION,
    POLE_COWORKING,
    POLE_EMEA,
    POLE_EVENEMENTS,
    POLE_HOTEL,
    POLE_ISHIRAKU,
    POLE_MAINTENANCE,
    POLE_YAKINUKU,
)
from houston.signals.constants import AI_ISSUE_FOCUS_MAX_LENGTH, AI_LOCATION_TEXT_MAX_LENGTH
from houston.signals.services import normalize_issue_focus

SCHEMA_VERSION = "konoha_dataset_observations_v1"
PARIS_TZ = ZoneInfo("Europe/Paris")
OCCURRED_AT_MIN = datetime(2025, 8, 1, 0, 0, 0, tzinfo=PARIS_TZ)
OCCURRED_AT_MAX = datetime(2026, 8, 29, 23, 59, 59, tzinfo=PARIS_TZ)
RAW_TEXT_MIN_LENGTH = 10
RAW_TEXT_MAX_LENGTH = 1000
RELATIONS = frozenset({"new_signal", "same_signal", "new_signal_same_pattern"})
ESTABLISHMENTS = frozenset({ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI})
PLACEHOLDER_ROUTING_SUFFIX = "placeholder"

DATA_DIR = Path(__file__).resolve().parent / "data"
ANBU_OBSERVATIONS_PATH = DATA_DIR / "konoha_anbu_observations.json"
AKATSUKI_OBSERVATIONS_PATH = DATA_DIR / "konoha_akatsuki_observations.json"
ACTIVITY_SUBJECTS_CSV_PATH = (
    Path(__file__).resolve().parents[4] / "docs" / "catalogue" / "activity_subjects.csv"
)

HELD_KONOHA_AUTHOR_EMAILS = frozenset(
    {
        "choji@konoha.com",
        "ishiraku@konoha.com",
        "zabuza@konoha.com",
        "haku@konoha.com",
        "tobirama@konoha.com",
    }
)
AUTHOR_NAME_ALIASES = {
    "Chôji": "Choji",
    "Choji": "Choji",
}

AUTHOR_DIRECTORY: frozenset[str] = frozenset(
    {seat.email.lower() for seat in KONOHA_DATASET_SEATS}
    | {email.lower() for email in HELD_KONOHA_AUTHOR_EMAILS}
    | {NARUTO_EMAIL.lower()}
)

AUTHOR_ESTABLISHMENT: dict[str, str] = {
    **{seat.email.lower(): seat.establishment_name for seat in KONOHA_DATASET_SEATS},
    "choji@konoha.com": ESTABLISHMENT_ANBU,
    "ishiraku@konoha.com": ESTABLISHMENT_ANBU,
    "zabuza@konoha.com": ESTABLISHMENT_ANBU,
    "haku@konoha.com": ESTABLISHMENT_ANBU,
    "tobirama@konoha.com": ESTABLISHMENT_ANBU,
    NARUTO_EMAIL.lower(): ESTABLISHMENT_ANBU,
}

ORIGIN_POLE_COUNTS: dict[tuple[str, str], int] = {
    (ESTABLISHMENT_ANBU, POLE_HOTEL): 35,
    (ESTABLISHMENT_ANBU, POLE_ISHIRAKU): 24,
    (ESTABLISHMENT_ANBU, POLE_YAKINUKU): 25,
    (ESTABLISHMENT_ANBU, POLE_COWORKING): 24,
    (ESTABLISHMENT_ANBU, POLE_MAINTENANCE): 17,
    (ESTABLISHMENT_ANBU, POLE_COMMUNICATION): 10,
    (ESTABLISHMENT_AKATSUKI, POLE_COMMERCE): 15,
    (ESTABLISHMENT_AKATSUKI, POLE_BASIC_FIT): 14,
    (ESTABLISHMENT_AKATSUKI, POLE_EMEA): 12,
    (ESTABLISHMENT_AKATSUKI, POLE_EVENEMENTS): 9,
    (ESTABLISHMENT_AKATSUKI, POLE_MAINTENANCE): 10,
    (ESTABLISHMENT_AKATSUKI, POLE_COMMUNICATION): 5,
}

SIGNAL_GROUP_COUNT_RANGES: dict[tuple[str, str], tuple[int, int]] = {
    (ESTABLISHMENT_ANBU, POLE_HOTEL): (28, 32),
    (ESTABLISHMENT_ANBU, POLE_ISHIRAKU): (19, 23),
    (ESTABLISHMENT_ANBU, POLE_YAKINUKU): (20, 24),
    (ESTABLISHMENT_ANBU, POLE_COWORKING): (20, 24),
    (ESTABLISHMENT_ANBU, POLE_MAINTENANCE): (14, 17),
    (ESTABLISHMENT_ANBU, POLE_COMMUNICATION): (9, 10),
    (ESTABLISHMENT_AKATSUKI, POLE_COMMERCE): (11, 14),
    (ESTABLISHMENT_AKATSUKI, POLE_BASIC_FIT): (10, 13),
    (ESTABLISHMENT_AKATSUKI, POLE_EMEA): (10, 12),
    (ESTABLISHMENT_AKATSUKI, POLE_EVENEMENTS): (8, 9),
    (ESTABLISHMENT_AKATSUKI, POLE_MAINTENANCE): (9, 10),
    (ESTABLISHMENT_AKATSUKI, POLE_COMMUNICATION): (5, 5),
}

POLE_ID_PREFIXES: dict[tuple[str, str], str] = {
    (ESTABLISHMENT_ANBU, POLE_HOTEL): "anbu.hotel.",
    (ESTABLISHMENT_ANBU, POLE_ISHIRAKU): "anbu.ishiraku.",
    (ESTABLISHMENT_ANBU, POLE_YAKINUKU): "anbu.yakinuku.",
    (ESTABLISHMENT_ANBU, POLE_COWORKING): "anbu.coworking.",
    (ESTABLISHMENT_ANBU, POLE_MAINTENANCE): "anbu.maintenance.",
    (ESTABLISHMENT_ANBU, POLE_COMMUNICATION): "anbu.communication.",
    (ESTABLISHMENT_AKATSUKI, POLE_COMMERCE): "akatsuki.commerce.",
    (ESTABLISHMENT_AKATSUKI, POLE_BASIC_FIT): "akatsuki.basic_fit.",
    (ESTABLISHMENT_AKATSUKI, POLE_EMEA): "akatsuki.emea.",
    (ESTABLISHMENT_AKATSUKI, POLE_EVENEMENTS): "akatsuki.evenements.",
    (ESTABLISHMENT_AKATSUKI, POLE_MAINTENANCE): "akatsuki.maintenance.",
    (ESTABLISHMENT_AKATSUKI, POLE_COMMUNICATION): "akatsuki.communication.",
}

FORBIDDEN_RAW_TEXT_PATTERNS = (
    re.compile(r"\bsignal\b", re.IGNORECASE),
    re.compile(r"\bmotifs?\b", re.IGNORECASE),
    re.compile(r"[a-z]+__[a-z0-9_]+", re.IGNORECASE),
    re.compile(r"agr[eé]gat", re.IGNORECASE),
    re.compile(r"same_signal|new_signal|pattern_group|signal_group", re.IGNORECASE),
    re.compile(r"\b(?:anbu|akatsuki)\.[a-z0-9_.]+", re.IGNORECASE),
)

REQUIRED_OBSERVATION_KEYS = frozenset(
    {
        "id",
        "author_email",
        "occurred_at",
        "raw_text",
        "establishment",
        "origin_pole_specific_name",
        "signal_group",
        "pattern_group",
        "relation",
        "same_signal_of",
        "cycle",
        "candidate",
    }
)
RESOLUTION_MANUAL = "manual"
RESOLUTION_LINKED_PLAN = "linked_plan"
RESOLUTION_INTERESTING = "interesting"
CYCLE_RESOLUTIONS = frozenset(
    {RESOLUTION_MANUAL, RESOLUTION_LINKED_PLAN, RESOLUTION_INTERESTING}
)
REQUIRED_CYCLE_KEYS = frozenset(
    {"open_at_cutoff", "resolved_at", "planned_action_at", "resolution"}
)
OPTIONAL_CYCLE_KEYS = frozenset({"marked_interesting_at"})
REQUIRED_CANDIDATE_KEYS = frozenset(
    {
        "title",
        "structured_summary",
        "issue_focus",
        "canonical_object",
        "signal_kind",
        "expected_action",
        "information_type",
        "affected_catalog_bu_key",
        "affected_pole_specific_name",
        "responsible_catalog_bu_key",
        "responsible_pole_specific_name",
        "activity_subject_catalog_key",
        "operational_unit_key",
        "location_text",
    }
)
FORBIDDEN_CANDIDATE_KEYS = frozenset(
    {
        "affected_business_unit_routing_key",
        "responsible_business_unit_routing_key",
        "activity_subject_routing_key",
    }
)


class KonohaDatasetObservationsError(ValueError):
    def __init__(self, messages: tuple[str, ...] | list[str]):
        self.messages = tuple(messages)
        super().__init("; ".join(self.messages))


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


@lru_cache(maxsize=1)
def catalog_subject_keys() -> frozenset[str]:
    with ACTIVITY_SUBJECTS_CSV_PATH.open(encoding="utf-8", newline="") as handle:
        return frozenset(row["key"] for row in csv.DictReader(handle) if row.get("key"))


@lru_cache(maxsize=1)
def catalog_subject_bu_prefix() -> dict[str, str]:
    with ACTIVITY_SUBJECTS_CSV_PATH.open(encoding="utf-8", newline="") as handle:
        return {
            row["key"]: row["business_unit_key"]
            for row in csv.DictReader(handle)
            if row.get("key") and row.get("business_unit_key")
        }


def _load_json_file(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise KonohaDatasetObservationsError([f"{path.name}: root must be an object"])
    return payload


@lru_cache(maxsize=1)
def load_anbu_dataset_observations() -> dict[str, Any]:
    return _load_json_file(ANBU_OBSERVATIONS_PATH)


@lru_cache(maxsize=1)
def load_akatsuki_dataset_observations() -> dict[str, Any]:
    return _load_json_file(AKATSUKI_OBSERVATIONS_PATH)


def load_konoha_dataset_observations() -> list[dict[str, Any]]:
    anbu = load_anbu_dataset_observations()
    akatsuki = load_akatsuki_dataset_observations()
    observations: list[dict[str, Any]] = []
    for payload in (anbu, akatsuki):
        rows = payload.get("observations")
        if isinstance(rows, list):
            observations.extend(row for row in rows if isinstance(row, dict))
    return observations


def candidate_as_pipeline_output(candidate: dict[str, Any]) -> PipelineCandidateOutput:
    affected = candidate["affected_catalog_bu_key"]
    responsible = candidate["responsible_catalog_bu_key"]
    return PipelineCandidateOutput(
        title=candidate["title"],
        structured_summary=candidate["structured_summary"],
        issue_focus=candidate["issue_focus"],
        canonical_object=candidate["canonical_object"],
        signal_kind=candidate["signal_kind"],
        expected_action=candidate["expected_action"],
        information_type=candidate["information_type"],
        affected_business_unit_routing_key=f"catalog--{affected}--{PLACEHOLDER_ROUTING_SUFFIX}",
        responsible_business_unit_routing_key=(
            f"catalog--{responsible}--{PLACEHOLDER_ROUTING_SUFFIX}"
        ),
        activity_subject_routing_key=candidate["activity_subject_catalog_key"],
        operational_unit_key=candidate["operational_unit_key"],
        location_text=candidate["location_text"],
    )


def _parse_aware_datetime(
    value: Any, *, field: str, obs_id: str, errors: list[str]
) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{obs_id}: {field} must be an ISO datetime string")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        errors.append(f"{obs_id}: {field} is not a valid ISO datetime")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{obs_id}: {field} must be timezone-aware")
        return None
    return parsed.astimezone(PARIS_TZ)


def _aggregation_key(observation: dict[str, Any]) -> tuple[Any, ...]:
    candidate = observation["candidate"]
    return (
        normalize_issue_focus(candidate.get("issue_focus")),
        candidate.get("affected_catalog_bu_key"),
        candidate.get("affected_pole_specific_name"),
        candidate.get("responsible_catalog_bu_key"),
        candidate.get("responsible_pole_specific_name"),
        candidate.get("activity_subject_catalog_key"),
        candidate.get("operational_unit_key"),
        observation.get("signal_group"),
    )


def _validate_file_envelope(
    payload: dict[str, Any],
    *,
    path: Path,
    establishment: str,
    expected_count: int,
    errors: list[str],
) -> list[dict[str, Any]]:
    label = path.name
    _require(
        payload.get("schema_version") == SCHEMA_VERSION,
        f"{label}: schema_version must be {SCHEMA_VERSION}",
        errors,
    )
    _require(
        payload.get("establishment") == establishment,
        f"{label}: establishment must be {establishment}",
        errors,
    )
    rows = payload.get("observations")
    _require(isinstance(rows, list), f"{label}: observations must be a list", errors)
    if not isinstance(rows, list):
        return []
    _require(
        len(rows) == expected_count,
        f"{label}: expected {expected_count} observations, got {len(rows)}",
        errors,
    )
    return [row for row in rows if isinstance(row, dict)]


def _validate_cycle(observation: dict[str, Any], errors: list[str]) -> datetime | None:
    obs_id = str(observation.get("id") or "<missing>")
    cycle = observation.get("cycle")
    _require(isinstance(cycle, dict), f"{obs_id}: cycle must be an object", errors)
    if not isinstance(cycle, dict):
        return None
    missing = REQUIRED_CYCLE_KEYS - set(cycle)
    _require(not missing, f"{obs_id}: cycle missing {sorted(missing)}", errors)
    extra = set(cycle) - REQUIRED_CYCLE_KEYS - OPTIONAL_CYCLE_KEYS
    _require(not extra, f"{obs_id}: cycle has unexpected keys {sorted(extra)}", errors)
    open_at_cutoff = cycle.get("open_at_cutoff")
    _require(
        isinstance(open_at_cutoff, bool),
        f"{obs_id}: cycle.open_at_cutoff must be a boolean",
        errors,
    )
    resolution = cycle.get("resolution")
    _require(
        resolution in CYCLE_RESOLUTIONS,
        f"{obs_id}: cycle.resolution must be manual, linked_plan, or interesting",
        errors,
    )
    resolved_at = cycle.get("resolved_at")
    planned_action_at = cycle.get("planned_action_at")
    marked_interesting_at = cycle.get("marked_interesting_at")
    resolved_dt = None
    if resolved_at is not None:
        resolved_dt = _parse_aware_datetime(
            resolved_at, field="cycle.resolved_at", obs_id=obs_id, errors=errors
        )
    if planned_action_at is not None:
        _parse_aware_datetime(
            planned_action_at,
            field="cycle.planned_action_at",
            obs_id=obs_id,
            errors=errors,
        )
    marked_dt = None
    if marked_interesting_at is not None:
        marked_dt = _parse_aware_datetime(
            marked_interesting_at,
            field="cycle.marked_interesting_at",
            obs_id=obs_id,
            errors=errors,
        )
        if marked_dt is not None:
            _require(
                marked_dt <= OCCURRED_AT_MAX,
                f"{obs_id}: cycle.marked_interesting_at is after cut-off",
                errors,
            )
    if resolution == RESOLUTION_INTERESTING:
        _require(
            open_at_cutoff is False,
            f"{obs_id}: interesting cycle must set open_at_cutoff=false",
            errors,
        )
        _require(
            resolved_at is None,
            f"{obs_id}: interesting cycle must not set resolved_at",
            errors,
        )
        _require(
            planned_action_at is None,
            f"{obs_id}: interesting cycle must not set planned_action_at",
            errors,
        )
        _require(
            marked_dt is not None,
            f"{obs_id}: interesting cycle must set marked_interesting_at",
            errors,
        )
        return None
    _require(
        marked_interesting_at is None,
        f"{obs_id}: marked_interesting_at is only valid for interesting cycles",
        errors,
    )
    if open_at_cutoff is True:
        _require(
            resolved_at is None,
            f"{obs_id}: open cycle must not set resolved_at",
            errors,
        )
        if resolution == RESOLUTION_MANUAL:
            _require(
                planned_action_at is None,
                f"{obs_id}: open manual cycle must not set planned_action_at",
                errors,
            )
        if resolution == RESOLUTION_LINKED_PLAN:
            _require(
                planned_action_at is not None,
                f"{obs_id}: open linked_plan cycle must set planned_action_at",
                errors,
            )
    if open_at_cutoff is False:
        _require(
            resolved_dt is not None,
            f"{obs_id}: closed cycle must set resolved_at",
            errors,
        )
    return resolved_dt


def _validate_candidate(observation: dict[str, Any], errors: list[str]) -> None:
    obs_id = str(observation.get("id") or "<missing>")
    candidate = observation.get("candidate")
    _require(isinstance(candidate, dict), f"{obs_id}: candidate must be an object", errors)
    if not isinstance(candidate, dict):
        return
    missing = REQUIRED_CANDIDATE_KEYS - set(candidate)
    _require(not missing, f"{obs_id}: candidate missing {sorted(missing)}", errors)
    leaked = FORBIDDEN_CANDIDATE_KEYS & set(candidate)
    _require(
        not leaked,
        f"{obs_id}: candidate must not store instance routing keys {sorted(leaked)}",
        errors,
    )
    location_text = candidate.get("location_text")
    _require(
        isinstance(location_text, str) and 1 <= len(location_text) <= AI_LOCATION_TEXT_MAX_LENGTH,
        f"{obs_id}: location_text must be 1–{AI_LOCATION_TEXT_MAX_LENGTH} chars",
        errors,
    )
    issue_focus = candidate.get("issue_focus")
    _require(
        isinstance(issue_focus, str) and issue_focus.strip(),
        f"{obs_id}: issue_focus required",
        errors,
    )
    if isinstance(issue_focus, str):
        normalized = normalize_issue_focus(issue_focus)
        _require(bool(normalized), f"{obs_id}: issue_focus empty after normalize", errors)
        _require(
            len(normalized) <= AI_ISSUE_FOCUS_MAX_LENGTH,
            f"{obs_id}: normalized issue_focus exceeds {AI_ISSUE_FOCUS_MAX_LENGTH}",
            errors,
        )
    _require(
        candidate.get("operational_unit_key") is None,
        f"{obs_id}: operational_unit_key must be null",
        errors,
    )
    subject_key = candidate.get("activity_subject_catalog_key")
    subjects = catalog_subject_keys()
    prefixes = catalog_subject_bu_prefix()
    _require(
        isinstance(subject_key, str) and subject_key in subjects,
        f"{obs_id}: unknown activity_subject_catalog_key {subject_key!r}",
        errors,
    )
    responsible = candidate.get("responsible_catalog_bu_key")
    if isinstance(subject_key, str) and subject_key in prefixes:
        _require(
            prefixes[subject_key] == responsible,
            f"{obs_id}: subject prefix {prefixes[subject_key]!r} != responsible {responsible!r}",
            errors,
        )
    try:
        candidate_as_pipeline_output(candidate)
    except Exception as exc:
        errors.append(f"{obs_id}: candidate is not a valid pipeline envelope: {exc}")


def _validate_observation_fields(observation: dict[str, Any], errors: list[str]) -> datetime | None:
    missing = REQUIRED_OBSERVATION_KEYS - set(observation)
    if missing:
        errors.append(f"observation missing keys {sorted(missing)}")
        return None
    extra = set(observation) - REQUIRED_OBSERVATION_KEYS
    _require(not extra, f"{observation.get('id')}: unexpected keys {sorted(extra)}", errors)
    obs_id = observation["id"]
    _require(isinstance(obs_id, str) and obs_id.strip(), "observation id required", errors)
    establishment = observation.get("establishment")
    _require(establishment in ESTABLISHMENTS, f"{obs_id}: invalid establishment", errors)
    origin = observation.get("origin_pole_specific_name")
    prefix = POLE_ID_PREFIXES.get((establishment, origin))
    _require(prefix is not None, f"{obs_id}: unknown origin pole {origin!r}", errors)
    if prefix is not None:
        _require(obs_id.startswith(prefix), f"{obs_id}: id must start with {prefix}", errors)
    author = observation.get("author_email")
    _require(
        isinstance(author, str) and author.lower() in AUTHOR_DIRECTORY,
        f"{obs_id}: author_email {author!r} is not in AUTHOR_DIRECTORY",
        errors,
    )
    if isinstance(author, str) and author.lower() in AUTHOR_ESTABLISHMENT:
        _require(
            AUTHOR_ESTABLISHMENT[author.lower()] == establishment
            or author.lower() == NARUTO_EMAIL.lower(),
            f"{obs_id}: author {author} does not belong to {establishment}",
            errors,
        )
    raw_text = observation.get("raw_text")
    _require(
        isinstance(raw_text, str) and RAW_TEXT_MIN_LENGTH <= len(raw_text) <= RAW_TEXT_MAX_LENGTH,
        f"{obs_id}: raw_text must be {RAW_TEXT_MIN_LENGTH}–{RAW_TEXT_MAX_LENGTH} chars",
        errors,
    )
    if isinstance(raw_text, str):
        for pattern in FORBIDDEN_RAW_TEXT_PATTERNS:
            if pattern.search(raw_text):
                errors.append(f"{obs_id}: raw_text contains forbidden token {pattern.pattern}")
                break
    relation = observation.get("relation")
    _require(relation in RELATIONS, f"{obs_id}: invalid relation {relation!r}", errors)
    same_of = observation.get("same_signal_of")
    if relation == "same_signal":
        _require(
            isinstance(same_of, str) and same_of.strip(),
            f"{obs_id}: same_signal_of required",
            errors,
        )
    else:
        _require(same_of is None, f"{obs_id}: same_signal_of must be null", errors)
    occurred_at = _parse_aware_datetime(
        observation.get("occurred_at"),
        field="occurred_at",
        obs_id=str(obs_id),
        errors=errors,
    )
    if occurred_at is not None:
        _require(
            OCCURRED_AT_MIN <= occurred_at <= OCCURRED_AT_MAX,
            f"{obs_id}: occurred_at out of dataset window",
            errors,
        )
    _validate_cycle(observation, errors)
    _validate_candidate(observation, errors)
    return occurred_at


def _validate_graph(observations: list[dict[str, Any]], errors: list[str]) -> None:
    by_id = {row["id"]: row for row in observations if isinstance(row.get("id"), str)}
    by_signal_group: dict[str, list[dict[str, Any]]] = {}
    for row in observations:
        by_signal_group.setdefault(row["signal_group"], []).append(row)

    for row in observations:
        obs_id = row["id"]
        if row["relation"] == "same_signal":
            target_id = row.get("same_signal_of")
            target = by_id.get(target_id)
            _require(
                target is not None,
                f"{obs_id}: same_signal_of {target_id!r} not found",
                errors,
            )
            if target is None:
                continue
            _require(
                target["signal_group"] == row["signal_group"],
                f"{obs_id}: same_signal must share signal_group",
                errors,
            )
            _require(
                _aggregation_key(target) == _aggregation_key(row),
                f"{obs_id}: same_signal aggregation key mismatch vs {target_id}",
                errors,
            )

        if row["relation"] == "new_signal_same_pattern":
            pattern = row["pattern_group"]
            occurred = datetime.fromisoformat(row["occurred_at"]).astimezone(PARIS_TZ)
            previous = [
                other
                for other in observations
                if other["pattern_group"] == pattern
                and other["signal_group"] != row["signal_group"]
                and datetime.fromisoformat(other["occurred_at"]).astimezone(PARIS_TZ) < occurred
            ]
            _require(
                bool(previous),
                f"{obs_id}: new_signal_same_pattern has no earlier pattern occurrence",
                errors,
            )
            if not previous:
                continue
            previous_group = max(
                previous,
                key=lambda item: datetime.fromisoformat(item["occurred_at"]),
            )["signal_group"]
            previous_cycle = by_signal_group[previous_group][0]["cycle"]
            _require(
                previous_cycle.get("open_at_cutoff") is False
                and previous_cycle.get("resolved_at"),
                f"{obs_id}: previous signal_group {previous_group} must be closed",
                errors,
            )
            resolved = datetime.fromisoformat(previous_cycle["resolved_at"]).astimezone(PARIS_TZ)
            _require(
                resolved < occurred,
                f"{obs_id}: previous signal_group {previous_group} must resolve before occurred_at",
                errors,
            )
            _require(
                row["signal_group"] != previous_group,
                f"{obs_id}: new_signal_same_pattern must use a new signal_group",
                errors,
            )

    for group, members in by_signal_group.items():
        keys = {_aggregation_key(member) for member in members}
        _require(len(keys) == 1, f"{group}: members must share the same aggregation key", errors)
        cycles = {
            (
                member["cycle"]["open_at_cutoff"],
                member["cycle"]["resolved_at"],
                member["cycle"]["planned_action_at"],
                member["cycle"]["resolution"],
                member["cycle"].get("marked_interesting_at"),
            )
            for member in members
        }
        _require(len(cycles) == 1, f"{group}: members must share the same cycle", errors)


def _validate_counts(observations: list[dict[str, Any]], errors: list[str]) -> None:
    counts: dict[tuple[str, str], int] = {}
    signal_groups: dict[tuple[str, str], set[str]] = {}
    for row in observations:
        key = (row["establishment"], row["origin_pole_specific_name"])
        counts[key] = counts.get(key, 0) + 1
        signal_groups.setdefault(key, set()).add(row["signal_group"])
    for key, expected in ORIGIN_POLE_COUNTS.items():
        actual = counts.get(key, 0)
        _require(
            actual == expected,
            f"{key}: expected {expected} observations, got {actual}",
            errors,
        )
    for key, (low, high) in SIGNAL_GROUP_COUNT_RANGES.items():
        actual = len(signal_groups.get(key, set()))
        _require(
            low <= actual <= high,
            f"{key}: unique signal_group count {actual} not in [{low}, {high}]",
            errors,
        )
    ids = [row["id"] for row in observations]
    _require(len(ids) == len(set(ids)), "duplicate observation ids", errors)
    _require(
        len(observations) == 200,
        f"expected 200 observations, got {len(observations)}",
        errors,
    )


def validate_konoha_dataset_observations() -> list[str]:
    errors: list[str] = []
    anbu = load_anbu_dataset_observations()
    akatsuki = load_akatsuki_dataset_observations()
    anbu_rows = _validate_file_envelope(
        anbu,
        path=ANBU_OBSERVATIONS_PATH,
        establishment=ESTABLISHMENT_ANBU,
        expected_count=135,
        errors=errors,
    )
    akatsuki_rows = _validate_file_envelope(
        akatsuki,
        path=AKATSUKI_OBSERVATIONS_PATH,
        establishment=ESTABLISHMENT_AKATSUKI,
        expected_count=65,
        errors=errors,
    )
    observations = anbu_rows + akatsuki_rows
    for row in observations:
        _validate_observation_fields(row, errors)
    if errors:
        return errors
    _validate_graph(observations, errors)
    _validate_counts(observations, errors)
    if errors:
        return errors
    from houston.establishments.konoha_dataset_action_cycles import (
        validate_konoha_dataset_action_overrides,
    )
    from houston.establishments.konoha_dataset_workflows import (
        validate_konoha_dataset_workflow_overrides,
    )

    errors.extend(validate_konoha_dataset_action_overrides(observations))
    errors.extend(validate_konoha_dataset_workflow_overrides(observations))
    return errors
