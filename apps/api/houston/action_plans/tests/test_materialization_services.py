from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from django.db import close_old_connections, connection, connections
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from houston.action_plans.constants import (
    CANCEL_ORIGIN_SCHEDULE_SYNC,
    EXECUTION_LIFECYCLE_EVENT_CREATED,
    EXECUTION_LIFECYCLE_EVENT_STARTED,
    EXECUTION_STATUS_CANCELED,
)
from houston.action_plans.materialization import (
    MATERIALIZATION_HORIZON_DAYS,
    VISIBLE_FROM_OFFSET,
    _load_schedule_for_materialization,
    ensure_visible_action_plan_executions_materialized,
    materialize_execution_from_schedule,
    materialize_schedule_occurrences_in_horizon,
    materialize_schedules_horizon,
    materialize_visible_schedule_occurrences_in_window,
)
from houston.action_plans.models import (
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
)
from houston.action_plans.schedule_services import (
    create_action_plan_schedule,
    normalize_recurring_recurrence_days,
)
from houston.action_plans.tests.helpers import (
    build_schedule_assignee_payload,
    schedule_window_from_datetime,
    visible_schedule_window,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.timezone_utils import establishment_local_date
from houston.notifications.models import Notification
from houston.testing.factories import create_membership
from houston.testing.taxonomy import create_membership_with_business_unit_scope

pytestmark = pytest.mark.django_db


def _create_staff(establishment, business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(membership=membership, business_unit=business_unit)
    return membership


def test_normalize_recurring_recurrence_days_rejects_empty():
    with pytest.raises(Exception):
        normalize_recurring_recurrence_days([])


def test_materialize_is_idempotent_shared(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()

    first_date = schedule.start_date
    while first_date.weekday() not in {0, 2, 4}:
        first_date += timezone.timedelta(days=1)

    first = materialize_execution_from_schedule(
        schedule=schedule,
        occurrence_date=first_date,
    )
    second = materialize_execution_from_schedule(
        schedule=schedule,
        occurrence_date=first_date,
    )
    assert first.id == second.id


def test_shared_chronology_one_execution_per_occurrence(
    owner_membership,
    catalog_action_plan,
    business_unit,
):
    establishment = owner_membership.establishment
    assignees = [
        build_schedule_assignee_payload(
            membership=_create_staff(establishment, business_unit),
            business_unit=business_unit,
        )
        for _ in range(5)
    ]
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=21)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=assignees,
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()

    materialize_schedule_occurrences_in_horizon(
        schedule=schedule,
        horizon_days=MATERIALIZATION_HORIZON_DAYS,
        now=now,
    )
    executions = ActionPlanExecution.objects.filter(action_plan_schedule=schedule)
    occurrence_dates = set(executions.values_list("occurrence_date", flat=True))
    assert executions.count() == len(occurrence_dates)
    assert len(occurrence_dates) >= 1


def test_individual_chronology_one_execution_per_occurrence_per_assignee(
    owner_membership,
    catalog_action_plan,
    business_unit,
):
    establishment = owner_membership.establishment
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=21)
    schedules = []
    for _ in range(5):
        schedules.append(
            create_action_plan_schedule(
                action_plan=catalog_action_plan,
                actor=owner_membership,
                recurrence_days=["monday", "wednesday", "friday"],
                assignees=[
                    build_schedule_assignee_payload(
                        membership=_create_staff(establishment, business_unit),
                        business_unit=business_unit,
                    )
                ],
                use_shared_chronology=False,
                **window,
            )
        )
    for schedule in schedules:
        ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()

    total = 0
    for schedule in schedules:
        materialize_schedule_occurrences_in_horizon(
            schedule=schedule,
            horizon_days=MATERIALIZATION_HORIZON_DAYS,
            now=now,
        )
        executions = ActionPlanExecution.objects.filter(action_plan_schedule=schedule)
        occurrence_dates = set(executions.values_list("occurrence_date", flat=True))
        assert executions.count() == len(occurrence_dates)
        total += executions.count()
    assert total >= 5


def test_visible_from_offset_applied(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    occurrence_date = schedule.start_date
    while occurrence_date.weekday() != 0:
        occurrence_date += timezone.timedelta(days=1)

    schedule_assignee = schedule.schedule_assignees.first()
    execution = materialize_execution_from_schedule(
        schedule=schedule,
        occurrence_date=occurrence_date,
        schedule_assignee=schedule_assignee,
    )
    assert execution.visible_from == execution.start_at - VISIBLE_FROM_OFFSET


@pytest.mark.django_db(transaction=True)
def test_concurrent_materialization_creates_single_execution(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    occurrence_date = schedule.start_date
    while occurrence_date.weekday() != 0:
        occurrence_date += timezone.timedelta(days=1)

    schedule_id = schedule.id

    def _worker(_: int):
        close_old_connections()
        try:
            loaded = ActionPlanSchedule.objects.get(id=schedule_id)
            return materialize_execution_from_schedule(
                schedule=loaded,
                occurrence_date=occurrence_date,
            )
        finally:
            connections.close_all()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(_worker, range(2)))
    finally:
        connections.close_all()

    assert results[0].id == results[1].id
    assert ActionPlanExecution.objects.filter(action_plan_schedule_id=schedule_id).count() == 1
    assert results[0].task_executions.exists()
    assert results[0].assignees.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("with_beat", [False, True])
def test_read_catch_up_converges_with_parallel_read_or_beat(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
    with_beat,
):
    today_name = timezone.now().strftime("%A").lower()
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=[today_name],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **visible_schedule_window(period_days=0),
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    ActionPlanSchedule.objects.filter(pk=schedule.pk).update(last_materialized_at=None)

    def read_worker():
        close_old_connections()
        try:
            membership = EstablishmentMembership.objects.select_related(
                "establishment",
            ).get(pk=owner_membership.pk)
            return ensure_visible_action_plan_executions_materialized(
                membership=membership,
                view_mode="general",
            )
        finally:
            connections.close_all()

    def beat_worker():
        close_old_connections()
        try:
            return materialize_schedules_horizon(
                establishment_id=owner_membership.establishment_id,
                horizon_days=0,
            )
        finally:
            connections.close_all()

    second_worker = beat_worker if with_beat else read_worker
    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as notify:
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(read_worker), executor.submit(second_worker)]
                for future in futures:
                    future.result()
        finally:
            connections.close_all()

    execution = ActionPlanExecution.objects.get(action_plan_schedule=schedule)
    assert (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution=execution,
                event_type=EXECUTION_LIFECYCLE_EVENT_CREATED,
        ).count()
        == 1
    )
    assert (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution=execution,
                event_type=EXECUTION_LIFECYCLE_EVENT_STARTED,
        ).count()
        == 1
    )
    assert (
        Notification.objects.filter(
            subject_id=execution.id,
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED,
        ).count()
        == 1
    )
    assert notify.call_count == 1


def test_concurrent_materialization_completes_structure_on_recovery(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    occurrence_date = schedule.start_date
    while occurrence_date.weekday() != 0:
        occurrence_date += timezone.timedelta(days=1)

    execution = materialize_execution_from_schedule(
        schedule=schedule,
        occurrence_date=occurrence_date,
    )
    execution.task_executions.all().delete()
    execution.assignees.all().delete()
    assert not execution.task_executions.exists()
    assert not execution.assignees.exists()

    rematerialized = materialize_execution_from_schedule(
        schedule=schedule,
        occurrence_date=occurrence_date,
    )
    assert rematerialized.id == execution.id
    assert rematerialized.task_executions.exists()
    assert rematerialized.assignees.exists()


def test_canceled_does_not_block_other_assignee_materialization(
    owner_membership,
    catalog_action_plan,
    business_unit,
):
    establishment = owner_membership.establishment
    staff_a = _create_staff(establishment, business_unit)
    staff_b = _create_staff(establishment, business_unit)
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=21)
    schedule_a = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday"],
        assignees=[
            build_schedule_assignee_payload(membership=staff_a, business_unit=business_unit),
        ],
        use_shared_chronology=False,
        **window,
    )
    schedule_b = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday"],
        assignees=[
            build_schedule_assignee_payload(membership=staff_b, business_unit=business_unit),
        ],
        use_shared_chronology=False,
        **window,
    )
    schedule_a.executions.all().delete()
    schedule_b.executions.all().delete()
    occurrence_date = schedule_a.start_date
    while occurrence_date.weekday() != 0:
        occurrence_date += timezone.timedelta(days=1)

    assignee_a = schedule_a.schedule_assignees.get(membership_id=staff_a.id)
    assignee_b = schedule_b.schedule_assignees.get(membership_id=staff_b.id)
    execution_a = materialize_execution_from_schedule(
        schedule=schedule_a,
        occurrence_date=occurrence_date,
        schedule_assignee=assignee_a,
    )
    execution_a.status = "canceled"
    execution_a.canceled_at = timezone.now()
    execution_a.save(update_fields=["status", "canceled_at", "updated_at"])

    execution_b = materialize_execution_from_schedule(
        schedule=schedule_b,
        occurrence_date=occurrence_date,
        schedule_assignee=assignee_b,
    )
    assert execution_b.status in {"scheduled", "in_progress"}
    assert execution_b.chronology_owner_membership_id == staff_b.id


def test_materialize_schedules_horizon_counts_executions(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()

    created = materialize_schedules_horizon(
        establishment_id=owner_membership.establishment_id,
    )
    assert created > 0


def _calendar_window(membership, *, days: int = 10, view_mode: str = "general"):
    today = establishment_local_date(establishment=membership.establishment)
    return {
        "membership": membership,
        "view_mode": view_mode,
        "from_date": today,
        "until_date": today + timezone.timedelta(days=days),
    }


def test_calendar_window_skips_settled_occurrences_and_keeps_repairs(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=21)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    stamped = ActionPlanSchedule.objects.get(pk=schedule.pk).last_materialized_at
    call = _calendar_window(owner_membership)

    created = materialize_visible_schedule_occurrences_in_window(**call)
    assert created > 0
    schedule.refresh_from_db()
    assert schedule.last_materialized_at == stamped
    occurrence_ids = set(
        ActionPlanExecution.objects.filter(action_plan_schedule=schedule).values_list(
            "id",
            flat=True,
        )
    )

    with CaptureQueriesContext(connection) as ctx:
        with patch(
            "houston.action_plans.materialization._materialize_occurrence"
        ) as materialize_occurrence:
            again = materialize_visible_schedule_occurrences_in_window(**call)
    assert again == 0
    materialize_occurrence.assert_not_called()
    assert len(ctx.captured_queries) < 12

    incomplete = (
        ActionPlanExecution.objects.filter(action_plan_schedule=schedule)
        .order_by("occurrence_date")
        .first()
    )
    incomplete.task_executions.all().delete()
    repaired = materialize_visible_schedule_occurrences_in_window(**call)
    assert repaired >= 1
    assert incomplete.task_executions.exists()

    missing_date = incomplete.occurrence_date
    incomplete.delete()
    materialize_visible_schedule_occurrences_in_window(**call)
    recreated = ActionPlanExecution.objects.get(
        action_plan_schedule=schedule,
        occurrence_date=missing_date,
    )
    assert recreated.id not in occurrence_ids
    assert recreated.task_executions.exists()
    assert recreated.assignees.exists()

    future = (
        ActionPlanExecution.objects.filter(
            action_plan_schedule=schedule,
            start_at__gt=timezone.now(),
        )
        .order_by("start_at")
        .first()
    )
    assert future is not None
    future.status = EXECUTION_STATUS_CANCELED
    future.cancel_origin = CANCEL_ORIGIN_SCHEDULE_SYNC
    future.canceled_at = timezone.now()
    future.save(update_fields=["status", "cancel_origin", "canceled_at", "updated_at"])
    materialize_visible_schedule_occurrences_in_window(**call)
    future.refresh_from_db()
    assert future.status != EXECUTION_STATUS_CANCELED
    assert future.cancel_origin is None


def test_calendar_window_materializes_a_new_individual_assignee(
    owner_membership,
    catalog_action_plan,
    business_unit,
):
    staff_a = _create_staff(owner_membership.establishment, business_unit)
    staff_b = _create_staff(owner_membership.establishment, business_unit)
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=21)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=[
            build_schedule_assignee_payload(membership=staff_a, business_unit=business_unit),
        ],
        use_shared_chronology=False,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    call = _calendar_window(owner_membership)
    assert materialize_visible_schedule_occurrences_in_window(**call) > 0
    assert not ActionPlanExecution.objects.filter(
        action_plan_schedule=schedule,
        chronology_owner_membership=staff_b,
    ).exists()

    ActionPlanScheduleAssignee.objects.create(
        action_plan_schedule=schedule,
        membership=staff_b,
        business_unit=business_unit,
    )
    materialize_visible_schedule_occurrences_in_window(**call)
    created_for_b = ActionPlanExecution.objects.filter(
        action_plan_schedule=schedule,
        chronology_owner_membership=staff_b,
    )
    assert created_for_b.exists()
    assert all(execution.task_executions.exists() for execution in created_for_b)
    assert all(execution.assignees.exists() for execution in created_for_b)

    with patch(
        "houston.action_plans.materialization._materialize_occurrence"
    ) as materialize_occurrence:
        assert materialize_visible_schedule_occurrences_in_window(**call) == 0
    materialize_occurrence.assert_not_called()


def test_calendar_window_personal_view_stays_on_assigned_schedules(
    owner_membership,
    catalog_action_plan,
    business_unit,
):
    staff_a = _create_staff(owner_membership.establishment, business_unit)
    staff_b = _create_staff(owner_membership.establishment, business_unit)
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=14)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=[
            build_schedule_assignee_payload(membership=staff_a, business_unit=business_unit),
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    hidden = materialize_visible_schedule_occurrences_in_window(
        **_calendar_window(staff_b, view_mode="personal"),
    )
    assert hidden == 0
    assert not ActionPlanExecution.objects.filter(action_plan_schedule=schedule).exists()

    visible = materialize_visible_schedule_occurrences_in_window(
        **_calendar_window(staff_a, view_mode="personal"),
    )
    assert visible > 0
    assert ActionPlanExecution.objects.filter(action_plan_schedule=schedule).exists()


def test_calendar_window_repairs_assignees_only_when_the_schedule_can_supply_them(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=21)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    call = _calendar_window(owner_membership)
    assert materialize_visible_schedule_occurrences_in_window(**call) > 0
    execution = ActionPlanExecution.objects.filter(action_plan_schedule=schedule).earliest(
        "occurrence_date"
    )
    execution.assignees.all().delete()
    assert execution.task_executions.exists()
    assert execution.execution_teams.exists()

    repaired = materialize_visible_schedule_occurrences_in_window(**call)
    assert repaired >= 1
    assert execution.assignees.filter(membership=staff_membership).exists()

    execution.assignees.all().delete()
    schedule.schedule_assignees.all().delete()
    with patch(
        "houston.action_plans.materialization._materialize_occurrence"
    ) as materialize_occurrence:
        assert materialize_visible_schedule_occurrences_in_window(**call) == 0
    materialize_occurrence.assert_not_called()

    ActionPlanScheduleAssignee.objects.create(
        action_plan_schedule=schedule,
        membership=staff_membership,
        business_unit=business_unit,
    )
    materialize_visible_schedule_occurrences_in_window(**call)
    assert execution.assignees.filter(membership=staff_membership).exists()


def test_calendar_window_loads_each_schedule_once_while_creating_occurrences(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=21)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    loads = {"count": 0}
    real_load = _load_schedule_for_materialization

    def counting_load(candidate):
        loads["count"] += 1
        return real_load(candidate)

    call = _calendar_window(owner_membership)
    with patch(
        "houston.action_plans.materialization._load_schedule_for_materialization",
        side_effect=counting_load,
    ):
        created = materialize_visible_schedule_occurrences_in_window(**call)
    assert created > 1
    assert loads["count"] == 1
    executions = list(ActionPlanExecution.objects.filter(action_plan_schedule=schedule))
    assert len(executions) == created
    assert len({execution.occurrence_date for execution in executions}) == created
    assert all(execution.task_executions.exists() for execution in executions)
    assert all(execution.assignees.exists() for execution in executions)

    loads["count"] = 0
    with patch(
        "houston.action_plans.materialization._load_schedule_for_materialization",
        side_effect=counting_load,
    ):
        assert materialize_visible_schedule_occurrences_in_window(**call) == 0
    assert loads["count"] == 0
