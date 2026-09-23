from __future__ import annotations

from datetime import date, datetime, time, timedelta
from unittest.mock import patch

import pytest

from houston.action_plans.constants import CATALOG_STATUS_ACTIVE
from houston.action_plans.models import ActionPlan, ActionPlanSchedule
from houston.action_plans.permissions import can_use_action_plan
from houston.action_plans.services import create_action_plan
from houston.establishments.mama_nice_dataset_clock import freeze_django_now
from houston.establishments.mama_nice_dataset_constants import (
    HISTORY_START,
    OBJECT_TYPE_PLAN,
    OBJECT_TYPE_SCHEDULE,
    OBJECT_TYPE_SEASON,
    RUNTIME_RH_PLAN_SEED_KEY,
    SEASON_MONTH_ACTIVE,
    SEASON_MONTHS_CLOSED,
    SNAPSHOT,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_ledger import canonical_fingerprint
from houston.establishments.mama_nice_dataset_manifest import load_mama_nice_manifest
from houston.establishments.mama_nice_dataset_replay import (
    SeedResult,
    _replay_plans,
    _replay_schedules,
    _replay_seasons,
    seed_mama_nice_dataset,
)
from houston.establishments.models import EstablishmentMembership, MamaNiceSeedRecord
from houston.gamification.models import GamificationSeason
from houston.gamification.services import open_season
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit


def test_production_seed_requires_establishment_id():
    with pytest.raises(MamaNiceDatasetError, match="establishment-id"):
        seed_mama_nice_dataset(
            establishment_id=None,
            dry_run=True,
            confirm=False,
            resume=False,
            local=False,
        )


def test_seed_refuses_write_without_confirm():
    with pytest.raises(MamaNiceDatasetError, match="--confirm"):
        seed_mama_nice_dataset(
            establishment_id="fe29f398-4a6b-4f9b-a92f-00805435ddc2",
            dry_run=False,
            confirm=False,
            resume=False,
        )


@pytest.mark.django_db
def test_replay_seasons_opens_and_closes_in_europe_paris():
    establishment = create_establishment(name="Mama seasons Paris", timezone="Europe/Paris")
    result = SeedResult(dry_run=False, resume=False)
    _replay_seasons(establishment, resume=False, result=result)

    seasons = list(
        GamificationSeason.objects.filter(establishment=establishment).order_by("starts_at")
    )
    assert len(seasons) == 7
    closed = [season for season in seasons if season.status == GamificationSeason.Status.CLOSED]
    active = [season for season in seasons if season.status == GamificationSeason.Status.ACTIVE]
    assert [
        season.starts_at.astimezone(SNAPSHOT.tzinfo).date() for season in closed
    ] == list(SEASON_MONTHS_CLOSED)
    assert len(active) == 1
    assert active[0].starts_at.astimezone(SNAPSHOT.tzinfo).date() == SEASON_MONTH_ACTIVE
    august = next(
        season for season in seasons if season.starts_at.astimezone(SNAPSHOT.tzinfo).month == 8
    )
    assert august.starts_at == datetime(2026, 8, 1, 0, 0, tzinfo=SNAPSHOT.tzinfo)
    assert result.written == 13
    assert result.skipped == 0


@pytest.mark.django_db
def test_replay_seasons_resumes_after_open_without_close():
    establishment = create_establishment(name="Mama seasons resume", timezone="Europe/Paris")
    month_start = SEASON_MONTHS_CLOSED[0]
    at = datetime(month_start.year, month_start.month, 1, 0, 0, tzinfo=SNAPSHOT.tzinfo)
    with freeze_django_now(at):
        season = open_season(establishment, month_start_local=month_start)
    MamaNiceSeedRecord.objects.create(
        establishment=establishment,
        object_type=OBJECT_TYPE_SEASON,
        seed_key=f"season:{month_start.isoformat()}",
        object_id=season.id,
        fingerprint=canonical_fingerprint({"month": month_start.isoformat(), "action": "open"}),
        event_kind="season_open",
        event_at=at,
    )

    result = SeedResult(dry_run=False, resume=True)
    _replay_seasons(establishment, resume=True, result=result)

    season.refresh_from_db()
    assert season.status == GamificationSeason.Status.CLOSED
    september = GamificationSeason.objects.get(
        establishment=establishment,
        starts_at=datetime(
            SEASON_MONTH_ACTIVE.year,
            SEASON_MONTH_ACTIVE.month,
            1,
            0,
            0,
            tzinfo=SNAPSHOT.tzinfo,
        ),
    )
    assert september.status == GamificationSeason.Status.ACTIVE
    assert result.skipped == 1
    assert result.written == 12


@pytest.mark.django_db
def test_replay_seasons_raises_mama_error_when_close_target_missing():
    establishment = create_establishment(name="Mama seasons missing", timezone="Europe/Paris")
    result = SeedResult(dry_run=False, resume=False)
    with patch(
        "houston.establishments.mama_nice_dataset_replay.get_season_by_starts_at",
        return_value=None,
    ):
        with pytest.raises(MamaNiceDatasetError, match="no season for starts_at"):
            _replay_seasons(establishment, resume=False, result=result)


def _colliding_schedule_rows() -> list[dict]:
    shared = {
        "plan_seed_key": "plan:collision",
        "pole": "restaurant",
        "start_at": "09:00",
        "end_at": "10:00",
        "start_date": "2025-09-23",
        "end_date": "2025-10-23",
        "use_shared_chronology": True,
        "assignee_persona": None,
    }
    return [
        {**shared, "n": 1, "seed_key": "schedule:collision-a", "recurrence_days": ["monday"]},
        {**shared, "n": 2, "seed_key": "schedule:collision-b", "recurrence_days": ["tuesday"]},
    ]


@pytest.mark.django_db
def test_replay_schedules_resolves_by_seed_record_when_window_collides():
    establishment = create_establishment(name="Mama schedules collide", timezone="Europe/Paris")
    actor = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    bus = create_business_unit(establishment=establishment, key="restaurant")
    plan = create_action_plan(
        establishment_id=establishment.id,
        created_by=actor,
        pilot_business_unit_id=bus.id,
        title="Plan collision",
        tasks=[{"position": 1, "task": "Faire le passage", "business_unit_id": bus.id}],
    )
    rows = _colliding_schedule_rows()
    manifest = {"schedules": {"schedules": rows}}
    plans = {"plan:collision": plan}
    buses = {"restaurant": bus}

    with patch(
        "houston.establishments.mama_nice_dataset_replay.load_mama_nice_manifest",
        return_value=manifest,
    ):
        first = SeedResult(dry_run=False, resume=False)
        schedules = _replay_schedules(
            establishment=establishment,
            actor=actor,
            plans=plans,
            memberships={},
            buses=buses,
            resume=False,
            result=first,
        )
        resumed = SeedResult(dry_run=False, resume=True)
        resumed_schedules = _replay_schedules(
            establishment=establishment,
            actor=actor,
            plans=plans,
            memberships={},
            buses=buses,
            resume=True,
            result=resumed,
        )

    first_ids = {key: schedule.id for key, schedule in schedules.items()}
    resumed_ids = {key: schedule.id for key, schedule in resumed_schedules.items()}
    assert first_ids == resumed_ids
    assert first_ids["schedule:collision-a"] != first_ids["schedule:collision-b"]
    assert first.written == 2
    assert first.skipped == 0
    assert resumed.written == 0
    assert resumed.skipped == 2
    assert ActionPlanSchedule.objects.filter(action_plan=plan).count() == 2
    for seed_key, schedule_id in first_ids.items():
        record = MamaNiceSeedRecord.objects.get(
            establishment=establishment,
            object_type=OBJECT_TYPE_SCHEDULE,
            seed_key=seed_key,
        )
        assert record.object_id == schedule_id


RH_PLAN_TITLE = "Routines planning RH"
RH_CREATE_PAYLOAD = {"title": RH_PLAN_TITLE, "reusable": False}
RH_SCHEDULE_SEED_KEY = "schedule:revue-planning-rh"


def _rh_only_manifest() -> dict:
    manifest = load_mama_nice_manifest()
    rh_plan = next(
        row
        for row in manifest["reusable_plans"]["plans"]
        if row["seed_key"] == RUNTIME_RH_PLAN_SEED_KEY
    )
    schedule = next(
        row
        for row in manifest["schedules"]["schedules"]
        if row["seed_key"] == RH_SCHEDULE_SEED_KEY
    )
    return {
        "reusable_plans": {"plans": [rh_plan]},
        "schedules": {"schedules": [schedule]},
    }


def _rh_actor_and_buses(establishment):
    actor = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    return actor, {"rh": create_business_unit(establishment=establishment, key="rh")}


def _replay_rh_plan_and_schedule(*, establishment, actor, buses, resume, result):
    with patch(
        "houston.establishments.mama_nice_dataset_replay.load_mama_nice_manifest",
        return_value=_rh_only_manifest(),
    ):
        plans = _replay_plans(
            establishment=establishment,
            actor=actor,
            buses=buses,
            resume=resume,
            result=result,
        )
        schedules = _replay_schedules(
            establishment=establishment,
            actor=actor,
            plans=plans,
            memberships={},
            buses=buses,
            resume=resume,
            result=result,
        )
    return plans, schedules


@pytest.mark.django_db
def test_replay_runtime_rh_plan_first_pass_publishes_and_schedules():
    establishment = create_establishment(name="Mama RH first pass", timezone="Europe/Paris")
    actor, buses = _rh_actor_and_buses(establishment)
    first = SeedResult(dry_run=False, resume=False)
    plans, schedules = _replay_rh_plan_and_schedule(
        establishment=establishment,
        actor=actor,
        buses=buses,
        resume=False,
        result=first,
    )
    resumed = SeedResult(dry_run=False, resume=True)
    resumed_plans, resumed_schedules = _replay_rh_plan_and_schedule(
        establishment=establishment,
        actor=actor,
        buses=buses,
        resume=True,
        result=resumed,
    )

    plan = plans[RUNTIME_RH_PLAN_SEED_KEY]
    plan.refresh_from_db()
    record = MamaNiceSeedRecord.objects.get(
        establishment=establishment,
        object_type=OBJECT_TYPE_PLAN,
        seed_key=RUNTIME_RH_PLAN_SEED_KEY,
    )
    assert plan.is_reusable is True
    assert plan.catalog_status == CATALOG_STATUS_ACTIVE
    assert can_use_action_plan(actor, plan)
    assert record.object_id == plan.id
    assert record.fingerprint == canonical_fingerprint(RH_CREATE_PAYLOAD)
    assert schedules[RH_SCHEDULE_SEED_KEY].action_plan_id == plan.id
    assert resumed_plans[RUNTIME_RH_PLAN_SEED_KEY].id == plan.id
    assert resumed_schedules[RH_SCHEDULE_SEED_KEY].id == schedules[RH_SCHEDULE_SEED_KEY].id
    assert ActionPlan.objects.filter(establishment=establishment, title=RH_PLAN_TITLE).count() == 1
    assert ActionPlanSchedule.objects.filter(action_plan=plan).count() == 1
    assert MamaNiceSeedRecord.objects.filter(
        establishment=establishment,
        seed_key=RUNTIME_RH_PLAN_SEED_KEY,
    ).count() == 1
    assert first.written == 2
    assert first.skipped == 0
    assert resumed.written == 0
    assert resumed.skipped == 2


@pytest.mark.django_db
def test_replay_runtime_rh_plan_resume_publishes_committed_one_shot():
    establishment = create_establishment(name="Mama RH resume", timezone="Europe/Paris")
    actor, buses = _rh_actor_and_buses(establishment)
    plan = create_action_plan(
        establishment_id=establishment.id,
        created_by=actor,
        pilot_business_unit_id=buses["rh"].id,
        title=RH_PLAN_TITLE,
        is_reusable=False,
        catalog_status=None,
        tasks=[
            {"position": 1, "task": "Préparer le planning", "business_unit_id": buses["rh"].id},
            {"position": 2, "task": "Valider le staffing", "business_unit_id": buses["rh"].id},
            {"position": 3, "task": "Clôturer la revue", "business_unit_id": buses["rh"].id},
        ],
    )
    fingerprint = canonical_fingerprint(RH_CREATE_PAYLOAD)
    MamaNiceSeedRecord.objects.create(
        establishment=establishment,
        object_type=OBJECT_TYPE_PLAN,
        seed_key=RUNTIME_RH_PLAN_SEED_KEY,
        object_id=plan.id,
        fingerprint=fingerprint,
        event_kind="plan_create",
        event_at=HISTORY_START + timedelta(hours=3),
    )

    resumed = SeedResult(dry_run=False, resume=True)
    plans, schedules = _replay_rh_plan_and_schedule(
        establishment=establishment,
        actor=actor,
        buses=buses,
        resume=True,
        result=resumed,
    )
    second = SeedResult(dry_run=False, resume=True)
    _replay_rh_plan_and_schedule(
        establishment=establishment,
        actor=actor,
        buses=buses,
        resume=True,
        result=second,
    )

    plan.refresh_from_db()
    record = MamaNiceSeedRecord.objects.get(
        establishment=establishment,
        object_type=OBJECT_TYPE_PLAN,
        seed_key=RUNTIME_RH_PLAN_SEED_KEY,
    )
    assert plan.is_reusable is True
    assert plan.catalog_status == CATALOG_STATUS_ACTIVE
    assert can_use_action_plan(actor, plan)
    assert plans[RUNTIME_RH_PLAN_SEED_KEY].id == plan.id
    assert record.object_id == plan.id
    assert record.fingerprint == fingerprint
    assert schedules[RH_SCHEDULE_SEED_KEY].action_plan_id == plan.id
    assert ActionPlan.objects.filter(establishment=establishment, title=RH_PLAN_TITLE).count() == 1
    assert ActionPlanSchedule.objects.filter(action_plan=plan).count() == 1
    assert resumed.written == 1
    assert resumed.skipped == 1
    assert second.written == 0
    assert second.skipped == 2


DYNAMIC_REFERENCE = datetime(2026, 9, 23, 15, 0, tzinfo=SNAPSHOT.tzinfo)
PAST_OCCURRENCE_DATE = date(2026, 9, 23)


def _materialize_past_scheduled_occurrence(*, name: str, requires_validation: bool = True):
    from houston.action_plans.constants import CATALOG_STATUS_ACTIVE, EXECUTION_STATUS_SCHEDULED
    from houston.action_plans.materialization import materialize_execution_from_schedule
    from houston.action_plans.models import ActionPlanExecution
    from houston.action_plans.schedule_services import create_action_plan_schedule

    establishment = create_establishment(name=name, timezone="Europe/Paris")
    actor = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    bus = create_business_unit(establishment=establishment, key="restaurant")
    plan = create_action_plan(
        establishment_id=establishment.id,
        created_by=actor,
        pilot_business_unit_id=bus.id,
        title=f"Routine {name}",
        requires_validation=requires_validation,
        is_reusable=True,
        catalog_status=CATALOG_STATUS_ACTIVE,
        tasks=[{"position": 1, "task": "Faire le passage", "business_unit_id": bus.id}],
    )
    schedule = create_action_plan_schedule(
        action_plan=plan,
        actor=actor,
        start_date=PAST_OCCURRENCE_DATE,
        end_date=PAST_OCCURRENCE_DATE,
        start_at=time(9, 0),
        end_at=time(10, 0),
        recurrence_days=["wednesday"],
        assignees=[{"membership_id": actor.id, "business_unit_id": bus.id}],
        use_shared_chronology=True,
        emit_side_effects=False,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    with freeze_django_now(SNAPSHOT):
        execution = materialize_execution_from_schedule(
            schedule=schedule,
            occurrence_date=PAST_OCCURRENCE_DATE,
            emit_side_effects=False,
        )
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_SCHEDULED
    assert ActionPlanExecution.objects.filter(action_plan_schedule=schedule).count() == 1
    return establishment, actor, execution


def _close_with_default_reference(*, establishment, actor, persist_clock: bool, resume: bool):
    from houston.establishments.mama_nice_dataset_clock import (
        resolve_seed_reference_at,
        use_reference_at,
    )
    from houston.establishments.mama_nice_dataset_replay import _close_past_schedule_executions

    with freeze_django_now(DYNAMIC_REFERENCE):
        reference_at = resolve_seed_reference_at(
            establishment=establishment,
            resume=resume,
            persist=persist_clock,
        )
        assert reference_at == DYNAMIC_REFERENCE
        with use_reference_at(reference_at):
            _close_past_schedule_executions(establishment=establishment, actor=actor)
    return reference_at


@pytest.mark.django_db
def test_close_past_schedule_executions_uses_domain_cycle_without_as_of():
    from houston.action_plans.constants import (
        EXECUTION_STATUS_DONE,
        EXECUTION_STATUS_IN_PROGRESS,
        EXECUTION_STATUS_PENDING_VALIDATION,
        EXECUTION_STATUS_SCHEDULED,
    )
    from houston.action_plans.lifecycle_promotion import promote_due_scheduled_executions
    from houston.action_plans.services import (
        mark_action_plan_execution_done,
        validate_action_plan_execution,
    )
    from houston.establishments.mama_nice_dataset_clock import load_persisted_reference_at

    scheduled_est, scheduled_actor, scheduled = _materialize_past_scheduled_occurrence(
        name="Mama close scheduled"
    )
    started_est, started_actor, started = _materialize_past_scheduled_occurrence(
        name="Mama close started"
    )
    pending_est, pending_actor, pending = _materialize_past_scheduled_occurrence(
        name="Mama close pending"
    )
    terminal_est, terminal_actor, terminal = _materialize_past_scheduled_occurrence(
        name="Mama close terminal"
    )

    with freeze_django_now(DYNAMIC_REFERENCE):
        assert started.status == EXECUTION_STATUS_SCHEDULED
        promote_due_scheduled_executions(
            establishment_id=started_est.id,
            execution_id=started.id,
        )
        started.refresh_from_db()
        assert started.status == EXECUTION_STATUS_IN_PROGRESS

        promote_due_scheduled_executions(
            establishment_id=pending_est.id,
            execution_id=pending.id,
        )
        mark_action_plan_execution_done(
            execution_id=pending.id,
            actor_membership=pending_actor,
        )
        pending.refresh_from_db()
        assert pending.status == EXECUTION_STATUS_PENDING_VALIDATION

        promote_due_scheduled_executions(
            establishment_id=terminal_est.id,
            execution_id=terminal.id,
        )
        mark_action_plan_execution_done(
            execution_id=terminal.id,
            actor_membership=terminal_actor,
        )
        validate_action_plan_execution(
            execution_id=terminal.id,
            actor_membership=terminal_actor,
            stars=4,
        )
        terminal.refresh_from_db()
        assert terminal.status == EXECUTION_STATUS_DONE

    for establishment, actor, execution in (
        (scheduled_est, scheduled_actor, scheduled),
        (started_est, started_actor, started),
        (pending_est, pending_actor, pending),
        (terminal_est, terminal_actor, terminal),
    ):
        _close_with_default_reference(
            establishment=establishment,
            actor=actor,
            persist_clock=True,
            resume=False,
        )
        execution.refresh_from_db()
        assert execution.status == EXECUTION_STATUS_DONE
        assert load_persisted_reference_at(establishment) == DYNAMIC_REFERENCE

    _close_with_default_reference(
        establishment=scheduled_est,
        actor=scheduled_actor,
        persist_clock=True,
        resume=True,
    )
    scheduled.refresh_from_db()
    assert scheduled.status == EXECUTION_STATUS_DONE
    assert load_persisted_reference_at(scheduled_est) == DYNAMIC_REFERENCE
