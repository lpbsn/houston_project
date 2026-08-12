from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.analytics.comparisons import get_analytics_kpi_comparison
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


def dashboard_url(query: str = "") -> str:
    return f"/api/v1/analytics/dashboard/{query}"


def pattern_list_url(query: str = "") -> str:
    return f"/api/v1/analytics/patterns/{query}"


def pattern_filter_options_url(query: str = "") -> str:
    return f"/api/v1/analytics/pattern-filter-options/{query}"


def pattern_detail_url(pattern_id, query: str = "") -> str:
    return f"/api/v1/analytics/patterns/{pattern_id}/{query}"


def pattern_signals_url(pattern_id, query: str = "") -> str:
    return f"/api/v1/analytics/patterns/{pattern_id}/signals/{query}"


def period_query(start, end) -> str:
    return "?" + urlencode(
        {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        }
    )


def create_pattern(membership, *, label="Pattern"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def create_signal(
    membership,
    *,
    title="Signal",
    status=Signal.Status.OPEN,
    created_at=None,
    resolved_at=None,
):
    signal = Signal.objects.create(
        establishment=membership.establishment,
        status=status,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary=f"Summary for {title}.",
        issue_focus=title.lower().replace(" ", "-"),
        last_activity_at=created_at or timezone.now(),
        resolved_at=resolved_at,
    )
    if created_at is not None:
        Signal.objects.filter(pk=signal.pk).update(created_at=created_at)
        signal.refresh_from_db()
    return signal


def assign_signal(signal, pattern):
    return SignalPatternAssignment.objects.create(
        signal=signal,
        pattern=pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature=f"sig-{signal.id}",
        assigned_classifier_version="classifier-v1",
        assigned_at=timezone.now(),
    )


def authenticated_get(api_client, user, url: str):
    token = login(api_client, user=user)
    return api_client.get(url, **auth_headers(token))


def test_dashboard_requires_authentication(api_client):
    start = timezone.now()
    end = start + timedelta(days=7)

    response = api_client.get(dashboard_url(period_query(start, end)))

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_staff_only_is_forbidden_instead_of_empty_analytics(api_client):
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    start = timezone.now()
    end = start + timedelta(days=7)

    response = authenticated_get(api_client, staff.user, dashboard_url(period_query(start, end)))

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


@pytest.mark.parametrize(
    "role",
    [
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
    ],
)
def test_analytics_roles_can_access_dashboard(api_client, role):
    membership = build_api_membership(role=role)
    start = timezone.now()
    end = start + timedelta(days=7)

    response = authenticated_get(
        api_client,
        membership.user,
        dashboard_url(period_query(start, end)),
    )

    assert response.status_code == 200
    assert response.json()["current_kpis"]["analytics_signal_population_count"] == 0


def test_staff_current_membership_does_not_block_other_analytics_membership(api_client):
    user = create_user(username="staff-plus-manager")
    staff_establishment = create_establishment(name="Staff site")
    manager_establishment = create_establishment(name="Manager site")
    create_membership(
        establishment=staff_establishment,
        user=user,
        role=EstablishmentMembership.Role.STAFF,
    )
    manager = create_membership(
        establishment=manager_establishment,
        user=user,
        role=EstablishmentMembership.Role.MANAGER,
    )
    pattern = create_pattern(manager, label="Manager scoped")
    start = timezone.now()
    end = start + timedelta(days=1)
    signal = create_signal(
        manager,
        title="Unassigned manager signal",
        created_at=start + timedelta(hours=1),
    )
    signal.routing_status = Signal.RoutingStatus.UNASSIGNED
    signal.save(update_fields=["routing_status", "updated_at"])
    assign_signal(signal, pattern)

    response = authenticated_get(api_client, user, pattern_list_url(period_query(start, end)))

    assert response.status_code == 200
    assert response.json()["items"][0]["pattern_id"] == str(pattern.id)


def test_naive_period_is_rejected_before_drf_timezone_conversion(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    query = "?period_start=2026-01-01T00:00:00&period_end=2026-01-08T00:00:00Z"

    response = authenticated_get(api_client, owner.user, dashboard_url(query))

    assert response.status_code == 400
    assert response.json()["code"] == "analytics_period_start_naive"


@pytest.mark.parametrize(
    "invalid_period_start",
    [
        "2026-13-01T00:00:00Z",
        "2026-01-01T00:00:00+99:99",
    ],
)
def test_invalid_iso_period_datetime_returns_validation_error(api_client, invalid_period_start):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    query = "?" + urlencode(
        {
            "period_start": invalid_period_start,
            "period_end": "2026-01-08T00:00:00Z",
        }
    )

    response = authenticated_get(api_client, owner.user, dashboard_url(query))

    assert response.status_code == 400
    assert response.json()["code"] == "analytics_period_invalid"


def test_pattern_detail_masks_invisible_pattern_for_authorized_user(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner)
    start = timezone.now()
    end = start + timedelta(days=1)
    signal = create_signal(owner, created_at=start + timedelta(hours=1))
    assign_signal(signal, pattern)

    response = authenticated_get(
        api_client,
        outsider.user,
        pattern_detail_url(pattern.id, period_query(start, end)),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "analytics_pattern_not_found"


def test_pattern_list_validation_errors_use_read_api_mapping(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=1)

    page_size_response = authenticated_get(
        api_client,
        owner.user,
        pattern_list_url(f"{period_query(start, end)}&page_size=999"),
    )
    cursor_response = authenticated_get(
        api_client,
        owner.user,
        pattern_list_url(f"{period_query(start, end)}&cursor=not-a-cursor"),
    )

    assert page_size_response.status_code == 400
    assert page_size_response.json()["code"] == "analytics_pattern_list_page_size_invalid"
    assert cursor_response.status_code == 400
    assert cursor_response.json()["code"] == "analytics_pattern_list_cursor_invalid"


@pytest.mark.parametrize("status_filter", ["canceled", "merged_into", "open,invalid"])
def test_pattern_list_rejects_invalid_status_filters(api_client, status_filter):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=1)

    response = authenticated_get(
        api_client,
        owner.user,
        pattern_list_url(f"{period_query(start, end)}&signal_statuses={status_filter}"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "analytics_pattern_list_filter_invalid"


def test_pattern_filter_options_returns_accessible_zero_result_options(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=owner.user)

    response = api_client.get(pattern_filter_options_url(), **auth_headers(token))

    assert response.status_code == 200
    assert response.json()["establishments"] == [
        {
            "establishment_id": str(owner.establishment_id),
            "name": owner.establishment.name,
        }
    ]


def test_pattern_signals_validation_errors_use_read_api_mapping(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner)
    start = timezone.now()
    end = start + timedelta(days=1)
    signal = create_signal(owner, created_at=start + timedelta(hours=1))
    assign_signal(signal, pattern)

    page_size_response = authenticated_get(
        api_client,
        owner.user,
        pattern_signals_url(pattern.id, f"{period_query(start, end)}&page_size=999"),
    )
    cursor_response = authenticated_get(
        api_client,
        owner.user,
        pattern_signals_url(pattern.id, f"{period_query(start, end)}&cursor=not-a-cursor"),
    )

    assert page_size_response.status_code == 400
    assert page_size_response.json()["code"] == "analytics_pattern_signals_page_size_invalid"
    assert cursor_response.status_code == 400
    assert cursor_response.json()["code"] == "analytics_pattern_signals_cursor_invalid"


def test_dashboard_response_matches_backend_primitive(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Water leak")
    start = timezone.now()
    end = start + timedelta(days=7)
    signal = create_signal(owner, title="Current", created_at=start + timedelta(days=1))
    assign_signal(signal, pattern)
    expected = get_analytics_kpi_comparison(
        owner.user,
        period_start=start,
        period_end=end,
    )

    response = authenticated_get(api_client, owner.user, dashboard_url(period_query(start, end)))
    body = response.json()

    assert response.status_code == 200
    assert (
        body["current_kpis"]["analytics_signal_population_count"]
        == expected.current_kpis.analytics_signal_population_count
    )
    assert body["current_kpis"]["signals_analyzed_count"] == (
        expected.current_kpis.signals_analyzed_count
    )
    assert body["signals_analyzed_count"]["absolute_delta"] == (
        expected.signals_analyzed_count.absolute_delta
    )


def test_pattern_list_detail_and_signals_payloads_are_allowlisted(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Water leak")
    start = timezone.now()
    end = start + timedelta(days=1)
    signal = create_signal(owner, title="Visible", created_at=start + timedelta(hours=1))
    assign_signal(signal, pattern)
    token = login(api_client, user=owner.user)

    list_response = api_client.get(
        pattern_list_url(period_query(start, end)),
        **auth_headers(token),
    )
    detail_response = api_client.get(
        pattern_detail_url(pattern.id, period_query(start, end)),
        **auth_headers(token),
    )
    signals_response = api_client.get(
        pattern_signals_url(pattern.id, period_query(start, end)),
        **auth_headers(token),
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert signals_response.status_code == 200
    assert list_response.json()["items"][0]["pattern_id"] == str(pattern.id)
    assert detail_response.json()["identity"]["pattern_id"] == str(pattern.id)
    signal_item = signals_response.json()["items"][0]
    assert set(signal_item) == {
        "signal_id",
        "title",
        "structured_summary",
        "status",
        "created_at",
        "resolved_at",
        "establishment",
        "responsible_business_unit",
    }
    assert signal_item["signal_id"] == str(signal.id)
    assert "assignment_source" not in signal_item
    assert "routing_key" not in signal_item
    assert "raw_text" not in str(signals_response.json())
