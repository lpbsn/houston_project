from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.utils import timezone

from houston.action_plans.materialization import (
    MATERIALIZATION_HORIZON_DAYS,
    VISIBLE_FROM_OFFSET,
    materialize_execution_from_schedule,
    materialize_schedule_occurrences_in_horizon,
    materialize_schedules_horizon,
)
from houston.action_plans.models import ActionPlanExecution, ActionPlanSchedule
from houston.action_plans.schedule_services import (
    create_action_plan_schedule,
    normalize_recurring_recurrence_days,
)
from houston.action_plans.tests.helpers import (
    build_schedule_assignee_payload,
    schedule_window_from_datetime,
)
from houston.establishments.models import EstablishmentMembership
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
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(_worker, range(2)))

    assert results[0].id == results[1].id
    assert ActionPlanExecution.objects.filter(action_plan_schedule_id=schedule_id).count() == 1
    assert results[0].task_executions.exists()
    assert results[0].assignees.exists()


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
