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


def test_retained_terminals_must_have_been_operational_before_the_transition(
    owner_membership,
    business_unit,
):
    now = timezone.now()
    canceled_before_start = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Canceled before start",
    )
    canceled_before_visibility = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Canceled before visibility",
    )
    started_but_not_visible = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Started but not visible",
        visible_from=now + timedelta(hours=1),
    )
    operational_then_canceled = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Operational then canceled",
        visible_from=now - timedelta(hours=48),
    )
    operational_then_done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Operational then done",
        requires_validation=False,
        visible_from=now - timedelta(days=10),
    )

    ActionPlanExecution.objects.filter(pk=canceled_before_start.pk).update(
        status=EXECUTION_STATUS_CANCELED,
        start_at=now + timedelta(hours=2),
        started_at=None,
        visible_from=now - timedelta(hours=1),
        canceled_at=now,
    )
    ActionPlanExecution.objects.filter(pk=canceled_before_visibility.pk).update(
        status=EXECUTION_STATUS_CANCELED,
        start_at=now + timedelta(hours=2),
        started_at=None,
        visible_from=now + timedelta(hours=1),
        canceled_at=now,
    )
    ActionPlanExecution.objects.filter(pk=started_but_not_visible.pk).update(
        status=EXECUTION_STATUS_CANCELED,
        started_at=now - timedelta(hours=1),
        canceled_at=now,
    )
    ActionPlanExecution.objects.filter(pk=operational_then_canceled.pk).update(
        status=EXECUTION_STATUS_CANCELED,
        started_at=now - timedelta(hours=48),
        canceled_at=now - timedelta(hours=47),
    )
    ActionPlanExecution.objects.filter(pk=operational_then_done.pk).update(
        status=EXECUTION_STATUS_DONE,
        started_at=now - timedelta(days=10),
        marked_done_at=now - timedelta(days=9),
    )

    visible = _visible_ids(owner_membership, now=now)

    assert canceled_before_start.id not in visible
    assert canceled_before_visibility.id not in visible
    assert started_but_not_visible.id not in visible
    assert operational_then_canceled.id in visible
    assert operational_then_done.id in visible


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


def test_terminal_category_counts_cover_the_retention_window_only(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done retained",
        status=EXECUTION_STATUS_DONE,
    )
    expired = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done expired",
        status=EXECUTION_STATUS_DONE,
    )
    canceled = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Canceled retained",
        status=EXECUTION_STATUS_CANCELED,
    )
    ActionPlanExecution.objects.filter(pk=done.pk).update(
        validated_at=now - timedelta(days=1),
    )
    ActionPlanExecution.objects.filter(pk=expired.pk).update(
        validated_at=now - timedelta(days=11),
    )
    ActionPlanExecution.objects.filter(pk=canceled.pk).update(
        canceled_at=now - timedelta(hours=1),
    )
    from houston.testing.auth import auth_headers, login

    token = login(api_client, user=owner_membership.user)
    filtered = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + "?view_mode=general&category=done",
        **auth_headers(token),
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert feed_execution_ids(body) == [str(done.id)]
    assert body["section_counts"]["done"] == 1
    assert body["section_counts"]["canceled"] == 1
    assert body["section_counts"]["in_progress"] == 0
