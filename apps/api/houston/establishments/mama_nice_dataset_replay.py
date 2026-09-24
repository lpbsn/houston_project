from __future__ import annotations

import os
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Iterator
from unittest.mock import patch
from uuid import UUID

from django.test import RequestFactory

from houston.accounts.legal_services import grant_current_legal_defaults
from houston.accounts.models import User
from houston.action_plans.lifecycle_promotion import promote_due_scheduled_executions
from houston.action_plans.materialization import (
    iter_occurrence_dates,
    materialize_execution_from_schedule,
    materialize_schedule_occurrences_in_horizon,
)
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.services import (
    cancel_action_plan_execution,
    create_action_plan,
    create_action_plan_with_execution,
    create_execution_from_action_plan,
    deactivate_action_plan,
    mark_action_plan_execution_done,
    publish_one_shot_action_plan,
    reopen_action_plan_execution,
    skip_execution_task,
    validate_action_plan_execution,
)
from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.analytics.classifier import FakePatternClassifierProvider
from houston.analytics.cutover import apply_analytics_history_cutover
from houston.analytics.models import OperationalPattern, PatternLifecycleEvent
from houston.analytics.services import (
    classify_signal_pattern,
    create_operational_pattern,
    merge_operational_patterns,
)
from houston.comments.services import create_action_plan_execution_comment, create_signal_comment
from houston.core.dev_guards import assert_local_dev_environment
from houston.establishments.mama_nice_dataset_clock import (
    freeze_django_now,
    in_progress_window,
    operational_now,
    pending_on_time_window,
    resolve_seed_reference_at,
    shift_sliding_instant,
    use_reference_at,
)
from houston.establishments.mama_nice_dataset_compiler import (
    CompiledCorpus,
    compile_mama_nice_dataset,
)
from houston.establishments.mama_nice_dataset_constants import (
    HISTORY_START,
    HORIZON_FROM,
    OBJECT_TYPE_COMMENT,
    OBJECT_TYPE_EXECUTION,
    OBJECT_TYPE_MEMBERSHIP,
    OBJECT_TYPE_OBSERVATION,
    OBJECT_TYPE_OPERATIONAL_UNIT,
    OBJECT_TYPE_PATTERN,
    OBJECT_TYPE_PLAN,
    OBJECT_TYPE_SCHEDULE,
    OBJECT_TYPE_SEASON,
    OBJECT_TYPE_SIGNAL,
    PERSONA_PASSWORD_ENV,
    RUNTIME_RH_PLAN_SEED_KEY,
    SEASON_MONTH_ACTIVE,
    SEASON_MONTHS_CLOSED,
    SNAPSHOT,
)
from houston.establishments.mama_nice_dataset_copy import (
    execution_comment_body,
    execution_tasks,
    execution_title,
    reply_body,
    signal_comment_body,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_ledger import apply_seed_event
from houston.establishments.mama_nice_dataset_manifest import load_mama_nice_manifest
from houston.establishments.mama_nice_dataset_preflight import (
    PreflightResult,
    preflight_mama_nice_local,
    preflight_mama_nice_production,
)
from houston.establishments.mama_nice_dataset_roster import ROSTER
from houston.establishments.mama_nice_dataset_scenarios import (
    ROOFTOP_CLOSURE_IDENTITY,
    overdue_execution_specs,
    proactive_project_specs,
)
from houston.establishments.membership_scope import MembershipScopeInput, MembershipScopeType
from houston.establishments.models import (
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
    MamaNiceSeedRecord,
    OperationalUnit,
)
from houston.establishments.services import (
    accept_establishment_invitation,
    deactivate_membership_for_management,
    invite_membership_for_establishment,
)
from houston.gamification.models import GamificationSeason
from houston.gamification.selectors import get_season_by_starts_at
from houston.gamification.services import close_season, open_season
from houston.observations.services import submit_observation
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import Signal
from houston.signals.resolution_request_services import (
    approve_signal_resolution_request,
    create_signal_resolution_request,
    reject_signal_resolution_request,
)
from houston.signals.services import (
    cancel_signal,
    mark_signal_interesting,
    qualify_signal_routing,
    resolve_signal,
    resolve_signal_from_execution_sync,
    run_observation_pipeline,
)


@dataclass
class SeedResult:
    dry_run: bool
    resume: bool
    establishment_id: UUID | None = None
    skipped: int = 0
    written: int = 0
    preflight_messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@contextmanager
def suppress_mama_nice_side_effects() -> Iterator[None]:
    def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    with ExitStack() as stack:
        stack.enter_context(patch("houston.signals.tasks.process_observation_task.delay", _noop))
        stack.enter_context(
            patch("houston.analytics.tasks.classify_signal_pattern_task.delay", _noop)
        )
        stack.enter_context(
            patch("houston.notifications.scheduling._run_notification_after_commit", _noop)
        )
        stack.enter_context(
            patch(
                "houston.establishments.invitation_email.schedule_establishment_invitation_email",
                _noop,
            )
        )
        yield


def _persona_password() -> str:
    password = os.environ.get(PERSONA_PASSWORD_ENV, "").strip()
    if not password:
        raise MamaNiceDatasetError([f"{PERSONA_PASSWORD_ENV} must be set"])
    return password


def _bu_by_key(establishment: Establishment) -> dict[str, BusinessUnit]:
    return {
        unit.catalog_business_unit.key: unit
        for unit in establishment.business_units.select_related("catalog_business_unit")
    }


def seed_mama_nice_dataset(
    *,
    establishment_id: str | None,
    dry_run: bool,
    confirm: bool,
    resume: bool,
    local: bool = False,
    as_of: str | datetime | None = None,
) -> SeedResult:
    if not dry_run and not confirm:
        raise MamaNiceDatasetError(["refusing to write without --confirm; use --dry-run"])
    corpus = compile_mama_nice_dataset()
    if corpus.errors:
        raise MamaNiceDatasetError(corpus.errors)
    if corpus.chat_event_count != 0:
        raise MamaNiceDatasetError(["compiler produced Chat events"])
    if local:
        assert_local_dev_environment()
        try:
            preflight = preflight_mama_nice_local()
        except MamaNiceDatasetError as exc:
            if dry_run:
                return SeedResult(
                    dry_run=True,
                    resume=resume,
                    preflight_messages=list(exc.messages),
                    errors=list(exc.messages),
                )
            raise
    else:
        if not establishment_id:
            raise MamaNiceDatasetError(["--establishment-id is required outside local bootstrap"])
        try:
            preflight = preflight_mama_nice_production(establishment_id=establishment_id)
        except MamaNiceDatasetError as exc:
            if dry_run:
                return SeedResult(
                    dry_run=True,
                    resume=resume,
                    preflight_messages=list(exc.messages),
                    errors=list(exc.messages),
                )
            raise
    result = SeedResult(
        dry_run=dry_run,
        resume=resume,
        establishment_id=preflight.establishment.id,
        preflight_messages=preflight.messages,
    )
    if dry_run:
        return result
    reference_at = resolve_seed_reference_at(
        establishment=preflight.establishment,
        resume=resume,
        as_of=as_of,
        persist=True,
    )
    with suppress_mama_nice_side_effects(), use_reference_at(reference_at):
        _replay(preflight=preflight, corpus=corpus, resume=resume, result=result)
    return result


def _replay(
    *,
    preflight: PreflightResult,
    corpus: CompiledCorpus,
    resume: bool,
    result: SeedResult,
) -> None:
    establishment = preflight.establishment
    owner = preflight.owner_membership
    governance_director = preflight.governance_director
    forbidden = {owner.id, governance_director.id}
    units = _upsert_operational_units(establishment, resume=resume, result=result)
    memberships = _replay_roster(
        establishment=establishment,
        actor=owner,
        resume=resume,
        result=result,
    )
    buses = _bu_by_key(establishment)
    subjects = {
        subject.catalog_activity_subject.key: subject
        for subject in establishment.activity_subjects.select_related("catalog_activity_subject")
        if subject.catalog_activity_subject_id
    }
    plans = _replay_plans(
        establishment=establishment,
        actor=_fictive_director(memberships),
        buses=buses,
        resume=resume,
        result=result,
    )
    schedules = _replay_schedules(
        establishment=establishment,
        actor=_fictive_director(memberships),
        plans=plans,
        memberships=memberships,
        buses=buses,
        resume=resume,
        result=result,
    )
    signals = _replay_observations_and_signals(
        establishment=establishment,
        corpus=corpus,
        memberships=memberships,
        buses=buses,
        subjects=subjects,
        units=units,
        forbidden=forbidden,
        resume=resume,
        result=result,
    )
    _replay_seasons(establishment, resume=resume, result=result, phase="before_points")
    _replay_signal_overlays(
        corpus=corpus,
        signals=signals,
        memberships=memberships,
        forbidden=forbidden,
        resume=resume,
        result=result,
    )
    _replay_patterns(
        establishment=establishment,
        signals=signals,
        corpus=corpus,
        actor=owner,
        resume=resume,
        result=result,
    )
    _replay_executions(
        establishment=establishment,
        corpus=corpus,
        signals=signals,
        plans=plans,
        schedules=schedules,
        memberships=memberships,
        buses=buses,
        forbidden=forbidden,
        resume=resume,
        result=result,
        period="before_active",
    )
    _replay_seasons(establishment, resume=resume, result=result, phase="after_points")
    executions = _replay_executions(
        establishment=establishment,
        corpus=corpus,
        signals=signals,
        plans=plans,
        schedules=schedules,
        memberships=memberships,
        buses=buses,
        forbidden=forbidden,
        resume=resume,
        result=result,
        period="active_month",
    )
    _close_historical_authored_signals(
        corpus=corpus,
        signals=signals,
        memberships=memberships,
    )
    _replay_comments(
        corpus=corpus,
        signals=signals,
        executions=executions,
        memberships=memberships,
        forbidden=forbidden,
        resume=resume,
        result=result,
    )
    _deactivate_alumni(establishment, memberships, actor=owner, resume=resume, result=result)
    apply_analytics_history_cutover(now=HISTORY_START)
    del forbidden


def _close_historical_authored_signals(*, corpus, signals, memberships) -> None:
    director = _fictive_director(memberships)
    with freeze_django_now(operational_now()):
        for spec in corpus.signal_specs:
            signal = signals.get(spec["seed_key"])
            if signal is None:
                continue
            signal.refresh_from_db()
            if spec["status"] not in {"resolved", "canceled"}:
                continue
            if signal.status in {"resolved", "canceled"}:
                continue
            if spec["status"] == "canceled":
                if signal.status == Signal.Status.IN_PROGRESS:
                    resolve_signal_from_execution_sync(signal=signal)
                    signal.refresh_from_db()
                    continue
                cancel_signal(signal=signal, actor_membership=director)
                continue
            if signal.status == Signal.Status.IN_PROGRESS:
                resolve_signal_from_execution_sync(signal=signal)
            else:
                resolve_signal(signal=signal, actor_membership=director)


def _fictive_director(memberships: dict[str, EstablishmentMembership]) -> EstablishmentMembership:
    return memberships["director.demo.mama.nice@example.com"]


def _record(
    *,
    establishment: Establishment,
    object_type: str,
    seed_key: str,
    event_kind: str,
    event_at: datetime,
    payload: dict[str, Any],
    resume: bool,
    result: SeedResult,
    writer,
    target_exists,
    natural_identity_exists=None,
) -> str:
    status = apply_seed_event(
        establishment=establishment,
        object_type=object_type,
        seed_key=seed_key,
        event_kind=event_kind,
        event_at=event_at,
        fingerprint_payload=payload,
        resume=resume,
        writer=writer,
        target_exists=target_exists,
        natural_identity_exists=natural_identity_exists,
    )
    if status == "skipped":
        result.skipped += 1
    else:
        result.written += 1
    return status


def _upsert_operational_units(establishment: Establishment, *, resume: bool, result: SeedResult):
    units = {}
    for row in load_mama_nice_manifest()["operational_units"]["units"]:

        def writer(row=row):
            unit, _created = OperationalUnit.objects.update_or_create(
                establishment=establishment,
                key=row["key"],
                defaults={"label": row["label"], "source": OperationalUnit.Source.MANUAL, "active": True},
            )
            return unit.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_OPERATIONAL_UNIT,
            seed_key=row["seed_key"],
            event_kind="ou_upsert",
            event_at=HISTORY_START,
            payload={"key": row["key"], "label": row["label"]},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: OperationalUnit.objects.filter(id=object_id).exists(),
        )
        units[row["key"]] = OperationalUnit.objects.get(establishment=establishment, key=row["key"])
    return units


def _month_start_dt(month_start: date) -> datetime:
    return datetime(month_start.year, month_start.month, 1, tzinfo=SNAPSHOT.tzinfo)


def _award_service_clock(natural: datetime, sequence: int) -> datetime:
    """Place a point-awarding call inside August 2026 while that season is active.

    Historical activity predates March 2026. A season per past month would exceed
    the six closed seasons, and points cannot be written into a season that is
    already closed. August stays open until these calls finish, then it is closed
    so badges are persisted. Timestamps already inside August are kept. September
    executions do not use this helper; they run after September is opened.
    """
    award_start = _month_start_dt(SEASON_MONTHS_CLOSED[-1])
    active_start = _month_start_dt(SEASON_MONTH_ACTIVE)
    if award_start <= natural < active_start:
        return natural
    return award_start + timedelta(days=11, seconds=sequence)


def _replay_seasons(
    establishment: Establishment,
    *,
    resume: bool,
    result: SeedResult,
    phase: str = "all",
) -> None:
    award_month = SEASON_MONTHS_CLOSED[-1]
    months = (*SEASON_MONTHS_CLOSED, SEASON_MONTH_ACTIVE)
    for month_start in months:
        open_this = True
        close_this = month_start != SEASON_MONTH_ACTIVE
        if phase == "before_points":
            if month_start == SEASON_MONTH_ACTIVE:
                continue
            if month_start == award_month:
                close_this = False
        elif phase == "after_points":
            if month_start not in {award_month, SEASON_MONTH_ACTIVE}:
                continue
            if month_start == award_month:
                open_this = False
        elif phase != "all":
            raise MamaNiceDatasetError([f"unknown season replay phase {phase}"])
        at = _month_start_dt(month_start)
        if open_this:

            def writer(month_start=month_start, at=at):
                with freeze_django_now(at):
                    season = open_season(establishment, month_start_local=month_start)
                return season.id

            _record(
                establishment=establishment,
                object_type=OBJECT_TYPE_SEASON,
                seed_key=f"season:{month_start.isoformat()}",
                event_kind="season_open",
                event_at=at,
                payload={"month": month_start.isoformat(), "action": "open"},
                resume=resume,
                result=result,
                writer=writer,
                target_exists=lambda object_id: GamificationSeason.objects.filter(id=object_id).exists(),
            )
        if not close_this:
            continue
        close_at = (datetime(month_start.year, month_start.month, 1, tzinfo=SNAPSHOT.tzinfo) + timedelta(days=32)).replace(day=1)

        def close_writer(month_start=month_start, close_at=close_at, at=at):
            season = get_season_by_starts_at(establishment, at)
            if season is None:
                raise MamaNiceDatasetError(
                    [f"season:{month_start.isoformat()}:close: no season for starts_at={at.isoformat()}"]
                )
            with freeze_django_now(close_at):
                close_season(season, closed_at=close_at)
            return season.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_SEASON,
            seed_key=f"season:{month_start.isoformat()}:close",
            event_kind="season_close",
            event_at=close_at,
            payload={"month": month_start.isoformat(), "action": "close"},
            resume=resume,
            result=result,
            writer=close_writer,
            target_exists=lambda object_id: GamificationSeason.objects.filter(id=object_id).exists(),
        )


def _replay_roster(
    *,
    establishment: Establishment,
    actor: EstablishmentMembership,
    resume: bool,
    result: SeedResult,
) -> dict[str, EstablishmentMembership]:
    password = _persona_password()
    buses = _bu_by_key(establishment)
    memberships: dict[str, EstablishmentMembership] = {}
    for person in ROSTER:
        scopes = []
        if person.primary_pole:
            scopes.append(
                MembershipScopeInput(
                    scope_type=MembershipScopeType.BUSINESS_UNIT,
                    scope_id=buses[person.primary_pole].id,
                )
            )
        if person.secondary_pole:
            scopes.append(
                MembershipScopeInput(
                    scope_type=MembershipScopeType.BUSINESS_UNIT,
                    scope_id=buses[person.secondary_pole].id,
                )
            )
        at = HISTORY_START + timedelta(minutes=1)

        def writer(person=person, scopes=scopes, at=at):
            with freeze_django_now(at):
                invitation = invite_membership_for_establishment(
                    current_membership=actor,
                    establishment_id=establishment.id,
                    email=person.email,
                    first_name=person.first_name,
                    last_name=person.last_name,
                    role=person.role,
                    scopes=scopes or None,
                )
                if person.status != "invited":
                    accept_establishment_invitation(
                        request=RequestFactory().post("/"),
                        raw_token=invitation.invitation_token,
                        password=password,
                    )
                    user = User.objects.get(email__iexact=person.email)
                    grant_current_legal_defaults(user=user)
            return invitation.membership.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_MEMBERSHIP,
            seed_key=person.seed_key,
            event_kind="roster_invite",
            event_at=at,
            payload={"email": person.email, "role": person.role, "status": person.status},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: EstablishmentMembership.objects.filter(id=object_id).exists(),
        )
        memberships[person.email] = EstablishmentMembership.objects.get(
            establishment=establishment,
            user__email__iexact=person.email,
        )
    return memberships


def _replay_plans(*, establishment, actor, buses, resume, result) -> dict[str, Any]:
    from houston.action_plans.constants import CATALOG_STATUS_ACTIVE, CATALOG_STATUS_INACTIVE
    from houston.action_plans.models import ActionPlan

    plans = {}
    for row in load_mama_nice_manifest()["reusable_plans"]["plans"]:
        if row["seed_key"] == RUNTIME_RH_PLAN_SEED_KEY:
            continue
        at = HISTORY_START + timedelta(hours=2)

        def writer(row=row, at=at):
            tasks = []
            for position, task in enumerate(row["tasks"], start=1):
                tasks.append(
                    {
                        "position": position,
                        "task": task["task"],
                        "business_unit_id": buses[task["pole"]].id,
                    }
                )
            with freeze_django_now(at):
                plan = create_action_plan(
                    establishment_id=establishment.id,
                    created_by=actor,
                    pilot_business_unit_id=buses[row["pilot"]].id,
                    title=row["title"],
                    description=row["title"],
                    is_reusable=True,
                    catalog_status=CATALOG_STATUS_ACTIVE,
                    tasks=tasks,
                )
                if row["status"] == "inactive":
                    deactivate_action_plan(action_plan=plan, actor=actor)
            return plan.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_PLAN,
            seed_key=row["seed_key"],
            event_kind="plan_create",
            event_at=at,
            payload={"title": row["title"], "status": row["status"]},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: ActionPlan.objects.filter(id=object_id).exists(),
        )
        plans[row["seed_key"]] = ActionPlan.objects.get(
            establishment=establishment,
            title=row["title"],
        )
    rh_row = next(
        row
        for row in load_mama_nice_manifest()["reusable_plans"]["plans"]
        if row["seed_key"] == RUNTIME_RH_PLAN_SEED_KEY
    )
    at = HISTORY_START + timedelta(hours=3)

    def rh_writer(row=rh_row, at=at):
        tasks = [
            {
                "position": position,
                "task": task["task"],
                "business_unit_id": buses[task["pole"]].id,
            }
            for position, task in enumerate(row["tasks"], start=1)
        ]
        with freeze_django_now(at):
            plan = create_action_plan(
                establishment_id=establishment.id,
                created_by=actor,
                pilot_business_unit_id=buses[row["pilot"]].id,
                title=row["title"],
                description=row["title"],
                is_reusable=False,
                catalog_status=None,
                tasks=tasks,
            )
        return plan.id

    _record(
        establishment=establishment,
        object_type=OBJECT_TYPE_PLAN,
        seed_key=rh_row["seed_key"],
        event_kind="plan_create",
        event_at=at,
        payload={"title": rh_row["title"], "reusable": False},
        resume=resume,
        result=result,
        writer=rh_writer,
        target_exists=lambda object_id: ActionPlan.objects.filter(id=object_id).exists(),
    )
    rh_plan = ActionPlan.objects.get(
        establishment=establishment,
        title=rh_row["title"],
    )
    plans[rh_row["seed_key"]] = publish_one_shot_action_plan(
        action_plan=rh_plan,
        actor=actor,
    )
    del CATALOG_STATUS_INACTIVE
    return plans


def _replay_schedules(*, establishment, actor, plans, memberships, buses, resume, result):
    from houston.action_plans.models import ActionPlanSchedule

    schedules = {}
    for row in load_mama_nice_manifest()["schedules"]["schedules"]:
        at = HISTORY_START + timedelta(hours=4)
        start_h, start_m = row["start_at"].split(":")
        end_h, end_m = row["end_at"].split(":")

        def writer(row=row, at=at):
            assignees = None
            if row["assignee_persona"]:
                member = memberships[row["assignee_persona"]]
                assignees = [
                    {
                        "membership_id": member.id,
                        "business_unit_id": buses[row["pole"]].id,
                    }
                ]
            with freeze_django_now(at):
                schedule = create_action_plan_schedule(
                    action_plan=plans[row["plan_seed_key"]],
                    actor=actor,
                    start_date=date.fromisoformat(row["start_date"]),
                    end_date=date.fromisoformat(row["end_date"]),
                    start_at=datetime.strptime(row["start_at"], "%H:%M").time(),
                    end_at=datetime.strptime(row["end_at"], "%H:%M").time(),
                    recurrence_days=list(row["recurrence_days"]),
                    assignees=assignees,
                    use_shared_chronology=row["use_shared_chronology"],
                    emit_side_effects=False,
                )
            return schedule.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_SCHEDULE,
            seed_key=row["seed_key"],
            event_kind="schedule_create",
            event_at=at,
            payload={"n": row["n"], "start_date": row["start_date"], "end_date": row["end_date"]},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: ActionPlanSchedule.objects.filter(id=object_id).exists(),
        )
        record = MamaNiceSeedRecord.objects.get(
            establishment=establishment,
            object_type=OBJECT_TYPE_SCHEDULE,
            seed_key=row["seed_key"],
        )
        schedules[row["seed_key"]] = ActionPlanSchedule.objects.get(id=record.object_id)
    return schedules


def _pipeline_payload(*, spec: dict[str, Any], buses, subjects, units, informational: bool):
    del units
    if informational:
        return ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[],
        ).model_dump(mode="json")
    candidate = PipelineCandidateOutput(
        title=spec["title"][:200],
        structured_summary=spec.get("raw_text", spec["title"])[:400],
        issue_focus=spec["issue_focus"][:80],
        canonical_object=spec["canonical_object"][:80],
        signal_kind="actionable",
        expected_action="inspect",
        information_type=None,
        affected_business_unit_routing_key=buses[spec.get("author_pole", spec["pole"])].routing_key,
        responsible_business_unit_routing_key=None
        if spec.get("routing_unassigned")
        else buses[spec["pole"]].routing_key,
        activity_subject_routing_key=None
        if spec.get("routing_unassigned")
        else subjects[spec["subject"]].routing_key,
        operational_unit_key=spec["operational_unit"],
        location_text=spec["title"][:120],
    )
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[candidate],
    ).model_dump(mode="json")


def _replay_observations_and_signals(
    *,
    establishment,
    corpus,
    memberships,
    buses,
    subjects,
    units,
    forbidden,
    resume,
    result,
) -> dict[str, Signal]:
    from houston.observations.models import Observation

    signals: dict[str, Signal] = {}
    signal_by_key = {spec["seed_key"]: spec for spec in corpus.signal_specs}
    for obs in corpus.observation_specs:
        author = memberships[obs["author_email"]]
        if author.id in forbidden:
            raise MamaNiceDatasetError([f"{obs['seed_key']}: governance author is forbidden"])
        spec = signal_by_key.get(obs["signal_seed_key"] or "")
        informational = obs["informational"]
        occurred_at = obs["occurred_at"]
        if spec is not None and spec["status"] in {"open", "in_progress", "interesting"}:
            occurred_at = shift_sliding_instant(obs["occurred_at"])
        if not informational and spec is None:
            raise MamaNiceDatasetError([f"{obs['seed_key']}: missing signal spec"])
        if (
            not informational
            and obs["relation"] != "new_signal"
            and spec.get("routing_unassigned")
        ):
            raise MamaNiceDatasetError(
                [f"{obs['seed_key']}: cannot aggregate an unassigned signal"]
            )
        payload_spec = {"raw_text": obs["raw_text"]} if informational else spec

        def writer(obs=obs, author=author, payload_spec=payload_spec, informational=informational, occurred_at=occurred_at):
            output = _pipeline_payload(
                spec={**payload_spec, "raw_text": obs["raw_text"]},
                buses=buses,
                subjects=subjects,
                units=units,
                informational=informational,
            )
            with freeze_django_now(occurred_at):
                observation = submit_observation(
                    membership=author,
                    text=obs["raw_text"],
                    temporary_upload_ids=[],
                )
                run_observation_pipeline(
                    observation.id,
                    provider=FakeObservationPipelineProvider(payload=output),
                )
            return observation.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_OBSERVATION,
            seed_key=obs["seed_key"],
            event_kind="observation_submit",
            event_at=occurred_at,
            payload={"text": obs["raw_text"], "signal": obs["signal_seed_key"]},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: Observation.objects.filter(id=object_id).exists(),
        )
        if obs["signal_seed_key"] and obs["relation"] == "new_signal":
            observation = Observation.objects.get(
                submitted_by_membership=author,
                raw_text=obs["raw_text"],
            )
            candidate = observation.candidate_signals.first()
            if candidate is not None and candidate.result_signal_id:
                signals[obs["signal_seed_key"]] = candidate.result_signal
    return signals


def _responsible_pole_key(signal) -> str:
    unit = signal.responsible_business_unit
    catalog = getattr(unit, "catalog_business_unit", None)
    if catalog is None:
        raise MamaNiceDatasetError([f"signal {signal.id} has no responsible pole"])
    return catalog.key


def _badge_assignee_for_pole(memberships, pole: str, index: int):
    eligible = [
        memberships[person.email]
        for person in ROSTER
        if person.badge_eligible
        and person.role != "director"
        and person.status == "active"
        and person.email in memberships
        and (person.primary_pole == pole or person.secondary_pole == pole)
    ]
    if not eligible:
        raise MamaNiceDatasetError([f"no badge-eligible assignee for pole {pole}"])
    return eligible[index % len(eligible)]


def _active_member_for_pole(memberships, *, role: str, pole: str):
    for person in ROSTER:
        if (
            person.role == role
            and person.primary_pole == pole
            and person.status == "active"
            and person.email in memberships
        ):
            return memberships[person.email]
    raise MamaNiceDatasetError([f"no active {role} for pole {pole}"])


def _replay_signal_overlays(*, corpus, signals, memberships, forbidden, resume, result) -> None:
    badge_actors = [
        memberships[person.email]
        for person in ROSTER
        if person.badge_eligible and person.email in memberships
    ]
    execution_signal_keys = {
        spec["seed_key"]
        for spec in [
            item
            for item in corpus.signal_specs
            if item["status"] in {"resolved", "canceled"}
        ][:180]
    }
    rr_done = 0
    rejected_retry = False
    sequence = 0
    for spec in corpus.signal_specs:
        signal = signals.get(spec["seed_key"])
        if signal is None:
            continue
        if spec["seed_key"] in execution_signal_keys:
            continue
        if spec["routing_unassigned"]:
            continue
        actor = badge_actors[rr_done % len(badge_actors)]
        occurred = spec["occurred_at"]
        if spec["status"] in {"open", "in_progress", "interesting"}:
            occurred = shift_sliding_instant(occurred)
        at = occurred + timedelta(hours=2)
        if spec["status"] in {"open", "interesting", "in_progress", "resolved", "canceled"} and not spec["routing_unassigned"]:

            def qualify_writer(signal=signal, actor=actor, at=at):
                with freeze_django_now(at):
                    qualify_signal_routing(
                        signal=signal,
                        membership=actor,
                        patch={},
                    )
                return signal.id

            try:
                _record(
                    establishment=signal.establishment,
                    object_type=OBJECT_TYPE_SIGNAL,
                    seed_key=f"{spec['seed_key']}:qualify",
                    event_kind="qualify",
                    event_at=at,
                    payload={"signal": spec["seed_key"]},
                    resume=resume,
                    result=result,
                    writer=qualify_writer,
                    target_exists=lambda object_id: Signal.objects.filter(id=object_id).exists(),
                )
            except Exception:
                pass
        if spec["status"] == "interesting":
            interesting_at = at + timedelta(minutes=10)

            def interesting_writer(signal=signal, actor=actor, interesting_at=interesting_at):
                with freeze_django_now(interesting_at):
                    mark_signal_interesting(signal=signal, actor_membership=actor)
                return signal.id

            _record(
                establishment=signal.establishment,
                object_type=OBJECT_TYPE_SIGNAL,
                seed_key=f"{spec['seed_key']}:interesting",
                event_kind="mark_interesting",
                event_at=interesting_at,
                payload={"signal": spec["seed_key"]},
                resume=resume,
                result=result,
                writer=interesting_writer,
                target_exists=lambda object_id: Signal.objects.filter(id=object_id).exists(),
            )
        if spec["status"] == "canceled":
            cancel_at = at + timedelta(hours=1)

            def cancel_writer(signal=signal, actor=actor, cancel_at=cancel_at):
                with freeze_django_now(cancel_at):
                    cancel_signal(signal=signal, actor_membership=actor)
                return signal.id

            _record(
                establishment=signal.establishment,
                object_type=OBJECT_TYPE_SIGNAL,
                seed_key=f"{spec['seed_key']}:cancel",
                event_kind="cancel",
                event_at=cancel_at,
                payload={"signal": spec["seed_key"]},
                resume=resume,
                result=result,
                writer=cancel_writer,
                target_exists=lambda object_id: Signal.objects.filter(id=object_id).exists(),
            )
        if spec["status"] == "resolved" and rr_done < 12:
            pole = _responsible_pole_key(signal)
            requester = _active_member_for_pole(memberships, role="staff", pole=pole)
            reviewer = _active_member_for_pole(memberships, role="manager", pole=pole)
            resolve_at = _award_service_clock(at + timedelta(hours=3), sequence)
            sequence += 1
            reject_first = rr_done < 3
            retry_after_reject = reject_first and not rejected_retry

            def resolution_writer(
                signal=signal,
                requester=requester,
                reviewer=reviewer,
                resolve_at=resolve_at,
                reject_first=reject_first,
                retry_after_reject=retry_after_reject,
            ):
                with freeze_django_now(resolve_at):
                    request = create_signal_resolution_request(
                        signal=signal,
                        actor_membership=requester,
                        request_comment="Demande de clôture après passage terrain.",
                    )
                    if reject_first:
                        reject_signal_resolution_request(
                            resolution_request=request,
                            actor_membership=reviewer,
                            review_comment="Manque une vérif, on reprend.",
                        )
                        if retry_after_reject:
                            retry = create_signal_resolution_request(
                                signal=signal,
                                actor_membership=requester,
                                request_comment="Nouvelle demande après reprise.",
                            )
                            approve_signal_resolution_request(
                                resolution_request=retry,
                                actor_membership=reviewer,
                                review_comment="Ok après reprise.",
                            )
                    else:
                        approve_signal_resolution_request(
                            resolution_request=request,
                            actor_membership=reviewer,
                            review_comment="Approuvé.",
                        )
                return signal.id

            _record(
                establishment=signal.establishment,
                object_type=OBJECT_TYPE_SIGNAL,
                seed_key=f"{spec['seed_key']}:resolution",
                event_kind="resolution_request",
                event_at=resolve_at,
                payload={"signal": spec["seed_key"], "reject_first": reject_first},
                resume=resume,
                result=result,
                writer=resolution_writer,
                target_exists=lambda object_id: Signal.objects.filter(id=object_id).exists(),
            )
            if retry_after_reject:
                rejected_retry = True
            rr_done += 1
        elif spec["status"] == "resolved":
            resolve_at = _award_service_clock(at + timedelta(hours=4), sequence)
            sequence += 1

            def resolve_writer(signal=signal, actor=actor, resolve_at=resolve_at):
                with freeze_django_now(resolve_at):
                    resolve_signal(signal=signal, actor_membership=actor)
                return signal.id

            _record(
                establishment=signal.establishment,
                object_type=OBJECT_TYPE_SIGNAL,
                seed_key=f"{spec['seed_key']}:resolve",
                event_kind="resolve",
                event_at=resolve_at,
                payload={"signal": spec["seed_key"]},
                resume=resume,
                result=result,
                writer=resolve_writer,
                target_exists=lambda object_id: Signal.objects.filter(id=object_id).exists(),
            )


def _replay_patterns(*, establishment, signals, corpus, actor, resume, result) -> None:
    from houston.analytics.models import OperationalPattern as Pattern

    by_key: dict[str, OperationalPattern] = {}
    for row in load_mama_nice_manifest()["patterns"]["patterns"]:
        at = HISTORY_START + timedelta(days=10)

        def writer(row=row, at=at):
            with freeze_django_now(at):
                pattern = create_operational_pattern(
                    organization=establishment.organization,
                    label=row["label"],
                    created_by_membership=actor,
                    occurred_at=at,
                )
            return pattern.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_PATTERN,
            seed_key=row["seed_key"],
            event_kind="pattern_create",
            event_at=at,
            payload={"label": row["label"], "status": row["status"]},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: Pattern.objects.filter(id=object_id).exists(),
        )
        by_key[row["seed_key"]] = Pattern.objects.get(
            organization=establishment.organization,
            label=row["label"],
        )
    for spec in corpus.signal_specs:
        signal = signals.get(spec["seed_key"])
        pattern_key = spec.get("pattern_seed_key")
        if signal is None or not pattern_key or pattern_key not in by_key:
            continue
        label = by_key[pattern_key].label
        try:
            classify_signal_pattern(
                signal.id,
                provider=FakePatternClassifierProvider(payload={"canonical_label": label}),
                duplicate_guard_enabled=False,
            )
        except Exception:
            continue
    merge_row = next(
        row
        for row in load_mama_nice_manifest()["patterns"]["patterns"]
        if row["status"] == "merged"
    )
    merge_at = SNAPSHOT - timedelta(days=30)

    def merge_writer(merge_row=merge_row, merge_at=merge_at):
        with freeze_django_now(merge_at):
            merge_operational_patterns(
                actor_membership=actor,
                source_pattern=by_key[merge_row["seed_key"]],
                target_pattern=by_key[merge_row["merge_into"]],
            )
        return by_key[merge_row["seed_key"]].id

    _record(
        establishment=establishment,
        object_type=OBJECT_TYPE_PATTERN,
        seed_key=f"{merge_row['seed_key']}:merge",
        event_kind="pattern_merge",
        event_at=merge_at,
        payload={"source": merge_row["seed_key"], "target": merge_row["merge_into"]},
        resume=resume,
        result=result,
        writer=merge_writer,
        target_exists=lambda object_id: Pattern.objects.filter(id=object_id).exists(),
    )
    retired = by_key["pattern:signaletique-lancement"]
    retire_at = SNAPSHOT - timedelta(days=40)

    def retire_writer(retired=retired, retire_at=retire_at):
        with freeze_django_now(retire_at):
            retired.status = OperationalPattern.Status.RETIRED
            retired.save(update_fields=["status", "updated_at"])
            PatternLifecycleEvent.objects.create(
                pattern=retired,
                organization=establishment.organization,
                event_type=PatternLifecycleEvent.EventType.RETIRED,
                actor_membership=actor,
                occurred_at=retire_at,
                metadata_safe={"seed": True},
            )
        return retired.id

    _record(
        establishment=establishment,
        object_type=OBJECT_TYPE_PATTERN,
        seed_key="pattern:signaletique-lancement:retire",
        event_kind="pattern_retire",
        event_at=retire_at,
        payload={"seed_key": "pattern:signaletique-lancement"},
        resume=resume,
        result=result,
        writer=retire_writer,
        target_exists=lambda object_id: Pattern.objects.filter(id=object_id).exists(),
    )


def _replay_executions(
    *,
    establishment,
    corpus,
    signals,
    plans,
    schedules,
    memberships,
    buses,
    forbidden,
    resume,
    result,
    period: str = "all",
) -> dict[str, Any]:
    from houston.action_plans.models import ActionPlanExecution

    director = _fictive_director(memberships)
    executions: dict[str, ActionPlanExecution] = {}
    linked_specs = [spec for spec in corpus.signal_specs if spec["status"] in {"resolved", "canceled"}][:180]
    for index, spec in enumerate(linked_specs):
        signal = signals.get(spec["seed_key"])
        if signal is None:
            continue
        actor = _badge_assignee_for_pole(memberships, _responsible_pole_key(signal), index)
        start = spec["occurred_at"] + timedelta(hours=6)
        end = min(start + timedelta(hours=2), SNAPSHOT)
        if 16 <= index < 36:
            end = min(start + timedelta(hours=2), SNAPSHOT)
        at = start
        starts_in_active_month = start >= _month_start_dt(SEASON_MONTH_ACTIVE)
        if period == "before_active" and starts_in_active_month:
            continue
        if period == "active_month" and not starts_in_active_month:
            continue

        def writer(signal=signal, actor=actor, director=director, start=start, end=end, spec=spec, index=index):
            if start >= _month_start_dt(SEASON_MONTH_ACTIVE):
                clock = start + timedelta(minutes=20)
            else:
                clock = _award_service_clock(start, index)
            with freeze_django_now(clock):
                _plan, execution = create_action_plan_with_execution(
                    establishment_id=establishment.id,
                    created_by=director,
                    pilot_business_unit_id=signal.responsible_business_unit_id
                    or buses[spec["pole"]].id,
                    title=execution_title(spec["issue_focus"]),
                    tasks=[
                        {
                            "position": position,
                            "task": task,
                            "business_unit_id": buses[spec["pole"]].id,
                        }
                        for position, task in enumerate(
                            execution_tasks(spec["canonical_object"]),
                            start=1,
                        )
                    ],
                    assignees=[
                        {
                            "membership_id": actor.id,
                            "business_unit_id": buses[spec["pole"]].id,
                        }
                    ],
                    source_signal_id=signal.id,
                    issue_focus=spec["issue_focus"],
                    use_shared_chronology=True,
                    start_at=start,
                    end_at=end,
                    visible_from=start - timedelta(hours=1),
                )
                _finish_historical_execution(
                    execution=execution,
                    index=index,
                    actor=actor,
                    director=director,
                )
            return execution.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_EXECUTION,
            seed_key=f"exec:signal:{spec['seed_key']}",
            event_kind="execution_from_signal",
            event_at=at,
            payload={"signal": spec["seed_key"], "end": end.isoformat()},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: ActionPlanExecution.objects.filter(id=object_id).exists(),
        )
    _replay_recent_in_progress_executions(
        establishment=establishment,
        corpus=corpus,
        signals=signals,
        memberships=memberships,
        buses=buses,
        resume=resume,
        result=result,
        period=period,
    )
    _replay_recent_pending_executions(
        establishment=establishment,
        corpus=corpus,
        signals=signals,
        memberships=memberships,
        buses=buses,
        resume=resume,
        result=result,
        period=period,
    )
    if period == "before_active":
        return executions
    with freeze_django_now(SNAPSHOT):
        for schedule in schedules.values():
            materialize_schedule_occurrences_in_horizon(
                schedule=schedule,
                now=SNAPSHOT,
                emit_side_effects=False,
            )
        historical_routines = 0
        historical_until = HORIZON_FROM - timedelta(days=1)
        for schedule in schedules.values():
            if not schedule.use_shared_chronology:
                continue
            for occurrence_date in iter_occurrence_dates(
                schedule=schedule,
                from_date=HISTORY_START.date(),
                until_date=historical_until,
            ):
                if historical_routines >= 47:
                    break
                materialize_execution_from_schedule(
                    schedule=schedule,
                    occurrence_date=occurrence_date,
                    emit_side_effects=False,
                )
                historical_routines += 1
            if historical_routines >= 47:
                break
        if historical_routines != 47:
            raise MamaNiceDatasetError(
                [f"historical routine executions materialized {historical_routines} != 47"]
            )
        extras = load_mama_nice_manifest()["schedules"]["out_of_horizon_linked_dates"]
        for seed_key, days in extras.items():
            schedule = schedules[seed_key]
            for day_text in days:
                materialize_execution_from_schedule(
                    schedule=schedule,
                    occurrence_date=date.fromisoformat(day_text),
                    emit_side_effects=False,
                )
        for oneshot in corpus.oneshots:

            def oneshot_writer(oneshot=oneshot):
                execution = create_execution_from_action_plan(
                    action_plan_id=plans[oneshot.plan_seed_key].id,
                    actor=director,
                    assignees=[
                        {
                            "membership_id": director.id,
                            "business_unit_id": buses[oneshot.pole].id,
                            "start_at": oneshot.start_at,
                            "end_at": oneshot.end_at,
                            "visible_from": oneshot.start_at - timedelta(hours=1),
                        }
                    ],
                    use_shared_chronology=True,
                    start_at=oneshot.start_at,
                    end_at=oneshot.end_at,
                    visible_from=oneshot.start_at - timedelta(hours=1),
                    emit_side_effects=False,
                )
                return execution.id

            _record(
                establishment=establishment,
                object_type=OBJECT_TYPE_EXECUTION,
                seed_key=oneshot.seed_key,
                event_kind="oneshot_execution",
                event_at=oneshot.start_at,
                payload={"title": oneshot.title, "start": oneshot.start_at.isoformat()},
                resume=resume,
                result=result,
                writer=oneshot_writer,
                target_exists=lambda object_id: ActionPlanExecution.objects.filter(id=object_id).exists(),
            )
        _promote_started_scheduled_executions(establishment=establishment)
        _close_past_schedule_executions(
            establishment=establishment,
            actor=director,
        )
        _replay_overdue_executions(
            establishment=establishment,
            actor=director,
            director=director,
            plans=plans,
            buses=buses,
            resume=resume,
            result=result,
        )
        _overlay_rooftop_closure_occurrence(
            establishment=establishment,
            schedules=schedules,
        )
    for execution in ActionPlanExecution.objects.filter(establishment=establishment):
        executions[str(execution.id)] = execution
    return executions


def _replay_recent_in_progress_executions(
    *,
    establishment,
    corpus,
    signals,
    memberships,
    buses,
    resume,
    result,
    period: str,
) -> None:
    from houston.action_plans.models import ActionPlanExecution

    if period == "before_active":
        return
    director = _fictive_director(memberships)
    specs = [spec for spec in corpus.signal_specs if spec["status"] == "in_progress"][:10]
    for index, spec in enumerate(specs):
        signal = signals.get(spec["seed_key"])
        if signal is None:
            continue
        actor = _badge_assignee_for_pole(memberships, _responsible_pole_key(signal), index)
        start, end = in_progress_window()
        starts_in_active_month = start >= _month_start_dt(SEASON_MONTH_ACTIVE)
        if period == "active_month" and not starts_in_active_month:
            continue

        def writer(signal=signal, actor=actor, director=director, start=start, end=end, spec=spec):
            with freeze_django_now(start + timedelta(minutes=15)):
                _plan, execution = create_action_plan_with_execution(
                    establishment_id=establishment.id,
                    created_by=director,
                    pilot_business_unit_id=signal.responsible_business_unit_id
                    or buses[spec["pole"]].id,
                    title=execution_title(spec["issue_focus"]),
                    tasks=[
                        {
                            "position": position,
                            "task": task,
                            "business_unit_id": buses[spec["pole"]].id,
                        }
                        for position, task in enumerate(
                            spec.get("oneshot_tasks") or execution_tasks(spec["canonical_object"]),
                            start=1,
                        )
                    ],
                    assignees=[
                        {
                            "membership_id": actor.id,
                            "business_unit_id": buses[spec["pole"]].id,
                        }
                    ],
                    source_signal_id=signal.id,
                    issue_focus=spec["issue_focus"],
                    use_shared_chronology=True,
                    start_at=start,
                    end_at=end,
                    visible_from=start - timedelta(hours=1),
                )
            return execution.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_EXECUTION,
            seed_key=spec.get("execution_seed_key") or f"exec:signal:{spec['seed_key']}",
            event_kind="execution_from_active_signal",
            event_at=start,
            payload={"signal": spec["seed_key"], "end": end.isoformat()},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: ActionPlanExecution.objects.filter(id=object_id).exists(),
        )


def _replay_recent_pending_executions(
    *,
    establishment,
    corpus,
    signals,
    memberships,
    buses,
    resume,
    result,
    period: str,
) -> None:
    from houston.action_plans.models import ActionPlanExecution

    if period == "before_active":
        return
    director = _fictive_director(memberships)
    specs = [spec for spec in corpus.signal_specs if spec["status"] == "in_progress"][10:20]
    for index, spec in enumerate(specs):
        signal = signals.get(spec["seed_key"])
        if signal is None:
            continue
        actor = _badge_assignee_for_pole(memberships, _responsible_pole_key(signal), index + 10)
        start, end = pending_on_time_window()
        if period == "active_month" and start < _month_start_dt(SEASON_MONTH_ACTIVE):
            continue

        def writer(signal=signal, actor=actor, start=start, end=end, spec=spec):
            with freeze_django_now(start + timedelta(minutes=20)):
                _plan, execution = create_action_plan_with_execution(
                    establishment_id=establishment.id,
                    created_by=director,
                    pilot_business_unit_id=signal.responsible_business_unit_id
                    or buses[spec["pole"]].id,
                    title=execution_title(spec["issue_focus"]),
                    description=spec.get("issue_focus") or "",
                    requires_validation=True,
                    tasks=[
                        {
                            "position": 1,
                            "task": spec["issue_focus"],
                            "business_unit_id": buses[spec["pole"]].id,
                        }
                    ],
                    assignees=[
                        {
                            "membership_id": actor.id,
                            "business_unit_id": buses[spec["pole"]].id,
                        }
                    ],
                    source_signal_id=signal.id,
                    issue_focus=spec["issue_focus"],
                    use_shared_chronology=True,
                    start_at=start,
                    end_at=end,
                    visible_from=start - timedelta(hours=1),
                )
                mark_action_plan_execution_done(
                    execution_id=execution.id,
                    actor_membership=actor,
                )
            return execution.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_EXECUTION,
            seed_key=f"exec:pending:{spec['seed_key']}",
            event_kind="pending_from_active_signal",
            event_at=start,
            payload={"signal": spec["seed_key"], "end": end.isoformat()},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: ActionPlanExecution.objects.filter(id=object_id).exists(),
        )


def _overlay_rooftop_closure_occurrence(*, establishment, schedules) -> None:
    from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionTask

    spec = next(item for item in proactive_project_specs() if item.seed_key == ROOFTOP_CLOSURE_IDENTITY)
    schedule = schedules["schedule:controle-rooftop"]
    execution = ActionPlanExecution.objects.get(
        establishment=establishment,
        action_plan_schedule=schedule,
        start_at=spec.start_at,
    )
    execution.title = spec.oneshot_title or spec.title
    execution.description = spec.context
    execution.save(update_fields=["title", "description", "updated_at"])
    overlay = list(spec.oneshot_tasks)
    tasks = list(ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).order_by("position"))
    for index, task in enumerate(tasks):
        task.task = overlay[index] if index < len(overlay) else overlay[-1]
        task.save(update_fields=["task", "updated_at"])


def _promote_started_scheduled_executions(*, establishment) -> None:
    from houston.action_plans.constants import EXECUTION_STATUS_SCHEDULED
    from houston.action_plans.models import ActionPlanExecution

    now = operational_now()
    due_ids = list(
        ActionPlanExecution.objects.filter(
            establishment=establishment,
            status=EXECUTION_STATUS_SCHEDULED,
            start_at__lte=now,
        ).values_list("id", flat=True)
    )
    with freeze_django_now(now):
        for execution_id in due_ids:
            promote_due_scheduled_executions(
                establishment_id=establishment.id,
                execution_id=execution_id,
            )


def _close_past_schedule_executions(*, establishment, actor) -> None:
    from houston.action_plans.constants import (
        EXECUTION_STATUS_CANCELED,
        EXECUTION_STATUS_DONE,
        EXECUTION_STATUS_IN_PROGRESS,
        EXECUTION_STATUS_PENDING_VALIDATION,
        EXECUTION_STATUS_SCHEDULED,
    )
    from houston.action_plans.models import ActionPlanExecution

    past = ActionPlanExecution.objects.filter(
        establishment=establishment,
        action_plan_schedule__isnull=False,
        start_at__lte=operational_now(),
        end_at__lte=operational_now(),
        status__in={
            EXECUTION_STATUS_SCHEDULED,
            EXECUTION_STATUS_IN_PROGRESS,
            EXECUTION_STATUS_PENDING_VALIDATION,
        },
    )
    for execution in past:
        clock = min(execution.end_at or operational_now(), operational_now())
        with freeze_django_now(clock):
            execution.refresh_from_db()
            if execution.status == EXECUTION_STATUS_SCHEDULED:
                promote_due_scheduled_executions(
                    establishment_id=establishment.id,
                    execution_id=execution.id,
                )
                execution.refresh_from_db()
            if execution.status == EXECUTION_STATUS_IN_PROGRESS:
                mark_action_plan_execution_done(
                    execution_id=execution.id,
                    actor_membership=actor,
                )
                execution.refresh_from_db()
            if execution.status == EXECUTION_STATUS_PENDING_VALIDATION:
                validate_action_plan_execution(
                    execution_id=execution.id,
                    actor_membership=actor,
                    stars=4,
                )
                execution.refresh_from_db()
            if execution.status not in {EXECUTION_STATUS_DONE, EXECUTION_STATUS_CANCELED}:
                raise MamaNiceDatasetError(
                    [
                        f"{execution.id}: past schedule execution remained {execution.status} "
                        "after the domain close cycle"
                    ]
                )


def _replay_overdue_executions(
    *,
    establishment,
    actor,
    director,
    plans,
    buses,
    resume,
    result,
) -> None:
    from houston.action_plans.models import ActionPlanExecution

    for spec in overdue_execution_specs():
        start = spec.end_at - timedelta(days=2)
        at = start

        def writer(spec=spec, start=start):
            with freeze_django_now(start):
                _plan, execution = create_action_plan_with_execution(
                    establishment_id=establishment.id,
                    created_by=director,
                    pilot_business_unit_id=buses[spec.pole].id,
                    title=spec.title,
                    description=spec.context,
                    requires_validation=True,
                    tasks=[
                        {
                            "position": 1,
                            "task": spec.context,
                            "business_unit_id": buses[spec.pole].id,
                        }
                    ],
                    assignees=[
                        {
                            "membership_id": actor.id,
                            "business_unit_id": buses[spec.pole].id,
                        }
                    ],
                    use_shared_chronology=True,
                    start_at=start,
                    end_at=spec.end_at,
                    visible_from=start - timedelta(hours=1),
                )
                mark_action_plan_execution_done(
                    execution_id=execution.id,
                    actor_membership=actor,
                )
            return execution.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_EXECUTION,
            seed_key=spec.seed_key,
            event_kind="overdue_pending_validation",
            event_at=at,
            payload={"title": spec.title, "end": spec.end_at.isoformat(), "days": spec.days_late},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: ActionPlanExecution.objects.filter(id=object_id).exists(),
        )


def _finish_historical_execution(*, execution, index, actor, director) -> None:
    from houston.action_plans.models import ActionPlanExecutionTask

    if index < 16:
        cancel_action_plan_execution(execution_id=execution.id, actor=director)
        execution.refresh_from_db()
        if execution.source_signal_id is not None:
            source_signal = Signal.objects.get(pk=execution.source_signal_id)
            if source_signal.status == Signal.Status.OPEN:
                resolve_signal(signal=source_signal, actor_membership=director)
        return
    if index < 26:
        mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=actor,
        )
        execution.refresh_from_db()
        if execution.status == "pending_validation":
            validate_action_plan_execution(
                execution_id=execution.id,
                actor_membership=director,
                stars=4,
            )
        return
    if index < 36:
        mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=actor,
        )
        execution.refresh_from_db()
        if execution.status == "pending_validation":
            validate_action_plan_execution(
                execution_id=execution.id,
                actor_membership=director,
                stars=4,
            )
        return
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=actor,
    )
    if 40 <= index < 43:
        reopen_action_plan_execution(execution_id=execution.id, actor=director)
        mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=actor,
        )
    execution.refresh_from_db()
    if execution.status == "pending_validation" and index < 32 + 153:
        stars_cycle = [5] * 69 + [4] * 54 + [3] * 15 + [2] * 8 + [1] * 4 + [0] * 3
        stars = stars_cycle[(index - 32) % len(stars_cycle)]
        validate_action_plan_execution(
            execution_id=execution.id,
            actor_membership=director,
            stars=stars,
            comment="Revue démo Mama Nice." if stars <= 2 else None,
        )
    if index < 10:
        task = ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).first()
        if task is not None:
            skip_execution_task(
                task_execution=task,
                actor=actor,
                skipped_reason="Plus nécessaire après passage terrain.",
            )


def _replay_comments(*, corpus, signals, executions, memberships, forbidden, resume, result) -> None:
    from houston.comments.models import Comment

    director = _fictive_director(memberships)
    staff = next(
        member
        for member in memberships.values()
        if member.role == "staff" and member.id not in forbidden
    )
    active_signals = [
        spec
        for spec in corpus.signal_specs
        if spec["status"] in {"open", "in_progress", "interesting"} and spec["seed_key"] in signals
    ][:19]
    historical_execs = list(executions.values())[:65]
    for index, spec in enumerate(active_signals):
        signal = signals[spec["seed_key"]]
        occurred = spec["occurred_at"]
        if spec["status"] in {"open", "in_progress", "interesting"}:
            occurred = shift_sliding_instant(occurred)
        at = occurred + timedelta(hours=5)
        body = signal_comment_body(spec["issue_focus"], index)

        def writer(signal=signal, at=at, body=body):
            with freeze_django_now(at):
                comment = create_signal_comment(
                    author_membership=staff,
                    signal=signal,
                    body=body,
                )
            return comment.id

        _record(
            establishment=signal.establishment,
            object_type=OBJECT_TYPE_COMMENT,
            seed_key=f"comment:signal:{spec['seed_key']}",
            event_kind="comment_signal",
            event_at=at,
            payload={"signal": spec["seed_key"]},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: Comment.objects.filter(id=object_id).exists(),
        )
    for index, execution in enumerate(historical_execs):
        at = operational_now() - timedelta(days=2)

        def writer(execution=execution, at=at, index=index):
            mentioned = [director.id] if index < 10 else None
            body = execution_comment_body(execution.title, index)
            reply = reply_body(execution.title, index)
            with freeze_django_now(at):
                comment = create_action_plan_execution_comment(
                    author_membership=staff,
                    execution=execution,
                    body=body,
                    mentioned_membership_ids=mentioned,
                )
                if index < 12:
                    create_action_plan_execution_comment(
                        author_membership=director,
                        execution=execution,
                        body=reply,
                        parent_comment_id=comment.id,
                    )
            return comment.id

        _record(
            establishment=execution.establishment,
            object_type=OBJECT_TYPE_COMMENT,
            seed_key=f"comment:exec:{execution.id}",
            event_kind="comment_execution",
            event_at=at,
            payload={"execution": str(execution.id)},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: Comment.objects.filter(id=object_id).exists(),
        )


def _deactivate_alumni(establishment, memberships, *, actor, resume, result) -> None:
    for person in ROSTER:
        if person.status != "deactivated" or not person.deactivate_on:
            continue
        membership = memberships[person.email]
        at = datetime.fromisoformat(person.deactivate_on).replace(tzinfo=SNAPSHOT.tzinfo)

        def writer(membership=membership, at=at):
            with freeze_django_now(at):
                deactivate_membership_for_management(
                    current_membership=actor,
                    establishment_id=establishment.id,
                    membership_id=membership.id,
                )
            return membership.id

        _record(
            establishment=establishment,
            object_type=OBJECT_TYPE_MEMBERSHIP,
            seed_key=f"{person.seed_key}:deactivate",
            event_kind="deactivate",
            event_at=at,
            payload={"email": person.email},
            resume=resume,
            result=result,
            writer=writer,
            target_exists=lambda object_id: EstablishmentMembership.objects.filter(id=object_id).exists(),
        )
