from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.exceptions import ActionPlanStateError
from houston.action_plans.lifecycle_promotion import (
    ensure_execution_lifecycle_for_read,
    promote_due_scheduled_executions,
    run_scheduled_execution_lifecycle_tick,
)
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import (
    create_action_plan_with_execution,
    initial_execution_status,
    mark_action_plan_execution_done,
)
from houston.action_plans.tests.helpers import (
    action_plan_execution_feed_url,
    action_plan_execution_upcoming_url,
    action_plan_execution_url,
    build_assignee_payload,
    build_task_payload,
    feed_query,
)
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.testing.auth import auth_headers, login
from houston.testing.auth import build_api_membership as build_foreign_membership

pytestmark = pytest.mark.django_db(transaction=True)

_FROZEN_NOW = timezone.make_aware(datetime(2026, 7, 20, 12, 0, 0))


def test_create_future_start_sets_scheduled(owner_membership, business_unit):
    start_at = timezone.now() + timedelta(hours=3)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Future plan",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        visible_from=start_at - timedelta(hours=1),
        end_at=start_at + timedelta(hours=1),
    )
    assert execution.status == EXECUTION_STATUS_SCHEDULED
    assert execution.availability_notified_at is None


def test_create_past_start_sets_in_progress(owner_membership, business_unit):
    start_at = timezone.now() - timedelta(minutes=5)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Started plan",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
    )
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS


def test_promote_due_scheduled_to_in_progress(owner_membership, business_unit):
    start_at = timezone.now() + timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Promote me",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        visible_from=timezone.now() - timedelta(minutes=1),
        end_at=start_at + timedelta(hours=1),
    )
    assert execution.status == EXECUTION_STATUS_SCHEDULED

    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timedelta(minutes=1),
    )
    promoted = promote_due_scheduled_executions(
        establishment_id=owner_membership.establishment_id,
    )
    assert promoted == 1
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS

    started = Notification.objects.filter(
        subject_id=execution.id,
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_STARTED,
    )
    assert started.exists()


def test_availability_emitted_once_when_visible(owner_membership, business_unit):
    start_at = timezone.now() + timedelta(hours=5)
    visible_from = timezone.now() + timedelta(minutes=30)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Deferred visibility",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        visible_from=visible_from,
        end_at=start_at + timedelta(hours=1),
    )
    assert execution.availability_notified_at is None
    assert not Notification.objects.filter(
        subject_id=execution.id,
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED,
    ).exists()

    ActionPlanExecution.objects.filter(pk=execution.id).update(
        visible_from=timezone.now() - timedelta(minutes=1),
    )
    result = run_scheduled_execution_lifecycle_tick(
        establishment_id=owner_membership.establishment_id,
    )
    assert result["availability_emitted"] == 1
    execution.refresh_from_db()
    assert execution.availability_notified_at is not None

    result_again = run_scheduled_execution_lifecycle_tick(
        establishment_id=owner_membership.establishment_id,
    )
    assert result_again["availability_emitted"] == 0
    assert (
        Notification.objects.filter(
            subject_id=execution.id,
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED,
        ).count()
        == 1
    )


def test_lazy_promote_scoped_to_execution_id(owner_membership, business_unit):
    start_at = timezone.now() + timedelta(hours=1)
    assignee = build_assignee_payload(
        membership=owner_membership,
        business_unit=business_unit,
    )
    _, due = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Due",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[assignee],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
    )
    _, other = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Other",
        requires_validation=False,
        tasks=[build_task_payload(task="t2", business_unit=business_unit)],
        assignees=[assignee],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
    )
    ActionPlanExecution.objects.filter(pk__in=[due.id, other.id]).update(
        start_at=timezone.now() - timedelta(minutes=1),
    )
    promoted = promote_due_scheduled_executions(
        establishment_id=owner_membership.establishment_id,
        execution_id=due.id,
    )
    assert promoted == 1
    due.refresh_from_db()
    other.refresh_from_db()
    assert due.status == EXECUTION_STATUS_IN_PROGRESS
    assert other.status == EXECUTION_STATUS_SCHEDULED


def test_ensure_lifecycle_for_read_requires_matching_establishment(
    owner_membership,
    business_unit,
):
    start_at = timezone.now() + timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Cross-tenant due",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
    )
    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timedelta(minutes=1),
    )
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)

    ensure_execution_lifecycle_for_read(
        establishment_id=foreign.establishment_id,
        execution_id=execution.id,
    )
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_SCHEDULED
    assert not Notification.objects.filter(
        subject_id=execution.id,
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_STARTED,
    ).exists()


def test_initial_status_null_start_at_is_in_progress():
    assert (
        initial_execution_status(start_at=None, now=_FROZEN_NOW)
        == EXECUTION_STATUS_IN_PROGRESS
    )


def test_initial_status_start_at_equal_now_is_in_progress():
    assert (
        initial_execution_status(start_at=_FROZEN_NOW, now=_FROZEN_NOW)
        == EXECUTION_STATUS_IN_PROGRESS
    )


def test_create_start_at_equal_now_sets_in_progress(owner_membership, business_unit):
    with patch("houston.action_plans.services.timezone.now", return_value=_FROZEN_NOW):
        _, execution = create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="Starts exactly now",
            requires_validation=False,
            tasks=[build_task_payload(task="t1", business_unit=business_unit)],
            assignees=[
                build_assignee_payload(
                    membership=owner_membership,
                    business_unit=business_unit,
                ),
            ],
            start_at=_FROZEN_NOW,
            end_at=_FROZEN_NOW + timedelta(hours=1),
        )
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS


def test_create_null_start_at_sets_in_progress(owner_membership, business_unit):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="No start",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=None,
    )
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS


def test_promote_does_not_touch_non_scheduled_statuses(owner_membership, business_unit):
    start_at = timezone.now() - timedelta(minutes=1)
    for status in (
        EXECUTION_STATUS_PENDING_VALIDATION,
        EXECUTION_STATUS_DONE,
        EXECUTION_STATUS_CANCELED,
    ):
        _, execution = create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title=f"Stay {status}",
            requires_validation=False,
            tasks=[build_task_payload(task=status, business_unit=business_unit)],
            assignees=[
                build_assignee_payload(
                    membership=owner_membership,
                    business_unit=business_unit,
                ),
            ],
            start_at=start_at,
            end_at=start_at + timedelta(hours=1),
        )
        ActionPlanExecution.objects.filter(pk=execution.id).update(status=status)
        promoted = promote_due_scheduled_executions(
            establishment_id=owner_membership.establishment_id,
            execution_id=execution.id,
        )
        assert promoted == 0
        execution.refresh_from_db()
        assert execution.status == status


def test_past_end_at_does_not_auto_complete(owner_membership, business_unit):
    start_at = timezone.now() - timedelta(hours=3)
    end_at = timezone.now() - timedelta(hours=1)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Overdue window",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        end_at=end_at,
    )
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS
    run_scheduled_execution_lifecycle_tick(
        establishment_id=owner_membership.establishment_id,
        execution_id=execution.id,
    )
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS


def test_mark_done_rejects_scheduled(owner_membership, business_unit):
    start_at = timezone.now() + timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Still scheduled",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
    )
    assert execution.status == EXECUTION_STATUS_SCHEDULED
    with pytest.raises(ActionPlanStateError):
        mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=owner_membership,
        )


def test_feed_lazy_promotes_due_scheduled(
    api_client,
    owner_membership,
    business_unit,
):
    start_at = timezone.now() + timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Lazy feed promote",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        visible_from=timezone.now() - timedelta(minutes=1),
        end_at=start_at + timedelta(hours=1),
    )
    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timedelta(minutes=1),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS


def test_upcoming_lazy_promotes_due_scheduled(
    api_client,
    owner_membership,
    business_unit,
):
    start_at = timezone.now() + timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Lazy upcoming promote",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
    )
    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timedelta(minutes=1),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_upcoming_url(owner_membership.establishment_id)
        + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS


def test_detail_lazy_promotes_due_scheduled(
    api_client,
    owner_membership,
    business_unit,
):
    start_at = timezone.now() + timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Lazy detail promote",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
    )
    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timedelta(minutes=1),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_url(owner_membership.establishment_id, execution.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == EXECUTION_STATUS_IN_PROGRESS
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS


def test_concurrent_promote_is_idempotent_for_status_and_started_notification(
    owner_membership,
    business_unit,
):
    start_at = timezone.now() + timedelta(hours=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Concurrent promote",
        requires_validation=False,
        tasks=[build_task_payload(task="t1", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        visible_from=timezone.now() - timedelta(minutes=1),
        end_at=start_at + timedelta(hours=1),
    )
    ActionPlanExecution.objects.filter(pk=execution.id).update(
        start_at=timezone.now() - timedelta(minutes=1),
    )

    def try_promote() -> int:
        close_old_connections()
        try:
            return promote_due_scheduled_executions(
                establishment_id=owner_membership.establishment_id,
                execution_id=execution.id,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: try_promote(), range(2)))

    assert sorted(results) == [0, 1]
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS
    assert (
        Notification.objects.filter(
            subject_id=execution.id,
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_STARTED,
        ).count()
        == 1
    )

    assert (
        promote_due_scheduled_executions(
            establishment_id=owner_membership.establishment_id,
            execution_id=execution.id,
        )
        == 0
    )
    assert (
        Notification.objects.filter(
            subject_id=execution.id,
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_STARTED,
        ).count()
        == 1
    )
