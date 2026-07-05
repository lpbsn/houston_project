from __future__ import annotations

import uuid

from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import BusinessUnit, EstablishmentMembership, MembershipScope
from houston.testing.factories import TEST_PASSWORD, build_membership
from houston.testing.taxonomy import create_membership_with_business_unit_scope

__all__ = [
    "TEST_PASSWORD",
    "assign_business_unit_scope",
    "auth_headers",
    "build_api_membership",
    "build_api_membership_on_establishment",
    "ensure_csrf",
    "login",
]


def build_api_membership(**kwargs) -> EstablishmentMembership:
    membership = build_membership(**kwargs)
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    return membership


def build_api_membership_on_establishment(
    establishment_membership: EstablishmentMembership,
    *,
    role=EstablishmentMembership.Role.STAFF,
) -> EstablishmentMembership:
    user = User.objects.create_user(
        username=f"user_{uuid.uuid4().hex[:8]}",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment_membership.establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )


def assign_business_unit_scope(
    membership: EstablishmentMembership,
    business_unit: BusinessUnit,
) -> MembershipScope:
    return create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return api_client.cookies["csrftoken"].value


def login(api_client: APIClient, *, user: User, password: str = TEST_PASSWORD) -> str:
    identifier = user.email if user.email else user.username
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}
