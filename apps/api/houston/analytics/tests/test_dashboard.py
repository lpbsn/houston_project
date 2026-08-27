from __future__ import annotations

import uuid
from datetime import timedelta
from urllib.parse import urlencode

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.action_plans.constants import EXECUTION_STATUS_DONE
from houston.action_plans.models import ActionPlanExecution
from houston.analytics.cutover import apply_analytics_history_cutover
from houston.analytics.dashboard import get_analytics_dashboard
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.services import create_operational_pattern
from houston.establishments.models import EstablishmentMembership
from houston.gamification.constants import CURRENT_RULE_VERSION
from houston.gamification.models import PointTransaction
from houston.gamification.services import open_season
from houston.signals.constants import SIGNAL_LIFECYCLE_EVENT_CREATED
from houston.signals.lifecycle_events import record_signal_lifecycle_event
from houston.signals.models import Signal
from houston.signals.services import merge_signal_into_resolved
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.factories import create_establishment, create_membership, create_user
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _create_signal(membership, *, title="Signal", created_at=None, status=Signal.Status.OPEN):
    moment = created_at or timezone.now()
    signal = Signal.objects.create(
        establishment=membership.establishment,
        status=status,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary=f"Summary for {title}.",
        issue_focus=title.lower().replace(" ", "-"),
        last_activity_at=moment,
    )
    if created_at is not None:
        Signal.objects.filter(pk=signal.pk).update(created_at=created_at)
        signal.refresh_from_db()
    return signal


def _assign(signal, pattern, *, assigned_at=None):
    return SignalPatternAssignment.objects.create(
        signal=signal,
        pattern=pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature=f"sig-{signal.id}",
        assigned_classifier_version="classifier-v1",
        assigned_at=assigned_at or timezone.now(),
    )


def test_dashboard_period_days_and_scope_payload():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    apply_analytics_history_cutover()
    now = timezone.now()
    pattern = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Chaîne du froid",
        created_by_membership=membership,
    )
    _assign(_create_signal(membership, title="A", created_at=now - timedelta(days=1)), pattern)
    _assign(_create_signal(membership, title="B", created_at=now - timedelta(hours=2)), pattern)

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)

    assert result.period_days == 7
    assert result.scope_type == "cross"
    assert result.establishment_id is None
    assert membership.establishment_id in result.establishment_ids
    assert result.recurring_patterns[0].signal_count == 2
    assert result.history_reliable_from is not None


def test_dashboard_rejects_invalid_period_and_out_of_scope_establishment(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = create_establishment(name="Other")
    token = login(api_client, user=owner.user)

    invalid = api_client.get(
        "/api/v1/analytics/dashboard/?" + urlencode({"period_days": "14"}),
        **auth_headers(token),
    )
    forbidden = api_client.get(
        "/api/v1/analytics/dashboard/?" + urlencode({"establishment_id": str(outsider.id)}),
        **auth_headers(token),
    )

    assert invalid.status_code == 400
    assert invalid.json()["code"] == "analytics_period_invalid"
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "analytics_scope_forbidden"


def test_dashboard_staff_is_forbidden(api_client):
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    token = login(api_client, user=staff.user)
    response = api_client.get("/api/v1/analytics/dashboard/", **auth_headers(token))
    assert response.status_code == 403


def test_pattern_correction_does_not_give_target_source_first_seen():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    earlier = now - timedelta(days=20)
    create_operational_pattern(
        organization=membership.establishment.organization,
        label="Motif A",
        created_by_membership=membership,
        occurred_at=earlier,
    )
    pattern_b = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Motif B",
        created_by_membership=membership,
        occurred_at=now - timedelta(days=1),
    )
    signal = _create_signal(membership, title="Moved", created_at=earlier)
    assignment = _assign(signal, pattern_b, assigned_at=now - timedelta(hours=1))
    assignment.assigned_at = now - timedelta(hours=1)
    assignment.save(update_fields=["assigned_at", "updated_at"])

    result = get_analytics_dashboard(
        membership.user,
        period_days=7,
        now=now,
        establishment_id=membership.establishment_id,
    )
    names = {item.name for item in result.new_patterns}
    assert "Motif B" in names
    motif_b = next(item for item in result.new_patterns if item.name == "Motif B")
    assert motif_b.first_seen_at > earlier


def test_cross_homonyms_stay_separated_by_establishment():
    user = create_user(username="cross-owner")
    first = create_establishment(name="Nord")
    second = create_establishment(name="Sud")
    membership_a = create_membership(
        establishment=first,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
    )
    membership_b = create_membership(
        establishment=second,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
    )
    now = timezone.now()
    _create_signal(membership_a, title="A", created_at=now - timedelta(hours=1))
    _create_signal(membership_b, title="B", created_at=now - timedelta(hours=1))

    result = get_analytics_dashboard(user, period_days=7, now=now)
    assert result.scope_type == "cross"
    assert set(result.establishment_ids) == {first.id, second.id}
    assert result.open_observation_count == 2


def test_dashboard_deadline_counts_match_n_and_empty_shares_are_null():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    apply_analytics_history_cutover()
    result = get_analytics_dashboard(membership.user, period_days=7)

    deadlines = result.plan_deadlines
    assert deadlines.early_count + deadlines.on_time_count + deadlines.late_count == deadlines.n
    if deadlines.n == 0:
        assert deadlines.early is None
        assert deadlines.on_time is None
        assert deadlines.late is None
        assert deadlines.early_count == 0
        assert deadlines.on_time_count == 0
        assert deadlines.late_count == 0


def _award_points(*, membership, occurred_at):
    season = open_season(membership.establishment)
    tx_id = uuid.uuid4()
    return PointTransaction.objects.create(
        id=tx_id,
        membership=membership,
        establishment=membership.establishment,
        season=season,
        delta=5,
        reason_code="test.award",
        source_type="test",
        source_id=str(tx_id),
        rule_version=CURRENT_RULE_VERSION,
        occurred_at=occurred_at,
        idempotency_key=f"tx:{tx_id}",
    )


def test_cross_contributors_expose_unique_sorted_establishment_names():
    owner = create_user(username="cross-owner-contrib")
    contributor = create_user(username="contributor-nadia")
    anbu = create_establishment(name="ANBU")
    akatsuki = create_establishment(name="AKATSUKI")
    konoha = create_establishment(name="Konoha")
    for establishment in (anbu, akatsuki, konoha):
        create_membership(
            establishment=establishment,
            user=owner,
            role=EstablishmentMembership.Role.OWNER,
        )
    staff_memberships = [
        create_membership(
            establishment=establishment,
            user=contributor,
            role=EstablishmentMembership.Role.STAFF,
        )
        for establishment in (anbu, akatsuki, konoha)
    ]
    now = timezone.now()
    for membership in staff_memberships:
        _award_points(membership=membership, occurred_at=now - timedelta(hours=1))

    result = get_analytics_dashboard(owner, period_days=7, now=now)

    assert result.scope_type == "cross"
    assert len(result.contributors) == 1
    assert result.contributors[0].establishment_names == ("AKATSUKI", "ANBU", "Konoha")


def test_canceled_delay_uses_canonical_timestamp_when_journal_event_is_missing():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    apply_analytics_history_cutover()
    now = timezone.now()
    created_at = now - timedelta(days=2)
    canceled_at = now - timedelta(hours=4)
    signal = _create_signal(
        membership,
        title="Dated cancel",
        created_at=created_at,
        status=Signal.Status.CANCELED,
    )
    Signal.objects.filter(pk=signal.pk).update(canceled_at=canceled_at)

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)

    assert result.observation_delay_canceled.n == 1
    assert result.undatable_signal_terminals.canceled == 0
    assert result.observation_delay_canceled.undatable_in_scope == 0


def test_undatable_canceled_is_counted_and_withholds_closure_share():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    apply_analytics_history_cutover()
    now = timezone.now()
    _create_signal(
        membership,
        title="Legacy cancel",
        created_at=now - timedelta(days=2),
        status=Signal.Status.CANCELED,
    )
    resolved = _create_signal(
        membership,
        title="Dated resolve",
        created_at=now - timedelta(days=3),
        status=Signal.Status.RESOLVED,
    )
    Signal.objects.filter(pk=resolved.pk).update(resolved_at=now - timedelta(hours=2))

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)

    assert result.undatable_signal_terminals.canceled == 1
    assert result.observation_delay_canceled.n == 0
    assert result.observation_delay_canceled.undatable_in_scope == 1
    assert result.closure_measured_resolved_count == 1
    assert result.closure_measured_canceled_count == 0
    assert result.closure_resolved_share.current_value is None


def test_done_execution_without_canonical_timestamps_is_undatable():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    apply_analytics_history_cutover()
    business_unit = create_business_unit(
        establishment=membership.establishment,
        key="analytics_undatable_done",
    )
    ActionPlanExecution.objects.create(
        establishment=membership.establishment,
        created_by=membership,
        title="Undatable done",
        pilot_business_unit=business_unit,
        last_activity_at=timezone.now(),
        use_shared_chronology=True,
        status=EXECUTION_STATUS_DONE,
    )

    result = get_analytics_dashboard(membership.user, period_days=7)

    assert result.undatable_execution_terminals.done == 1
    assert result.plan_delay_resolved.undatable_in_scope == 1
    assert result.plan_delay_resolved.n == 0


def _create_undatable_done_execution(
    membership,
    *,
    title,
    business_unit,
    source_signal=None,
):
    return ActionPlanExecution.objects.create(
        establishment=membership.establishment,
        created_by=membership,
        title=title,
        source_signal=source_signal,
        pilot_business_unit=business_unit,
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
        last_activity_at=timezone.now(),
        use_shared_chronology=True,
        status=EXECUTION_STATUS_DONE,
    )


def test_manager_dashboard_plan_metrics_exclude_out_of_scope_executions():
    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    apply_analytics_history_cutover()
    in_scope_bu = create_business_unit(
        establishment=membership.establishment,
        key="analytics_manager_in_scope",
    )
    out_scope_bu = create_business_unit(
        establishment=membership.establishment,
        key="analytics_manager_out_scope",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=in_scope_bu,
    )
    out_of_scope_signal = Signal.objects.create(
        establishment=membership.establishment,
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title="Out of scope source",
        structured_summary="Summary for out of scope source.",
        issue_focus="out-of-scope-source",
        last_activity_at=timezone.now(),
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    _create_undatable_done_execution(
        membership,
        title="In scope unlinked",
        business_unit=in_scope_bu,
    )
    _create_undatable_done_execution(
        membership,
        title="Out of scope unlinked",
        business_unit=out_scope_bu,
    )
    _create_undatable_done_execution(
        membership,
        title="Linked out of scope signal on in-scope execution BU",
        business_unit=in_scope_bu,
        source_signal=out_of_scope_signal,
    )

    result = get_analytics_dashboard(membership.user, period_days=7)

    assert result.undatable_execution_terminals.done == 1
    assert result.plan_delay_resolved.undatable_in_scope == 1
    assert result.plan_delay_resolved.n == 0


def test_transform_delay_uses_association_field_minus_signal_created_at():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    apply_analytics_history_cutover()
    now = timezone.now()
    created_at = now - timedelta(days=4)
    plan_at = now - timedelta(days=1)
    journal_created = now - timedelta(days=10)
    signal = _create_signal(membership, title="Transform field", created_at=created_at)
    Signal.objects.filter(pk=signal.pk).update(first_action_plan_associated_at=plan_at)
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_CREATED,
        occurred_at=journal_created,
    )

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)

    assert result.observation_delay_transformed.n == 1
    assert result.observation_delay_transformed.median_seconds == 3 * 24 * 3600


def test_transform_delay_excludes_signal_with_live_execution_but_null_association():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    apply_analytics_history_cutover()
    now = timezone.now()
    business_unit = create_business_unit(
        establishment=membership.establishment,
        key="analytics_transform_null_field",
    )
    signal = _create_signal(
        membership,
        title="Legacy execution",
        created_at=now - timedelta(days=2),
    )
    ActionPlanExecution.objects.create(
        establishment=membership.establishment,
        created_by=membership,
        title="Live without stamp",
        source_signal=signal,
        pilot_business_unit=business_unit,
        last_activity_at=now,
        use_shared_chronology=True,
        status=EXECUTION_STATUS_DONE,
    )
    signal.refresh_from_db()
    assert signal.first_action_plan_associated_at is None

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)

    assert result.observation_delay_transformed.n == 0
    assert result.observation_delay_transformed.median_seconds is None


def test_transform_and_aging_after_older_source_merged_into_newer_survivor():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    apply_analytics_history_cutover()
    now = timezone.now()
    source_created = now - timedelta(days=6)
    plan_at = now - timedelta(days=5)
    target_created = now - timedelta(days=1)
    source = _create_signal(
        membership,
        title="Older merged source",
        created_at=source_created,
    )
    target = _create_signal(
        membership,
        title="Newer survivor",
        created_at=target_created,
    )
    Signal.objects.filter(pk=source.pk).update(first_action_plan_associated_at=plan_at)
    source.refresh_from_db()
    merge_signal_into_resolved(
        source=source,
        target=target,
        resolution_audit={},
        candidate_expected_action=None,
    )
    target.refresh_from_db()

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)

    assert target.created_at == source_created
    assert target.first_action_plan_associated_at == plan_at
    assert result.observation_delay_transformed.n == 2
    assert result.observation_delay_transformed.median_seconds == 24 * 3600
    assert result.open_observation_count == 1
    aging_by_key = {bucket.key: bucket.count for bucket in result.aging_buckets}
    assert aging_by_key["3–7 j"] == 1
    assert aging_by_key["< 3 j"] == 0

