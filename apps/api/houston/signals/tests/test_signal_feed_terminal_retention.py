from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.signals.feed_filters import SignalFeedFilters
from houston.signals.models import Signal
from houston.signals.selectors import (
    cross_signal_feed_queryset,
    signal_feed_list_queryset,
    signal_feed_queryset,
)
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    login,
    signal_feed_url,
)
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.testing.signal_feed import flatten_signal_feed_items
from houston.testing.taxonomy import create_restaurant_v3_taxonomy, create_signal_v3_for_membership

pytestmark = pytest.mark.django_db


def _ids(membership, *, view_mode: str, now=None, statuses: str | None = None):
    filters = None if statuses is None else SignalFeedFilters(statuses=(statuses,))
    queryset = signal_feed_list_queryset(
        signal_feed_queryset(membership=membership, view_mode=view_mode, now=now, filters=filters),
        filters=filters,
    )
    return set(queryset.values_list("id", flat=True))


def test_resolved_and_canceled_signals_follow_the_retention_boundary():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    resolved = create_minimal_v3_signal(membership, title="Resolved", status=Signal.Status.RESOLVED)
    canceled = create_minimal_v3_signal(membership, title="Canceled", status=Signal.Status.CANCELED)
    resolved_edge = create_minimal_v3_signal(
        membership,
        title="Resolved edge",
        status=Signal.Status.RESOLVED,
    )
    canceled_edge = create_minimal_v3_signal(
        membership,
        title="Canceled edge",
        status=Signal.Status.CANCELED,
    )
    resolved_missing = create_minimal_v3_signal(
        membership,
        title="Resolved undated",
        status=Signal.Status.RESOLVED,
    )
    canceled_missing = create_minimal_v3_signal(
        membership,
        title="Canceled undated",
        status=Signal.Status.CANCELED,
    )
    Signal.objects.filter(pk=resolved.pk).update(
        resolved_at=now - timedelta(days=10, microseconds=-1),
    )
    Signal.objects.filter(pk=canceled.pk).update(
        canceled_at=now - timedelta(hours=48, microseconds=-1),
    )
    Signal.objects.filter(pk=resolved_edge.pk).update(resolved_at=now - timedelta(days=10))
    Signal.objects.filter(pk=canceled_edge.pk).update(canceled_at=now - timedelta(hours=48))

    visible = _ids(membership, view_mode="general", now=now)

    assert resolved.id in visible
    assert canceled.id in visible
    assert resolved_edge.id not in visible
    assert canceled_edge.id not in visible
    assert resolved_missing.id not in visible
    assert canceled_missing.id not in visible


def test_status_filter_excludes_retained_terminals():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    resolved = create_minimal_v3_signal(membership, title="Resolved", status=Signal.Status.RESOLVED)
    Signal.objects.filter(pk=resolved.pk).update(resolved_at=now - timedelta(hours=1))

    assert resolved.id in _ids(membership, view_mode="general", now=now)
    assert resolved.id not in _ids(membership, view_mode="general", now=now, statuses="open")


def test_cross_feed_uses_the_same_retention_window():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    recent = create_minimal_v3_signal(membership, title="Recent", status=Signal.Status.RESOLVED)
    expired = create_minimal_v3_signal(membership, title="Expired", status=Signal.Status.RESOLVED)
    Signal.objects.filter(pk=recent.pk).update(resolved_at=now - timedelta(days=1))
    Signal.objects.filter(pk=expired.pk).update(resolved_at=now - timedelta(days=11))

    visible = set(cross_signal_feed_queryset(memberships=[membership]).values_list("id", flat=True))

    assert recent.id in visible
    assert expired.id not in visible


def test_personal_feed_keeps_scope_on_retained_canceled_signals(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.bar is not None
    assert taxonomy.lighting_subject is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    in_scope = create_signal_v3_for_membership(
        owner,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        status=Signal.Status.CANCELED,
        title="In scope",
    )
    out_of_scope = create_signal_v3_for_membership(
        owner,
        affected_business_unit=taxonomy.bar,
        responsible_business_unit=taxonomy.bar,
        activity_subject=taxonomy.lighting_subject,
        status=Signal.Status.CANCELED,
        title="Out of scope",
    )
    canceled_at = timezone.now() - timedelta(hours=2)
    Signal.objects.filter(pk__in=[in_scope.pk, out_of_scope.pk]).update(canceled_at=canceled_at)
    token = login(api_client, user=manager.user)

    response = api_client.get(
        signal_feed_url(owner.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert response.status_code == 200
    feed_ids = {item["id"] for item in flatten_signal_feed_items(response.json())}
    assert str(in_scope.id) in feed_ids
    assert str(out_of_scope.id) not in feed_ids
