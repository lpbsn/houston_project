from __future__ import annotations

from rest_framework.test import APIClient

from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.tests.taxonomy_helpers import create_business_unit
from houston.organizations.models import Organization

REGISTRATION_PASSWORD = "SecurePass123!"


def create_membership(
    *,
    user,
    organization_status=Organization.Status.ACTIVE,
    establishment_status=Establishment.Status.ACTIVE,
    membership_status=EstablishmentMembership.Status.ACTIVE,
    role=EstablishmentMembership.Role.OWNER,
    name="Demo Hotel",
    business_unit_keys=None,
):
    organization = Organization.objects.create(name=f"{name} Group", status=organization_status)
    establishment = Establishment.objects.create(
        name=name,
        organization=organization,
        status=establishment_status,
    )
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        status=membership_status,
        role=role,
    )

    for key in business_unit_keys or []:
        business_unit = create_business_unit(establishment=establishment, key=key)
        MembershipScope.objects.create(membership=membership, business_unit=business_unit)

    return membership


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")

    assert response.status_code == 200
    assert "csrftoken" in api_client.cookies

    return api_client.cookies["csrftoken"].value


def auth_headers(csrf_token: str, access_token: str | None = None) -> dict:
    headers = {
        "HTTP_X_CSRFTOKEN": csrf_token,
    }

    if access_token is not None:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"

    return headers


def login(
    api_client: APIClient,
    csrf_token: str,
    *,
    identifier: str,
    password: str,
    **extra_headers,
):
    return api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password},
        format="json",
        **auth_headers(csrf_token),
        **extra_headers,
    )


def registration_payload(**overrides):
    payload = {
        "invite_code": "valid-code",
        "first_name": "Alex",
        "last_name": "Owner",
        "email": "alex.owner@example.com",
        "password": REGISTRATION_PASSWORD,
        "password_confirmation": REGISTRATION_PASSWORD,
        "organization_name": "Northwind Group",
        "establishment_name": "Northwind Hotel",
    }
    payload.update(overrides)
    return payload


def post_register(api_client: APIClient, csrf_token: str, payload: dict):
    return api_client.post(
        "/api/v1/auth/register/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )


def owner_validate_payload(**overrides):
    payload = {
        "invite_code": "valid-code",
        "first_name": "Alex",
        "last_name": "Owner",
        "email": "alex.owner@example.com",
        "password": REGISTRATION_PASSWORD,
        "password_confirmation": REGISTRATION_PASSWORD,
    }
    payload.update(overrides)
    return payload


def post_validate_owner(api_client: APIClient, csrf_token: str, payload: dict):
    return api_client.post(
        "/api/v1/auth/register/validate-owner/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )


def post_login(api_client: APIClient, csrf_token: str, *, identifier: str, password: str):
    return api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
