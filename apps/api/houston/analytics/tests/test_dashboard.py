from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.analytics.cutover import apply_analytics_history_cutover
from houston.analytics.dashboard import get_analytics_dashboard
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.services import create_operational_pattern
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.factories import create_establishment, create_membership, create_user

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
