from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipScope,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
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


def create_taxonomy_tree(establishment: Establishment):
    module = OperationalModule.objects.create(
        establishment=establishment,
        key=f"module_{uuid.uuid4().hex[:6]}",
        label="Hotel",
        active=True,
    )
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key=f"domain_{uuid.uuid4().hex[:6]}",
        label="Housekeeping",
        active=True,
    )
    subject = OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=domain,
        key=f"subject_{uuid.uuid4().hex[:6]}",
        label="Room cleaning",
        active=True,
    )
    return module, domain, subject


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


def test_owner_can_invite_staff_with_domain_scope(api_client):
    establishment = create_establishment(name="Invite Hotel")
    owner = create_user(username="invite_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    _, domain, _ = create_taxonomy_tree(establishment)

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(scopes=[scope_item(scope_type="domain", scope_id=domain.id)]),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["membership"]["role"] == EstablishmentMembership.Role.STAFF
    assert body["membership"]["scopes"] == [
        {"scope_type": "domain", "scope_id": str(domain.id)}
    ]
    assert body["membership"]["scope_summary"]["domain_count"] == 1


@pytest.mark.parametrize(
    ("scope_type", "node_index"),
    [
        ("module", 0),
        ("domain", 1),
        ("subject", 2),
    ],
)
def test_owner_can_invite_manager_with_module_domain_or_subject_scope(
    api_client,
    scope_type,
    node_index,
):
    establishment = create_establishment(name="Manager Hotel")
    owner = create_user(username="manager_invite_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    nodes = create_taxonomy_tree(establishment)

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            email="manager@example.com",
            role=EstablishmentMembership.Role.MANAGER,
            scopes=[scope_item(scope_type=scope_type, scope_id=nodes[node_index].id)],
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["membership"]["role"] == EstablishmentMembership.Role.MANAGER
    assert len(body["membership"]["scopes"]) == 1


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
        payload=invite_payload(scopes=[scope_item(scope_type="domain", scope_id=uuid.uuid4())]),
    )

    assert response.status_code == 400


def test_invitation_rejects_cross_establishment_scope(api_client):
    establishment_a = create_establishment(name="Hotel A")
    establishment_b = create_establishment(name="Hotel B")
    owner = create_user(username="cross_est_owner")
    create_membership(user=owner, establishment=establishment_a, role=ROLE_OWNER)
    _, domain_b, _ = create_taxonomy_tree(establishment_b)

    response = post_invitation(
        api_client,
        establishment_id=establishment_a.id,
        owner=owner,
        payload=invite_payload(scopes=[scope_item(scope_type="domain", scope_id=domain_b.id)]),
    )

    assert response.status_code == 400


def test_invitation_rejects_inactive_scope(api_client):
    establishment = create_establishment(name="Inactive Scope Hotel")
    owner = create_user(username="inactive_scope_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    _, domain, _ = create_taxonomy_tree(establishment)
    domain.active = False
    domain.save(update_fields=["active", "updated_at"])

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(scopes=[scope_item(scope_type="domain", scope_id=domain.id)]),
    )

    assert response.status_code == 400


def test_invitation_normalizes_redundant_child_scope(api_client):
    establishment = create_establishment(name="Normalize Hotel")
    owner = create_user(username="normalize_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    module, domain, _ = create_taxonomy_tree(establishment)

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            scopes=[
                scope_item(scope_type="module", scope_id=module.id),
                scope_item(scope_type="domain", scope_id=domain.id),
            ],
        ),
    )

    assert response.status_code == 201
    assert response.json()["membership"]["scopes"] == [
        {"scope_type": "module", "scope_id": str(module.id)}
    ]


def test_cannot_invite_owner_or_director_roles(api_client):
    establishment = create_establishment(name="Role Guard Hotel")
    owner = create_user(username="role_guard_owner")
    create_membership(user=owner, establishment=establishment, role=ROLE_OWNER)
    module, _, _ = create_taxonomy_tree(establishment)

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
                scopes=[scope_item(scope_type="module", scope_id=module.id)],
            ),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
            **auth_headers(access_token),
        )
        assert response.status_code == 403


def test_staff_cannot_invite_members(api_client):
    establishment = create_establishment(name="Forbidden Invite Hotel")
    actor = create_user(username="staff_invite_actor")
    create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    module, _, _ = create_taxonomy_tree(establishment)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[scope_item(scope_type="module", scope_id=module.id)]),
    )

    assert response.status_code == 403


def test_manager_can_invite_staff_with_module_scope(api_client):
    establishment = create_establishment(name="Manager Invite Module Hotel")
    actor = create_user(username="manager_invite_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    module, _, _ = create_taxonomy_tree(establishment)
    MembershipScope.objects.create(membership=manager_membership, operational_module=module)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[scope_item(scope_type="module", scope_id=module.id)]),
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
    module, _, _ = create_taxonomy_tree(establishment)
    MembershipScope.objects.create(membership=manager_membership, operational_module=module)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(
            email=f"{target_role}@example.com",
            role=target_role,
            scopes=[scope_item(scope_type="module", scope_id=module.id)],
        ),
    )

    assert response.status_code == 403


def test_manager_with_domain_scope_can_invite_staff_in_same_domain(api_client):
    establishment = create_establishment(name="Manager Domain Hotel")
    actor = create_user(username="manager_domain_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    _, domain, _ = create_taxonomy_tree(establishment)
    MembershipScope.objects.create(membership=manager_membership, operational_domain=domain)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[scope_item(scope_type="domain", scope_id=domain.id)]),
    )

    assert response.status_code == 201


def test_manager_with_domain_scope_can_invite_staff_on_child_subject(api_client):
    establishment = create_establishment(name="Manager Domain Subject Hotel")
    actor = create_user(username="manager_domain_subject_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    _, domain, subject = create_taxonomy_tree(establishment)
    MembershipScope.objects.create(membership=manager_membership, operational_domain=domain)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[scope_item(scope_type="subject", scope_id=subject.id)]),
    )

    assert response.status_code == 201


def test_manager_with_subject_scope_can_invite_staff_on_same_subject(api_client):
    establishment = create_establishment(name="Manager Subject Hotel")
    actor = create_user(username="manager_subject_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    _, _, subject = create_taxonomy_tree(establishment)
    MembershipScope.objects.create(membership=manager_membership, operational_subject=subject)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[scope_item(scope_type="subject", scope_id=subject.id)]),
    )

    assert response.status_code == 201


def test_manager_with_subject_scope_cannot_invite_staff_on_parent_domain(api_client):
    establishment = create_establishment(name="Manager Subject Parent Domain Hotel")
    actor = create_user(username="manager_subject_parent_domain_actor")
    manager_membership = create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    _, domain, subject = create_taxonomy_tree(establishment)
    MembershipScope.objects.create(membership=manager_membership, operational_subject=subject)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[scope_item(scope_type="domain", scope_id=domain.id)]),
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
    _, domain_a, _ = create_taxonomy_tree(establishment)
    module_b = OperationalModule.objects.create(
        establishment=establishment,
        key=f"module_{uuid.uuid4().hex[:6]}",
        label="Other Module",
        active=True,
    )
    domain_b = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module_b,
        key=f"domain_{uuid.uuid4().hex[:6]}",
        label="Other Domain",
        active=True,
    )
    MembershipScope.objects.create(membership=manager_membership, operational_domain=domain_a)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(scopes=[scope_item(scope_type="domain", scope_id=domain_b.id)]),
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
    _, domain_a, _ = create_taxonomy_tree(establishment)
    module_b = OperationalModule.objects.create(
        establishment=establishment,
        key=f"module_{uuid.uuid4().hex[:6]}",
        label="Other Module",
        active=True,
    )
    domain_b = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module_b,
        key=f"domain_{uuid.uuid4().hex[:6]}",
        label="Other Domain",
        active=True,
    )
    MembershipScope.objects.create(membership=manager_membership, operational_domain=domain_a)

    response = post_invitation_as_actor(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=invite_payload(
            scopes=[
                scope_item(scope_type="domain", scope_id=domain_a.id),
                scope_item(scope_type="domain", scope_id=domain_b.id),
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
    _, domain, _ = create_taxonomy_tree(establishment)

    response = post_invitation(
        api_client,
        establishment_id=establishment.id,
        owner=owner,
        payload=invite_payload(
            email="persist@example.com",
            scopes=[scope_item(scope_type="domain", scope_id=domain.id)],
        ),
    )

    assert response.status_code == 201
    membership_id = response.json()["membership"]["id"]
    scopes = MembershipScope.objects.filter(membership_id=membership_id)
    assert scopes.count() == 1
    assert scopes.first().operational_domain_id == domain.id
