from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_user
from houston.testing.platform import grant_operator

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def test_functional_status_query_param_is_not_a_list_filter(api_client):
    operator = create_user(username="plat_list_fs_op")
    grant_operator(operator)
    token = login(api_client, user=operator)

    draft = api_client.post(
        "/api/v1/platform/onboardings/",
        {"organization_name": "List Draft Org", "establishment_name": "List Draft Site"},
        format="json",
        **auth_headers(token),
    )
    active = api_client.post(
        "/api/v1/platform/onboardings/",
        {"organization_name": "List Active Org", "establishment_name": "List Active Site"},
        format="json",
        **auth_headers(token),
    )
    assert draft.status_code == 201
    assert active.status_code == 201
    Establishment.objects.filter(pk=active.json()["establishment_id"]).update(
        status=Establishment.Status.ACTIVE
    )

    unfiltered = api_client.get(
        "/api/v1/platform/establishments/",
        **auth_headers(token),
    )
    pretended = api_client.get(
        "/api/v1/platform/establishments/?functional_status=activated",
        **auth_headers(token),
    )
    onboardings_unfiltered = api_client.get(
        "/api/v1/platform/onboardings/",
        **auth_headers(token),
    )
    onboardings_pretended = api_client.get(
        "/api/v1/platform/onboardings/?functional_status=activated",
        **auth_headers(token),
    )
    assert unfiltered.status_code == 200
    assert pretended.status_code == 200
    assert {item["id"] for item in unfiltered.json()["results"]} == {
        item["id"] for item in pretended.json()["results"]
    }
    assert {item["id"] for item in onboardings_unfiltered.json()["results"]} == {
        item["id"] for item in onboardings_pretended.json()["results"]
    }
    statuses = {
        item["id"]: item["onboarding"]["functional_status"]
        for item in unfiltered.json()["results"]
        if item["id"] in {draft.json()["establishment_id"], active.json()["establishment_id"]}
    }
    assert statuses[draft.json()["establishment_id"]] != statuses[active.json()["establishment_id"]]


def test_remaining_list_filters_apply_on_queryset_before_page(api_client):
    operator = create_user(username="plat_list_q_op")
    grant_operator(operator)
    token = login(api_client, user=operator)
    Organization.objects.create(name="Alpha Filter Org", status=Organization.Status.ACTIVE)
    Organization.objects.create(name="Beta Filter Org", status=Organization.Status.SUSPENDED)
    Organization.objects.create(name="Gamma Other Org", status=Organization.Status.ACTIVE)

    named = api_client.get(
        "/api/v1/platform/organizations/?q=Alpha%20Filter",
        **auth_headers(token),
    )
    assert named.status_code == 200
    names = [item["name"] for item in named.json()["results"]]
    assert names == ["Alpha Filter Org"]

    suspended = api_client.get(
        "/api/v1/platform/organizations/?status=suspended",
        **auth_headers(token),
    )
    assert suspended.status_code == 200
    assert {item["name"] for item in suspended.json()["results"]} == {"Beta Filter Org"}

    membership = EstablishmentMembership.objects.create(
        user=create_user(username="listed_member"),
        establishment=Establishment.objects.create(
            name="Filter Site",
            organization=Organization.objects.get(name="Alpha Filter Org"),
            status=Establishment.Status.DRAFT,
        ),
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.INVITED,
    )
    by_role = api_client.get(
        f"/api/v1/platform/memberships/?role={EstablishmentMembership.Role.STAFF}&status=invited",
        **auth_headers(token),
    )
    assert by_role.status_code == 200
    assert [item["id"] for item in by_role.json()["results"]] == [str(membership.id)]
