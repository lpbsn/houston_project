from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.models import BusinessUnit
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.taxonomy_helpers import create_establishment

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def active_user():
    return User.objects.create_user(
        username="catalog_user",
        email="catalog@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )


def _login(api_client: APIClient, *, user: User) -> str:
    csrf = api_client.get("/api/v1/auth/csrf/").cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": user.email, "password": TEST_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(api_client, active_user):
    token = _login(api_client, user=active_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def imported_catalog():
    return sync_catalog_from_normalized_rows()


def test_catalog_business_unit_suggest_returns_empty_without_import(api_client, auth_headers):
    response = api_client.get(
        "/api/v1/catalog/business-units/suggest/",
        {"q": "Cow"},
        **auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


def test_catalog_business_unit_suggest_returns_coworking_after_import(
    api_client,
    auth_headers,
    imported_catalog,
):
    response = api_client.get(
        "/api/v1/catalog/business-units/suggest/",
        {"q": "Cow"},
        **auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert any(item["key"] == "coworking" and item["label"] == "Coworking" for item in body)


def test_catalog_business_unit_suggest_returns_transversal_default_for_maintenance(
    api_client,
    auth_headers,
    imported_catalog,
):
    response = api_client.get(
        "/api/v1/catalog/business-units/suggest/",
        {"q": "Maintenance"},
        **auth_headers,
    )
    assert response.status_code == 200
    maintenance = next(item for item in response.json() if item["key"] == "maintenance")
    assert maintenance["default_unit_type"] == "transversal"


def test_catalog_activity_subject_suggest_returns_coworking_subjects_from_db(
    api_client,
    auth_headers,
    imported_catalog,
):
    response = api_client.get(
        "/api/v1/catalog/activity-subjects/suggest/",
        {"business_unit_key": "coworking", "q": "prop"},
        **auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body
    assert all(item["business_unit_key"] == "coworking" for item in body)


def test_establishment_business_unit_can_exist_without_catalog_match(imported_catalog):
    establishment = create_establishment(name="Free Text Hotel")
    business_unit = BusinessUnit.objects.create(
        establishment=establishment,
        key="custom_free_pole",
        label="Mon pôle perso",
        unit_type=BusinessUnit.UnitType.DEDICATED,
    )
    assert business_unit.catalog_business_unit_id is None
