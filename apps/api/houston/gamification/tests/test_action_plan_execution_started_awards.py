from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import time as dt_time
from unittest.mock import patch

import pytest
from django.db import close_old_connections, connections
from django.utils import timezone

from houston.action_plans.constants import (
    CANCEL_ORIGIN_SCHEDULE_SYNC,
    CATALOG_STATUS_ACTIVE,
    EXECUTION_LIFECYCLE_EVENT_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_CREATED,
    EXECUTION_LIFECYCLE_EVENT_REACTIVATED,
    EXECUTION_LIFECYCLE_EVENT_STARTED,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.lifecycle_promotion import promote_due_scheduled_executions
from houston.action_plans.materialization import materialize_execution_from_schedule
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
    ActionPlanTask,
)
from houston.action_plans.planning_services import submit_action_plan_planning
from houston.action_plans.schedule_services import reactivate_schedule_future_execution
from houston.action_plans.services import (
    _award_gam04_for_created_in_progress_execution,
    create_action_plan_with_execution,
    create_execution_from_action_plan,
    mark_action_plan_execution_done,
    reopen_action_plan_execution,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.gamification.constants import (
    DELTA_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
    REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
    SOURCE_TYPE_ACTION_PLAN_EXECUTION,
)
from houston.gamification.exceptions import GamificationValidationError
from houston.gamification.models import PointTransaction
from houston.gamification.services import award_action_plan_execution_started_points
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
    create_minimal_v3_signal,
)

pytestmark = pytest.mark.django_db


def _setup():
    establishment = create_establishment(name="GAM-04 Hotel", timezone="UTC")
    business_unit = create_business_unit(establishment=establishment, key="restaurant")
    creator = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    assignee = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=assignee,
        business_unit=business_unit,
    )
    return establishment, business_unit, creator, assignee


def _gam04_txs(*, membership=None, execution=None):
    qs = PointTransaction.objects.filter(
        reason_code=REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
        source_type=SOURCE_TYPE_ACTION_PLAN_EXECUTION,
    )
    if membership is not None:
        qs = qs.filter(membership=membership)
    if execution is not None:
        qs = qs.filter(source_id=str(execution.id))
    return list(qs.order_by("created_at", "id"))


def _create_catalog_plan(*, creator, business_unit, task_assignee=None):
    plan = ActionPlan.objects.create(
        establishment=creator.establishment,
        created_by=creator,
        pilot_business_unit=business_unit,
        title="Reusable opening",
        description="Reusable plan",
        requires_validation=True,
        is_reusable=True,
        catalog_status=CATALOG_STATUS_ACTIVE,
    )
    ActionPlanTask.objects.create(
        action_plan=plan,
        business_unit=business_unit,
        task="Open",
        position=1,
        assigned_membership=task_assignee,
    )
    return plan


def _create_due_direct_execution(*, creator, business_unit, assignee):
    start_at = timezone.now() - timezone.timedelta(minutes=5)
    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=business_unit.id,
        title="Due execution",
        requires_validation=True,
        tasks=[build_task_payload(task="Do it", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=assignee, business_unit=business_unit)],
        start_at=start_at,
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
    )
    return execution


def _created_event(execution):
    return (
        execution.lifecycle_events.filter(event_type=EXECUTION_LIFECYCLE_EVENT_CREATED)
        .order_by("occurred_at", "id")
        .first()
    )


def _schedule_for_dates(*, creator, business_unit, assignee, start_date, end_date):
    plan = _create_catalog_plan(creator=creator, business_unit=business_unit)
    schedule = ActionPlanSchedule.objects.create(
        action_plan=plan,
        establishment=creator.establishment,
        created_by=creator,
        use_shared_chronology=True,
        start_date=start_date,
        end_date=end_date,
        start_at=dt_time(8, 0),
        end_at=dt_time(9, 0),
        recurrence_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        status="active",
    )
    ActionPlanScheduleAssignee.objects.create(
        action_plan_schedule=schedule,
        membership=assignee,
        business_unit=business_unit,
    )
    return schedule


def test_linked_signal_creator_and_other_assignee_awards():
    _establishment, business_unit, creator, assignee = _setup()
    signal = create_minimal_v3_signal(creator, title="Linked eligible")
    responsible = signal.responsible_business_unit
    assert responsible is not None
    create_membership_with_business_unit_scope(
        membership=assignee,
        business_unit=responsible,
    )

    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=responsible.id,
        title="Linked execution",
        source_signal_id=signal.id,
        requires_validation=True,
        tasks=[build_task_payload(task="Fix", business_unit=responsible)],
        assignees=[
            build_assignee_payload(membership=creator, business_unit=responsible),
            build_assignee_payload(membership=assignee, business_unit=responsible),
        ],
        use_shared_chronology=True,
    )

    txs = _gam04_txs(membership=creator, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == DELTA_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE
    assert txs[0].source_event_id == str(_created_event(execution).id)


def test_linked_signal_creator_only_assignee_awards_zero():
    _establishment, _business_unit, creator, _assignee = _setup()
    signal = create_minimal_v3_signal(creator, title="Linked ineligible")
    responsible = signal.responsible_business_unit
    assert responsible is not None

    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=responsible.id,
        title="Linked self execution",
        source_signal_id=signal.id,
        requires_validation=True,
        tasks=[build_task_payload(task="Fix", business_unit=responsible)],
        assignees=[build_assignee_payload(membership=creator, business_unit=responsible)],
        use_shared_chronology=True,
    )

    assert _gam04_txs(execution=execution) == []


def test_unlinked_other_assignee_awards():
    _establishment, business_unit, creator, assignee = _setup()

    execution = _create_due_direct_execution(
        creator=creator,
        business_unit=business_unit,
        assignee=assignee,
    )

    txs = _gam04_txs(membership=creator, execution=execution)
    assert len(txs) == 1
    assert txs[0].delta == DELTA_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE


def test_unlinked_creator_direct_assignee_awards_zero():
    _establishment, business_unit, creator, _assignee = _setup()

    execution = _create_due_direct_execution(
        creator=creator,
        business_unit=business_unit,
        assignee=creator,
    )

    assert _gam04_txs(execution=execution) == []


def test_unlinked_creator_task_assignee_awards_zero():
    _establishment, business_unit, creator, assignee = _setup()
    start_at = timezone.now() - timezone.timedelta(minutes=5)

    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=business_unit.id,
        title="Creator task assigned",
        requires_validation=True,
        tasks=[
            build_task_payload(
                task="Creator task",
                business_unit=business_unit,
                assigned_membership=creator,
            )
        ],
        assignees=[build_assignee_payload(membership=assignee, business_unit=business_unit)],
        start_at=start_at,
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
    )

    assert _gam04_txs(execution=execution) == []


def test_unassigned_tasks_only_awards_zero():
    _establishment, business_unit, creator, _assignee = _setup()

    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=business_unit.id,
        title="Unassigned task only",
        requires_validation=True,
        tasks=[build_task_payload(task="Unassigned", business_unit=business_unit)],
        assignees=[],
        use_shared_chronology=True,
    )

    assert _gam04_txs(execution=execution) == []


def test_catalog_execution_awards_execution_creator_not_plan_creator():
    _establishment, business_unit, alice, _assignee = _setup()
    bob = create_membership(
        establishment=alice.establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    plan = _create_catalog_plan(creator=alice, business_unit=business_unit)

    execution = create_execution_from_action_plan(
        action_plan_id=plan.id,
        actor=bob,
        assignees=[
            build_assignee_payload(
                membership=create_membership(
                    establishment=alice.establishment,
                    role=EstablishmentMembership.Role.OWNER,
                ),
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
    )

    assert len(_gam04_txs(membership=bob, execution=execution)) == 1
    assert _gam04_txs(membership=alice, execution=execution) == []


def test_scheduled_create_awards_zero_then_promotion_awards_started():
    _establishment, business_unit, creator, assignee = _setup()
    start_at = timezone.now() + timezone.timedelta(hours=3)
    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=business_unit.id,
        title="Scheduled execution",
        requires_validation=True,
        tasks=[build_task_payload(task="Later", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=assignee, business_unit=business_unit)],
        start_at=start_at,
        visible_from=start_at + timezone.timedelta(hours=1),
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
    )
    assert execution.status == EXECUTION_STATUS_SCHEDULED
    assert _gam04_txs(execution=execution) == []

    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timezone.timedelta(minutes=1),
        visible_from=timezone.now() + timezone.timedelta(hours=1),
    )
    assert promote_due_scheduled_executions(execution_id=execution.id) == 1

    execution.refresh_from_db()
    txs = _gam04_txs(membership=creator, execution=execution)
    assert len(txs) == 1
    started = execution.lifecycle_events.get(event_type=EXECUTION_LIFECYCLE_EVENT_STARTED)
    assert txs[0].source_event_id == str(started.id)
    assert txs[0].occurred_at == started.occurred_at


def test_created_then_started_reuses_created_canonical_payload():
    _establishment, business_unit, creator, assignee = _setup()
    execution = _create_due_direct_execution(
        creator=creator,
        business_unit=business_unit,
        assignee=assignee,
    )
    created = _created_event(execution)
    assert created is not None
    txs = _gam04_txs(membership=creator, execution=execution)
    assert len(txs) == 1
    assert txs[0].source_event_id == str(created.id)
    assert txs[0].occurred_at == created.occurred_at

    ActionPlanExecution.objects.filter(pk=execution.id).update(
        status=EXECUTION_STATUS_SCHEDULED,
        start_at=timezone.now() - timezone.timedelta(minutes=1),
        started_at=None,
        started_by_membership=None,
    )
    assert promote_due_scheduled_executions(execution_id=execution.id) == 1

    execution.refresh_from_db()
    started = execution.lifecycle_events.get(event_type=EXECUTION_LIFECYCLE_EVENT_STARTED)
    assert started.id != created.id
    txs = _gam04_txs(membership=creator, execution=execution)
    assert len(txs) == 1
    assert txs[0].source_event_id == str(created.id)
    assert txs[0].occurred_at == created.occurred_at


def test_inactive_creator_still_receives_points_on_start():
    _establishment, business_unit, creator, assignee = _setup()
    start_at = timezone.now() + timezone.timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=business_unit.id,
        title="Inactive creator scheduled",
        requires_validation=True,
        tasks=[build_task_payload(task="Later", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=assignee, business_unit=business_unit)],
        start_at=start_at,
        visible_from=start_at + timezone.timedelta(hours=1),
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
    )
    creator.status = EstablishmentMembership.Status.DEACTIVATED
    creator.save(update_fields=["status", "updated_at"])

    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timezone.timedelta(minutes=1),
        visible_from=timezone.now() + timezone.timedelta(hours=1),
    )
    assert promote_due_scheduled_executions(execution_id=execution.id) == 1

    assert len(_gam04_txs(membership=creator, execution=execution)) == 1


def test_three_recurring_occurrences_award_three_transactions():
    _establishment, business_unit, creator, assignee = _setup()
    today = timezone.now().date()
    schedule = _schedule_for_dates(
        creator=creator,
        business_unit=business_unit,
        assignee=assignee,
        start_date=today - timezone.timedelta(days=3),
        end_date=today - timezone.timedelta(days=1),
    )

    for offset in (3, 2, 1):
        materialize_execution_from_schedule(
            schedule=schedule,
            occurrence_date=today - timezone.timedelta(days=offset),
        )

    txs = _gam04_txs(membership=creator)
    assert len(txs) == 3
    assert len({tx.source_id for tx in txs}) == 3


def test_cancel_before_start_awards_zero():
    _establishment, business_unit, creator, assignee = _setup()
    start_at = timezone.now() + timezone.timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=business_unit.id,
        title="Cancel before start",
        requires_validation=True,
        tasks=[build_task_payload(task="Later", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=assignee, business_unit=business_unit)],
        start_at=start_at,
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
    )

    execution.status = EXECUTION_STATUS_CANCELED
    execution.canceled_at = timezone.now()
    execution.canceled_by_membership = creator
    execution.cancel_origin = "manual"
    execution.save(
        update_fields=[
            "status",
            "canceled_at",
            "canceled_by_membership",
            "cancel_origin",
            "updated_at",
        ]
    )
    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timezone.timedelta(minutes=1),
    )
    assert promote_due_scheduled_executions(execution_id=execution.id) == 0
    assert _gam04_txs(execution=execution) == []


def test_reopen_and_reactivate_do_not_reaward():
    _establishment, business_unit, creator, assignee = _setup()
    execution = _create_due_direct_execution(
        creator=creator,
        business_unit=business_unit,
        assignee=assignee,
    )
    assert len(_gam04_txs(execution=execution)) == 1

    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=assignee,
    )
    reopen_action_plan_execution(execution_id=pending.id, actor=creator)
    assert len(_gam04_txs(execution=execution)) == 1

    today = timezone.now().date()
    occurrence_date = today - timezone.timedelta(days=1)
    schedule = _schedule_for_dates(
        creator=creator,
        business_unit=business_unit,
        assignee=assignee,
        start_date=occurrence_date,
        end_date=occurrence_date,
    )
    scheduled = materialize_execution_from_schedule(
        schedule=schedule,
        occurrence_date=occurrence_date,
    )
    assert len(_gam04_txs(execution=scheduled)) == 1
    now = timezone.now()
    scheduled.status = EXECUTION_STATUS_CANCELED
    scheduled.cancel_origin = CANCEL_ORIGIN_SCHEDULE_SYNC
    scheduled.canceled_at = now
    scheduled.canceled_by_membership = None
    scheduled.start_at = now + timezone.timedelta(days=2)
    scheduled.save(
        update_fields=[
            "status",
            "cancel_origin",
            "canceled_at",
            "canceled_by_membership",
            "start_at",
            "updated_at",
        ]
    )
    ActionPlanExecutionLifecycleEvent.objects.create(
        action_plan_execution=scheduled,
        establishment_id=scheduled.establishment_id,
        event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
        actor_membership=None,
        occurred_at=now,
        metadata_safe={"cancel_origin": CANCEL_ORIGIN_SCHEDULE_SYNC},
    )
    schedule.start_at = (timezone.now() - timezone.timedelta(hours=2)).time().replace(
        second=0,
        microsecond=0,
    )
    schedule.end_at = (timezone.now() - timezone.timedelta(hours=1)).time().replace(
        second=0,
        microsecond=0,
    )
    if schedule.end_at <= schedule.start_at:
        schedule.start_at = dt_time(0, 0)
        schedule.end_at = dt_time(1, 0)
    schedule.save(update_fields=["start_at", "end_at", "updated_at"])

    reactivated = reactivate_schedule_future_execution(execution=scheduled, schedule=schedule)
    assert reactivated.status == EXECUTION_STATUS_IN_PROGRESS
    assert reactivated.lifecycle_events.filter(
        event_type=EXECUTION_LIFECYCLE_EVENT_REACTIVATED,
    ).exists()
    assert len(_gam04_txs(execution=scheduled)) == 1


def test_double_helper_call_is_idempotent():
    _establishment, business_unit, creator, assignee = _setup()
    execution = _create_due_direct_execution(
        creator=creator,
        business_unit=business_unit,
        assignee=assignee,
    )

    _award_gam04_for_created_in_progress_execution(execution=execution)

    assert len(_gam04_txs(execution=execution)) == 1


def test_missing_canonical_lifecycle_noops_when_execution_not_started():
    _establishment, business_unit, creator, assignee = _setup()
    start_at = timezone.now() + timezone.timedelta(hours=3)
    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=business_unit.id,
        title="Missing lifecycle scheduled",
        requires_validation=True,
        tasks=[build_task_payload(task="Later", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=assignee, business_unit=business_unit)],
        start_at=start_at,
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
    )
    stale_event = _created_event(execution)
    assert stale_event is not None
    execution.lifecycle_events.all().delete()

    award_action_plan_execution_started_points(
        execution=execution,
        lifecycle_event=stale_event,
    )

    assert _gam04_txs(execution=execution) == []


@pytest.mark.django_db(transaction=True)
def test_missing_canonical_lifecycle_rolls_back_promotion():
    _establishment, business_unit, creator, assignee = _setup()
    start_at = timezone.now() + timezone.timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=business_unit.id,
        title="Missing lifecycle promotion",
        requires_validation=True,
        tasks=[build_task_payload(task="Later", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=assignee, business_unit=business_unit)],
        start_at=start_at,
        visible_from=start_at + timezone.timedelta(hours=1),
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
    )
    execution.lifecycle_events.all().delete()
    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timezone.timedelta(minutes=1),
        visible_from=timezone.now() + timezone.timedelta(hours=1),
    )

    with patch(
        "houston.action_plans.lifecycle_events.record_execution_lifecycle_event",
        return_value=object(),
    ), pytest.raises(
        GamificationValidationError,
        match="canonical lifecycle event",
    ):
        promote_due_scheduled_executions(execution_id=execution.id)

    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_SCHEDULED
    assert not execution.lifecycle_events.filter(event_type=EXECUTION_LIFECYCLE_EVENT_STARTED)
    assert _gam04_txs(execution=execution) == []


@pytest.mark.django_db(transaction=True)
def test_created_and_started_hooks_converge_under_concurrency():
    _establishment, business_unit, creator, assignee = _setup()
    execution = _create_due_direct_execution(
        creator=creator,
        business_unit=business_unit,
        assignee=assignee,
    )
    created = _created_event(execution)
    assert created is not None
    started = ActionPlanExecutionLifecycleEvent.objects.create(
        action_plan_execution=execution,
        establishment_id=execution.establishment_id,
        event_type=EXECUTION_LIFECYCLE_EVENT_STARTED,
        actor_membership=None,
        occurred_at=timezone.now(),
    )
    PointTransaction.objects.filter(
        reason_code=REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
        source_type=SOURCE_TYPE_ACTION_PLAN_EXECUTION,
        source_id=str(execution.id),
    ).delete()

    def _worker(event_id):
        close_old_connections()
        try:
            loaded_execution = ActionPlanExecution.objects.get(pk=execution.id)
            lifecycle_event = ActionPlanExecutionLifecycleEvent.objects.get(pk=event_id)
            award_action_plan_execution_started_points(
                execution=loaded_execution,
                lifecycle_event=lifecycle_event,
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(_worker, [created.id, started.id]))

    txs = _gam04_txs(membership=creator, execution=execution)
    assert len(txs) == 1
    assert txs[0].source_event_id == str(created.id)
    assert txs[0].occurred_at == created.occurred_at


@pytest.mark.django_db(transaction=True)
def test_award_failure_rolls_back_active_create_and_lifecycle():
    _establishment, business_unit, creator, assignee = _setup()

    with patch(
        "houston.gamification.services.award_points",
        side_effect=RuntimeError("forced award failure"),
    ):
        with pytest.raises(RuntimeError, match="forced award failure"):
            _create_due_direct_execution(
                creator=creator,
                business_unit=business_unit,
                assignee=assignee,
            )

    assert ActionPlanExecution.objects.count() == 0
    assert ActionPlanExecutionLifecycleEvent.objects.count() == 0
    assert PointTransaction.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_award_failure_rolls_back_promotion_and_no_on_commit():
    _establishment, business_unit, creator, assignee = _setup()
    start_at = timezone.now() + timezone.timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=creator.establishment_id,
        created_by=creator,
        pilot_business_unit_id=business_unit.id,
        title="Promotion rollback",
        requires_validation=True,
        tasks=[build_task_payload(task="Later", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=assignee, business_unit=business_unit)],
        start_at=start_at,
        visible_from=start_at + timezone.timedelta(hours=1),
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
    )
    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timezone.timedelta(minutes=1),
        visible_from=timezone.now() + timezone.timedelta(hours=1),
    )

    with patch(
        "houston.gamification.services.award_points",
        side_effect=RuntimeError("forced award failure"),
    ), patch("django.db.transaction.on_commit") as on_commit:
        with pytest.raises(RuntimeError, match="forced award failure"):
            promote_due_scheduled_executions(execution_id=execution.id)

    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_SCHEDULED
    assert not execution.lifecycle_events.filter(event_type=EXECUTION_LIFECYCLE_EVENT_STARTED)
    assert _gam04_txs(execution=execution) == []
    on_commit.assert_not_called()


def test_planning_replay_does_not_duplicate_award():
    _establishment, business_unit, creator, assignee = _setup()
    plan = _create_catalog_plan(creator=creator, business_unit=business_unit)
    submission_id = uuid.uuid4()
    start_at = timezone.now() - timezone.timedelta(minutes=10)
    items = [
        {
            "item_id": uuid.uuid4(),
            "kind": "execution",
            "primary_membership_id": assignee.id,
            "business_unit_id": business_unit.id,
            "start_at": start_at,
            "end_at": start_at + timezone.timedelta(hours=1),
        }
    ]

    result = submit_action_plan_planning(
        actor=creator,
        establishment_id=creator.establishment_id,
        submission_id=submission_id,
        use_shared_chronology=False,
        items=items,
        action_plan=plan,
    )
    replay = submit_action_plan_planning(
        actor=creator,
        establishment_id=creator.establishment_id,
        submission_id=submission_id,
        use_shared_chronology=False,
        items=items,
        action_plan=plan,
    )

    execution = ActionPlanExecution.objects.get(id=result.executions[0].resource_id)
    assert replay.replayed is True
    assert len(_gam04_txs(execution=execution)) == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_materialization_awards_once():
    _establishment, business_unit, creator, assignee = _setup()
    occurrence_date = timezone.now().date() - timezone.timedelta(days=1)
    schedule = _schedule_for_dates(
        creator=creator,
        business_unit=business_unit,
        assignee=assignee,
        start_date=occurrence_date,
        end_date=occurrence_date,
    )
    schedule_id = schedule.id

    def _worker(_: int):
        close_old_connections()
        try:
            loaded = ActionPlanSchedule.objects.get(pk=schedule_id)
            return materialize_execution_from_schedule(
                schedule=loaded,
                occurrence_date=occurrence_date,
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(_worker, range(2)))

    assert results[0].id == results[1].id
    execution = ActionPlanExecution.objects.get(pk=results[0].id)
    assert len(_gam04_txs(execution=execution)) == 1
