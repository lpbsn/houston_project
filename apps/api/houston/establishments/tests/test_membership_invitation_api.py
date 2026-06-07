from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.taxonomy_helpers import (
    assert_business_unit_scope_response,
    business_unit_scope_payload,
    create_business_unit,
    create_legacy_taxonomy_with_business_unit_mapping,
    create_membership_with_business_unit_scope,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db

ROLE_OWNER = EstablishmentMembership.Role.OWNER


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


def create_establishment(*, name: str = "Demo Hotel") -> Establishment:
    organization = Organization.objects.create(
        name=f"{name} Group {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name=name,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


def create_membership(
    *,
    user: User,
    establishment: Establishment,
    role: str = EstablishmentMembership.Role.STAFF,
    membership_status: str = EstablishmentMembership.Status.ACTIVE,
) -> EstablishmentMembership:
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=membership_status,
    )


def scope_item(*, scope_type: str, scope_id) -> dict:
    return {"scope_type": scope_type, "scope_id": str(scope_id)}


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


def invite_payload(*, scopes: list[dict], **overrides):
    payload = {
        "email": "new-staff@example.com",
        "first_name": "New",
        "last_name": "Staff",
        "role": EstablishmentMembership.Role.STAFF,
        "scopes": scopes,
    }
    payload.update(overrides)
    return payload


def post_invitation(api_client, *, establishment_id, owner, payload):
    access_token = login(api_client, identifier=owner.email)
    csrf_token = ensure_csrf(api_client)
    return api_client.post(
        f"/api/v1/establishments/{establishment_id}/membership-invitations/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )


def post_invitation_as_actor(api_client, *, establishment_id, actor, payload):
    access_token = login(api_client, identifier=actor.email)
    csrf_token = ensure_csrf(api_client)
    return api_client.post(
        f"/api/v1/establishments/{establishment_id}/membership-invitations/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )


def test_owner_can_invite_staff_with_business_unit_scope(api_client):
    establishment = create_establishment(name="Invite Hotel")
    owner = create_user(username="invite_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="housekeeping")

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            scopes=[business_unit_scope_payload(business_unit)],
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["membership"]["role"] == EstablishmentMembership.Role.STAFF
    assert_business_unit_scope_response(body["membership"], business_unit=business_unit)


def test_owner_can_invite_manager_with_business_unit_scope(api_client):
    establishment = create_establishment(name="Manager Hotel")
    owner = create_user(username="manager_invite_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            email="manager@example.com",
            role=EstablishmentMembership.Role.MANAGER,
            scopes=[business_unit_scope_payload(business_unit)],
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["membership"]["role"] == EstablishmentMembership.Role.MANAGER
    assert_business_unit_scope_response(body["membership"], business_unit=business_unit)


def test_legacy_domain_scope_input_normalizes_to_business_unit(api_client):
    establishment = create_establishment(name="Legacy Invite Hotel")
    owner = create_user(username="legacy_invite_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    _, domain, _, business_unit = create_legacy_taxonomy_with_business_unit_mapping(
        establishment,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            scopes=[scope_item(scope_type="domain", scope_id=domain.id)],
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert_business_unit_scope_response(body["membership"], business_unit=business_unit)
    membership_id = body["membership"]["id"]
    scope = MembershipScope.objects.get(membership_id=membership_id)
    assert scope.business_unit_id == business_unit.id


def test_staff_invitation_requires_scopes(api_client):
    establishment = create_establishment(name="Staff Scope Hotel")
    owner = create_user(username="staff_scope_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload={
            "email": "staff@example.com",
            "first_name": "New",
            "last_name": "Staff",
            "role": EstablishmentMembership.Role.STAFF,
        },
    )

    assert response.status_code == 400


def test_invitation_rejects_invalid_scope_id(api_client):
    establishment = create_establishment(name="Invalid Scope Hotel")
    owner = create_user(username="invalid_scope_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            scopes=[scope_item(scope_type="business_unit", scope_id=uuid.uuid4())],
        ),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "membership_invitation_invalid"
    assert isinstance(body["detail"], str)


def test_invitation_rejects_cross_establishment_scope(api_client):
    establishment_a = create_establishment(name="Hotel A")
    establishment_b = create_establishment(name="Hotel B")
    owner = create_user(username="cross_est_owner")
    create_membership(user=owner, establishment=establishment_a, role=ROLE_OWNER)
    foreign_business_unit = create_business_unit(establishment=establishment_b, key="hotel")

    response = post_invitation(
        api_client,
        establishment_id=establishment_a.id,
        owner=owner,
        payload=invite_payload(
            scopes=[business_unit_scope_payload(foreign_business_unit)],
        ),
    )

    assert response.status_code == 400


def test_invitation_rejects_inactive_scope(api_client):
    establishment = create_establishment(name="Inactive Scope Hotel")
    owner = create_user(username="inactive_scope_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="hotel")
    business_unit.active = False
    business_unit.save(update_fields=["active", "updated_at"])

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(scopes=[business_unit_scope_payload(business_unit)]),
    )

    assert response.status_code == 400


def test_invitation_normalizes_duplicate_business_unit_scope(api_client):
    establishment = create_establishment(name="Normalize Hotel")
    owner = create_user(username="normalize_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            scopes=[
                business_unit_scope_payload(business_unit),
                business_unit_scope_payload(business_unit),
            ],
        ),
    )

    assert response.status_code == 201
    assert_business_unit_scope_response(
        response.json()["membership"],
        business_unit=business_unit,
    )


def test_cannot_invite_owner_or_director_roles(api_client):
    establishment = create_establishment(name="Role Guard Hotel")
    owner = create_user(username="role_guard_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    access_token = login(api_client, identifier=owner.email)
    csrf_token = ensure_csrf(api_client)

    for role in (
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    ):
        response = api_client.post(
            f"/api/v1/establishments/{establishment.id}/membership-invitations/",
            invite_payload(
                email=f"{role}@example.com",
                role=role,
                scopes=[business_unit_scope_payload(business_unit)],
            ),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
            **auth_headers(access_token),
        )
        assert response.status_code == 403
        body = response.json()
        assert body["code"] == "membership_invitation_role_not_allowed"
        assert isinstance(body["detail"], str)


def test_staff_cannot_invite_members(api_client):
    establishment = create_establishment(name="Forbidden Invite Hotel")
    actor = create_user(username="staff_invite_actor")
    create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[business_unit_scope_payload(business_unit)]),
    )

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "permission_denied"
    assert isinstance(body["detail"], str)


def test_manager_can_invite_staff_with_business_unit_scope(api_client):
    establishment = create_establishment(name="Manager Invite Hotel")
    actor = create_user(username="manager_invite_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    business_unit = create_business_unit(establishment=establishment, key="hotel")
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=business_unit,
    )

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[business_unit_scope_payload(business_unit)]),
    )

    assert response.status_code == 201
    assert response.json()["membership"]["role"] == EstablishmentMembership.Role.STAFF


@pytest.mark.parametrize(
    "target_role",
    [
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.OWNER,
    ],
)
def test_manager_cannot_invite_non_staff_roles(api_client, target_role):
    establishment = create_establishment(name="Manager Role Guard Hotel")
    actor = create_user(username=f"manager_role_guard_{target_role}")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    business_unit = create_business_unit(establishment=establishment, key="hotel")
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=business_unit,
    )

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(
            email=f"{target_role}@example.com",
            role=target_role,
            scopes=[business_unit_scope_payload(business_unit)],
        ),
    )

    assert response.status_code == 403


def test_manager_with_business_unit_scope_can_invite_staff_on_same_unit(api_client):
    establishment = create_establishment(name="Manager Same BU Hotel")
    actor = create_user(username="manager_same_bu_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    business_unit = create_business_unit(establishment=establishment, key="housekeeping")
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=business_unit,
    )

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[business_unit_scope_payload(business_unit)]),
    )

    assert response.status_code == 201


def test_manager_with_narrow_scope_cannot_invite_staff_on_broader_unit(api_client):
    establishment = create_establishment(name="Manager Narrow Scope Hotel")
    actor = create_user(username="manager_narrow_scope_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    scoped_unit = create_business_unit(establishment=establishment, key="housekeeping")
    broader_unit = create_business_unit(establishment=establishment, key="hotel")
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=scoped_unit,
    )

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[business_unit_scope_payload(broader_unit)]),
    )

    assert response.status_code == 403


def test_manager_cannot_invite_staff_with_scope_outside_perimeter(api_client):
    establishment = create_establishment(name="Manager Outside Scope Hotel")
    actor = create_user(username="manager_outside_scope_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    scoped_unit = create_business_unit(establishment=establishment, key="housekeeping")
    outside_unit = create_business_unit(establishment=establishment, key="maintenance")
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=scoped_unit,
    )

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[business_unit_scope_payload(outside_unit)]),
    )

    assert response.status_code == 403


def test_manager_invitation_fails_when_any_target_scope_is_outside_perimeter(api_client):
    establishment = create_establishment(name="Manager Mixed Scope Hotel")
    actor = create_user(username="manager_mixed_scope_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    scoped_unit = create_business_unit(establishment=establishment, key="housekeeping")
    outside_unit = create_business_unit(establishment=establishment, key="maintenance")
    create_membership_with_business_unit_scope(
        membership=manager_membership,
        business_unit=scoped_unit,
    )

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(
            scopes=[
                business_unit_scope_payload(scoped_unit),
                business_unit_scope_payload(outside_unit),
            ]
        ),
    )

    assert response.status_code == 403


def test_manager_invitation_requires_scopes(api_client):
    establishment = create_establishment(name="Manager Scope Required Hotel")
    actor = create_user(username="manager_scope_required_actor")
    create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload={
            "email": "new-staff-no-scope@example.com",
            "first_name": "No",
            "last_name": "Scope",
            "role": EstablishmentMembership.Role.STAFF,
        },
    )

    assert response.status_code == 400


def test_invitation_persists_membership_scopes(api_client):
    establishment = create_establishment(name="Persist Scope Hotel")
    owner = create_user(username="persist_scope_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="housekeeping")

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            email="persist@example.com",
            scopes=[business_unit_scope_payload(business_unit)],
        ),
    )

    assert response.status_code == 201
    membership_id = response.json()["membership"]["id"]
    scopes = MembershipScope.objects.filter(membership_id=membership_id)
    assert scopes.count() == 1
    assert scopes.first().business_unit_id == business_unit.id
