from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.services import (
    DuplicateEstablishmentNameError,
    InvalidEstablishmentCreationError,
    OrganizationalOwnerInvariantConflictError,
    create_establishment_for_organization,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db

ROLE_OWNER = EstablishmentMembership.Role.OWNER
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


def create_organization(*, name: str = "Org") -> Organization:
    return Organization.objects.create(
        name=f"{name} {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )


def create_establishment(
    *,
    name: str = "Demo Hotel",
    organization: Organization | None = None,
    status: str = Establishment.Status.ACTIVE,
) -> Establishment:
    if organization is None:
        organization = create_organization(name=f"{name} Group")
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
    membership_status: str = EstablishmentMembership.Status.ACTIVE,
) -> EstablishmentMembership:
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=membership_status,
    )


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return api_client.cookies["csrftoken"].value


def login(api_client: APIClient, *, identifier: str, password: str = TEST_PASSWORD) -> str:
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password, "refresh_token_transport": "cookie"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(access_token: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}


def owner_invite_payload(*, email: str = "new-owner@example.com") -> dict:
    return {
        "email": email,
        "first_name": "Nora",
        "last_name": "Owner",
    }


def setup_full_coverage_actor(
    *,
    establishments: list[Establishment],
    username: str = "full_coverage_owner",
) -> User:
    actor = create_user(username=username)
    for establishment in establishments:
        create_membership(user=actor, establishment=establishment, role=ROLE_OWNER)
    return actor


def post_owner_invitation(
    api_client: APIClient,
    *,
    organization_id,
    actor: User,
    payload: dict | None = None,
):
    access_token = login(api_client, identifier=actor.email)
    csrf_token = ensure_csrf(api_client)
    return api_client.post(
        f"/api/v1/organizations/{organization_id}/owner-invitations/",
        payload or owner_invite_payload(),
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )


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


def _owner_membership(*, user: User, establishment: Establishment) -> EstablishmentMembership:
    return EstablishmentMembership.objects.get(
        user=user,
        establishment=establishment,
        role=ROLE_OWNER,
    )


def test_create_establishment_for_organization_seeds_then_accept(api_client):
    organization = create_organization(name="Create Then Accept Org")
    active_a = create_establishment(name="Seed A", organization=organization)
    actor = setup_full_coverage_actor(establishments=[active_a], username="cta_actor")

    response = post_owner_invitation(
        api_client,
        organization_id=organization.id,
        actor=actor,
        payload=owner_invite_payload(email="cta-owner@example.com"),
    )
    assert response.status_code == 201
    token = response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="cta-owner@example.com")

    draft_b = create_establishment_for_organization(
        organization_id=organization.id,
        name="Seed B",
    )
    assert draft_b.status == Establishment.Status.DRAFT
    invitee_b = _owner_membership(user=invitee, establishment=draft_b)
    assert invitee_b.status == EstablishmentMembership.Status.INVITED
    assert _owner_membership(user=actor, establishment=draft_b).status == (
        EstablishmentMembership.Status.ACTIVE
    )

    accept_response = post_accept(APIClient(enforce_csrf_checks=True), token=token)
    assert accept_response.status_code == 201, accept_response.json()

    invitee.refresh_from_db()
    assert invitee.status == User.Status.ACTIVE
    for establishment in (active_a, draft_b):
        membership = _owner_membership(user=invitee, establishment=establishment)
        assert membership.status == EstablishmentMembership.Status.ACTIVE


def test_accept_then_create_establishment_seeds_active_owner(api_client):
    organization = create_organization(name="Accept Then Create Org")
    active_a = create_establishment(name="ATC A", organization=organization)
    actor = setup_full_coverage_actor(establishments=[active_a], username="atc_actor")

    response = post_owner_invitation(
        api_client,
        organization_id=organization.id,
        actor=actor,
        payload=owner_invite_payload(email="atc-owner@example.com"),
    )
    assert response.status_code == 201
    token = response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="atc-owner@example.com")

    accept_response = post_accept(APIClient(enforce_csrf_checks=True), token=token)
    assert accept_response.status_code == 201, accept_response.json()

    draft_b = create_establishment_for_organization(
        organization_id=organization.id,
        name="ATC B",
    )
    membership = _owner_membership(user=invitee, establishment=draft_b)
    assert membership.status == EstablishmentMembership.Status.ACTIVE


@pytest.mark.django_db(transaction=True)
def test_concurrent_accept_and_create_establishment_preserve_coverage():
    organization = create_organization(name="Concurrent Create Accept Org")
    active_a = create_establishment(name="CCA A", organization=organization)
    actor = setup_full_coverage_actor(establishments=[active_a], username="cca_actor")
    client = APIClient(enforce_csrf_checks=True)
    response = post_owner_invitation(
        client,
        organization_id=organization.id,
        actor=actor,
        payload=owner_invite_payload(email="cca-owner@example.com"),
    )
    assert response.status_code == 201
    token = response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="cca-owner@example.com")

    barrier = threading.Barrier(2)
    outcomes: dict[str, object] = {}

    def accept_worker() -> None:
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            accept_client = APIClient(enforce_csrf_checks=True)
            outcomes["accept"] = post_accept(
                accept_client,
                token=token,
                password=REGISTRATION_PASSWORD,
            ).status_code
        finally:
            close_old_connections()

    def create_worker() -> None:
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            outcomes["created"] = create_establishment_for_organization(
                organization_id=organization.id,
                name="CCA Concurrent B",
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(accept_worker), executor.submit(create_worker)]
        for future in futures:
            future.result(timeout=30)

    assert outcomes["accept"] == 201
    created = outcomes["created"]
    assert isinstance(created, Establishment)

    invitee.refresh_from_db()
    assert invitee.status == User.Status.ACTIVE
    for establishment in (active_a, created):
        membership = _owner_membership(user=invitee, establishment=establishment)
        assert membership.status == EstablishmentMembership.Status.ACTIVE
        assert membership.role == ROLE_OWNER


def test_create_establishment_seeds_homogeneous_owner_statuses():
    organization = create_organization(name="Multi Status Seed Org")
    active_a = create_establishment(name="MSS A", organization=organization)

    active_owner = create_user(username="mss_active", status=User.Status.ACTIVE)
    create_membership(
        user=active_owner,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.ACTIVE,
    )

    invited_owner = create_user(username="mss_invited", status=User.Status.PENDING)
    create_membership(
        user=invited_owner,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )

    deactivated_owner = create_user(username="mss_deactivated", status=User.Status.ACTIVE)
    create_membership(
        user=deactivated_owner,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        draft_b = create_establishment_for_organization(
            organization_id=organization.id,
            name="MSS B",
        )

    assert (
        _owner_membership(user=active_owner, establishment=draft_b).status
        == EstablishmentMembership.Status.ACTIVE
    )
    assert (
        _owner_membership(user=invited_owner, establishment=draft_b).status
        == EstablishmentMembership.Status.INVITED
    )
    assert (
        _owner_membership(user=deactivated_owner, establishment=draft_b).status
        == EstablishmentMembership.Status.DEACTIVATED
    )

    updated_calls = [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.updated"
    ]
    active_seed = _owner_membership(user=active_owner, establishment=draft_b)
    assert {
        (call.kwargs["membership_id"], call.kwargs["establishment_id"])
        for call in updated_calls
    } == {(active_seed.id, draft_b.id)}


def test_create_establishment_active_seed_emits_membership_updated_with_ids():
    organization = create_organization(name="Active Event Org")
    active_a = create_establishment(name="AE A", organization=organization)
    actor = setup_full_coverage_actor(establishments=[active_a], username="ae_actor")

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        draft_b = create_establishment_for_organization(
            organization_id=organization.id,
            name="AE B",
        )

    seeded = _owner_membership(user=actor, establishment=draft_b)
    assert seeded.status == EstablishmentMembership.Status.ACTIVE
    updated_calls = [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.updated"
    ]
    assert len(updated_calls) == 1
    assert updated_calls[0].kwargs["membership_id"] == seeded.id
    assert updated_calls[0].kwargs["establishment_id"] == draft_b.id


def test_create_establishment_invited_and_deactivated_emit_no_access_events():
    organization = create_organization(name="No Event Org")
    active_a = create_establishment(name="NE A", organization=organization)

    invited_owner = create_user(username="ne_invited", status=User.Status.PENDING)
    create_membership(
        user=invited_owner,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )
    deactivated_owner = create_user(username="ne_deactivated", status=User.Status.ACTIVE)
    create_membership(
        user=deactivated_owner,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        create_establishment_for_organization(
            organization_id=organization.id,
            name="NE B",
        )

    assert access_mock.call_count == 0


def test_create_establishment_conflict_rolls_back_establishment_memberships_and_events():
    organization = create_organization(name="Rollback Org")
    active_a = create_establishment(name="RB A", organization=organization)
    active_b = create_establishment(name="RB B", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a, active_b],
        username="rb_actor",
    )
    conflict_user = create_user(username="rb_conflict", status=User.Status.ACTIVE)
    create_membership(
        user=conflict_user,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        user=conflict_user,
        establishment=active_b,
        role=EstablishmentMembership.Role.STAFF,
        membership_status=EstablishmentMembership.Status.ACTIVE,
    )

    before_ids = set(
        Establishment.objects.filter(organization=organization).values_list("id", flat=True)
    )
    before_membership_count = EstablishmentMembership.objects.filter(
        establishment__organization=organization,
    ).count()

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        with pytest.raises(OrganizationalOwnerInvariantConflictError):
            create_establishment_for_organization(
                organization_id=organization.id,
                name="RB Should Not Persist",
            )

    assert (
        set(Establishment.objects.filter(organization=organization).values_list("id", flat=True))
        == before_ids
    )
    assert (
        EstablishmentMembership.objects.filter(
            establishment__organization=organization,
        ).count()
        == before_membership_count
    )
    assert access_mock.call_count == 0
    assert not Establishment.objects.filter(name="RB Should Not Persist").exists()
    assert EstablishmentMembership.objects.filter(user=actor).count() == 2


def test_create_establishment_rejects_active_initial_status():
    organization = create_organization(name="Reject Active Org")
    create_establishment(name="RA A", organization=organization)

    with pytest.raises(InvalidEstablishmentCreationError, match="draft"):
        create_establishment_for_organization(
            organization_id=organization.id,
            name="RA Active",
            status=Establishment.Status.ACTIVE,
        )

    assert not Establishment.objects.filter(
        organization=organization,
        name="RA Active",
    ).exists()


def test_create_establishment_strips_name_and_rejects_duplicate_case_insensitive():
    organization = create_organization(name="Name Uniq Org")
    create_establishment(name="Hotel Alpha", organization=organization)

    created = create_establishment_for_organization(
        organization_id=organization.id,
        name="  Hotel Beta  ",
    )
    assert created.name == "Hotel Beta"

    with pytest.raises(DuplicateEstablishmentNameError):
        create_establishment_for_organization(
            organization_id=organization.id,
            name="  hotel alpha ",
        )

    deactivated = create_establishment(
        name="Hotel Gamma",
        organization=organization,
        status=Establishment.Status.DEACTIVATED,
    )
    assert deactivated.status == Establishment.Status.DEACTIVATED
    with pytest.raises(DuplicateEstablishmentNameError):
        create_establishment_for_organization(
            organization_id=organization.id,
            name="HOTEL GAMMA",
        )


@pytest.mark.django_db(transaction=True)
def test_create_establishment_concurrent_duplicate_name_no_partial_rows():
    organization = create_organization(name="Concurrent Name Org")
    create_establishment(name="Seed A", organization=organization)
    barrier = threading.Barrier(2)
    outcomes: dict[str, object] = {}

    def worker(label: str) -> None:
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            outcomes[label] = create_establishment_for_organization(
                organization_id=organization.id,
                name="Concurrent Hotel",
            )
        except Exception as exc:  # noqa: BLE001 — capture for assertion
            outcomes[label] = exc
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(worker, "a"), executor.submit(worker, "b")]
        for future in futures:
            future.result(timeout=10)

    successes = [value for value in outcomes.values() if isinstance(value, Establishment)]
    failures = [
        value for value in outcomes.values() if isinstance(value, DuplicateEstablishmentNameError)
    ]
    assert len(successes) == 1
    assert len(failures) == 1
    assert (
        Establishment.objects.filter(
            organization=organization,
            name="Concurrent Hotel",
        ).count()
        == 1
    )


def test_accept_owner_heals_missing_coverage_on_raw_orm_establishment(api_client):
    """Defense path: ORM create without seed must still heal on accept."""
    organization = create_organization(name="Heal ORM Org")
    active_a = create_establishment(name="Heal ORM A", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a],
        username="heal_orm_actor",
    )
    response = post_owner_invitation(
        api_client,
        organization_id=organization.id,
        actor=actor,
        payload=owner_invite_payload(email="heal-orm-owner@example.com"),
    )
    assert response.status_code == 201
    token = response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="heal-orm-owner@example.com")

    draft_b = Establishment.objects.create(
        name="Heal ORM B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    create_membership(user=actor, establishment=draft_b, role=ROLE_OWNER)

    assert not EstablishmentMembership.objects.filter(
        user=invitee,
        establishment=draft_b,
    ).exists()

    accept_response = post_accept(APIClient(enforce_csrf_checks=True), token=token)
    assert accept_response.status_code == 201, accept_response.json()

    membership = _owner_membership(user=invitee, establishment=draft_b)
    assert membership.status == EstablishmentMembership.Status.ACTIVE


def test_create_establishment_rejects_inactive_organization():
    organization = Organization.objects.create(
        name=f"Inactive Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.SUSPENDED,
    )

    with pytest.raises(InvalidEstablishmentCreationError, match="active organization"):
        create_establishment_for_organization(
            organization_id=organization.id,
            name="Should Fail",
        )
