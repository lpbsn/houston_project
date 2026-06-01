from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User, UserSession
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipScope,
    OperationalDomain,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def create_user(
    *,
    username: str,
    email: str | None = None,
    status: str = User.Status.ACTIVE,
) -> User:
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password=TEST_PASSWORD,
        status=status,
    )


def create_membership(
    *,
    user: User,
    role: str = EstablishmentMembership.Role.STAFF,
    membership_status: str = EstablishmentMembership.Status.ACTIVE,
    establishment_status: str = Establishment.Status.ACTIVE,
    organization_status: str = Organization.Status.ACTIVE,
    name: str = "Demo Hotel",
    domain_keys: list[str] | None = None,
) -> EstablishmentMembership:
    organization = Organization.objects.create(
        name=f"{name} Group {uuid.uuid4().hex[:6]}",
        status=organization_status,
    )
    establishment = Establishment.objects.create(
        name=name,
        organization=organization,
        status=establishment_status,
    )
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=membership_status,
    )
    for domain_key in domain_keys or []:
        domain = OperationalDomain.objects.create(
            establishment=establishment,
            key=domain_key,
            label=domain_key.title(),
            active=True,
        )
        MembershipScope.objects.create(
            membership=membership,
            operational_domain=domain,
        )
    return membership


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return api_client.cookies["csrftoken"].value


def login(api_client: APIClient, *, identifier: str, password: str = TEST_PASSWORD) -> str:
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(access_token: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}


@pytest.mark.parametrize(
    "actor_role",
    [
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    ],
)
def test_owner_and_director_can_list_only_current_establishment_memberships(
    api_client,
    actor_role,
):
    actor = create_user(username=f"{actor_role}_actor")
    actor_membership = create_membership(
        user=actor,
        role=actor_role,
        name="Nice",
    )
    visible_target = EstablishmentMembership.objects.create(
        user=create_user(username=f"{actor_role}_staff"),
        establishment=actor_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    foreign_membership = create_membership(
        user=create_user(username=f"{actor_role}_foreign"),
        role=EstablishmentMembership.Role.STAFF,
        name="Cannes",
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert {item["id"] for item in body} == {
        str(actor_membership.id),
        str(visible_target.id),
    }
    assert {item["user"]["username"] for item in body} == {
        actor.username,
        visible_target.user.username,
    }
    assert all(item["establishment_id"] == str(actor_membership.establishment_id) for item in body)
    assert str(foreign_membership.id) not in {item["id"] for item in body}


@pytest.mark.parametrize(
    "actor_role",
    [
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    ],
)
def test_manager_and_staff_cannot_list_memberships(api_client, actor_role):
    actor = create_user(username=f"{actor_role}_actor")
    actor_membership = create_membership(
        user=actor,
        role=actor_role,
        name="Nice",
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/",
        **auth_headers(access_token),
    )

    assert response.status_code == 403


def test_membership_list_returns_not_found_when_path_establishment_is_outside_current_context(
    api_client,
):
    actor = create_user(username="owner_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    foreign_establishment = Establishment.objects.create(
        name="Cannes",
        organization=Organization.objects.create(name="Cannes Group"),
        status=Establishment.Status.ACTIVE,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{foreign_establishment.id}/memberships/",
        **auth_headers(access_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
    assert actor_membership.establishment_id != foreign_establishment.id


def test_membership_detail_returns_not_found_for_foreign_membership(api_client):
    actor = create_user(username="owner_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    foreign_membership = create_membership(
        user=create_user(username="foreign_user"),
        role=EstablishmentMembership.Role.STAFF,
        name="Cannes",
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{foreign_membership.id}/"
        ),
        **auth_headers(access_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


def test_membership_patch_updates_role_and_scopes(api_client):
    actor = create_user(username="owner_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    target_user = create_user(username="staff_target")
    target_membership = EstablishmentMembership.objects.create(
        user=target_user,
        establishment=actor_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    housekeeping = OperationalDomain.objects.create(
        establishment=actor_membership.establishment,
        key="housekeeping",
        label="Housekeeping",
        active=True,
    )
    maintenance = OperationalDomain.objects.create(
        establishment=actor_membership.establishment,
        key="maintenance",
        label="Maintenance",
        active=True,
    )
    MembershipScope.objects.create(
        membership=target_membership,
        operational_domain=housekeeping,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.patch(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{target_membership.id}/"
        ),
        {
            "role": EstablishmentMembership.Role.MANAGER,
            "scopes": [
                {"scope_type": "domain", "scope_id": str(maintenance.id)},
            ],
        },
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == EstablishmentMembership.Role.MANAGER
    assert body["scopes"] == [
        {"scope_type": "domain", "scope_id": str(maintenance.id)},
    ]
    assert body["scope_summary"]["domain_count"] == 1

    target_membership.refresh_from_db()
    assert target_membership.role == EstablishmentMembership.Role.MANAGER
    assert MembershipScope.objects.filter(membership=target_membership).count() == 1


def test_membership_patch_rejects_foreign_or_inactive_scopes(api_client):

    actor = create_user(username="owner_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    target_membership = EstablishmentMembership.objects.create(
        user=create_user(username="staff_target"),
        establishment=actor_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    active_domain = OperationalDomain.objects.create(
        establishment=actor_membership.establishment,
        key="housekeeping",
        label="Housekeeping",
        active=True,
    )
    inactive_domain = OperationalDomain.objects.create(
        establishment=actor_membership.establishment,
        key="inactive-domain",
        label="Inactive Domain",
        active=False,
    )
    foreign_establishment = Establishment.objects.create(
        name="Cannes",
        organization=Organization.objects.create(name="Cannes Group"),
        status=Establishment.Status.ACTIVE,
    )
    foreign_domain = OperationalDomain.objects.create(
        establishment=foreign_establishment,
        key="security",
        label="Security",
        active=True,
    )
    MembershipScope.objects.create(
        membership=target_membership,
        operational_domain=active_domain,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.patch(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{target_membership.id}/"
        ),
        {
            "scopes": [
                {"scope_type": "domain", "scope_id": str(inactive_domain.id)},
                {"scope_type": "domain", "scope_id": str(foreign_domain.id)},
            ]
        },
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert "establishment" in response.json()["detail"].lower()
    assert MembershipScope.objects.filter(membership=target_membership).count() == 1


def test_membership_patch_cannot_demote_last_active_owner(api_client):
    actor = create_user(username="owner_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.patch(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{actor_membership.id}/"
        ),
        {"role": EstablishmentMembership.Role.DIRECTOR},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "The last active owner cannot be demoted."}
    actor_membership.refresh_from_db()
    assert actor_membership.role == EstablishmentMembership.Role.OWNER


def test_membership_patch_can_demote_owner_when_another_active_owner_exists(api_client):
    actor = create_user(username="owner_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    second_owner = EstablishmentMembership.objects.create(
        user=create_user(username="second_owner"),
        establishment=actor_membership.establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.patch(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{second_owner.id}/"
        ),
        {"role": EstablishmentMembership.Role.DIRECTOR},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["role"] == EstablishmentMembership.Role.DIRECTOR
    second_owner.refresh_from_db()
    assert second_owner.role == EstablishmentMembership.Role.DIRECTOR


def test_membership_patch_rejects_scopes_for_owner_membership(api_client):
    actor = create_user(username="owner_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    target_owner = EstablishmentMembership.objects.create(
        user=create_user(username="target_owner"),
        establishment=actor_membership.establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    security = OperationalDomain.objects.create(
        establishment=actor_membership.establishment,
        key="security",
        label="Security",
        active=True,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.patch(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{target_owner.id}/"
        ),
        {
            "scopes": [
                {"scope_type": "domain", "scope_id": str(security.id)},
            ],
        },
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert "owner or director" in response.json()["detail"].lower()


def test_membership_deactivate_blocks_last_active_owner(api_client):
    actor = create_user(username="owner_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.post(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{actor_membership.id}/deactivate/"
        ),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "The last active owner cannot be deactivated."}
    actor_membership.refresh_from_db()
    assert actor_membership.status == EstablishmentMembership.Status.ACTIVE


def test_membership_deactivate_succeeds_and_clears_selected_establishment(api_client):
    actor = create_user(username="owner_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.OWNER,
        name="Nice",
    )
    target_user = create_user(username="target_owner")
    target_membership = EstablishmentMembership.objects.create(
        user=target_user,
        establishment=actor_membership.establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    target_session = UserSession.objects.create(
        user=target_user,
        selected_establishment=actor_membership.establishment,
        refresh_token_family_id=uuid.uuid4(),
        refresh_expires_at=timezone.now() + timedelta(hours=1),
        absolute_expires_at=timezone.now() + timedelta(days=1),
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.post(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{target_membership.id}/deactivate/"
        ),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == EstablishmentMembership.Status.DEACTIVATED

    target_membership.refresh_from_db()
    target_session.refresh_from_db()
    assert target_membership.status == EstablishmentMembership.Status.DEACTIVATED
    assert target_session.selected_establishment is None


def test_director_cannot_patch_owner_membership(api_client):
    actor = create_user(username="director_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.DIRECTOR,
        name="Nice",
    )
    owner_user = create_user(username="target_owner")
    owner_membership = EstablishmentMembership.objects.create(
        user=owner_user,
        establishment=actor_membership.establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.patch(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{owner_membership.id}/"
        ),
        {"role": EstablishmentMembership.Role.STAFF},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "membership_management_forbidden"


def test_director_cannot_deactivate_owner_membership(api_client):
    actor = create_user(username="director_deactivate_actor")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.DIRECTOR,
        name="Nice",
    )
    owner_user = create_user(username="owner_target")
    owner_membership = EstablishmentMembership.objects.create(
        user=owner_user,
        establishment=actor_membership.establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.post(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{owner_membership.id}/deactivate/"
        ),
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "membership_management_forbidden"


def test_director_can_patch_manager_membership(api_client):
    actor = create_user(username="director_patch_manager")
    actor_membership = create_membership(
        user=actor,
        role=EstablishmentMembership.Role.DIRECTOR,
        name="Nice",
    )
    manager_user = create_user(username="manager_target")
    manager_membership = EstablishmentMembership.objects.create(
        user=manager_user,
        establishment=actor_membership.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.patch(
        (
            f"/api/v1/establishments/{actor_membership.establishment_id}/memberships/"
            f"{manager_membership.id}/"
        ),
        {"role": EstablishmentMembership.Role.STAFF},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["role"] == EstablishmentMembership.Role.STAFF
