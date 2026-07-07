from __future__ import annotations

from datetime import time

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    CANCEL_ORIGIN_MANUAL,
    CANCEL_ORIGIN_SCHEDULE_SYNC,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
)
from houston.action_plans.exceptions import (
    ActionPlanConflictError,
    ActionPlanPermissionError,
    ActionPlanValidationError,
)
from houston.action_plans.schedule_services import (
    create_action_plan_schedule,
    deactivate_action_plan_schedule,
    update_action_plan_schedule,
)
from houston.action_plans.services import cancel_action_plan_execution
from houston.action_plans.tests.helpers import (
    _RECURRENCE_DAY_NAMES,
    build_schedule_assignee_payload,
    recurrence_days_for_visible_today,
    schedule_window_from_datetime,
    visible_schedule_window,
)

pytestmark = pytest.mark.django_db


def test_manager_cannot_assign_out_of_scope_on_schedule_create(
    manager_membership,
    cross_pole_catalog_action_plan,
    out_of_scope_staff,
    maintenance_business_unit,
):
    with pytest.raises(ActionPlanPermissionError, match="Not allowed to assign"):
        create_action_plan_schedule(
            action_plan=cross_pole_catalog_action_plan,
            actor=manager_membership,
            recurrence_days=recurrence_days_for_visible_today(),
            assignees=[
                build_schedule_assignee_payload(
                    membership=out_of_scope_staff,
                    business_unit=maintenance_business_unit,
                )
            ],
            use_shared_chronology=True,
            **visible_schedule_window(),
        )


def test_manager_cannot_assign_out_of_scope_on_schedule_update(
    manager_membership,
    cross_pole_catalog_action_plan,
    staff_membership,
    business_unit,
    out_of_scope_staff,
    maintenance_business_unit,
):
    schedule = create_action_plan_schedule(
        action_plan=cross_pole_catalog_action_plan,
        actor=manager_membership,
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **visible_schedule_window(),
    )

    with pytest.raises(ActionPlanPermissionError, match="Not allowed to assign"):
        update_action_plan_schedule(
            schedule=schedule,
            actor=manager_membership,
            assignees=[
                build_schedule_assignee_payload(
                    membership=out_of_scope_staff,
                    business_unit=maintenance_business_unit,
                )
            ],
        )


def _create_schedule(owner_membership, catalog_action_plan, staff_membership, business_unit):
    return create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **visible_schedule_window(),
    )


def test_update_cancels_future_execution_outside_recurrence(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    # Schedule sync cancels on occurrence_date membership in recurrence_days,
    # not on the weekday of start_at after manual window edits.
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    future_execution = schedule.executions.filter(status="in_progress").first()
    assert future_execution is not None
    future_execution.start_at = timezone.now() + timezone.timedelta(days=2)
    future_execution.end_at = future_execution.start_at + timezone.timedelta(hours=1)
    future_execution.visible_from = future_execution.start_at - timezone.timedelta(hours=1)
    future_execution.save(
        update_fields=["start_at", "end_at", "visible_from", "updated_at"],
    )
    occurrence_date = future_execution.occurrence_date
    excluded_day = next(
        day
        for weekday, day in enumerate(_RECURRENCE_DAY_NAMES)
        if weekday != occurrence_date.weekday()
    )

    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        recurrence_days=[excluded_day],
    )

    future_execution.refresh_from_db()
    assert future_execution.status == EXECUTION_STATUS_CANCELED
    assert future_execution.cancel_origin == CANCEL_ORIGIN_SCHEDULE_SYNC

    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        recurrence_days=recurrence_days_for_visible_today(),
    )
    future_execution.refresh_from_db()
    assert future_execution.status == EXECUTION_STATUS_IN_PROGRESS
    assert future_execution.canceled_at is None
    assert future_execution.cancel_origin is None
    assert future_execution.occurrence_date == occurrence_date
    assert future_execution.start_at.hour == schedule.start_at.hour


def test_manual_cancel_future_stays_canceled_on_schedule_patch(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    future_execution = schedule.executions.filter(status="in_progress").first()
    assert future_execution is not None
    future_execution.start_at = timezone.now() + timezone.timedelta(days=2)
    future_execution.end_at = future_execution.start_at + timezone.timedelta(hours=1)
    future_execution.visible_from = future_execution.start_at - timezone.timedelta(hours=1)
    future_execution.save(
        update_fields=["start_at", "end_at", "visible_from", "updated_at"],
    )

    cancel_action_plan_execution(
        execution_id=future_execution.id,
        actor=owner_membership,
    )
    future_execution.refresh_from_db()
    assert future_execution.status == EXECUTION_STATUS_CANCELED
    assert future_execution.cancel_origin == CANCEL_ORIGIN_MANUAL

    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
    )
    future_execution.refresh_from_db()
    assert future_execution.status == EXECUTION_STATUS_CANCELED
    assert future_execution.cancel_origin == CANCEL_ORIGIN_MANUAL


def test_manual_cancel_future_stays_canceled_on_materialize(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    from houston.action_plans.materialization import materialize_schedule_occurrences_in_horizon

    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    future_execution = schedule.executions.filter(status="in_progress").first()
    assert future_execution is not None
    future_execution.start_at = timezone.now() + timezone.timedelta(days=2)
    future_execution.end_at = future_execution.start_at + timezone.timedelta(hours=1)
    future_execution.visible_from = future_execution.start_at - timezone.timedelta(hours=1)
    future_execution.save(
        update_fields=["start_at", "end_at", "visible_from", "updated_at"],
    )

    cancel_action_plan_execution(
        execution_id=future_execution.id,
        actor=owner_membership,
    )
    future_execution.refresh_from_db()
    assert future_execution.status == EXECUTION_STATUS_CANCELED
    assert future_execution.cancel_origin == CANCEL_ORIGIN_MANUAL

    materialize_schedule_occurrences_in_horizon(schedule=schedule, visible_only=False)
    future_execution.refresh_from_db()
    assert future_execution.status == EXECUTION_STATUS_CANCELED
    assert future_execution.cancel_origin == CANCEL_ORIGIN_MANUAL


def test_update_syncs_future_window_without_changing_occurrence_date(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    future_execution = (
        schedule.executions.filter(status="in_progress", start_at__gt=timezone.now())
        .order_by("occurrence_date")
        .first()
    )
    if future_execution is None:
        future_execution = schedule.executions.filter(status="in_progress").first()
        future_execution.start_at = timezone.now() + timezone.timedelta(days=2)
        future_execution.end_at = future_execution.start_at + timezone.timedelta(hours=1)
        future_execution.visible_from = future_execution.start_at - timezone.timedelta(hours=1)
        future_execution.save(
            update_fields=["start_at", "end_at", "visible_from", "updated_at"],
        )

    original_occurrence_date = future_execution.occurrence_date
    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        start_at=time(10, 0),
        end_at=time(11, 0),
    )

    future_execution.refresh_from_db()
    assert future_execution.occurrence_date == original_occurrence_date
    assert future_execution.start_at.hour == 10


def test_update_use_shared_chronology_forbidden_after_materialization(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    assert schedule.executions.exists()

    with pytest.raises(ActionPlanValidationError):
        update_action_plan_schedule(
            schedule=schedule,
            actor=owner_membership,
            use_shared_chronology=False,
        )


def test_deactivate_blocks_active_started_execution(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    active = schedule.executions.filter(status="in_progress").first()
    active.start_at = timezone.now() - timezone.timedelta(minutes=5)
    active.end_at = timezone.now() + timezone.timedelta(hours=1)
    active.visible_from = active.start_at - timezone.timedelta(hours=1)
    active.save(update_fields=["start_at", "end_at", "visible_from", "updated_at"])

    with pytest.raises(ActionPlanConflictError) as exc_info:
        deactivate_action_plan_schedule(schedule=schedule, actor=owner_membership)
    assert exc_info.value.active_execution_id == active.id


def test_deactivate_cancels_future_preserves_terminal(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    done = schedule.executions.filter(status="in_progress").first()
    done.status = EXECUTION_STATUS_DONE
    done.save(update_fields=["status", "updated_at"])

    future = schedule.executions.filter(status="in_progress").exclude(id=done.id).first()
    if future is not None:
        future.start_at = timezone.now() + timezone.timedelta(days=2)
        future.end_at = future.start_at + timezone.timedelta(hours=1)
        future.visible_from = future.start_at - timezone.timedelta(hours=1)
        future.save(update_fields=["start_at", "end_at", "visible_from", "updated_at"])

    deactivate_action_plan_schedule(schedule=schedule, actor=owner_membership)

    done.refresh_from_db()
    assert done.status == EXECUTION_STATUS_DONE
    if future is not None:
        future.refresh_from_db()
        assert future.status == EXECUTION_STATUS_CANCELED


def _create_individual_schedule(
    owner_membership,
    catalog_action_plan,
    assignees,
):
    return create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=assignees,
        use_shared_chronology=False,
        **visible_schedule_window(period_days=21),
    )


def test_update_materializes_missing_individual_assignee_occurrences(
    owner_membership,
    catalog_action_plan,
    business_unit,
):
    from houston.action_plans.materialization import materialize_execution_from_schedule
    from houston.establishments.models import EstablishmentMembership
    from houston.testing.factories import create_membership
    from houston.testing.taxonomy import create_membership_with_business_unit_scope

    establishment = owner_membership.establishment

    def _staff():
        membership = create_membership(
            establishment=establishment,
            role=EstablishmentMembership.Role.STAFF,
        )
        create_membership_with_business_unit_scope(
            membership=membership,
            business_unit=business_unit,
        )
        return membership

    staff_a = _staff()
    staff_b = _staff()
    schedule = _create_individual_schedule(
        owner_membership,
        catalog_action_plan,
        [
            build_schedule_assignee_payload(membership=staff_a, business_unit=business_unit),
            build_schedule_assignee_payload(membership=staff_b, business_unit=business_unit),
        ],
    )
    schedule.executions.all().delete()

    assignee_a = schedule.schedule_assignees.get(membership_id=staff_a.id)
    occurrence_date = schedule.start_date
    while occurrence_date.weekday() not in {0, 2, 4}:
        occurrence_date += timezone.timedelta(days=1)

    materialize_execution_from_schedule(
        schedule=schedule,
        occurrence_date=occurrence_date,
        schedule_assignee=assignee_a,
    )
    assert not schedule.executions.filter(
        schedule_source_membership_id=staff_b.id,
        occurrence_date=occurrence_date,
    ).exists()

    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        start_at=schedule.start_at,
        end_at=schedule.end_at,
    )

    assert schedule.executions.filter(
        schedule_source_membership_id=staff_b.id,
        occurrence_date=occurrence_date,
        status=EXECUTION_STATUS_IN_PROGRESS,
    ).exists()


def test_update_syncs_individual_assignee_time_override(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=False,
        **visible_schedule_window(period_days=21),
    )
    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        assignees=[
            {
                **build_schedule_assignee_payload(
                    membership=staff_membership,
                    business_unit=business_unit,
                ),
                "start_at": time(10, 0),
                "end_at": time(11, 0),
            }
        ],
    )
    future_execution = schedule.executions.filter(status="in_progress").first()
    assert future_execution is not None
    future_execution.start_at = timezone.now() + timezone.timedelta(days=2)
    future_execution.end_at = future_execution.start_at + timezone.timedelta(hours=1)
    future_execution.visible_from = future_execution.start_at - timezone.timedelta(hours=1)
    future_execution.save(
        update_fields=["start_at", "end_at", "visible_from", "updated_at"],
    )

    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        start_at=time(8, 0),
        end_at=time(9, 0),
    )

    future_execution.refresh_from_db()
    assert future_execution.start_at.hour == 10
    assert future_execution.end_at.hour == 11


def test_update_assignees_cancels_removed_member_future_executions(
    owner_membership,
    catalog_action_plan,
    business_unit,
):
    from houston.establishments.models import EstablishmentMembership
    from houston.testing.factories import create_membership
    from houston.testing.taxonomy import create_membership_with_business_unit_scope

    establishment = owner_membership.establishment

    def _staff():
        membership = create_membership(
            establishment=establishment,
            role=EstablishmentMembership.Role.STAFF,
        )
        create_membership_with_business_unit_scope(
            membership=membership,
            business_unit=business_unit,
        )
        return membership

    staff_a = _staff()
    staff_b = _staff()
    schedule = _create_individual_schedule(
        owner_membership,
        catalog_action_plan,
        [
            build_schedule_assignee_payload(membership=staff_a, business_unit=business_unit),
            build_schedule_assignee_payload(membership=staff_b, business_unit=business_unit),
        ],
    )
    removed_execution = schedule.executions.filter(
        schedule_source_membership_id=staff_b.id,
        status=EXECUTION_STATUS_IN_PROGRESS,
    ).first()
    assert removed_execution is not None
    removed_execution.start_at = timezone.now() + timezone.timedelta(days=2)
    removed_execution.end_at = removed_execution.start_at + timezone.timedelta(hours=1)
    removed_execution.visible_from = removed_execution.start_at - timezone.timedelta(hours=1)
    removed_execution.save(
        update_fields=["start_at", "end_at", "visible_from", "updated_at"],
    )

    kept_execution = schedule.executions.filter(
        schedule_source_membership_id=staff_a.id,
        status=EXECUTION_STATUS_IN_PROGRESS,
    ).first()
    assert kept_execution is not None

    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        assignees=[
            build_schedule_assignee_payload(membership=staff_a, business_unit=business_unit),
        ],
    )

    removed_execution.refresh_from_db()
    kept_execution.refresh_from_db()
    assert removed_execution.status == EXECUTION_STATUS_CANCELED
    assert kept_execution.status == EXECUTION_STATUS_IN_PROGRESS


def test_partial_assignee_time_validated_against_schedule_defaults(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now)

    with pytest.raises(ActionPlanValidationError, match="end_at must be after start_at"):
        create_action_plan_schedule(
            action_plan=catalog_action_plan,
            actor=owner_membership,
            recurrence_days=["monday"],
            assignees=[
                {
                    **build_schedule_assignee_payload(
                        membership=staff_membership,
                        business_unit=business_unit,
                    ),
                    "start_at": time(11, 0),
                }
            ],
            use_shared_chronology=False,
            **window,
        )
