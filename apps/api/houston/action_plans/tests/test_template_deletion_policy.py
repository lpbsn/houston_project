from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    CANCEL_ORIGIN_MANUAL,
    CANCEL_ORIGIN_SCHEDULE_SYNC,
    CATALOG_STATUS_INACTIVE,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
    SCHEDULE_STATUS_ACTIVE,
    SCHEDULE_STATUS_INACTIVE,
)
from houston.action_plans.exceptions import (
    ActionPlanExecutionObservationIntegrityError,
    ActionPlanStateError,
)
from houston.action_plans.materialization import materialize_schedule_occurrences_in_horizon
from houston.action_plans.models import (
    ActionPlanExecution,
    ActionPlanExecutionFeedPin,
    ActionPlanExecutionTask,
    ActionPlanTask,
)
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.services import (
    create_execution_from_action_plan,
    initial_execution_status,
    mark_action_plan_execution_done,
)
from houston.action_plans.template_deletion_policy import (
    TEMPLATE_DELETION_FATE_HARD_DELETE,
    TEMPLATE_DELETION_FATE_KEEP_DETACH,
    classify_execution_for_template_deletion,
)
from houston.action_plans.template_deletion_services import (
    detach_execution_from_template_for_deletion,
    hard_delete_scheduled_execution_for_template_deletion,
    stop_template_materialization_for_deletion,
)
from houston.action_plans.tests.helpers import (
    build_assignee_payload,
    build_schedule_assignee_payload,
    recurrence_days_for_visible_today,
    visible_schedule_window,
)
from houston.comments.models import Comment
from houston.notifications.models import Notification
from houston.notifications.tests.conftest import create_test_notification
from houston.observations.models import Observation

pytestmark = pytest.mark.django_db


def _make_scheduled_execution(
    *,
    catalog_action_plan,
    owner_membership,
    staff_membership,
    business_unit,
):
    start_at = timezone.now() + timezone.timedelta(days=2)
    execution = create_execution_from_action_plan(
        action_plan_id=catalog_action_plan.id,
        actor=owner_membership,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        start_at=start_at,
        end_at=start_at + timezone.timedelta(hours=1),
        visible_from=start_at - timezone.timedelta(hours=1),
        emit_side_effects=False,
    )
    assert execution.status == EXECUTION_STATUS_SCHEDULED
    return execution


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (EXECUTION_STATUS_SCHEDULED, TEMPLATE_DELETION_FATE_HARD_DELETE),
        (EXECUTION_STATUS_IN_PROGRESS, TEMPLATE_DELETION_FATE_KEEP_DETACH),
        (EXECUTION_STATUS_PENDING_VALIDATION, TEMPLATE_DELETION_FATE_KEEP_DETACH),
        (EXECUTION_STATUS_DONE, TEMPLATE_DELETION_FATE_KEEP_DETACH),
        (EXECUTION_STATUS_CANCELED, TEMPLATE_DELETION_FATE_KEEP_DETACH),
    ],
)
def test_classify_execution_for_template_deletion_by_status_only(status, expected):
    assert classify_execution_for_template_deletion(status=status) == expected


def test_classify_canceled_ignores_cancel_origin():
    assert (
        classify_execution_for_template_deletion(status=EXECUTION_STATUS_CANCELED)
        == TEMPLATE_DELETION_FATE_KEEP_DETACH
    )
    # cancel_origin is not an input — both origins stay keep_detach at status level
    assert CANCEL_ORIGIN_MANUAL
    assert CANCEL_ORIGIN_SCHEDULE_SYNC


def test_initial_execution_status_never_scheduled_without_start_at():
    assert initial_execution_status(start_at=None) == EXECUTION_STATUS_IN_PROGRESS


def test_create_future_execution_is_scheduled_with_start_at(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = _make_scheduled_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    assert execution.start_at is not None
    assert execution.status == EXECUTION_STATUS_SCHEDULED


def test_hard_delete_scheduled_execution_happy_path(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = _make_scheduled_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    execution_id = execution.id
    task_ids = list(
        ActionPlanExecutionTask.objects.filter(
            action_plan_execution_id=execution_id,
        ).values_list("id", flat=True)
    )
    assert task_ids

    hard_delete_scheduled_execution_for_template_deletion(execution_id=execution_id)

    assert not ActionPlanExecution.objects.filter(id=execution_id).exists()
    assert not ActionPlanExecutionTask.objects.filter(id__in=task_ids).exists()


def test_hard_delete_scheduled_with_comment_thread_and_notifications(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = _make_scheduled_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    other_execution = create_execution_from_action_plan(
        action_plan_id=catalog_action_plan.id,
        actor=owner_membership,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        emit_side_effects=False,
    )
    other_notif = create_test_notification(
        recipient=staff_membership,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=other_execution.id,
    )
    root = Comment.objects.create(
        establishment_id=execution.establishment_id,
        action_plan_execution=execution,
        author_membership=owner_membership,
        body="Root comment",
    )
    reply = Comment.objects.create(
        establishment_id=execution.establishment_id,
        action_plan_execution=execution,
        author_membership=staff_membership,
        parent_comment=root,
        body="Reply",
    )
    nested = Comment.objects.create(
        establishment_id=execution.establishment_id,
        action_plan_execution=execution,
        author_membership=owner_membership,
        parent_comment=reply,
        body="Nested reply",
    )
    comment_ids_before_delete = {
        root.id,
        reply.id,
        nested.id,
    }
    exec_notif = create_test_notification(
        recipient=staff_membership,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution.id,
    )
    root_notif = create_test_notification(
        recipient=staff_membership,
        event_key=Notification.EventKey.COMMENT_ACTION_PLAN_EXECUTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=root.id,
        title="Comment",
        body="New comment",
    )
    nested_notif = create_test_notification(
        recipient=owner_membership,
        event_key=Notification.EventKey.COMMENT_REPLY_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=nested.id,
        title="Reply",
        body="Nested reply notif",
    )
    ActionPlanExecutionFeedPin.objects.create(
        membership=staff_membership,
        action_plan_execution=execution,
    )

    hard_delete_scheduled_execution_for_template_deletion(execution_id=execution.id)

    assert not ActionPlanExecution.objects.filter(id=execution.id).exists()
    assert not Comment.objects.filter(id__in=comment_ids_before_delete).exists()
    assert not Notification.objects.filter(
        id__in=[exec_notif.id, root_notif.id, nested_notif.id],
    ).exists()
    assert Notification.objects.filter(id=other_notif.id).exists()
    assert not ActionPlanExecutionFeedPin.objects.filter(
        action_plan_execution_id=execution.id,
    ).exists()


def test_hard_delete_fails_when_observation_linked_to_execution(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = _make_scheduled_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    Observation.objects.create(
        establishment_id=execution.establishment_id,
        submitted_by_membership=owner_membership,
        raw_text="Linked to execution",
        origin=Observation.Origin.DIRECT_REPORT,
        action_plan_execution=execution,
        submitted_at=timezone.now(),
    )

    with pytest.raises(ActionPlanExecutionObservationIntegrityError):
        hard_delete_scheduled_execution_for_template_deletion(execution_id=execution.id)

    assert ActionPlanExecution.objects.filter(id=execution.id).exists()
    assert Observation.objects.filter(action_plan_execution_id=execution.id).exists()


def test_hard_delete_fails_when_observation_linked_to_execution_task(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = _make_scheduled_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    task = ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).first()
    assert task is not None
    Observation.objects.create(
        establishment_id=execution.establishment_id,
        submitted_by_membership=owner_membership,
        raw_text="Linked to task",
        origin=Observation.Origin.ACTION_PLAN_TASK,
        action_plan_execution=execution,
        action_plan_execution_task=task,
        submitted_at=timezone.now(),
    )

    with pytest.raises(ActionPlanExecutionObservationIntegrityError):
        hard_delete_scheduled_execution_for_template_deletion(execution_id=execution.id)

    assert ActionPlanExecution.objects.filter(id=execution.id).exists()
    assert Observation.objects.filter(action_plan_execution_task_id=task.id).exists()


def test_hard_delete_rejects_non_scheduled(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = create_execution_from_action_plan(
        action_plan_id=catalog_action_plan.id,
        actor=owner_membership,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        emit_side_effects=False,
    )
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS

    with pytest.raises(ActionPlanStateError, match="scheduled"):
        hard_delete_scheduled_execution_for_template_deletion(execution_id=execution.id)


def test_detach_execution_nulls_template_schedule_and_task_fks(
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
        use_shared_chronology=True,
        **visible_schedule_window(),
    )
    execution = schedule.executions.filter(status=EXECUTION_STATUS_IN_PROGRESS).first()
    if execution is None:
        execution = create_execution_from_action_plan(
            action_plan_id=catalog_action_plan.id,
            actor=owner_membership,
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
            emit_side_effects=False,
        )
        execution.action_plan_schedule = schedule
        execution.save(update_fields=["action_plan_schedule", "updated_at"])

    task = ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).first()
    assert task is not None
    assert task.action_plan_task_id is not None
    comment = Comment.objects.create(
        establishment_id=execution.establishment_id,
        action_plan_execution=execution,
        author_membership=owner_membership,
        body="Keep me",
    )
    notif = create_test_notification(
        recipient=staff_membership,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution.id,
    )

    detached = detach_execution_from_template_for_deletion(execution_id=execution.id)

    detached.refresh_from_db()
    task.refresh_from_db()
    assert detached.action_plan_id is None
    assert detached.action_plan_schedule_id is None
    assert task.action_plan_task_id is None
    assert Comment.objects.filter(id=comment.id).exists()
    assert Notification.objects.filter(id=notif.id).exists()
    assert detached.title
    assert detached.status == EXECUTION_STATUS_IN_PROGRESS


def test_detach_preserves_runtime_after_detach(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = create_execution_from_action_plan(
        action_plan_id=catalog_action_plan.id,
        actor=owner_membership,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        emit_side_effects=False,
    )
    detach_execution_from_template_for_deletion(execution_id=execution.id)

    updated = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )
    assert updated.status in {
        EXECUTION_STATUS_PENDING_VALIDATION,
        EXECUTION_STATUS_DONE,
    }
    updated.refresh_from_db()
    assert updated.action_plan_id is None


def test_detach_rejects_scheduled(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = _make_scheduled_execution(
        catalog_action_plan=catalog_action_plan,
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    with pytest.raises(ActionPlanStateError, match="hard-deleted"):
        detach_execution_from_template_for_deletion(execution_id=execution.id)


def _force_execution_scheduled(execution: ActionPlanExecution) -> ActionPlanExecution:
    execution.status = EXECUTION_STATUS_SCHEDULED
    execution.start_at = timezone.now() + timezone.timedelta(days=3)
    execution.end_at = execution.start_at + timezone.timedelta(hours=1)
    execution.visible_from = execution.start_at - timezone.timedelta(hours=1)
    execution.canceled_at = None
    execution.cancel_origin = None
    execution.save(
        update_fields=[
            "status",
            "start_at",
            "end_at",
            "visible_from",
            "canceled_at",
            "cancel_origin",
            "updated_at",
        ],
    )
    return execution


def test_stop_keeps_scheduled_for_hard_delete(
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
        use_shared_chronology=True,
        **visible_schedule_window(),
    )
    execution = schedule.executions.order_by("start_at").first()
    assert execution is not None
    _force_execution_scheduled(execution)

    stop_template_materialization_for_deletion(
        action_plan=catalog_action_plan,
    )

    schedule.refresh_from_db()
    execution.refresh_from_db()
    catalog_action_plan.refresh_from_db()
    assert catalog_action_plan.catalog_status == CATALOG_STATUS_INACTIVE
    assert schedule.status == SCHEDULE_STATUS_INACTIVE
    assert execution.status == EXECUTION_STATUS_SCHEDULED
    assert (
        classify_execution_for_template_deletion(status=execution.status)
        == TEMPLATE_DELETION_FATE_HARD_DELETE
    )

    created = materialize_schedule_occurrences_in_horizon(schedule=schedule, horizon_days=14)
    assert created == []

    hard_delete_scheduled_execution_for_template_deletion(execution_id=execution.id)
    assert not ActionPlanExecution.objects.filter(id=execution.id).exists()


def test_stop_preserves_existing_canceled(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = create_execution_from_action_plan(
        action_plan_id=catalog_action_plan.id,
        actor=owner_membership,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        emit_side_effects=False,
    )
    execution.status = EXECUTION_STATUS_CANCELED
    execution.canceled_at = timezone.now()
    execution.cancel_origin = CANCEL_ORIGIN_MANUAL
    execution.save(update_fields=["status", "canceled_at", "cancel_origin", "updated_at"])

    stop_template_materialization_for_deletion(
        action_plan=catalog_action_plan,
    )

    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_CANCELED
    assert execution.cancel_origin == CANCEL_ORIGIN_MANUAL
    assert (
        classify_execution_for_template_deletion(status=execution.status)
        == TEMPLATE_DELETION_FATE_KEEP_DETACH
    )


def test_stop_template_materialization_idempotent_when_already_inactive(
    owner_membership,
    business_unit,
    inactive_catalog_action_plan,
    staff_membership,
):
    ActionPlanTask.objects.create(
        action_plan=inactive_catalog_action_plan,
        business_unit=business_unit,
        task="Task on inactive catalog",
        position=1,
    )
    # Bypass catalog-active guard for fixture setup of linked executions.
    scheduled = ActionPlanExecution.objects.create(
        action_plan=inactive_catalog_action_plan,
        establishment=inactive_catalog_action_plan.establishment,
        created_by=owner_membership,
        title="Inactive template scheduled",
        pilot_business_unit=business_unit,
        requires_validation=True,
        use_shared_chronology=True,
        status=EXECUTION_STATUS_SCHEDULED,
        start_at=timezone.now() + timezone.timedelta(days=2),
        last_activity_at=timezone.now(),
    )
    canceled = ActionPlanExecution.objects.create(
        action_plan=inactive_catalog_action_plan,
        establishment=inactive_catalog_action_plan.establishment,
        created_by=owner_membership,
        title="Inactive template canceled",
        pilot_business_unit=business_unit,
        requires_validation=True,
        use_shared_chronology=True,
        status=EXECUTION_STATUS_CANCELED,
        canceled_at=timezone.now(),
        cancel_origin=CANCEL_ORIGIN_SCHEDULE_SYNC,
        last_activity_at=timezone.now(),
    )

    stop_template_materialization_for_deletion(
        action_plan=inactive_catalog_action_plan,
    )
    stop_template_materialization_for_deletion(
        action_plan=inactive_catalog_action_plan,
    )

    inactive_catalog_action_plan.refresh_from_db()
    scheduled.refresh_from_db()
    canceled.refresh_from_db()
    assert inactive_catalog_action_plan.catalog_status == CATALOG_STATUS_INACTIVE
    assert scheduled.status == EXECUTION_STATUS_SCHEDULED
    assert canceled.status == EXECUTION_STATUS_CANCELED


def test_stop_deactivates_all_schedules_without_mutating_execution_statuses(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule_one = create_action_plan_schedule(
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
    schedule_two = create_action_plan_schedule(
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
    statuses_before = {
        str(execution.id): execution.status
        for execution in ActionPlanExecution.objects.filter(action_plan=catalog_action_plan)
    }
    assert statuses_before
    assert schedule_one.status == SCHEDULE_STATUS_ACTIVE
    assert schedule_two.status == SCHEDULE_STATUS_ACTIVE

    stop_template_materialization_for_deletion(
        action_plan=catalog_action_plan,
    )

    schedule_one.refresh_from_db()
    schedule_two.refresh_from_db()
    assert schedule_one.status == SCHEDULE_STATUS_INACTIVE
    assert schedule_two.status == SCHEDULE_STATUS_INACTIVE
    statuses_after = {
        str(execution.id): execution.status
        for execution in ActionPlanExecution.objects.filter(action_plan=catalog_action_plan)
    }
    assert statuses_after == statuses_before
