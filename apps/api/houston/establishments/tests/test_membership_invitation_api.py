from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.test import override_settings
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.accounts.services import tokens as auth_tokens
from houston.establishments.models import (
    Establishment,
    EstablishmentInvitation,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.taxonomy_helpers import (
    assert_business_unit_scope_response,
    business_unit_scope_payload,
    create_business_unit,
    create_membership_with_business_unit_scope,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db

ROLE_OWNER = EstablishmentMembership.Role.OWNER
ROLE_DIRECTOR = EstablishmentMembership.Role.DIRECTOR
REGISTRATION_PASSWORD = "SecurePass123!"


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


def create_establishment(
    *,
    name: str = "Demo Hotel",
    status: str = Establishment.Status.ACTIVE,
) -> Establishment:
    organization = Organization.objects.create(
        name=f"{name} Group {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name=name,
        organization=organization,
        status=status,
    )


def director_invite_payload(*, email: str = "new-director@example.com", **overrides):
    payload = {
        "email": email,
        "first_name": "New",
        "last_name": "Director",
        "role": ROLE_DIRECTOR,
    }
    payload.update(overrides)
    return payload


def post_accept(api_client: APIClient, *, token: str, password: str = REGISTRATION_PASSWORD):
    csrf_token = ensure_csrf(api_client)
    return api_client.post(
        f"/api/v1/invitations/{token}/accept/",
        {
            "password": password,
            "password_confirmation": password,
            "refresh_token_transport": "cookie",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
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
        {
            "identifier": identifier,
            "password": password,
            "refresh_token_transport": "cookie",
        },
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


def switch_establishment_if_possible(
    api_client: APIClient,
    *,
    access_token: str,
    establishment_id,
) -> str:
    """Select path establishment when switchable (active establishment membership)."""
    response = api_client.post(
        "/api/v1/auth/switch_establishment/",
        {"establishment_id": str(establishment_id)},
        format="json",
        **auth_headers(access_token),
    )
    if response.status_code != 200:
        return access_token
    return response.json().get("access_token", access_token)


def post_invitation(api_client, *, establishment_id, owner, payload):
    access_token = login(api_client, identifier=owner.email)
    access_token = switch_establishment_if_possible(
        api_client,
        access_token=access_token,
        establishment_id=establishment_id,
    )
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
    access_token = switch_establishment_if_possible(
        api_client,
        access_token=access_token,
        establishment_id=establishment_id,
    )
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


@pytest.mark.django_db(transaction=True)
def test_concurrent_membership_invitation_same_email_returns_409():
    establishment = create_establishment(name="Concurrent Invite Hotel")
    owner = create_user(username="concurrent_invite_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="concurrent_hk")
    payload = invite_payload(
        email="concurrent-staff@example.com",
        scopes=[business_unit_scope_payload(business_unit)],
    )

    def invite(_: int) -> tuple[int, str | None]:
        close_old_connections()
        try:
            client = APIClient(enforce_csrf_checks=True)
            access_token = login(client, identifier=owner.email)
            csrf_token = ensure_csrf(client)
            response = client.post(
                f"/api/v1/establishments/{establishment.id}/membership-invitations/",
                payload,
                format="json",
                HTTP_X_CSRFTOKEN=csrf_token,
                **auth_headers(access_token),
            )
            body = response.json()
            return response.status_code, body.get("code")
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(invite, range(2)))

    statuses = [status for status, _ in results]
    codes = [code for _, code in results]
    assert 201 in statuses
    assert 409 in statuses
    assert statuses.count(201) == 1
    assert statuses.count(409) == 1
    assert codes.count(None) == 1  # successful 201 has no error code
    conflict_codes = [code for code in codes if code is not None]
    assert conflict_codes == ["membership_invitation_duplicate"] or conflict_codes == [
        "membership_invitation_user_exists"
    ]
    assert (
        EstablishmentMembership.objects.filter(
            establishment=establishment,
            user__email__iexact="concurrent-staff@example.com",
        ).count()
        == 1
    )


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


def test_legacy_domain_scope_input_rejected_with_400(api_client):
    establishment = create_establishment(name="Legacy Invite Hotel")
    owner = create_user(username="legacy_invite_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            scopes=[scope_item(scope_type="domain", scope_id=uuid.uuid4())],
        ),
    )

    assert response.status_code == 400


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


def test_owner_can_invite_multiple_directors_on_active_establishment(api_client):
    establishment = create_establishment(name="Multi Director Owner")
    actor = create_user(username="multi_director_actor_owner")
    create_membership(user=actor, establishment=establishment, role=ROLE_OWNER)

    first = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=director_invite_payload(email="director-one-owner@example.com"),
    )
    second = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=director_invite_payload(email="director-two-owner@example.com"),
    )

    assert first.status_code == 201, first.json()
    assert second.status_code == 201, second.json()
    assert first.json()["membership"]["role"] == ROLE_DIRECTOR
    assert second.json()["membership"]["role"] == ROLE_DIRECTOR
    assert first.json()["membership"]["id"] != second.json()["membership"]["id"]
    assert (
        EstablishmentMembership.objects.filter(
            establishment=establishment,
            role=ROLE_DIRECTOR,
            status=EstablishmentMembership.Status.INVITED,
        ).count()
        == 2
    )


def test_director_cannot_invite_director_on_active_establishment(api_client):
    establishment = create_establishment(name="Director Invite Director Guard")
    actor = create_user(username="director_invite_director_actor")
    create_membership(user=actor, establishment=establishment, role=ROLE_DIRECTOR)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=director_invite_payload(email="peer-director@example.com"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "membership_invitation_role_not_allowed"


def test_establishment_invite_rejects_owner_role(api_client):
    establishment = create_establishment(name="Owner Invite Path Guard")
    actor = create_user(username="owner_invite_path_actor")
    create_membership(user=actor, establishment=establishment, role=ROLE_OWNER)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload={
            "email": "org-owner@example.com",
            "first_name": "Org",
            "last_name": "Owner",
            "role": ROLE_OWNER,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert "role" in body["errors"]


@pytest.mark.parametrize(
    "actor_role,membership_status",
    [
        (ROLE_OWNER, EstablishmentMembership.Status.INVITED),
        (ROLE_OWNER, EstablishmentMembership.Status.DEACTIVATED),
        (ROLE_DIRECTOR, EstablishmentMembership.Status.INVITED),
        (ROLE_DIRECTOR, EstablishmentMembership.Status.DEACTIVATED),
    ],
)
def test_non_active_owner_or_director_cannot_invite_director(
    api_client,
    actor_role,
    membership_status,
):
    establishment = create_establishment(name=f"Non Active {actor_role} {membership_status}")
    actor = create_user(username=f"non_active_{actor_role}_{membership_status}")
    create_membership(
        user=actor,
        establishment=establishment,
        role=actor_role,
        membership_status=membership_status,
    )

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=director_invite_payload(
            email=f"blocked-{actor_role}-{membership_status}@example.com"
        ),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Not found."
    assert not EstablishmentMembership.objects.filter(
        establishment=establishment,
        role=ROLE_DIRECTOR,
        user__email__iexact=f"blocked-{actor_role}-{membership_status}@example.com",
    ).exists()


def test_director_invite_rejects_draft_establishment(api_client):
    establishment = create_establishment(
        name="Draft Director Invite",
        status=Establishment.Status.DRAFT,
    )
    owner = create_user(username="draft_director_invite_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=owner,
        payload=director_invite_payload(email="draft-director@example.com"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "membership_invitation_invalid"


def test_director_invite_rejects_deactivated_establishment(api_client):
    establishment = create_establishment(
        name="Deactivated Director Invite",
        status=Establishment.Status.DEACTIVATED,
    )
    owner = create_user(username="deactivated_director_invite_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=owner,
        payload=director_invite_payload(email="deactivated-director@example.com"),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Not found."


def test_director_invitation_rejects_non_empty_scopes(api_client):
    establishment = create_establishment(name="Scope Guard Hotel")
    owner = create_user(username="scope_guard_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    access_token = login(api_client, identifier=owner.email)
    csrf_token = ensure_csrf(api_client)

    response = api_client.post(
        f"/api/v1/establishments/{establishment.id}/membership-invitations/",
        invite_payload(
            email="director-scoped@example.com",
            role=EstablishmentMembership.Role.DIRECTOR,
            scopes=[business_unit_scope_payload(business_unit)],
        ),
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert "scopes" in body["errors"]


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
    ],
)
def test_manager_cannot_invite_non_staff_roles(api_client, target_role):
    # Owner → 400 via serializer; see test_establishment_invite_rejects_owner_role.
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

    if target_role == EstablishmentMembership.Role.DIRECTOR:
        payload = {
            "email": f"{target_role}@example.com",
            "first_name": "New",
            "last_name": "Member",
            "role": target_role,
        }
    else:
        payload = invite_payload(
            email=f"{target_role}@example.com",
            role=target_role,
            scopes=[business_unit_scope_payload(business_unit)],
        )

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=payload,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "membership_invitation_role_not_allowed"


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


@pytest.mark.parametrize(
    "user_status",
    [
        User.Status.ACTIVE,
        User.Status.SUSPENDED,
        User.Status.ANONYMIZED,
    ],
)
def test_membership_invitation_rejects_existing_non_pending_user(api_client, user_status):
    establishment = create_establishment(name=f"User Exists {user_status}")
    owner = create_user(username=f"owner_user_exists_{user_status}")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="housekeeping")
    existing = create_user(
        username=f"existing_{user_status}",
        email=f"existing-{user_status}@example.com",
        status=user_status,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            email=existing.email,
            scopes=[business_unit_scope_payload(business_unit)],
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "membership_invitation_user_exists"
    assert body["detail"] == "A Houston account with this email already exists."
    assert "pending" not in body["detail"].lower()
    assert user_status not in body["detail"].lower()
    assert "membership" not in body["detail"].lower()
    assert not EstablishmentMembership.objects.filter(
        user=existing, establishment=establishment
    ).exists()


def test_membership_invitation_rejects_pending_user_without_membership(api_client):
    establishment = create_establishment(name="Pending No Membership")
    owner = create_user(username="owner_pending_no_m")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="housekeeping")
    pending = create_user(
        username="pending_elsewhere",
        email="pending-elsewhere@example.com",
        status=User.Status.PENDING,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            email=pending.email,
            scopes=[business_unit_scope_payload(business_unit)],
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "membership_invitation_user_exists"
    assert body["detail"] == "A Houston account with this email already exists."
    assert not EstablishmentMembership.objects.filter(
        user=pending, establishment=establishment
    ).exists()


def test_membership_invitation_resume_deactivated_replaces_scopes(api_client):
    establishment = create_establishment(name="Resume Scope Replace")
    owner = create_user(username="owner_resume_scopes")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    old_unit = create_business_unit(establishment=establishment, key="old_unit")
    new_unit = create_business_unit(establishment=establishment, key="new_unit")
    pending = create_user(
        username="pending_resume_scopes",
        email="resume-scopes@example.com",
        status=User.Status.PENDING,
    )
    membership = create_membership(
        user=pending,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=old_unit,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            email=pending.email,
            first_name="Resumed",
            last_name="Staff",
            scopes=[business_unit_scope_payload(new_unit)],
        ),
    )

    assert response.status_code == 201
    membership.refresh_from_db()
    assert membership.status == EstablishmentMembership.Status.INVITED
    assert membership.role == EstablishmentMembership.Role.STAFF
    scopes = list(MembershipScope.objects.filter(membership=membership))
    assert len(scopes) == 1
    assert scopes[0].business_unit_id == new_unit.id


def test_membership_invitation_incompatible_role_leaves_scopes_untouched(api_client):
    establishment = create_establishment(name="Incompatible Role Scopes")
    owner = create_user(username="owner_incompat_scopes")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    old_unit = create_business_unit(establishment=establishment, key="keep_unit")
    new_unit = create_business_unit(establishment=establishment, key="attempt_unit")
    pending = create_user(
        username="pending_incompat_role",
        email="incompat-role@example.com",
        status=User.Status.PENDING,
    )
    membership = create_membership(
        user=pending,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=old_unit,
    )
    scope_ids_before = set(
        MembershipScope.objects.filter(membership=membership).values_list("id", flat=True)
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            email=pending.email,
            role=EstablishmentMembership.Role.STAFF,
            scopes=[business_unit_scope_payload(new_unit)],
        ),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_duplicate"
    membership.refresh_from_db()
    assert membership.status == EstablishmentMembership.Status.DEACTIVATED
    assert membership.role == EstablishmentMembership.Role.MANAGER
    assert (
        set(MembershipScope.objects.filter(membership=membership).values_list("id", flat=True))
        == scope_ids_before
    )


def test_membership_invitation_pending_active_same_role_is_duplicate(api_client):
    establishment = create_establishment(name="Pending Active Duplicate")
    owner = create_user(username="owner_pending_active_dup")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=establishment, key="housekeeping")
    pending = create_user(
        username="pending_active_dup",
        email="pending-active-dup@example.com",
        status=User.Status.PENDING,
    )
    create_membership(
        user=pending,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        membership_status=EstablishmentMembership.Status.ACTIVE,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            email=pending.email,
            scopes=[business_unit_scope_payload(business_unit)],
        ),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_duplicate"


def test_create_invited_membership_race_returns_duplicate_regardless_of_role():
    from houston.establishments.services import (
        DirectorInvitationDuplicateError,
        _create_invited_membership,
    )

    establishment = create_establishment(name="Race Membership Hotel")
    user = create_user(username="race_membership_user", status=User.Status.PENDING)
    create_membership(
        user=user,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )

    with pytest.raises(DirectorInvitationDuplicateError):
        _create_invited_membership(
            user=user,
            establishment=establishment,
            role=EstablishmentMembership.Role.STAFF,
        )

    membership = EstablishmentMembership.objects.get(user=user, establishment=establishment)
    assert membership.role == EstablishmentMembership.Role.MANAGER
    assert membership.status == EstablishmentMembership.Status.DEACTIVATED


@pytest.mark.parametrize(
    "user_status",
    [
        User.Status.ACTIVE,
        User.Status.SUSPENDED,
        User.Status.ANONYMIZED,
    ],
)
def test_director_invitation_rejects_existing_non_pending_user(api_client, user_status):
    establishment = create_establishment(name=f"Director User Exists {user_status}")
    owner = create_user(username=f"owner_director_exists_{user_status}")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    existing = create_user(
        username=f"existing_director_{user_status}",
        email=f"existing-director-{user_status}@example.com",
        status=user_status,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=director_invite_payload(email=existing.email),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "membership_invitation_user_exists"
    assert body["detail"] == "A Houston account with this email already exists."


def test_director_invitation_rejects_pending_user_without_membership(api_client):
    establishment = create_establishment(name="Director Pending No Membership")
    owner = create_user(username="owner_director_pending_no_m")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    pending = create_user(
        username="pending_director_elsewhere",
        email="pending-director-elsewhere@example.com",
        status=User.Status.PENDING,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=director_invite_payload(email=pending.email),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_user_exists"


@pytest.mark.parametrize(
    "membership_status,expected_code",
    [
        (EstablishmentMembership.Status.INVITED, "membership_invitation_duplicate"),
        (EstablishmentMembership.Status.ACTIVE, "membership_invitation_duplicate"),
    ],
)
def test_director_invitation_pending_same_role_invited_or_active_is_duplicate(
    api_client,
    membership_status,
    expected_code,
):
    establishment = create_establishment(name=f"Director Dup {membership_status}")
    owner = create_user(username=f"owner_director_dup_{membership_status}")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    pending = create_user(
        username=f"pending_director_dup_{membership_status}",
        email=f"pending-director-dup-{membership_status}@example.com",
        status=User.Status.PENDING,
    )
    create_membership(
        user=pending,
        establishment=establishment,
        role=ROLE_DIRECTOR,
        membership_status=membership_status,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=director_invite_payload(email=pending.email),
    )

    assert response.status_code == 409
    assert response.json()["code"] == expected_code


def test_director_invitation_resumes_deactivated_same_role(api_client):
    establishment = create_establishment(name="Director Resume")
    owner = create_user(username="owner_director_resume")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    pending = create_user(
        username="pending_director_resume",
        email="resume-director@example.com",
        status=User.Status.PENDING,
    )
    membership = create_membership(
        user=pending,
        establishment=establishment,
        role=ROLE_DIRECTOR,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=director_invite_payload(
            email=pending.email,
            first_name="Resumed",
            last_name="Director",
        ),
    )

    assert response.status_code == 201, response.json()
    membership.refresh_from_db()
    pending.refresh_from_db()
    assert membership.status == EstablishmentMembership.Status.INVITED
    assert membership.role == ROLE_DIRECTOR
    assert pending.first_name == "Resumed"
    assert pending.last_name == "Director"


def test_director_invitation_rejects_deactivated_different_role(api_client):
    establishment = create_establishment(name="Director Incompat Role")
    owner = create_user(username="owner_director_incompat")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    pending = create_user(
        username="pending_director_incompat",
        email="incompat-director@example.com",
        status=User.Status.PENDING,
    )
    membership = create_membership(
        user=pending,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=director_invite_payload(email=pending.email),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_duplicate"
    membership.refresh_from_db()
    assert membership.status == EstablishmentMembership.Status.DEACTIVATED
    assert membership.role == EstablishmentMembership.Role.STAFF


def test_accept_director_invitation_activates_only_target_membership(api_client):
    establishment = create_establishment(name="Accept Director Isolation")
    owner = create_user(username="accept_director_isolation_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)

    first = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=director_invite_payload(email="accept-director-one@example.com"),
    )
    second = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=director_invite_payload(email="accept-director-two@example.com"),
    )
    assert first.status_code == 201, first.json()
    assert second.status_code == 201, second.json()

    first_membership = EstablishmentMembership.objects.get(id=first.json()["membership"]["id"])
    second_membership = EstablishmentMembership.objects.get(id=second.json()["membership"]["id"])
    first_token = first.json()["invitation_token"]

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        accept_response = post_accept(
            APIClient(enforce_csrf_checks=True),
            token=first_token,
        )

    assert accept_response.status_code == 201, accept_response.json()
    first_membership.refresh_from_db()
    second_membership.refresh_from_db()
    assert first_membership.status == EstablishmentMembership.Status.ACTIVE
    assert second_membership.status == EstablishmentMembership.Status.INVITED

    updated_calls = [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.updated"
    ]
    assert len(updated_calls) == 1
    assert updated_calls[0].kwargs["membership_id"] == first_membership.id
    assert updated_calls[0].kwargs["establishment_id"] == establishment.id


def test_accept_director_invitation_invalid_emits_no_access_event(api_client):
    establishment = create_establishment(name="Accept Director Invalid")
    owner = create_user(username="accept_director_invalid_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)

    invite = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=director_invite_payload(email="invalid-accept-director@example.com"),
    )
    assert invite.status_code == 201, invite.json()
    token = invite.json()["invitation_token"]
    membership = EstablishmentMembership.objects.get(id=invite.json()["membership"]["id"])
    invitation = EstablishmentInvitation.objects.get(
        token_digest=auth_tokens.digest_token(token),
    )
    invitation.revoked_at = invitation.created_at
    invitation.save(update_fields=["revoked_at", "updated_at"])

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        accept_response = post_accept(
            APIClient(enforce_csrf_checks=True),
            token=token,
        )

    assert accept_response.status_code == 400
    assert accept_response.json()["code"] == "invitation_invalid"
    membership.refresh_from_db()
    assert membership.status == EstablishmentMembership.Status.INVITED
    assert not [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.updated"
    ]


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_invitation_rejects_path_establishment_outside_session_context(api_client):
    organization = Organization.objects.create(
        name=f"Session Mismatch Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    selected = Establishment.objects.create(
        name="Selected Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    other = Establishment.objects.create(
        name="Other Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    owner = create_user(username="session_mismatch_owner")
    create_membership(user=owner, establishment=selected, role=ROLE_OWNER)
    create_membership(user=owner, establishment=other, role=ROLE_OWNER)
    business_unit = create_business_unit(establishment=other, key="housekeeping")
    invite_email = "session-mismatch-staff@example.com"
    before_membership_count = EstablishmentMembership.objects.filter(
        establishment=other,
    ).count()
    before_invitation_count = EstablishmentInvitation.objects.filter(
        membership__establishment=other,
    ).count()

    access_token = login(api_client, identifier=owner.email)
    access_token = switch_establishment_if_possible(
        api_client,
        access_token=access_token,
        establishment_id=selected.id,
    )
    csrf_token = ensure_csrf(api_client)
    payload = invite_payload(
        email=invite_email,
        scopes=[business_unit_scope_payload(business_unit)],
    )

    with patch(
        "houston.establishments.tasks.send_establishment_invitation_email_task.apply_async"
    ) as apply_async:
        response = api_client.post(
            f"/api/v1/establishments/{other.id}/membership-invitations/",
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
            **auth_headers(access_token),
        )

    assert response.status_code == 404
    assert (
        EstablishmentMembership.objects.filter(establishment=other).count()
        == before_membership_count
    )
    assert (
        EstablishmentInvitation.objects.filter(membership__establishment=other).count()
        == before_invitation_count
    )
    assert not User.objects.filter(email__iexact=invite_email).exists()
    apply_async.assert_not_called()


@pytest.mark.parametrize(
    "invited_role",
    [
        EstablishmentMembership.Role.STAFF,
        EstablishmentMembership.Role.MANAGER,
    ],
)
def test_invitation_allows_draft_path_when_active_establishment_selected(
    api_client,
    invited_role,
):
    organization = Organization.objects.create(
        name=f"Draft Fallback Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    selected = Establishment.objects.create(
        name="Selected Active Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    draft = Establishment.objects.create(
        name="Draft Onboarding Hotel",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    owner = create_user(username=f"draft_fallback_owner_{invited_role}")
    create_membership(user=owner, establishment=selected, role=ROLE_OWNER)
    create_membership(user=owner, establishment=draft, role=ROLE_OWNER)
    draft_business_unit = create_business_unit(establishment=draft, key="housekeeping")
    invite_email = f"draft-fallback-{invited_role}@example.com"

    access_token = login(api_client, identifier=owner.email)
    access_token = switch_establishment_if_possible(
        api_client,
        access_token=access_token,
        establishment_id=selected.id,
    )
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        f"/api/v1/establishments/{draft.id}/membership-invitations/",
        invite_payload(
            email=invite_email,
            role=invited_role,
            scopes=[business_unit_scope_payload(draft_business_unit)],
        ),
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["membership"]["role"] == invited_role
    assert body["membership"]["establishment_id"] == str(draft.id)
    assert_business_unit_scope_response(
        body["membership"],
        business_unit=draft_business_unit,
    )

    membership = EstablishmentMembership.objects.get(
        establishment=draft,
        user__email__iexact=invite_email,
    )
    assert membership.role == invited_role
    assert membership.status == EstablishmentMembership.Status.INVITED
    assert EstablishmentInvitation.objects.filter(membership=membership).exists()
    assert MembershipScope.objects.filter(
        membership=membership,
        business_unit=draft_business_unit,
    ).exists()
    assert not EstablishmentMembership.objects.filter(
        establishment=selected,
        user__email__iexact=invite_email,
    ).exists()
