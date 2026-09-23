from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from typing import Any

from houston.action_plans.materialization import iter_occurrence_dates
from houston.establishments.mama_nice_dataset_archetypes import ARCHETYPES
from houston.establishments.mama_nice_dataset_constants import (
    ACTIVE_PLAN_COUNT,
    CATALOG_KEYS,
    COMMENT_BUCKETS,
    COMMENT_EXECUTION_COUNT,
    COMMENT_MENTIONS,
    COMMENT_SIGNAL_COUNT,
    COMMENT_THREAD_REPLIES,
    COMMENT_TOTAL,
    CROSS_PLAN_COUNT,
    FUTURE_BY_MONTH,
    FUTURE_EXECUTION_COUNT,
    HISTORICAL_CANCELED,
    HISTORICAL_DONE,
    HISTORICAL_EXECUTION_COUNT,
    HISTORICAL_FROM_SIGNAL,
    HISTORICAL_IN_PROGRESS_ON_TIME,
    HISTORICAL_PENDING_VALIDATION_ON_TIME,
    HISTORICAL_ROUTINE,
    HISTORICAL_SCHEDULED_OR_OVERDUE,
    HORIZON_FROM,
    HORIZON_UNTIL,
    INACTIVE_PLAN_COUNT,
    INDIVIDUAL_SCHEDULE_COUNT,
    INFORMATIONAL_OBSERVATION_COUNT,
    MONO_PLAN_COUNT,
    OVERDUE_EXECUTION_COUNT,
    OVERDUE_MAX_DAYS,
    OVERDUE_MIN_DAYS,
    PARIS_TZ,
    PATTERN_SIGNAL_COUNT,
    REOPEN_COUNT,
    REUSABLE_PLAN_COUNT,
    REVIEW_COUNT,
    REVIEW_STARS,
    RR_APPROVED,
    RR_REJECTED,
    SCHEDULE_COUNT,
    SHARED_SCHEDULE_COUNT,
    SIGNAL_COUNTS_BY_POLE,
    SIGNAL_STATUS_COUNTS,
    SKIP_COUNT,
    SNAPSHOT,
    TOTAL_OBSERVATIONS,
    TOTAL_SIGNALS,
    UNASSIGNED_OPEN_SIGNALS,
    WEEKDAYS_ALL,
    combine_paris,
)
from houston.establishments.mama_nice_dataset_copy import (
    assign_pattern_keys,
    copy_quality_errors,
    informational_texts,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_manifest import load_mama_nice_manifest
from houston.establishments.mama_nice_dataset_roster import ROSTER, validate_roster
from houston.establishments.mama_nice_dataset_scenarios import (
    authored_scenarios,
    overdue_execution_specs,
    scenario_errors,
)


@dataclass(frozen=True)
class CompiledOccurrence:
    schedule_seed_key: str
    occurrence_date: date
    start_at: datetime
    end_at: datetime
    source: str


@dataclass(frozen=True)
class CompiledOneshot:
    seed_key: str
    title: str
    start_at: datetime
    end_at: datetime
    plan_seed_key: str
    pole: str
    public: bool
    schedule_id_null: bool = True


@dataclass
class CompiledCorpus:
    errors: list[str] = field(default_factory=list)
    horizon_occurrences: list[CompiledOccurrence] = field(default_factory=list)
    out_of_horizon_occurrences: list[CompiledOccurrence] = field(default_factory=list)
    historical_sept22_occurrences: list[CompiledOccurrence] = field(default_factory=list)
    future_executions: list[CompiledOneshot | CompiledOccurrence] = field(default_factory=list)
    oneshots: list[CompiledOneshot] = field(default_factory=list)
    observation_specs: list[dict[str, Any]] = field(default_factory=list)
    signal_specs: list[dict[str, Any]] = field(default_factory=list)
    scenario_specs: list[dict[str, Any]] = field(default_factory=list)
    overdue_specs: list[Any] = field(default_factory=list)
    chat_event_count: int = 0


_CHAT_WORD = re.compile(r"\bchat\b", re.IGNORECASE)


def observation_mentions_chat(raw_text: str) -> bool:
    return _CHAT_WORD.search(raw_text) is not None


def missing_catalog_plan_keys(plan_keys: Iterable[str | None], plans: list[dict]) -> list[str]:
    catalog = {row["seed_key"] for row in plans}
    return sorted(
        {key for key in plan_keys if key and key.startswith("plan:") and key not in catalog}
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_clock(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute), tzinfo=None)


def _schedule_proxy(row: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        recurrence_days=list(row["recurrence_days"]),
        start_date=_parse_date(row["start_date"]),
        end_date=_parse_date(row["end_date"]),
    )


def _occurrence(row: dict[str, Any], occurrence_date: date, source: str) -> CompiledOccurrence:
    start_clock = _parse_clock(row["start_at"])
    end_clock = _parse_clock(row["end_at"])
    return CompiledOccurrence(
        schedule_seed_key=row["seed_key"],
        occurrence_date=occurrence_date,
        start_at=combine_paris(occurrence_date, start_clock),
        end_at=combine_paris(occurrence_date, end_clock),
        source=source,
    )


def _month_key(instant: datetime) -> tuple[int, int]:
    local = instant.astimezone(PARIS_TZ)
    return local.year, local.month


def _expand_dated_oneshots(manifest: dict[str, Any]) -> list[CompiledOneshot]:
    oneshots: list[CompiledOneshot] = []
    for row in manifest["public_events"]["events"]:
        start_day = _parse_date(row.get("start_date") or row["date"])
        end_day = _parse_date(row.get("end_date") or row["date"])
        oneshots.append(
            CompiledOneshot(
                seed_key=row["seed_key"],
                title=row["title"],
                start_at=combine_paris(start_day, _parse_clock(row["start_at"])),
                end_at=combine_paris(end_day, _parse_clock(row["end_at"])),
                plan_seed_key=row["plan_seed_key"],
                pole=row["pole"],
                public=True,
            )
        )
    for row in manifest["oneshots"]["oneshots"]:
        start_day = _parse_date(row.get("start_date") or row["date"])
        end_day = _parse_date(row.get("end_date") or row["date"])
        oneshots.append(
            CompiledOneshot(
                seed_key=row["seed_key"],
                title=row["title"],
                start_at=combine_paris(start_day, _parse_clock(row["start_at"])),
                end_at=combine_paris(end_day, _parse_clock(row["end_at"])),
                plan_seed_key=row["plan_seed_key"],
                pole=row["pole"],
                public=False,
                schedule_id_null=bool(row.get("schedule_id_null", True)),
            )
        )
    titles = {
        "2026-12": [
            ("séminaire interne cuisine", "plan:preparation-seminaire", "evenements_privatisations"),
            ("revue RH de fin d'année", "plan:runtime-rh-routines", "rh"),
            ("campagne communication décembre", "plan:avis-client-negatif", "communication"),
            ("contrôle maintenance cuisine", "plan:incident-service-resto", "restaurant"),
            ("brief équipes séminaire", "plan:preparation-seminaire", "evenements_privatisations"),
            ("prépa communication fêtes", "plan:avis-client-negatif", "communication"),
            ("contrôle stocks bar décembre", "plan:incident-service-resto", "restaurant"),
            ("formation express service", "plan:runtime-rh-routines", "rh"),
            ("privatisation Atelier 1", "plan:preparation-privatisation", "evenements_privatisations"),
        ],
        "2027-01": [
            ("séminaire rentrée opérationnelle", "plan:preparation-seminaire", "evenements_privatisations"),
            ("revue RH janvier", "plan:runtime-rh-routines", "rh"),
            ("campagne communication janvier", "plan:avis-client-negatif", "communication"),
            ("contrôle maintenance CVC local", "plan:diagnostic-clim", "maintenance"),
            ("brief staffing janvier", "plan:runtime-rh-routines", "rh"),
            ("prépa contenus janvier", "plan:avis-client-negatif", "communication"),
            ("contrôle cuisine janvier", "plan:incident-service-resto", "restaurant"),
            ("privatisation Studio 2", "plan:preparation-privatisation", "evenements_privatisations"),
        ],
        "2027-02": [
            ("séminaire commercial février", "plan:preparation-seminaire", "evenements_privatisations"),
            ("revue RH février", "plan:runtime-rh-routines", "rh"),
            ("campagne communication février", "plan:avis-client-negatif", "communication"),
            ("contrôle plomberie préventif", "plan:fuite-sanitaire", "maintenance"),
            ("brief événements février", "plan:preparation-evenement-dj", "evenements_privatisations"),
            ("prépa éditoriale février", "plan:avis-client-negatif", "communication"),
            ("contrôle stocks février", "plan:incident-service-resto", "restaurant"),
            ("privatisation Breakroom", "plan:preparation-privatisation", "evenements_privatisations"),
        ],
        "2027-03": [
            ("séminaire de saison", "plan:preparation-seminaire", "evenements_privatisations"),
            ("revue RH mars", "plan:runtime-rh-routines", "rh"),
            ("campagne communication mars", "plan:avis-client-negatif", "communication"),
            ("contrôle éclairage mars", "plan:defaut-eclairage", "maintenance"),
            ("brief réouverture espaces", "plan:ouverture-saison-rooftop-piscine", "evenements_privatisations"),
            ("prépa contenus mars", "plan:avis-client-negatif", "communication"),
            ("contrôle cuisine mars", "plan:incident-service-resto", "restaurant"),
            ("privatisation Atelier 2", "plan:preparation-privatisation", "evenements_privatisations"),
        ],
    }
    dated = manifest["oneshots"]["private_oneshot_dates"]
    for month_key, days in dated.items():
        month_titles = titles[month_key]
        if len(days) != len(month_titles):
            raise MamaNiceDatasetError(
                [f"{month_key}: oneshot title count {len(month_titles)} != {len(days)}"]
            )
        for day_text, (title, plan_key, pole) in zip(days, month_titles, strict=True):
            day = _parse_date(day_text)
            oneshots.append(
                CompiledOneshot(
                    seed_key=f"oneshot:private:{day_text}",
                    title=title,
                    start_at=combine_paris(day, time(10, 0)),
                    end_at=combine_paris(day, time(12, 0)),
                    plan_seed_key=plan_key,
                    pole=pole,
                    public=False,
                )
            )
    return oneshots


def _compile_schedule_occurrences(manifest: dict[str, Any], errors: list[str]) -> tuple[
    list[CompiledOccurrence],
    list[CompiledOccurrence],
    list[CompiledOccurrence],
]:
    horizon: list[CompiledOccurrence] = []
    out_of_horizon: list[CompiledOccurrence] = []
    historical_today: list[CompiledOccurrence] = []
    linked = manifest["schedules"]["out_of_horizon_linked_dates"]
    for row in manifest["schedules"]["schedules"]:
        dates = iter_occurrence_dates(
            schedule=_schedule_proxy(row),
            from_date=HORIZON_FROM,
            until_date=HORIZON_UNTIL,
        )
        for occurrence_date in dates:
            item = _occurrence(row, occurrence_date, "horizon")
            if item.start_at <= SNAPSHOT:
                historical_today.append(item)
            else:
                horizon.append(item)
        expected_extra = [_parse_date(value) for value in linked.get(row["seed_key"], [])]
        actual_extra: list[date] = []
        for extra in expected_extra:
            extra_dates = iter_occurrence_dates(
                schedule=_schedule_proxy(row),
                from_date=extra,
                until_date=extra,
            )
            if extra_dates != [extra]:
                errors.append(
                    f"{row['seed_key']}: extra date {extra.isoformat()} is not emitted "
                    "by iter_occurrence_dates"
                )
                continue
            if HORIZON_FROM <= extra <= HORIZON_UNTIL:
                errors.append(
                    f"{row['seed_key']}: extra date {extra.isoformat()} is inside the "
                    "product horizon and must not be listed as out-of-horizon"
                )
                continue
            actual_extra.append(extra)
            out_of_horizon.append(_occurrence(row, extra, "out_of_horizon"))
        if actual_extra != expected_extra:
            errors.append(f"{row['seed_key']}: out-of-horizon dates diverge from manifesto")
    return horizon, out_of_horizon, historical_today


def _pole_subjects(manifest: dict[str, Any]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {key: [] for key in CATALOG_KEYS}
    for subject in manifest["catalog_lock"]["activity_subjects"]:
        pole = subject.split("__", 1)[0]
        grouped[pole].append(subject)
    return grouped


def _author_cycle() -> list[str]:
    # Points land on observation authors. Bronze needs 30 points in one closed
    # season, so authorship stays on the badge-eligible fictive members. The
    # other active members remain on the roster without crossing that threshold.
    return [
        person.email
        for person in ROSTER
        if person.status == "active" and person.badge_eligible and person.role != "director"
    ]


def _build_signal_and_observation_specs(manifest: dict[str, Any]) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    del manifest
    authors = _author_cycle()
    try:
        scenarios = authored_scenarios()
    except ValueError as exc:
        raise MamaNiceDatasetError([str(exc)]) from exc
    signals: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    scenario_specs: list[dict[str, Any]] = []
    for index, scenario in enumerate(scenarios):
        signal = {
            "seed_key": scenario.seed_key,
            "pole": scenario.pole,
            "subject": scenario.subject,
            "operational_unit": scenario.operational_unit,
            "status": scenario.status,
            "issue_focus": scenario.issue_focus,
            "title": scenario.issue_focus,
            "canonical_object": scenario.canonical_object,
            "topic": scenario.topic,
            "pattern_seed_key": scenario.pattern_seed_key,
            "plan_seed_key": scenario.plan_seed_key,
            "execution_seed_key": scenario.execution_seed_key,
            "activity": scenario.activity,
            "narrative_family": scenario.narrative_family,
            "author_pole": scenario.author_pole,
            "interesting_kind": scenario.interesting_kind,
            "cancel_reason": scenario.cancel_reason,
            "oneshot_title": scenario.oneshot_title,
            "oneshot_tasks": list(scenario.oneshot_tasks),
            "routing_unassigned": scenario.routing_unassigned,
            "observation_count": len(scenario.observations),
            "author_email": authors[index % len(authors)],
            "occurred_at": scenario.occurred_at,
        }
        signals.append(signal)
        scenario_specs.append(
            {
                **signal,
                "observation_texts": list(scenario.observations),
                "relations": {
                    "observations": list(scenario.relations.observation_seed_keys),
                    "signal": scenario.relations.signal_seed_key,
                    "pattern": scenario.relations.pattern_seed_key,
                    "plan": scenario.relations.plan_seed_key,
                    "executions": list(scenario.relations.execution_seed_keys),
                },
            }
        )
        if len(scenario.observations) != signal["observation_count"]:
            raise MamaNiceDatasetError([f"{scenario.seed_key}: observation count mismatch"])
        for obs_index, text in enumerate(scenario.observations):
            observations.append(
                {
                    "seed_key": f"obs:{scenario.seed_key}:{obs_index + 1}",
                    "signal_seed_key": scenario.seed_key,
                    "author_email": authors[(index + obs_index) % len(authors)],
                    "raw_text": text,
                    "occurred_at": scenario.occurred_at + timedelta(minutes=obs_index * 12),
                    "informational": False,
                    "relation": "new_signal" if obs_index == 0 else "same_signal",
                }
            )
    for info_index, text in enumerate(informational_texts()):
        occurred = datetime(2025, 10, 1, 7, 0, tzinfo=PARIS_TZ) + timedelta(days=info_index * 3)
        if occurred > SNAPSHOT:
            occurred = SNAPSHOT - timedelta(hours=info_index + 1)
        observations.append(
            {
                "seed_key": f"obs:info:{info_index + 1:03d}",
                "signal_seed_key": None,
                "author_email": authors[info_index % len(authors)],
                "raw_text": text,
                "occurred_at": occurred,
                "informational": True,
                "relation": "none",
            }
        )
    return signals, observations, scenario_specs


def compile_mama_nice_dataset() -> CompiledCorpus:
    errors: list[str] = []
    errors.extend(validate_roster())
    manifest = load_mama_nice_manifest()
    catalog = manifest["catalog_lock"]
    if len(catalog["business_units"]) != 7:
        errors.append("catalog lock must list 7 business units")
    if len(catalog["activity_subjects"]) != 66:
        errors.append(f"catalog lock subjects {len(catalog['activity_subjects'])} != 66")
    expected_counts = {row["catalog_key"]: row["subject_count"] for row in catalog["business_units"]}
    actual_counts = Counter(key.split("__", 1)[0] for key in catalog["activity_subjects"])
    if dict(actual_counts) != expected_counts:
        errors.append(f"catalog subject counts {dict(actual_counts)} != {expected_counts}")
    if "chat" in manifest or any("chat" in name for name in manifest):
        errors.append("chat artefact found in manifest")

    schedules = manifest["schedules"]["schedules"]
    if len(schedules) != SCHEDULE_COUNT:
        errors.append(f"schedule count {len(schedules)} != {SCHEDULE_COUNT}")
    shared = sum(1 for row in schedules if row["use_shared_chronology"])
    individual = SCHEDULE_COUNT - shared
    if shared != SHARED_SCHEDULE_COUNT or individual != INDIVIDUAL_SCHEDULE_COUNT:
        errors.append(f"schedule chronology {shared}/{individual}")
    for row in schedules:
        if not row["recurrence_days"] or any(day not in WEEKDAYS_ALL for day in row["recurrence_days"]):
            errors.append(f"{row['seed_key']}: invalid recurrence_days")
        start_clock = _parse_clock(row["start_at"])
        end_clock = _parse_clock(row["end_at"])
        if end_clock <= start_clock:
            errors.append(f"{row['seed_key']}: end_at must be after start_at on the same civil day")

    bornes = next(row for row in schedules if row["n"] == 20)
    fournisseurs = next(row for row in schedules if row["n"] == 25)
    if bornes["start_date"] != "2026-11-02" or bornes["end_date"] != "2026-11-02":
        errors.append("schedule #20 must be 2026-11-02 only")
    if fournisseurs["start_date"] != "2026-11-03" or fournisseurs["end_date"] != "2026-11-03":
        errors.append("schedule #25 must be 2026-11-03 only")

    horizon, extras, sept22 = _compile_schedule_occurrences(manifest, errors)
    oneshots = _expand_dated_oneshots(manifest)
    if any(item.seed_key.endswith("2026-11-13") or item.seed_key.endswith("2026-11-24") for item in oneshots):
        errors.append("November must not contain Studio 13 or RH brief 24 oneshots")

    future: list[CompiledOneshot | CompiledOccurrence] = []
    future.extend(item for item in horizon if item.start_at > SNAPSHOT)
    future.extend(item for item in extras if item.start_at > SNAPSHOT)
    future.extend(item for item in oneshots if item.start_at > SNAPSHOT)
    if len(future) != FUTURE_EXECUTION_COUNT:
        errors.append(f"future executions {len(future)} != {FUTURE_EXECUTION_COUNT}")
    by_month = Counter(_month_key(item.start_at) for item in future)
    if dict(by_month) != FUTURE_BY_MONTH:
        errors.append(f"future month split {dict(sorted(by_month.items()))} != {FUTURE_BY_MONTH}")

    october = [item for item in future if _month_key(item.start_at) == (2026, 10)]
    october_keys = {
        getattr(item, "schedule_seed_key", None) or getattr(item, "seed_key", "")
        for item in october
    }
    if "schedule:bornes-electriques" in october_keys or "schedule:revue-fournisseurs" in october_keys:
        errors.append("October must not contain schedule #20 or #25")
    public_october = [
        item for item in october if isinstance(item, CompiledOneshot) and item.public
    ]
    if len(public_october) != 2:
        errors.append(f"October public events {len(public_october)} != 2")

    november = [item for item in future if _month_key(item.start_at) == (2026, 11)]
    november_schedule_keys = {
        item.schedule_seed_key
        for item in november
        if isinstance(item, CompiledOccurrence)
    }
    if "schedule:bornes-electriques" not in november_schedule_keys:
        errors.append("November must contain schedule #20 on 2026-11-02")
    if "schedule:revue-fournisseurs" not in november_schedule_keys:
        errors.append("November must contain schedule #25 on 2026-11-03")

    if len(sept22) != 7:
        errors.append(f"22 Sept historical schedule occurrences {len(sept22)} != 7")

    plans = manifest["reusable_plans"]["plans"]
    if len(plans) != REUSABLE_PLAN_COUNT:
        errors.append(f"reusable plans must be {REUSABLE_PLAN_COUNT}")
    active_plans = [row for row in plans if row["status"] == "active"]
    if len(active_plans) != ACTIVE_PLAN_COUNT:
        errors.append(f"active reusable plans must be {ACTIVE_PLAN_COUNT}")
    if sum(1 for row in plans if row["status"] == "inactive") != INACTIVE_PLAN_COUNT:
        errors.append(f"inactive reusable plans must be {INACTIVE_PLAN_COUNT}")
    if sum(1 for row in plans if row["kind"] == "mono") != MONO_PLAN_COUNT:
        errors.append(f"mono plans must be {MONO_PLAN_COUNT}")
    if sum(1 for row in plans if row["kind"] == "cross") != CROSS_PLAN_COUNT:
        errors.append(f"cross plans must be {CROSS_PLAN_COUNT}")
    active_keys = {row["seed_key"] for row in active_plans}
    for row in schedules:
        if row["plan_seed_key"] not in active_keys:
            errors.append(
                f"{row['seed_key']}: plan {row['plan_seed_key']} is not an active reusable plan"
            )
    for item in oneshots:
        if item.plan_seed_key not in active_keys:
            errors.append(
                f"{item.seed_key}: plan {item.plan_seed_key} is not an active reusable plan"
            )

    patterns = manifest["patterns"]["patterns"]
    if len(patterns) != 24:
        errors.append("patterns must be 24")
    signals, observations, scenario_specs = _build_signal_and_observation_specs(manifest)
    try:
        errors.extend(scenario_errors(authored_scenarios()))
    except ValueError as exc:
        errors.append(str(exc))
    errors.extend(assign_pattern_keys(signals))
    if len(signals) != TOTAL_SIGNALS:
        errors.append(f"signals {len(signals)} != {TOTAL_SIGNALS}")
    if len(observations) != TOTAL_OBSERVATIONS:
        errors.append(f"observations {len(observations)} != {TOTAL_OBSERVATIONS}")
    pole_counts = Counter(signal["pole"] for signal in signals)
    if dict(pole_counts) != SIGNAL_COUNTS_BY_POLE:
        errors.append(f"signal poles {dict(pole_counts)}")
    status_counts = Counter(signal["status"] for signal in signals)
    if dict(status_counts) != SIGNAL_STATUS_COUNTS:
        errors.append(f"signal statuses {dict(status_counts)}")
    if sum(1 for signal in signals if signal["routing_unassigned"]) != UNASSIGNED_OPEN_SIGNALS:
        errors.append("unassigned open signals must be 2")
    if sum(1 for obs in observations if obs["informational"]) != INFORMATIONAL_OBSERVATION_COUNT:
        errors.append("informational observations must be 104")
    source_obs = [obs for obs in observations if not obs["informational"]]
    if len(source_obs) != 588:
        errors.append(f"source observations {len(source_obs)} != 588")
    texts = [obs["raw_text"] for obs in observations]
    if len(texts) != len(set(texts)):
        errors.append("observation texts must be unique")
    if any(observation_mentions_chat(obs["raw_text"]) for obs in observations):
        errors.append("observation text mentions chat")
    unknown_plans = set(
        missing_catalog_plan_keys(
            (item.get("plan_seed_key") for item in scenario_specs),
            plans,
        )
    )
    for item in scenario_specs:
        plan_key = item.get("plan_seed_key")
        if plan_key in unknown_plans:
            errors.append(f"{item['seed_key']}: plan {plan_key} is not a reusable plan")
    for archetype in ARCHETYPES.values():
        for plan_key in missing_catalog_plan_keys(archetype.plans, plans):
            errors.append(f"{archetype.key}: plan {plan_key} is not a reusable plan")
    patterned = {signal["seed_key"] for signal in signals if signal["pattern_seed_key"]}
    if len(patterned) < PATTERN_SIGNAL_COUNT:
        errors.append(f"patterned signals {len(patterned)} < {PATTERN_SIGNAL_COUNT}")
    visible = [plan["title"] for plan in plans]
    visible.extend(task["task"] for plan in plans for task in plan["tasks"])
    visible.extend(row["title"] for row in schedules)
    visible.extend(item.title for item in oneshots)
    visible.extend(row["label"] for row in patterns)
    errors.extend(
        copy_quality_errors(
            signals=signals,
            observations=observations,
            extra_visible=visible,
        )
    )

    used_subjects = {signal["subject"] for signal in signals}
    unused = set(catalog["activity_subjects"]) - used_subjects
    if unused:
        errors.append(f"unused activity subjects: {sorted(unused)}")

    if COMMENT_TOTAL != sum(size * count for size, count in COMMENT_BUCKETS):
        errors.append("comment bucket arithmetic is inconsistent")
    if COMMENT_SIGNAL_COUNT + COMMENT_EXECUTION_COUNT != 84:
        errors.append("comment object count must be 84")
    if REVIEW_COUNT != sum(REVIEW_STARS.values()):
        errors.append("review star totals must be 153")
    if RR_APPROVED + RR_REJECTED != 12:
        errors.append("resolution requests must be 12")
    if (
        HISTORICAL_DONE
        + HISTORICAL_CANCELED
        + HISTORICAL_IN_PROGRESS_ON_TIME
        + HISTORICAL_PENDING_VALIDATION_ON_TIME
        + HISTORICAL_SCHEDULED_OR_OVERDUE
        != HISTORICAL_EXECUTION_COUNT
    ):
        errors.append("historical execution partition must be 260")
    if HISTORICAL_FROM_SIGNAL + HISTORICAL_ROUTINE != HISTORICAL_EXECUTION_COUNT:
        errors.append("historical origin split must be 180+80")
    if SKIP_COUNT != 10 or REOPEN_COUNT != 3:
        errors.append("skip/reopen counts are frozen")
    if COMMENT_THREAD_REPLIES != 12 or COMMENT_MENTIONS != 10:
        errors.append("comment reply/mention counts are frozen")

    overdue = overdue_execution_specs()
    if len(overdue) != OVERDUE_EXECUTION_COUNT:
        errors.append(f"overdue specs {len(overdue)} != {OVERDUE_EXECUTION_COUNT}")
    if {item.days_late for item in overdue} != set(range(OVERDUE_MIN_DAYS, OVERDUE_MAX_DAYS + 1)):
        errors.append("overdue specs must cover 2 through 7 days")
    if any(item.end_at >= SNAPSHOT for item in overdue):
        errors.append("overdue specs must end before the reference instant")
    if any(item.end_at == SNAPSHOT for item in overdue):
        errors.append("overdue end_at must not equal the snapshot")
    extra_overdue = [
        item
        for item in future
        if item.end_at is not None and item.end_at < SNAPSHOT
    ]
    if extra_overdue:
        errors.append("compiled future executions contain extra overdues")
    horizon_azur = next((item for item in oneshots if "horizon-azur" in item.seed_key), None)
    if horizon_azur is None or horizon_azur.end_at - horizon_azur.start_at < timedelta(days=2):
        errors.append("Horizon Azur must span several days")
    tim = next((item for item in oneshots if item.seed_key == "oneshot:public:tim-lienderss"), None)
    if tim is None or tim.start_at.date() != date(2026, 9, 24) or tim.end_at.date() != date(2026, 9, 26):
        errors.append("TIM LIENDERSS must cover 24-26 September on its existing future line")
    if tim is not None and _month_key(tim.start_at) != (2026, 9):
        errors.append("TIM LIENDERSS must remain counted in September")
    club = next((item for item in oneshots if "club-sonore" in item.seed_key), None)
    if club is None or _month_key(club.start_at) != (2026, 10):
        errors.append("Mama Club Sonore must remain counted in October")
    super_sunday = [
        item
        for item in future
        if getattr(item, "schedule_seed_key", None) == "schedule:super-sunday"
        and item.occurrence_date == date(2026, 9, 27)
    ]
    if len(super_sunday) != 1 or (super_sunday[0].end_at - super_sunday[0].start_at) > timedelta(hours=4):
        errors.append("Super Sunday 27 September must stay an hourly schedule occurrence")

    return CompiledCorpus(
        errors=errors,
        horizon_occurrences=horizon,
        out_of_horizon_occurrences=extras,
        historical_sept22_occurrences=sept22,
        future_executions=future,
        oneshots=oneshots,
        observation_specs=observations,
        signal_specs=signals,
        scenario_specs=scenario_specs,
        overdue_specs=list(overdue),
        chat_event_count=0,
    )


def validate_mama_nice_dataset_manifest() -> list[str]:
    return list(compile_mama_nice_dataset().errors)
