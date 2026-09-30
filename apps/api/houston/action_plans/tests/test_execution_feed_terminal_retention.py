from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_PENDING_VALIDATION,
)
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.selectors import (
    action_plan_execution_calendar_items_queryset,
    action_plan_execution_feed_queryset,
)
from houston.action_plans.tests.helpers import (
    action_plan_execution_feed_url,
    create_execution,
    feed_execution_ids,
)

pytestmark = pytest.mark.django_db


def _visible_ids(membership, *, now, view_mode="general"):
    return set(
        action_plan_execution_feed_queryset(
            membership=membership,
            view_mode=view_mode,
            now=now,
        ).values_list("id", flat=True)
    )


def test_done_and_canceled_executions_follow_the_canonical_terminal_clock(
    owner_membership,
    business_unit,
):
    now = timezone.now()
    validated = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Validated",
        status=EXECUTION_STATUS_DONE,
        requires_validation=True,
    )
    validated_edge = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Validated edge",
        status=EXECUTION_STATUS_DONE,
        requires_validation=True,
    )
    marked_done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Marked done",
        status=EXECUTION_STATUS_DONE,
        requires_validation=False,
    )
    marked_done_ignored = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Validation clock wins",
        status=EXECUTION_STATUS_DONE,
        requires_validation=True,
    )
    undated_done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Undated done",
        status=EXECUTION_STATUS_DONE,
        requires_validation=True,
    )
    canceled = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Canceled",
        status=EXECUTION_STATUS_CANCELED,
    )
    canceled_edge = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Canceled edge",
        status=EXECUTION_STATUS_CANCELED,
    )
    pending = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pending",
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        requires_validation=True,
    )
    ActionPlanExecution.objects.filter(pk=validated.pk).update(
        validated_at=now - timedelta(days=10, microseconds=-1),
        marked_done_at=now - timedelta(days=30),
    )
    ActionPlanExecution.objects.filter(pk=validated_edge.pk).update(
        validated_at=now - timedelta(days=10),
    )
    ActionPlanExecution.objects.filter(pk=marked_done.pk).update(
        marked_done_at=now - timedelta(days=1),
    )
    ActionPlanExecution.objects.filter(pk=marked_done_ignored.pk).update(
        marked_done_at=now - timedelta(hours=1),
        validated_at=now - timedelta(days=11),
    )
    ActionPlanExecution.objects.filter(pk=canceled.pk).update(
        canceled_at=now - timedelta(hours=48, microseconds=-1),
    )
    ActionPlanExecution.objects.filter(pk=canceled_edge.pk).update(
        canceled_at=now - timedelta(hours=48),
    )

    visible = _visible_ids(owner_membership, now=now)

    assert validated.id in visible
    assert marked_done.id in visible
    assert canceled.id in visible
    assert pending.id in visible
    assert validated_edge.id not in visible
    assert marked_done_ignored.id not in visible
    assert undated_done.id not in visible
    assert canceled_edge.id not in visible


def test_category_filter_and_calendar_do_not_keep_retained_terminals(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done in list",
        status=EXECUTION_STATUS_DONE,
    )
    ActionPlanExecution.objects.filter(pk=done.pk).update(
        validated_at=now - timedelta(days=1),
        start_at=now,
        end_at=now + timedelta(hours=1),
    )
    from houston.testing.auth import auth_headers, login

    token = login(api_client, user=owner_membership.user)
    filtered = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + "?view_mode=general&category=in_progress",
        **auth_headers(token),
    )
    assert filtered.status_code == 200
    assert str(done.id) not in feed_execution_ids(filtered.json())

    calendar_ids = set(
        action_plan_execution_calendar_items_queryset(
            membership=owner_membership,
            view_mode="general",
            window_start=now - timedelta(days=1),
            window_end=now + timedelta(days=1),
        ).values_list("id", flat=True)
    )
    assert done.id not in calendar_ids
    assert done.id in _visible_ids(owner_membership, now=now)
