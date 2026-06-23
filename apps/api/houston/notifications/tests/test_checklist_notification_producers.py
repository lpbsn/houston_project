from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest
from django.db import transaction
from django.utils import timezone

from houston.checklists.materialization import materialize_execution_from_assignment
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.services import (
    cancel_checklist_execution,
    create_checklist_assignment,
    create_checklist_template,
    create_execution_from_template,
    deactivate_checklist_assignment,
    update_checklist_assignment,
)
from houston.checklists.tests.conftest import (
    add_task_template,
    assignment_schedule_from_datetime,
    stable_assignment_times,
)
from houston.notifications.models import Notification

pytest_plugins = ["houston.checklists.tests.conftest"]

pytestmark = pytest.mark.django_db(transaction=True)

SENSITIVE_TEMPLATE_TITLE = "Secret checklist title"


def _notifications_for_execution(*, execution_id) -> list[Notification]:
    return list(
        Notification.objects.filter(
            subject_type=Notification.SubjectType.CHECKLIST_EXECUTION,
            subject_id=execution_id,
        ).order_by("recipient_membership_id", "event_key")
    )


def _recipient_ids(notifications: list[Notification]) -> set:
    return {item.recipient_membership_id for item in notifications}


def _assert_generic_copy(notification: Notification) -> None:
    assert SENSITIVE_TEMPLATE_TITLE not in notification.title
    assert SENSITIVE_TEMPLATE_TITLE not in notification.body


def _next_weekday_datetime(weekday: int, *, hour: int = 8) -> datetime:
    now = timezone.now()
    days_ahead = (weekday - now.weekday()) % 7
    target_date = (now + timedelta(days=days_ahead)).date()
    return datetime.combine(
        target_date,
        datetime.min.time().replace(hour=hour),
        tzinfo=now.tzinfo,
    )


def _create_assignment(
    owner_membership,
    staff_membership,
    business_unit,
    *,
    task_count: int = 1,
    **kwargs,
):
    template = _active_registered_template(owner_membership, business_unit)
    for position in range(2, task_count + 1):
        add_task_template(template=template, task=f"Task {position}", position=position)
    legacy_start = kwargs.pop("start_at", None)
    legacy_end = kwargs.pop("end_at", None)
    if legacy_start is not None and isinstance(legacy_start, datetime):
        duration_hours = 1
        if isinstance(legacy_end, datetime):
            duration_hours = max(1, int((legacy_end - legacy_start).total_seconds() // 3600))
        schedule = assignment_schedule_from_datetime(legacy_start, duration_hours=duration_hours)
        start_date = kwargs.pop("start_date", schedule["start_date"])
        end_date = kwargs.pop("end_date", schedule["end_date"])
        start_at = kwargs.pop("start_at", schedule["start_at"])
        end_at = kwargs.pop("end_at", schedule["end_at"])
    else:
        default_date = timezone.now().date()
        start_date = kwargs.pop("start_date", default_date)
        end_date = kwargs.pop("end_date", start_date + timedelta(days=14))
        start_at = legacy_start if isinstance(legacy_start, time) else time(8, 0)
        end_at = legacy_end if isinstance(legacy_end, time) else time(10, 0)
    return create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=start_date,
        end_date=end_date,
        start_at=start_at,
        end_at=end_at,
        **kwargs,
    )


def _active_registered_template(owner_membership, business_unit, *, title: str = "Routine"):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        title=title,
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    return template


def _assignment_execution(owner_membership, staff_membership, business_unit):
    template = _active_registered_template(owner_membership, business_unit)
    now = timezone.now()
    start_at, end_at = stable_assignment_times(duration_hours=2)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=start_at,
        end_at=end_at,
    )
    return ChecklistExecution.objects.select_related("assigned_to", "assigned_by").get(
        checklist_assignment=assignment,
    )


def test_materialization_notifies_assignee_with_system_actor(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    now = timezone.now()
    start_at, end_at = stable_assignment_times(duration_hours=2)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=start_at,
        end_at=end_at,
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()

    execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=now.date(),
    )

    notifications = [
        item
        for item in _notifications_for_execution(execution_id=execution.id)
        if item.event_key == Notification.EventKey.CHECKLIST_EXECUTION_CREATED
    ]
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff_membership.id
    assert notifications[0].actor_membership_id is None
    assert notifications[0].priority == Notification.Priority.ACTION_REQUIRED
    _assert_generic_copy(notifications[0])


def test_materialization_idempotent_skips_second_notification(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    now = timezone.now()
    start_at, end_at = stable_assignment_times(duration_hours=2)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=start_at,
        end_at=end_at,
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    occurrence_date = now.date()

    first = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=occurrence_date,
    )
    materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=occurrence_date,
    )

    created_notifications = [
        item
        for item in _notifications_for_execution(execution_id=first.id)
        if item.event_key == Notification.EventKey.CHECKLIST_EXECUTION_CREATED
    ]
    assert len(created_notifications) == 1


def test_create_execution_from_template_notifies_other_assignee(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(
        owner_membership,
        business_unit,
        title=SENSITIVE_TEMPLATE_TITLE,
    )

    execution = create_execution_from_template(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
    )

    notifications = [
        item
        for item in _notifications_for_execution(execution_id=execution.id)
        if item.event_key == Notification.EventKey.CHECKLIST_EXECUTION_CREATED
    ]
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff_membership.id
    _assert_generic_copy(notifications[0])


def test_create_execution_from_template_self_launch_zero_notifications(
    staff_membership,
    owner_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)

    execution = create_execution_from_template(
        template=template,
        actor=staff_membership,
    )

    assert _notifications_for_execution(execution_id=execution.id) == []


def test_cancel_execution_actor_is_assigned_by_notifies_assignee_only(
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _assignment_execution(owner_membership, staff_membership, business_unit)
    Notification.objects.filter(subject_id=execution.id).delete()

    cancel_checklist_execution(execution=execution, actor=owner_membership)

    notifications = [
        item
        for item in _notifications_for_execution(execution_id=execution.id)
        if item.event_key == Notification.EventKey.CHECKLIST_EXECUTION_CANCELED
    ]
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff_membership.id


def test_cancel_execution_actor_differs_from_assigned_by_notifies_both(
    owner_membership,
    staff_membership,
    manager_membership,
    business_unit,
):
    execution = _assignment_execution(owner_membership, staff_membership, business_unit)
    Notification.objects.filter(subject_id=execution.id).delete()

    cancel_checklist_execution(execution=execution, actor=manager_membership)

    notifications = [
        item
        for item in _notifications_for_execution(execution_id=execution.id)
        if item.event_key == Notification.EventKey.CHECKLIST_EXECUTION_CANCELED
    ]
    assert _recipient_ids(notifications) == {staff_membership.id, owner_membership.id}


def test_cancel_execution_assigned_by_null_actor_is_assignee_zero_notifications(
    staff_membership,
    owner_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    execution = create_execution_from_template(
        template=template,
        actor=staff_membership,
    )
    assert execution.assigned_by_id is None
    Notification.objects.filter(subject_id=execution.id).delete()

    cancel_checklist_execution(execution=execution, actor=staff_membership)

    assert _notifications_for_execution(execution_id=execution.id) == []


def test_cancel_execution_assigned_by_null_actor_differs_notifies_assignee(
    staff_membership,
    owner_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    execution = create_execution_from_template(
        template=template,
        actor=staff_membership,
    )
    Notification.objects.filter(subject_id=execution.id).delete()

    cancel_checklist_execution(execution=execution, actor=owner_membership)

    notifications = [
        item
        for item in _notifications_for_execution(execution_id=execution.id)
        if item.event_key == Notification.EventKey.CHECKLIST_EXECUTION_CANCELED
    ]
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff_membership.id


def test_deactivate_assignment_notifies_only_newly_canceled_assigned_executions(
    owner_membership,
    staff_membership,
    business_unit,
):
    monday_start = _next_weekday_datetime(0)
    tuesday_date = monday_start.date() + timedelta(days=1)
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        start_at=monday_start,
        end_at=monday_start + timedelta(hours=2),
        recurrence_days=["monday", "tuesday"],
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    done_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=monday_start.date(),
    )
    done_execution.status = ChecklistExecution.Status.DONE
    done_execution.done_at = timezone.now()
    done_execution.save(update_fields=["status", "done_at", "updated_at"])
    assigned_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=tuesday_date,
    )
    assert assigned_execution.status == ChecklistExecution.Status.ASSIGNED

    Notification.objects.filter(
        subject_type=Notification.SubjectType.CHECKLIST_EXECUTION,
    ).delete()

    deactivate_checklist_assignment(assignment=assignment, actor=owner_membership)

    canceled_notifications = list(
        Notification.objects.filter(
            event_key=Notification.EventKey.CHECKLIST_EXECUTION_CANCELED,
        )
    )
    assert len(canceled_notifications) == 1
    assert canceled_notifications[0].subject_id == assigned_execution.id
    assert canceled_notifications[0].recipient_membership_id == staff_membership.id
    assert done_execution.id not in {item.subject_id for item in canceled_notifications}


def test_update_assignment_schedule_sync_notifies_only_out_of_schedule_canceled(
    owner_membership,
    staff_membership,
    business_unit,
):
    monday_start = _next_weekday_datetime(0)
    tuesday_date = monday_start.date() + timedelta(days=1)
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        start_at=monday_start,
        end_at=monday_start + timedelta(hours=2),
        recurrence_days=["monday", "tuesday"],
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    monday_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=monday_start.date(),
    )
    tuesday_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=tuesday_date,
    )
    Notification.objects.filter(
        subject_type=Notification.SubjectType.CHECKLIST_EXECUTION,
    ).delete()

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        recurrence_days=["monday"],
    )

    canceled_notifications = list(
        Notification.objects.filter(
            event_key=Notification.EventKey.CHECKLIST_EXECUTION_CANCELED,
        )
    )
    assert len(canceled_notifications) == 1
    assert canceled_notifications[0].subject_id == tuesday_execution.id
    assert canceled_notifications[0].recipient_membership_id == staff_membership.id
    assert monday_execution.id not in {item.subject_id for item in canceled_notifications}


def test_business_rollback_creates_zero_notifications(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)

    with pytest.raises(RuntimeError, match="force rollback"):
        with transaction.atomic():
            create_execution_from_template(
                template=template,
                actor=owner_membership,
                assigned_to_id=staff_membership.id,
            )
            raise RuntimeError("force rollback")

    assert Notification.objects.filter(
        event_key=Notification.EventKey.CHECKLIST_EXECUTION_CREATED,
    ).count() == 0


def test_no_template_title_in_notification_copy(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(
        owner_membership,
        business_unit,
        title=SENSITIVE_TEMPLATE_TITLE,
    )

    execution = create_execution_from_template(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
    )

    notification = _notifications_for_execution(execution_id=execution.id)[0]
    _assert_generic_copy(notification)
