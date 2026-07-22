from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User, UserSession
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.organizations.models import Organization
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_membership, create_user
from houston.testing.taxonomy import create_business_unit, create_membership_with_business_unit_scope

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _org_path(organization_id, suffix: str = "") -> str:
    return f"/api/v1/organizations/{organization_id}/{suffix}"


def _selected_establishment_id(user: User):
    session = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session is not None
    return session.selected_establishment_id


def _setup_owner_org(
    *,
    with_active: bool = True,
    with_draft: bool = True,
) -> tuple[User, Organization, Establishment | None, Establishment | None]:
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    owner = create_user(username=f"owner_{uuid.uuid4().hex[:6]}")
    active = None
    draft = None
    if with_active:
        active = Establishment.objects.create(
            name="Active Hotel",
            organization=organization,
            status=Establishment.Status.ACTIVE,
        )
        create_membership(
            establishment=active,
            user=owner,
            role=EstablishmentMembership.Role.OWNER,
        )
    if with_draft:
        draft = Establishment.objects.create(
            name="Draft Hotel",
            organization=organization,
            status=Establishment.Status.DRAFT,
        )
        create_membership(
            establishment=draft,
            user=owner,
            role=EstablishmentMembership.Role.OWNER,
        )
    return owner, organization, active, draft


def test_organization_admin_overview_owner_ok(api_client, imported_catalog):
    del imported_catalog
    owner, organization, active, draft = _setup_owner_org()
    access_token = login(api_client, user=owner)
    before = _selected_establishment_id(owner)

    response = api_client.get(
        _org_path(organization.id),
        **auth_headers(access_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(organization.id)
    assert body["name"] == organization.name
    assert body["active_establishment_count"] == 1
    assert body["draft_establishment_count"] == 1
    assert _selected_establishment_id(owner) == before
    assert active is not None and draft is not None


def test_organization_admin_director_forbidden(api_client):
    owner, organization, active, _draft = _setup_owner_org(with_draft=False)
    assert active is not None
    director = create_user(username=f"director_{uuid.uuid4().hex[:6]}")
    create_membership(
        establishment=active,
        user=director,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    access_token = login(api_client, user=director)

    response = api_client.get(
        _org_path(organization.id),
        **auth_headers(access_token),
    )
    assert response.status_code == 403
    del owner


def test_organization_admin_cross_org_forbidden(api_client):
    owner_a, org_a, _active_a, _draft_a = _setup_owner_org(with_draft=False)
    _owner_b, org_b, _active_b, _draft_b = _setup_owner_org(with_draft=False)
    access_token = login(api_client, user=owner_a)

    response = api_client.get(
        _org_path(org_b.id),
        **auth_headers(access_token),
    )
    assert response.status_code == 403
    del org_a


def test_organization_admin_establishments_lists_active_and_draft_not_deactivated(
    api_client,
):
    owner, organization, active, draft = _setup_owner_org()
    assert active is not None and draft is not None
    deactivated = Establishment.objects.create(
        name="Dead Hotel",
        organization=organization,
        status=Establishment.Status.DEACTIVATED,
    )
    create_membership(
        establishment=deactivated,
        user=owner,
        role=EstablishmentMembership.Role.OWNER,
    )
    create_membership(
        establishment=active,
        user=create_user(username=f"dir_{uuid.uuid4().hex[:6]}"),
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    OnboardingSession.objects.create(
        organization=organization,
        establishment=draft,
        started_by=owner,
        current_step="description",
    )

    access_token = login(api_client, user=owner)
    before = _selected_establishment_id(owner)
    response = api_client.get(
        _org_path(organization.id, "establishments/"),
        **auth_headers(access_token),
    )
    assert response.status_code == 200
    results = response.json()["results"]
    ids = {row["id"] for row in results}
    assert str(active.id) in ids
    assert str(draft.id) in ids
    assert str(deactivated.id) not in ids

    draft_row = next(row for row in results if row["id"] == str(draft.id))
    assert draft_row["can_continue_onboarding"] is True
    assert draft_row["onboarding_session_id"] is not None
    assert draft_row["onboarding_current_step"] == "description"

    active_row = next(row for row in results if row["id"] == str(active.id))
    assert len(active_row["directors"]) == 1
    assert _selected_establishment_id(owner) == before


def test_organization_admin_members_dedup_and_scope(api_client, imported_catalog):
    owner, organization, active, draft = _setup_owner_org()
    assert active is not None and draft is not None
    deactivated = Establishment.objects.create(
        name="Gone",
        organization=organization,
        status=Establishment.Status.DEACTIVATED,
    )
    shared = create_user(
        username=f"shared_{uuid.uuid4().hex[:6]}",
    )
    shared.first_name = "Ada"
    shared.last_name = "Lovelace"
    shared.save(update_fields=["first_name", "last_name"])

    create_membership(
        establishment=active,
        user=shared,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership(
        establishment=draft,
        user=shared,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.INVITED,
    )
    create_membership(
        establishment=deactivated,
        user=shared,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership(
        establishment=active,
        user=create_user(username=f"deact_{uuid.uuid4().hex[:6]}"),
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.DEACTIVATED,
    )

    bu = create_business_unit(establishment=active, key="hotel", label="Hotel")
    manager = EstablishmentMembership.objects.get(
        user=shared,
        establishment=active,
    )
    create_membership_with_business_unit_scope(membership=manager, business_unit=bu)

    access_token = login(api_client, user=owner)
    response = api_client.get(
        _org_path(organization.id, "members/"),
        **auth_headers(access_token),
    )
    assert response.status_code == 200
    results = response.json()["results"]
    shared_rows = [row for row in results if row["user_id"] == str(shared.id)]
    assert len(shared_rows) == 1
    membership_est_ids = {
        item["establishment_id"] for item in shared_rows[0]["memberships"]
    }
    assert str(active.id) in membership_est_ids
    assert str(draft.id) in membership_est_ids
    assert str(deactivated.id) not in membership_est_ids
    statuses = {item["status"] for item in shared_rows[0]["memberships"]}
    assert "active" in statuses
    assert "invited" in statuses

    filtered = api_client.get(
        _org_path(organization.id, "members/"),
        {"status": "deactivated"},
        **auth_headers(access_token),
    )
    assert filtered.status_code == 200
    assert any(
        any(m["status"] == "deactivated" for m in row["memberships"])
        for row in filtered.json()["results"]
    )

    options = api_client.get(
        _org_path(organization.id, "members/filter-options/"),
        **auth_headers(access_token),
    )
    assert options.status_code == 200
    options_body = options.json()
    option_ids = {row["id"] for row in options_body["establishments"]}
    assert str(active.id) in option_ids
    assert str(draft.id) in option_ids
    assert str(deactivated.id) not in option_ids
    assert "owner" in options_body["roles"]
    assert "deactivated" in options_body["statuses"]
    assert any(row["id"] == str(bu.id) for row in options_body["business_units"])
    del imported_catalog


def test_organization_admin_owners_and_invite_draft_only(api_client):
    owner, organization, _active, draft = _setup_owner_org(
        with_active=False,
        with_draft=True,
    )
    assert draft is not None
    access_token = login(api_client, user=owner)
    before = _selected_establishment_id(owner)

    invite = api_client.post(
        _org_path(organization.id, "owner-invitations/"),
        {
            "email": "co-owner@example.com",
            "first_name": "Co",
            "last_name": "Owner",
        },
        format="json",
        **auth_headers(access_token),
    )
    assert invite.status_code == 201, invite.json()
    assert "invitation_token" in invite.json()
    assert _selected_establishment_id(owner) == before

    owners = api_client.get(
        _org_path(organization.id, "owners/"),
        **auth_headers(access_token),
    )
    assert owners.status_code == 200
    results = owners.json()["results"]
    invited = next(row for row in results if row["email"] == "co-owner@example.com")
    assert invited["status"] == "invited"
    assert invited["can_resend_invitation"] is True

    reissue = api_client.post(
        _org_path(organization.id, "owner-invitations/"),
        {
            "email": "co-owner@example.com",
            "first_name": "Co",
            "last_name": "Owner",
        },
        format="json",
        **auth_headers(access_token),
    )
    assert reissue.status_code == 201, reissue.json()

    duplicate_active = api_client.post(
        _org_path(organization.id, "owner-invitations/"),
        {
            "email": owner.email,
            "first_name": "Same",
            "last_name": "Owner",
        },
        format="json",
        **auth_headers(access_token),
    )
    assert duplicate_active.status_code == 409


def test_create_establishment_does_not_switch_via_org_flow(api_client):
    """Regression: POST /establishments/ (reused by Lot C UI) keeps session selection."""
    owner, organization, active, _draft = _setup_owner_org(with_draft=False)
    assert active is not None
    access_token = login(api_client, user=owner)
    switch = api_client.post(
        "/api/v1/auth/switch_establishment/",
        {"establishment_id": str(active.id)},
        format="json",
        **auth_headers(access_token),
    )
    assert switch.status_code == 200
    access_token = switch.json().get("access_token", access_token)
    before = _selected_establishment_id(owner)
    assert before == active.id

    created = api_client.post(
        "/api/v1/establishments/",
        {"name": f"New Draft {uuid.uuid4().hex[:4]}"},
        format="json",
        **auth_headers(access_token),
    )
    assert created.status_code == 201, created.json()
    assert created.json()["organization_id"] == str(organization.id)
    assert _selected_establishment_id(owner) == before


def test_establishment_membership_invitation_still_rejects_owner(api_client):
    owner, _organization, active, _draft = _setup_owner_org(with_draft=False)
    assert active is not None
    access_token = login(api_client, user=owner)
    switch = api_client.post(
        "/api/v1/auth/switch_establishment/",
        {"establishment_id": str(active.id)},
        format="json",
        **auth_headers(access_token),
    )
    assert switch.status_code == 200
    access_token = switch.json().get("access_token", access_token)
    response = api_client.post(
        f"/api/v1/establishments/{active.id}/membership-invitations/",
        {
            "email": "owner-via-team@example.com",
            "first_name": "Nope",
            "last_name": "Owner",
            "role": EstablishmentMembership.Role.OWNER,
        },
        format="json",
        **auth_headers(access_token),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "membership_invitation_role_not_allowed"
