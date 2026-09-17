from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.lifecycle_events import record_execution_lifecycle_event
from houston.action_plans.models import ActionPlan, ActionPlanExecution, ActionPlanExecutionReview
from houston.analytics.cutover import apply_analytics_history_cutover, reset_history_reliable_from
from houston.analytics.dashboard import (
    DESTINATION_ACTION_PLAN_IN_PROGRESS,
    DESTINATION_CANCELED,
    DESTINATION_INTERESTING,
    DESTINATION_KEYS,
    DESTINATION_RESOLVED_DIRECT,
    DESTINATION_RESOLVED_VIA_ACTION_PLAN,
    DESTINATION_RESOLVED_VIA_RESOLUTION_REQUEST,
    DESTINATION_WAITING,
    get_analytics_dashboard,
    list_analytics_dashboard_rankings,
)
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.services import create_operational_pattern
from houston.establishments.models import EstablishmentMembership
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    SIGNAL_LIFECYCLE_EVENT_CANCELED,
    SIGNAL_LIFECYCLE_EVENT_CREATED,
    SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
    SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
    SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN,
    SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST,
)
from houston.signals.lifecycle_events import record_signal_lifecycle_event
from houston.signals.models import Signal
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _dashboard(membership, *, now, period_days=7):
    return get_analytics_dashboard(
        membership.user,
        period_days=period_days,
        now=now,
        establishment_id=membership.establishment_id,
    )


def _create_signal(membership, *, title, created_at, status=Signal.Status.OPEN):
    signal = Signal.objects.create(
        establishment=membership.establishment,
        status=status,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary=f"Summary for {title}.",
        issue_focus=title.lower().replace(" ", "-"),
        last_activity_at=created_at,
    )
    Signal.objects.filter(pk=signal.pk).update(created_at=created_at)
    signal.refresh_from_db()
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_CREATED,
        occurred_at=created_at,
        metadata_safe={"to_status": Signal.Status.OPEN},
    )
    return signal


def _event(signal, event_type, occurred_at, **metadata):
    record_signal_lifecycle_event(
        signal=signal,
        event_type=event_type,
        occurred_at=occurred_at,
        metadata_safe=metadata,
    )


def test_destinations_seven_keys_include_waiting_exclude_archived_and_pinned():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    apply_analytics_history_cutover(now=now - timedelta(days=30))
    created = now - timedelta(days=1)
    _create_signal(membership, title="Waiting", created_at=created)
    interesting = _create_signal(
        membership, title="Interesting", created_at=created, status=Signal.Status.INTERESTING
    )
    _event(
        interesting,
        SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
        created + timedelta(hours=1),
        to_status=Signal.Status.INTERESTING,
    )
    in_progress = _create_signal(
        membership, title="In progress", created_at=created, status=Signal.Status.IN_PROGRESS
    )
    _event(
        in_progress,
        SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
        created + timedelta(hours=2),
        to_status=Signal.Status.IN_PROGRESS,
    )
    direct = _create_signal(
        membership, title="Direct", created_at=created, status=Signal.Status.RESOLVED
    )
    _event(
        direct,
        SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        created + timedelta(hours=3),
        to_status=Signal.Status.RESOLVED,
        resolution_origin=SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    )
    via_plan = _create_signal(
        membership, title="Via plan", created_at=created, status=Signal.Status.RESOLVED
    )
    _event(
        via_plan,
        SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        created + timedelta(hours=3),
        to_status=Signal.Status.RESOLVED,
        resolution_origin=SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN,
    )
    via_request = _create_signal(
        membership, title="Via request", created_at=created, status=Signal.Status.RESOLVED
    )
    _event(
        via_request,
        SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        created + timedelta(hours=3),
        to_status=Signal.Status.RESOLVED,
        resolution_origin=SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST,
    )
    canceled = _create_signal(
        membership, title="Canceled", created_at=created, status=Signal.Status.CANCELED
    )
    _event(
        canceled,
        SIGNAL_LIFECYCLE_EVENT_CANCELED,
        created + timedelta(hours=4),
        to_status=Signal.Status.CANCELED,
    )
    archived = _create_signal(
        membership, title="Archived", created_at=created, status=Signal.Status.ARCHIVED
    )
    _event(
        archived,
        SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
        created + timedelta(hours=5),
        to_status=Signal.Status.ARCHIVED,
    )

    result = _dashboard(membership, now=now)
    destinations = result.observation_destinations
    assert tuple(destinations) == DESTINATION_KEYS
    assert "archived" not in destinations
    assert "pinned" not in destinations
    assert destinations[DESTINATION_WAITING].count == 1
    assert destinations[DESTINATION_INTERESTING].count == 1
    assert destinations[DESTINATION_ACTION_PLAN_IN_PROGRESS].count == 1
    assert destinations[DESTINATION_RESOLVED_DIRECT].count == 1
    assert destinations[DESTINATION_RESOLVED_VIA_ACTION_PLAN].count == 1
    assert destinations[DESTINATION_RESOLVED_VIA_RESOLUTION_REQUEST].count == 1
    assert destinations[DESTINATION_CANCELED].count == 1
    total_share = sum(item.share or 0 for item in destinations.values())
    assert round(total_share, 6) == 1.0
    assert DESTINATION_WAITING not in result.observation_destination_delays


def test_resolved_direct_after_canceled_plan_and_historical_period_keeps_origin():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    reset_history_reliable_from(now=now - timedelta(days=40))
    created = now - timedelta(days=10)
    resolved_at = created + timedelta(hours=3)
    period_a_end = resolved_at + timedelta(hours=1)
    signal = _create_signal(
        membership, title="Direct after cancel", created_at=created, status=Signal.Status.RESOLVED
    )
    _event(
        signal,
        SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
        created + timedelta(hours=1),
        to_status=Signal.Status.IN_PROGRESS,
    )
    _event(
        signal,
        SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
        created + timedelta(hours=2),
        to_status=Signal.Status.OPEN,
    )
    _event(
        signal,
        SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        created + timedelta(hours=3),
        to_status=Signal.Status.RESOLVED,
        resolution_origin=SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    )
    _event(
        signal,
        SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
        now - timedelta(days=2),
        to_status=Signal.Status.OPEN,
    )
    _event(
        signal,
        SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
        now - timedelta(days=1),
        to_status=Signal.Status.IN_PROGRESS,
    )
    Signal.objects.filter(pk=signal.pk).update(status=Signal.Status.IN_PROGRESS)
    result = get_analytics_dashboard(
        membership.user,
        period_days=7,
        now=period_a_end,
        establishment_id=membership.establishment_id,
    )
    assert result.observation_destinations[DESTINATION_RESOLVED_DIRECT].count == 1
    assert result.observation_destinations[DESTINATION_ACTION_PLAN_IN_PROGRESS].count == 0


def test_in_progress_delay_uses_second_cycle_not_first_plan():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    apply_analytics_history_cutover(now=now - timedelta(days=30))
    created = now - timedelta(days=2)
    signal = _create_signal(
        membership, title="Second cycle", created_at=created, status=Signal.Status.IN_PROGRESS
    )
    first_plan = created + timedelta(hours=2)
    reopen = created + timedelta(hours=4)
    second_plan = created + timedelta(hours=10)
    _event(
        signal,
        SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
        first_plan,
        to_status=Signal.Status.IN_PROGRESS,
    )
    _event(
        signal,
        SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
        reopen,
        to_status=Signal.Status.OPEN,
    )
    _event(
        signal,
        SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
        second_plan,
        to_status=Signal.Status.IN_PROGRESS,
    )
    signal.first_action_plan_associated_at = first_plan
    signal.save(update_fields=["first_action_plan_associated_at", "updated_at"])
    result = _dashboard(membership, now=now)
    delay = result.observation_destination_delays[DESTINATION_ACTION_PLAN_IN_PROGRESS]
    assert delay.n == 1
    assert delay.mean_seconds == pytest.approx((second_plan - created).total_seconds())


def test_deadline_uses_marked_done_snapshot_and_excludes_missing_start_at():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    apply_analytics_history_cutover(now=now - timedelta(days=30))
    bu = create_business_unit(establishment=membership.establishment, key="salle")
    plan = ActionPlan.objects.create(
        establishment=membership.establishment,
        created_by=membership,
        title="Deadline plan",
        pilot_business_unit=bu,
        affected_business_unit=bu,
        responsible_business_unit=bu,
    )
    start_at = now - timedelta(hours=10)
    end_at = now - timedelta(hours=2)
    finished = now - timedelta(hours=1, minutes=1)
    execution = ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        title="Snapshot late",
        status=EXECUTION_STATUS_DONE,
        start_at=now - timedelta(hours=20),
        end_at=now + timedelta(hours=5),
        marked_done_at=finished,
        last_activity_at=finished,
        use_shared_chronology=True,
        requires_validation=False,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        pilot_business_unit=bu,
    )
    record_execution_lifecycle_event(
        execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
        occurred_at=finished,
        metadata_safe={
            "to_status": EXECUTION_STATUS_DONE,
            "start_at": start_at,
            "end_at": end_at,
        },
    )
    missing = ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        title="Missing start",
        status=EXECUTION_STATUS_DONE,
        start_at=start_at,
        end_at=end_at,
        marked_done_at=finished,
        last_activity_at=finished,
        use_shared_chronology=True,
        requires_validation=False,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        pilot_business_unit=bu,
    )
    record_execution_lifecycle_event(
        execution=missing,
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
        occurred_at=finished,
        metadata_safe={"to_status": EXECUTION_STATUS_DONE, "end_at": end_at},
    )
    result = _dashboard(membership, now=now)
    deadlines = result.plan_deadline_respect
    assert deadlines.n == 1
    assert deadlines.late_count == 1
    assert deadlines.excluded_count == 1


def test_current_overrun_excludes_pending_validation_and_measures_133_percent():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    apply_analytics_history_cutover(now=now - timedelta(days=30))
    bu = create_business_unit(establishment=membership.establishment, key="cuisine")
    plan = ActionPlan.objects.create(
        establishment=membership.establishment,
        created_by=membership,
        title="Overrun plan",
        pilot_business_unit=bu,
        affected_business_unit=bu,
        responsible_business_unit=bu,
    )
    ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        title="Four hours late on three",
        status=EXECUTION_STATUS_IN_PROGRESS,
        start_at=now - timedelta(hours=7),
        end_at=now - timedelta(hours=4),
        last_activity_at=now,
        use_shared_chronology=True,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        pilot_business_unit=bu,
    )
    ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        title="Pending validation ignored",
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        start_at=now - timedelta(hours=7),
        end_at=now - timedelta(hours=4),
        last_activity_at=now,
        use_shared_chronology=True,
        requires_validation=True,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        pilot_business_unit=bu,
    )
    ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        title="Scheduled late",
        status=EXECUTION_STATUS_SCHEDULED,
        start_at=now - timedelta(hours=7),
        end_at=now - timedelta(hours=4),
        last_activity_at=now,
        use_shared_chronology=True,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        pilot_business_unit=bu,
    )
    result = _dashboard(membership, now=now)
    buckets = {bucket.key: bucket.count for bucket in result.plan_overrun}
    assert buckets["gte_100"] == 2
    assert sum(buckets.values()) == 2


def test_resolution_quality_includes_zero_stars():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    apply_analytics_history_cutover(now=now - timedelta(days=30))
    bu = create_business_unit(establishment=membership.establishment, key="bar")
    plan = ActionPlan.objects.create(
        establishment=membership.establishment,
        created_by=membership,
        title="Quality plan",
        pilot_business_unit=bu,
        affected_business_unit=bu,
        responsible_business_unit=bu,
    )
    execution = ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        title="Reviewed",
        status=EXECUTION_STATUS_DONE,
        last_activity_at=now,
        use_shared_chronology=True,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        pilot_business_unit=bu,
    )
    ActionPlanExecutionReview.objects.create(
        action_plan_execution=execution,
        reviewer_membership=membership,
        stars=0,
        reviewed_at=now - timedelta(hours=1),
        is_active=True,
    )
    result = _dashboard(membership, now=now)
    zero = next(bucket for bucket in result.resolution_quality if bucket.stars == 0)
    assert zero.count == 1
    assert zero.share == 1.0


def test_rankings_paginate_all_locations(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    apply_analytics_history_cutover(now=now - timedelta(days=30))
    for index in range(7):
        signal = _create_signal(
            membership,
            title=f"Place {index}",
            created_at=now - timedelta(hours=index + 1),
        )
        Signal.objects.filter(pk=signal.pk).update(location_text=f"Lieu {index}")
    first = list_analytics_dashboard_rankings(
        membership.user,
        establishment_id=membership.establishment_id,
        kind="locations",
        period_days=7,
        page_size=3,
        now=now,
    )
    assert first.total_count == 7
    assert len(first.items) == 3
    assert first.has_more is True
    second = list_analytics_dashboard_rankings(
        membership.user,
        establishment_id=membership.establishment_id,
        kind="locations",
        period_days=7,
        page_size=3,
        cursor=first.next_cursor,
        now=now,
    )
    third = list_analytics_dashboard_rankings(
        membership.user,
        establishment_id=membership.establishment_id,
        kind="locations",
        period_days=7,
        page_size=3,
        cursor=second.next_cursor,
        now=now,
    )
    names = [item.name for item in (*first.items, *second.items, *third.items)]
    assert len(names) == 7
    assert third.has_more is False
    token = login(api_client, user=membership.user)
    query = urlencode(
        {
            "establishment_id": str(membership.establishment_id),
            "kind": "locations",
            "page_size": 3,
            "period_days": 7,
        }
    )
    response = api_client.get(
        f"/api/v1/analytics/dashboard/rankings/?{query}",
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["total_count"] == 7


def test_recurring_preview_is_five_with_total_count():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    apply_analytics_history_cutover(now=now - timedelta(days=30))
    for index in range(6):
        pattern = create_operational_pattern(
            organization=membership.establishment.organization,
            label=f"Motif {index}",
            created_by_membership=membership,
        )
        for copy in range(2):
            signal = _create_signal(
                membership,
                title=f"Motif {index} {copy}",
                created_at=now - timedelta(hours=index + copy + 1),
            )
            SignalPatternAssignment.objects.create(
                signal=signal,
                pattern=pattern,
                classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
                assigned_signature=f"sig-{signal.id}",
                assigned_classifier_version="classifier-v1",
                assigned_at=signal.created_at,
            )
    result = _dashboard(membership, now=now)
    assert result.recurring_patterns.total_count == 6
    assert len(result.recurring_patterns.items) == 5
    assert result.recurring_patterns.items[0].last_seen_at is not None
