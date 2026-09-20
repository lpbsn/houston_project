from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization
from houston.platform.models import PlatformLifecycleEvent
from houston.testing.auth import auth_headers, login
from houston.testing.factories import build_membership, create_user
from houston.testing.platform import grant_operator

pytestmark = pytest.mark.django_db

PLATFORM_PATHS = [
    "/api/v1/platform/session/",
    "/api/v1/platform/organizations/",
    "/api/v1/platform/establishments/",
    "/api/v1/platform/users/",
    "/api/v1/platform/memberships/",
    "/api/v1/platform/onboardings/",
]


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def test_authenticated_non_operator_gets_403_on_every_platform_collection(api_client):
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=membership.user)
    for path in PLATFORM_PATHS:
        response = api_client.get(path, **auth_headers(token))
        assert response.status_code == 403, path


def test_operator_can_start_list_and_delete_abandoned_resources(api_client):
    operator = create_user(username="plat_api_op")
    grant_operator(operator)
    token = login(api_client, user=operator)

    created = api_client.post(
        "/api/v1/platform/onboardings/",
        {"organization_name": "Platform Org", "establishment_name": "Platform Site"},
        format="json",
        **auth_headers(token),
    )
    assert created.status_code == 201
    session_id = created.json()["id"]
    establishment_id = created.json()["establishment_id"]
    organization_id = created.json()["organization_id"]
    assert EstablishmentMembership.objects.filter(user=operator).count() == 0

    listed = api_client.get("/api/v1/platform/organizations/", **auth_headers(token))
    assert listed.status_code == 200
    assert any(item["id"] == organization_id for item in listed.json()["results"])

    deleted_est = api_client.post(
        f"/api/v1/platform/establishments/{establishment_id}/delete/",
        {"justification": "abandoned before activation"},
        format="json",
        **auth_headers(token),
    )
    assert deleted_est.status_code == 204
    assert not Establishment.objects.filter(pk=establishment_id).exists()
    assert Organization.objects.filter(pk=organization_id).exists()

    deleted_org = api_client.post(
        f"/api/v1/platform/organizations/{organization_id}/delete/",
        {"justification": "empty never operational"},
        format="json",
        **auth_headers(token),
    )
    assert deleted_org.status_code == 204
    assert not Organization.objects.filter(pk=organization_id).exists()
    assert PlatformLifecycleEvent.objects.filter(
        action="delete_organization",
        result=PlatformLifecycleEvent.Result.OK,
    ).exists()
    assert not EstablishmentMembership.objects.filter(user=operator).exists()
    assert session_id
