from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership, OnboardingSession
from houston.establishments.services import (
    EstablishmentCreationForbiddenError,
    provision_establishment_onboarding,
)
from houston.organizations.models import Organization
from houston.testing.auth import TEST_PASSWORD, auth_headers, login

pytestmark = pytest.mark.django_db

ROLE_OWNER = EstablishmentMembership.Role.OWNER
ROLE_DIRECTOR = EstablishmentMembership.Role.DIRECTOR


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def create_user(*, username: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )


def create_organization(*, name: str = "Org") -> Organization:
    return Organization.objects.create(
        name=f"{name} {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )


def create_establishment(
    *,
    name: str,
    organization: Organization,
    status: str = Establishment.Status.ACTIVE,
) -> Establishment:
    return Establishment.objects.create(
        name=name,
        organization=organization,
        status=status,
    )


def create_membership(
    *,
    user: User,
    establishment: Establishment,
    role: str = ROLE_OWNER,
) -> EstablishmentMembership:
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )


def switch_establishment(api_client: APIClient, *, access_token: str, establishment_id) -> None:
    response = api_client.post(
        "/api/v1/auth/switch_establishment/",
        {"establishment_id": str(establishment_id)},
        format="json",
        **auth_headers(access_token),
    )
    assert response.status_code == 200, response.json()


def post_create_establishment(api_client: APIClient, *, access_token: str, name: str):
    return api_client.post(
        "/api/v1/establishments/",
        {"name": name},
        format="json",
        **auth_headers(access_token),
    )


def test_provision_establishment_onboarding_atomic_success():
    organization = create_organization(name="Provision Org")
    active = create_establishment(name="Active A", organization=organization)
    actor = create_user(username="prov_owner")
    create_membership(user=actor, establishment=active, role=ROLE_OWNER)

    provision = provision_establishment_onboarding(
        actor=actor,
        organization=organization,
        name="  New Draft  ",
    )

    assert provision.establishment.status == Establishment.Status.DRAFT
    assert provision.establishment.name == "New Draft"
    assert provision.onboarding_session.establishment_id == provision.establishment.id
    assert provision.onboarding_session.status == OnboardingSession.Status.STARTED
    assert EstablishmentMembership.objects.filter(
        user=actor,
        establishment=provision.establishment,
        role=ROLE_OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    ).exists()


def test_provision_rolls_back_when_onboarding_session_fails():
    organization = create_organization(name="Rollback Session Org")
    active = create_establishment(name="Active A", organization=organization)
    actor = create_user(username="rollback_owner")
    create_membership(user=actor, establishment=active, role=ROLE_OWNER)

    before_est = set(
        Establishment.objects.filter(organization=organization).values_list("id", flat=True)
    )
    before_memberships = EstablishmentMembership.objects.filter(
        establishment__organization=organization,
    ).count()

    with patch(
        "houston.establishments.services.start_onboarding_session",
        side_effect=RuntimeError("session boom"),
    ):
        with pytest.raises(RuntimeError, match="session boom"):
            provision_establishment_onboarding(
                actor=actor,
                organization=organization,
                name="Should Not Persist",
            )

    assert (
        set(Establishment.objects.filter(organization=organization).values_list("id", flat=True))
        == before_est
    )
    assert (
        EstablishmentMembership.objects.filter(
            establishment__organization=organization,
        ).count()
        == before_memberships
    )
    assert not OnboardingSession.objects.filter(organization=organization).exists()


def test_provision_forbids_non_owner():
    organization = create_organization(name="Forbid Org")
    active = create_establishment(name="Active A", organization=organization)
    actor = create_user(username="director_actor")
    create_membership(user=actor, establishment=active, role=ROLE_DIRECTOR)

    with pytest.raises(EstablishmentCreationForbiddenError):
        provision_establishment_onboarding(
            actor=actor,
            organization=organization,
            name="No Create",
        )


def test_create_establishment_api_owner_success(api_client):
    organization = create_organization(name="API Create Org")
    active = create_establishment(name="Active A", organization=organization)
    actor = create_user(username="api_owner")
    create_membership(user=actor, establishment=active, role=ROLE_OWNER)
    access_token = login(api_client, user=actor)
    switch_establishment(api_client, access_token=access_token, establishment_id=active.id)

    response = post_create_establishment(
        api_client,
        access_token=access_token,
        name="  Draft From API  ",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["name"] == "Draft From API"
    assert body["status"] == Establishment.Status.DRAFT
    assert body["organization_id"] == str(organization.id)
    assert OnboardingSession.objects.filter(id=body["onboarding_session_id"]).exists()

    bootstrap = api_client.get(
        "/api/v1/auth/bootstrap/",
        **auth_headers(access_token),
    )
    assert bootstrap.status_code == 200
    hints = bootstrap.json()["permission_hints"]
    assert hints["can_create_establishment"] is True
    pending_ids = {
        item["establishment_id"] for item in bootstrap.json()["pending_onboarding_memberships"]
    }
    assert body["establishment_id"] in pending_ids


def test_create_establishment_api_ambiguous_org_without_selection_fails(api_client):
    organization = create_organization(name="No Selected Org")
    active = create_establishment(name="Active A", organization=organization)
    actor = create_user(username="no_selected_owner")
    create_membership(user=actor, establishment=active, role=ROLE_OWNER)
    other_org = create_organization(name="Other Org")
    other_active = create_establishment(name="Other Active", organization=other_org)
    create_membership(user=actor, establishment=other_active, role=ROLE_OWNER)

    api_client_b = APIClient(enforce_csrf_checks=True)
    access_token = login(api_client_b, user=actor)
    from houston.accounts.models import UserSession

    session = UserSession.objects.filter(user=actor, revoked_at__isnull=True).latest(
        "created_at"
    )
    session.selected_establishment = None
    session.save(update_fields=["selected_establishment", "updated_at"])

    response = post_create_establishment(
        api_client_b,
        access_token=access_token,
        name="Should Fail",
    )
    assert response.status_code == 403


def test_create_establishment_api_draft_only_org_without_selection(api_client):
    organization = create_organization(name="Draft Only Create Org")
    draft = create_establishment(
        name="Only Draft",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    actor = create_user(username="draft_only_create_owner")
    create_membership(user=actor, establishment=draft, role=ROLE_OWNER)
    access_token = login(api_client, user=actor)

    response = post_create_establishment(
        api_client,
        access_token=access_token,
        name="Second Draft",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["organization_id"] == str(organization.id)
    assert response.json()["status"] == Establishment.Status.DRAFT


def test_provision_draft_only_owner_succeeds():
    organization = create_organization(name="Draft Provision Org")
    draft = create_establishment(
        name="Draft A",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    actor = create_user(username="draft_provision_owner")
    create_membership(user=actor, establishment=draft, role=ROLE_OWNER)

    provision = provision_establishment_onboarding(
        actor=actor,
        organization=organization,
        name="Another Draft",
    )
    assert provision.establishment.status == Establishment.Status.DRAFT
    assert provision.establishment.organization_id == organization.id


def test_invite_organizational_owner_draft_only_and_tenant_isolation():
    from houston.establishments.services import (
        MembershipManagementForbiddenError,
        invite_organizational_owner_for_organization,
    )

    organization = create_organization(name="Draft Invite Org")
    draft = create_establishment(
        name="Draft Invite A",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    actor = create_user(username="draft_invite_owner")
    create_membership(user=actor, establishment=draft, role=ROLE_OWNER)

    result = invite_organizational_owner_for_organization(
        actor=actor,
        organization_id=organization.id,
        email="draft-org-owner@example.com",
        first_name="Draft",
        last_name="Owner",
    )
    assert result.membership.role == ROLE_OWNER
    assert result.membership.establishment_id == draft.id

    foreign = create_organization(name="Foreign Org")
    foreign_draft = create_establishment(
        name="Foreign Draft",
        organization=foreign,
        status=Establishment.Status.DRAFT,
    )
    create_membership(
        user=create_user(username="foreign_owner"),
        establishment=foreign_draft,
        role=ROLE_OWNER,
    )
    with pytest.raises(MembershipManagementForbiddenError):
        invite_organizational_owner_for_organization(
            actor=actor,
            organization_id=foreign.id,
            email="cross-tenant@example.com",
            first_name="Cross",
            last_name="Tenant",
        )


def test_create_establishment_api_forbids_director(api_client):
    organization = create_organization(name="Director Forbid Org")
    active = create_establishment(name="Active A", organization=organization)
    actor = create_user(username="api_director")
    create_membership(user=actor, establishment=active, role=ROLE_DIRECTOR)
    access_token = login(api_client, user=actor)
    switch_establishment(api_client, access_token=access_token, establishment_id=active.id)

    response = post_create_establishment(
        api_client,
        access_token=access_token,
        name="Director Draft",
    )
    assert response.status_code == 403


def test_create_establishment_api_duplicate_name(api_client):
    organization = create_organization(name="Dup API Org")
    active = create_establishment(name="Active A", organization=organization)
    create_establishment(name="Existing Name", organization=organization)
    actor = create_user(username="dup_owner")
    create_membership(user=actor, establishment=active, role=ROLE_OWNER)
    access_token = login(api_client, user=actor)
    switch_establishment(api_client, access_token=access_token, establishment_id=active.id)

    response = post_create_establishment(
        api_client,
        access_token=access_token,
        name="existing name",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "duplicate_establishment_name"
