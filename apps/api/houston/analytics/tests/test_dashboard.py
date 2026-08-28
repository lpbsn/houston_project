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
from houston.analytics.journal import COVERAGE_COMPLETE
from houston.analytics.models import (
    AnalyticsHistoryCoverage,
    PatternEstablishmentSighting,
    SignalPatternAssignment,
)
from houston.analytics.services import (
    create_operational_pattern,
    mark_assignment_processing,
    mark_assignment_succeeded,
    merge_operational_patterns,
    split_operational_pattern_to_new,
)
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    OperationalUnit,
)
from houston.gamification.constants import CURRENT_RULE_VERSION
from houston.gamification.models import PointTransaction
from houston.gamification.services import open_season
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_CANCELED,
    SIGNAL_LIFECYCLE_EVENT_CREATED,
    SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
)
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


def _create_signal(
    membership,
    *,
    title="Signal",
    created_at=None,
    status=Signal.Status.OPEN,
    operational_unit=None,
    responsible_business_unit=None,
):
    moment = created_at or timezone.now()
    signal = Signal.objects.create(
        establishment=membership.establishment,
        status=status,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary=f"Summary for {title}.",
        issue_focus=title.lower().replace(" ", "-"),
        last_activity_at=moment,
        operational_unit=operational_unit,
        responsible_business_unit=responsible_business_unit,
    )
    if created_at is not None:
        Signal.objects.filter(pk=signal.pk).update(created_at=created_at)
        signal.refresh_from_db()
    return signal


def _cutover_complete_for_period(*, now, period_days=7):
    reliable_from = now - timedelta(days=period_days + 3)
    apply_analytics_history_cutover(now=reliable_from)
    AnalyticsHistoryCoverage.objects.filter(
        singleton_key=AnalyticsHistoryCoverage.SINGLETON_KEY,
    ).update(reliable_from=reliable_from)
    return reliable_from


def _assign(signal, pattern, *, assigned_at=None):
    return SignalPatternAssignment.objects.create(
        signal=signal,
        pattern=pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature=f"sig-{signal.id}",
        assigned_classifier_version="classifier-v1",
        assigned_at=assigned_at or timezone.now(),
    )


def _succeed_assign(signal, pattern, *, assigned_at=None):
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature=f"sig-{signal.id}-{uuid.uuid4()}",
        pending_classifier_version="classifier-v1",
    )
    return mark_assignment_succeeded(
        signal=signal,
        pattern=pattern,
        assigned_signature=processing.pending_signature,
        assigned_classifier_version="classifier-v1",
        expected_attempt_count=processing.attempt_count,
        assigned_at=assigned_at,
    )


def _new_pattern_names(result):
    return {item.name for item in result.new_patterns}


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


def test_pattern_correction_cross_does_not_give_target_source_first_seen():
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
    _assign(signal, pattern_b, assigned_at=now - timedelta(hours=1))

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)
    motif_b = next(item for item in result.new_patterns if item.name == "Motif B")
    assert motif_b.first_seen_at > earlier


def test_cross_new_patterns_use_assignment_not_created_event():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    created_at = now - timedelta(days=20)
    assigned_at = now - timedelta(hours=2)
    pattern = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Backdated create",
        created_by_membership=membership,
        occurred_at=created_at,
    )
    _succeed_assign(
        _create_signal(membership, title="Seen now", created_at=assigned_at),
        pattern,
        assigned_at=assigned_at,
    )

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)
    item = next(row for row in result.new_patterns if row.name == "Backdated create")
    assert item.first_seen_at == assigned_at


def test_cross_new_patterns_use_earlier_assignment_without_sighting():
    user = create_user(username="cross-first-seen")
    first = create_establishment(name="Nord")
    second = Establishment.objects.create(
        name="Sud",
        organization=first.organization,
        status=Establishment.Status.ACTIVE,
    )
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
    earlier = now - timedelta(days=20)
    seen = now - timedelta(days=1)
    pattern = create_operational_pattern(
        organization=first.organization,
        label="Shared motif",
        created_by_membership=membership_a,
        occurred_at=earlier,
    )
    _assign(
        _create_signal(membership_a, title="Old site", created_at=earlier),
        pattern,
        assigned_at=earlier,
    )
    _succeed_assign(
        _create_signal(membership_b, title="New site", created_at=seen),
        pattern,
        assigned_at=seen,
    )
    assert not PatternEstablishmentSighting.objects.filter(
        pattern=pattern,
        establishment=first,
    ).exists()

    cross = get_analytics_dashboard(user, period_days=7, now=now)
    establishment_b = get_analytics_dashboard(
        user,
        period_days=7,
        now=now,
        establishment_id=second.id,
    )
    assert "Shared motif" not in _new_pattern_names(cross)
    item = next(row for row in establishment_b.new_patterns if row.name == "Shared motif")
    assert item.first_seen_at == seen


def test_split_to_new_is_not_listed_as_new_pattern():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    earlier = now - timedelta(days=20)
    source = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Broad source",
        created_by_membership=membership,
        occurred_at=earlier,
    )
    signal = _create_signal(membership, title="Stock", created_at=earlier)
    _succeed_assign(signal, source, assigned_at=earlier)

    split = split_operational_pattern_to_new(
        actor_membership=membership,
        source_pattern=source,
        label="Split pasted",
        signal_ids=[signal.id],
        occurred_at=now - timedelta(hours=1),
    )

    cross = get_analytics_dashboard(membership.user, period_days=7, now=now)
    establishment = get_analytics_dashboard(
        membership.user,
        period_days=7,
        now=now,
        establishment_id=membership.establishment_id,
    )
    assert split.target_pattern is not None
    assert "Split pasted" not in _new_pattern_names(cross)
    assert "Split pasted" not in _new_pattern_names(establishment)


def test_establishment_sighting_write_once_ignores_later_assignment():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    earlier = now - timedelta(days=20)
    later = now - timedelta(hours=1)
    pattern = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Already seen",
        created_by_membership=membership,
        occurred_at=earlier,
    )
    signal = _create_signal(membership, title="Reclassified", created_at=earlier)
    _succeed_assign(signal, pattern, assigned_at=earlier)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature=f"sig-later-{signal.id}",
        pending_classifier_version="classifier-v2",
    )
    mark_assignment_succeeded(
        signal=signal,
        pattern=pattern,
        assigned_signature=processing.pending_signature,
        assigned_classifier_version="classifier-v2",
        expected_attempt_count=processing.attempt_count,
        assigned_at=later,
    )

    result = get_analytics_dashboard(
        membership.user,
        period_days=7,
        now=now,
        establishment_id=membership.establishment_id,
    )
    assert "Already seen" not in _new_pattern_names(result)
    sighting = PatternEstablishmentSighting.objects.get(
        pattern=pattern,
        establishment=membership.establishment,
    )
    assert sighting.observed_at == earlier


def test_pattern_merge_keeps_earliest_sighting_not_merge_clock():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    first_seen = now - timedelta(days=3)
    later_seen = now - timedelta(days=1)
    merge_at = now - timedelta(hours=1)
    source = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Older identity",
        created_by_membership=membership,
        occurred_at=first_seen,
    )
    target = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Newer survivor",
        created_by_membership=membership,
        occurred_at=later_seen,
    )
    _succeed_assign(
        _create_signal(membership, title="From source", created_at=first_seen),
        source,
        assigned_at=first_seen,
    )
    _succeed_assign(
        _create_signal(membership, title="On target", created_at=later_seen),
        target,
        assigned_at=later_seen,
    )
    merge_operational_patterns(
        actor_membership=membership,
        source_pattern=source,
        target_pattern=target,
        occurred_at=merge_at,
    )

    cross = get_analytics_dashboard(membership.user, period_days=7, now=now)
    establishment = get_analytics_dashboard(
        membership.user,
        period_days=7,
        now=now,
        establishment_id=membership.establishment_id,
    )
    for result in (cross, establishment):
        item = next(row for row in result.new_patterns if row.pattern_id == target.id)
        assert item.first_seen_at == first_seen
        assert item.first_seen_at < merge_at
    assert "Older identity" not in _new_pattern_names(cross)


def test_pattern_merge_hides_survivor_when_earliest_sighting_is_outside_period():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    earlier = now - timedelta(days=20)
    source = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Legacy source",
        created_by_membership=membership,
        occurred_at=earlier,
    )
    target = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Born in period",
        created_by_membership=membership,
        occurred_at=now - timedelta(days=1),
    )
    _succeed_assign(
        _create_signal(membership, title="Legacy", created_at=earlier),
        source,
        assigned_at=earlier,
    )
    _succeed_assign(
        _create_signal(membership, title="Fresh", created_at=now - timedelta(days=1)),
        target,
        assigned_at=now - timedelta(days=1),
    )
    merge_operational_patterns(
        actor_membership=membership,
        source_pattern=source,
        target_pattern=target,
        occurred_at=now - timedelta(hours=1),
    )

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)
    assert "Born in period" not in _new_pattern_names(result)


def test_real_pattern_merged_into_split_created_can_appear():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    earlier = now - timedelta(days=20)
    seen = now - timedelta(days=2)
    stock = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Stock to split",
        created_by_membership=membership,
        occurred_at=earlier,
    )
    real = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Real origin",
        created_by_membership=membership,
        occurred_at=seen,
    )
    stock_signal = _create_signal(membership, title="Stock", created_at=earlier)
    real_signal = _create_signal(membership, title="Real", created_at=seen)
    _succeed_assign(stock_signal, stock, assigned_at=earlier)
    _succeed_assign(real_signal, real, assigned_at=seen)
    split = split_operational_pattern_to_new(
        actor_membership=membership,
        source_pattern=stock,
        label="Split vessel",
        signal_ids=[stock_signal.id],
        occurred_at=now - timedelta(hours=2),
    )
    merge_operational_patterns(
        actor_membership=membership,
        source_pattern=real,
        target_pattern=split.target_pattern,
        occurred_at=now - timedelta(hours=1),
    )

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)
    item = next(row for row in result.new_patterns if row.pattern_id == split.target_pattern.id)
    assert item.first_seen_at == seen


def test_real_pattern_outside_period_merged_into_split_created_is_absent():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    earlier = now - timedelta(days=20)
    stock = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Stock to split",
        created_by_membership=membership,
        occurred_at=earlier,
    )
    real = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Real origin outside period",
        created_by_membership=membership,
        occurred_at=earlier,
    )
    stock_signal = _create_signal(membership, title="Stock", created_at=earlier)
    real_signal = _create_signal(membership, title="Real", created_at=earlier)
    _succeed_assign(stock_signal, stock, assigned_at=earlier)
    _succeed_assign(real_signal, real, assigned_at=earlier)
    split = split_operational_pattern_to_new(
        actor_membership=membership,
        source_pattern=stock,
        label="Split vessel",
        signal_ids=[stock_signal.id],
        occurred_at=now - timedelta(hours=2),
    )
    merge_operational_patterns(
        actor_membership=membership,
        source_pattern=real,
        target_pattern=split.target_pattern,
        occurred_at=now - timedelta(hours=1),
    )

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)
    assert split.target_pattern is not None
    assert split.target_pattern.id not in {row.pattern_id for row in result.new_patterns}
    assert "Split vessel" not in _new_pattern_names(result)


def test_split_created_chain_is_not_entirely_split_when_real_origin_is_two_hops():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    earlier = now - timedelta(days=20)
    seen = now - timedelta(days=2)
    stock_b = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Stock B",
        created_by_membership=membership,
        occurred_at=earlier,
    )
    stock_c = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Stock C",
        created_by_membership=membership,
        occurred_at=earlier,
    )
    real = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Real A",
        created_by_membership=membership,
        occurred_at=seen,
    )
    signal_b = _create_signal(membership, title="For B", created_at=earlier)
    signal_c = _create_signal(membership, title="For C", created_at=earlier)
    signal_a = _create_signal(membership, title="Real A", created_at=seen)
    _succeed_assign(signal_b, stock_b, assigned_at=earlier)
    _succeed_assign(signal_c, stock_c, assigned_at=earlier)
    _succeed_assign(signal_a, real, assigned_at=seen)
    split_b = split_operational_pattern_to_new(
        actor_membership=membership,
        source_pattern=stock_b,
        label="Split B",
        signal_ids=[signal_b.id],
        occurred_at=now - timedelta(hours=3),
    )
    merge_operational_patterns(
        actor_membership=membership,
        source_pattern=real,
        target_pattern=split_b.target_pattern,
        occurred_at=now - timedelta(hours=2),
    )
    split_c = split_operational_pattern_to_new(
        actor_membership=membership,
        source_pattern=stock_c,
        label="Split C",
        signal_ids=[signal_c.id],
        occurred_at=now - timedelta(hours=2),
    )
    merge_operational_patterns(
        actor_membership=membership,
        source_pattern=split_b.target_pattern,
        target_pattern=split_c.target_pattern,
        occurred_at=now - timedelta(hours=1),
    )
    real.refresh_from_db()
    split_b.target_pattern.refresh_from_db()
    assert real.merged_into_id == split_b.target_pattern.id
    assert split_b.target_pattern.merged_into_id == split_c.target_pattern.id

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)
    item = next(
        row for row in result.new_patterns if row.pattern_id == split_c.target_pattern.id
    )
    assert item.first_seen_at == seen


def test_recurring_patterns_follow_canonical_after_pattern_merge():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    source = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Source count",
        created_by_membership=membership,
    )
    target = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Survivor count",
        created_by_membership=membership,
    )
    _succeed_assign(
        _create_signal(membership, title="S1", created_at=now - timedelta(days=1)),
        source,
        assigned_at=now - timedelta(days=1),
    )
    _succeed_assign(
        _create_signal(membership, title="S2", created_at=now - timedelta(hours=2)),
        target,
        assigned_at=now - timedelta(hours=2),
    )
    merge_operational_patterns(
        actor_membership=membership,
        source_pattern=source,
        target_pattern=target,
    )

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)
    assert len(result.recurring_patterns) == 1
    assert result.recurring_patterns[0].pattern_id == target.id
    assert result.recurring_patterns[0].name == "Survivor count"
    assert result.recurring_patterns[0].signal_count == 2


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
    cuisine = create_business_unit(
        establishment=membership.establishment,
        key="cuisine",
        label="Cuisine",
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
    )
    zone_a = OperationalUnit.objects.create(
        establishment=membership.establishment,
        key="zone_a",
        label="Zone A",
        active=True,
    )
    zone_b = OperationalUnit.objects.create(
        establishment=membership.establishment,
        key="zone_b",
        label="Zone B",
        active=True,
    )
    source = _create_signal(
        membership,
        title="Older merged source",
        created_at=source_created,
        operational_unit=zone_a,
        responsible_business_unit=cuisine,
    )
    target = _create_signal(
        membership,
        title="Newer survivor",
        created_at=target_created,
        operational_unit=zone_b,
        responsible_business_unit=maintenance,
    )
    resolved_at = now - timedelta(days=4)
    reopened_at = now - timedelta(days=3)
    Signal.objects.filter(pk=source.pk).update(
        first_action_plan_associated_at=plan_at,
        status=Signal.Status.RESOLVED,
        resolved_at=resolved_at,
    )
    source.refresh_from_db()
    record_signal_lifecycle_event(
        signal=source,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=resolved_at,
        metadata_safe={"to_status": Signal.Status.RESOLVED},
    )
    Signal.objects.filter(pk=source.pk).update(
        status=Signal.Status.OPEN,
        resolved_at=None,
    )
    source.refresh_from_db()
    record_signal_lifecycle_event(
        signal=source,
        event_type=SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
        occurred_at=reopened_at,
        metadata_safe={
            "from_status": Signal.Status.RESOLVED,
            "to_status": Signal.Status.OPEN,
        },
    )
    assert source.status == Signal.Status.OPEN
    merge_signal_into_resolved(
        source=source,
        target=target,
        resolution_audit={},
        candidate_expected_action=None,
    )
    target.refresh_from_db()

    result = get_analytics_dashboard(
        membership.user,
        period_days=7,
        now=now,
        establishment_id=membership.establishment_id,
    )

    assert target.created_at == source_created
    assert target.first_action_plan_associated_at == plan_at
    assert result.observation_delay_transformed.n == 1
    assert result.observation_delay_transformed.median_seconds == 24 * 3600
    assert result.open_observation_count == 1
    aging_by_key = {bucket.key: bucket.count for bucket in result.aging_buckets}
    assert aging_by_key["3–7 j"] == 1
    assert aging_by_key["< 3 j"] == 0
    assert {item.name for item in result.poles} == {"Maintenance"}
    assert {item.name for item in result.zones} == {"Zone B"}
    assert result.poles[0].count == 1
    assert result.zones[0].count == 1
    assert result.closure_measured_resolved_count == 0
    assert result.closure_measured_canceled_count == 0


def test_closure_counts_last_journal_terminal_after_reopen_and_resolve():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    _cutover_complete_for_period(now=now)
    signal = _create_signal(
        membership,
        title="Reopened",
        created_at=now - timedelta(days=3),
        status=Signal.Status.RESOLVED,
    )
    first_resolved = now - timedelta(hours=6)
    reopened = now - timedelta(hours=4)
    second_resolved = now - timedelta(hours=1)
    Signal.objects.filter(pk=signal.pk).update(resolved_at=second_resolved)
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=first_resolved,
        metadata_safe={"to_status": Signal.Status.RESOLVED},
    )
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
        occurred_at=reopened,
        metadata_safe={
            "from_status": Signal.Status.RESOLVED,
            "to_status": Signal.Status.OPEN,
        },
    )
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=second_resolved,
        metadata_safe={"to_status": Signal.Status.RESOLVED},
    )

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)

    assert result.closure_measured_resolved_count == 1
    assert result.closure_measured_canceled_count == 0
    assert result.closure_resolved_share.current_value == 1.0


def test_closure_counts_last_journal_terminal_when_resolve_then_cancel():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    _cutover_complete_for_period(now=now)
    signal = _create_signal(
        membership,
        title="Resolved then canceled",
        created_at=now - timedelta(days=2),
        status=Signal.Status.CANCELED,
    )
    resolved_at = now - timedelta(hours=5)
    canceled_at = now - timedelta(hours=1)
    Signal.objects.filter(pk=signal.pk).update(
        resolved_at=resolved_at,
        canceled_at=canceled_at,
    )
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=resolved_at,
        metadata_safe={"to_status": Signal.Status.RESOLVED},
    )
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_CANCELED,
        occurred_at=canceled_at,
        metadata_safe={"to_status": Signal.Status.CANCELED},
    )

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)

    assert result.closure_measured_resolved_count == 0
    assert result.closure_measured_canceled_count == 1
    assert result.closure_resolved_share.current_value == 0.0


def test_complete_window_does_not_count_column_only_closure():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    _cutover_complete_for_period(now=now)
    signal = _create_signal(
        membership,
        title="Column only resolve",
        created_at=now - timedelta(days=2),
        status=Signal.Status.RESOLVED,
    )
    Signal.objects.filter(pk=signal.pk).update(resolved_at=now - timedelta(hours=2))
    signal.refresh_from_db()
    assert not signal.lifecycle_events.filter(
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED
    ).exists()

    result = get_analytics_dashboard(membership.user, period_days=7, now=now)

    assert result.current_period.period_start >= result.history_reliable_from
    assert result.closure_measured_resolved_count == 0
    assert result.closure_measured_canceled_count == 0
    assert result.undatable_signal_terminals.resolved == 0
    assert result.closure_resolved_share.current_value is None


def test_qualify_moves_period_volume_to_current_pole_and_zone():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    _cutover_complete_for_period(now=now)
    cuisine = create_business_unit(
        establishment=membership.establishment,
        key="cuisine",
        label="Cuisine",
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
    )
    zone_a = OperationalUnit.objects.create(
        establishment=membership.establishment,
        key="zone_a",
        label="Zone A",
        active=True,
    )
    zone_b = OperationalUnit.objects.create(
        establishment=membership.establishment,
        key="zone_b",
        label="Zone B",
        active=True,
    )
    current = _create_signal(
        membership,
        title="Requalified current",
        created_at=now - timedelta(days=1),
        operational_unit=zone_a,
        responsible_business_unit=cuisine,
    )
    previous = _create_signal(
        membership,
        title="Requalified previous",
        created_at=now - timedelta(days=10),
        operational_unit=zone_a,
        responsible_business_unit=cuisine,
    )
    Signal.objects.filter(pk__in=[current.pk, previous.pk]).update(
        operational_unit=zone_b,
        responsible_business_unit=maintenance,
    )

    result = get_analytics_dashboard(
        membership.user,
        period_days=7,
        now=now,
        establishment_id=membership.establishment_id,
    )

    assert {item.name for item in result.poles} == {"Maintenance"}
    assert {item.name for item in result.zones} == {"Zone B"}
    assert result.poles[0].count == 1
    assert result.zones[0].count == 1
    assert result.poles[0].comparison.previous_value == 1
    assert result.zones[0].comparison.previous_value == 1
    assert result.poles[0].comparison.coverage == COVERAGE_COMPLETE
    assert result.zones[0].comparison.coverage == COVERAGE_COMPLETE

