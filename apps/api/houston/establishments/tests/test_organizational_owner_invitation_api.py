from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.accounts.services import tokens as auth_tokens
from houston.establishments.models import (
    Establishment,
    EstablishmentInvitation,
    EstablishmentMembership,
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
        {"identifier": identifier, "password": password},
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
        "role": ROLE_OWNER,
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
    establishment_id,
    actor: User,
    payload: dict | None = None,
):
    access_token = login(api_client, identifier=actor.email)
    csrf_token = ensure_csrf(api_client)
    return api_client.post(
        f"/api/v1/establishments/{establishment_id}/membership-invitations/",
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
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )


def create_pending_invitation(*, membership: EstablishmentMembership, raw_token: str):
    return EstablishmentInvitation.objects.create(
        membership=membership,
        token_digest=auth_tokens.digest_token(raw_token),
        expires_at=timezone.now() + timedelta(days=7),
    )


def test_owner_invite_fanout_creates_invited_memberships(api_client):
    organization = create_organization(name="Fanout Org")
    active_a = create_establishment(name="Active A", organization=organization)
    draft_b = create_establishment(
        name="Draft B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    deactivated = create_establishment(
        name="Deactivated C",
        organization=organization,
        status=Establishment.Status.DEACTIVATED,
    )
    actor = setup_full_coverage_actor(establishments=[active_a, draft_b])

    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="fanout-owner@example.com"),
    )

    assert response.status_code == 201, response.json()

    invitee = User.objects.get(email__iexact="fanout-owner@example.com")
    assert invitee.status == User.Status.PENDING

    memberships = list(EstablishmentMembership.objects.filter(user=invitee))
    assert {membership.establishment_id for membership in memberships} == {
        active_a.id,
        draft_b.id,
    }
    assert all(membership.role == ROLE_OWNER for membership in memberships)
    assert all(
        membership.status == EstablishmentMembership.Status.INVITED
        for membership in memberships
    )
    assert not EstablishmentMembership.objects.filter(
        user=invitee,
        establishment=deactivated,
    ).exists()

    body = response.json()
    assert body["invitation_token"]
    assert body["membership"]["role"] == ROLE_OWNER
    assert str(body["membership"]["establishment_id"]) == str(active_a.id)

    invitations = EstablishmentInvitation.objects.filter(
        membership__user=invitee,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    )
    assert invitations.count() == 1
    assert invitations.get().membership.establishment_id == active_a.id


def test_owner_invite_schedules_exactly_one_email(api_client):
    organization = create_organization(name="Email Org")
    active_a = create_establishment(name="Email A", organization=organization)
    draft_b = create_establishment(
        name="Email B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    actor = setup_full_coverage_actor(establishments=[active_a, draft_b], username="email_actor")

    with patch(
        "houston.establishments.invitation_email.schedule_establishment_invitation_email"
    ) as schedule_email:
        response = post_owner_invitation(
            api_client,
            establishment_id=active_a.id,
            actor=actor,
            payload=owner_invite_payload(email="single-email-owner@example.com"),
        )

    assert response.status_code == 201
    assert schedule_email.call_count == 1


def test_owner_invite_non_owner_conflict_rolls_back(api_client):
    organization = create_organization(name="Conflict Org")
    active_a = create_establishment(name="Conflict A", organization=organization)
    active_b = create_establishment(name="Conflict B", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a, active_b],
        username="conflict_actor",
    )
    pending = create_user(
        username="conflict_pending",
        email="conflict-owner@example.com",
        status=User.Status.PENDING,
    )
    # Path has compatible owner/invited so eligibility allows fan-out; sibling
    # establishment has non-owner → global owner_conflict + full rollback.
    create_membership(
        user=pending,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )
    create_membership(
        user=pending,
        establishment=active_b,
        role=EstablishmentMembership.Role.STAFF,
        membership_status=EstablishmentMembership.Status.INVITED,
    )

    before_statuses = {
        (membership.establishment_id, membership.role, membership.status)
        for membership in EstablishmentMembership.objects.filter(user=pending)
    }
    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="conflict-owner@example.com"),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_owner_conflict"
    after_statuses = {
        (membership.establishment_id, membership.role, membership.status)
        for membership in EstablishmentMembership.objects.filter(user=pending)
    }
    assert after_statuses == before_statuses
    assert not EstablishmentInvitation.objects.filter(membership__user=pending).exists()


def test_owner_invite_anchor_active_returns_duplicate_without_email(api_client):
    organization = create_organization(name="Anchor Active Org")
    active_a = create_establishment(name="Anchor Active A", organization=organization)
    active_b = create_establishment(name="Anchor Active B", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a, active_b],
        username="anchor_active_actor",
    )
    existing = create_user(
        username="already_active_owner",
        email="active-anchor@example.com",
        status=User.Status.PENDING,
    )
    create_membership(
        user=existing,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        user=existing,
        establishment=active_b,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )

    with patch(
        "houston.establishments.invitation_email.schedule_establishment_invitation_email"
    ) as schedule_email:
        response = post_owner_invitation(
            api_client,
            establishment_id=active_a.id,
            actor=actor,
            payload=owner_invite_payload(email="active-anchor@example.com"),
        )

    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_duplicate"
    schedule_email.assert_not_called()
    assert not EstablishmentInvitation.objects.filter(membership__user=existing).exists()


def test_owner_invite_reissues_token_for_invited_anchor(api_client):
    organization = create_organization(name="Reissue Org")
    active_a = create_establishment(name="Reissue A", organization=organization)
    active_b = create_establishment(name="Reissue B", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a, active_b],
        username="reissue_actor",
    )
    pending = create_user(
        username="reissue_pending",
        email="reissue-owner@example.com",
        status=User.Status.PENDING,
    )
    anchor = create_membership(
        user=pending,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )
    create_membership(
        user=pending,
        establishment=active_b,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )
    old_invitation = create_pending_invitation(
        membership=anchor,
        raw_token="old-owner-token",
    )

    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="reissue-owner@example.com"),
    )

    assert response.status_code == 201
    old_invitation.refresh_from_db()
    assert old_invitation.revoked_at is not None
    new_digest = auth_tokens.digest_token(response.json()["invitation_token"])
    assert new_digest != old_invitation.token_digest
    assert EstablishmentInvitation.objects.filter(
        membership=anchor,
        token_digest=new_digest,
        revoked_at__isnull=True,
        accepted_at__isnull=True,
    ).exists()


def test_owner_invite_sequential_reinvite_after_commit_reissues_token_and_email(api_client):
    organization = create_organization(name="Sequential Reinvite Org")
    active_a = create_establishment(name="Sequential A", organization=organization)
    active_b = create_establishment(name="Sequential B", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a, active_b],
        username="sequential_reinvite_actor",
    )
    email = "sequential-reinvite-owner@example.com"

    with patch(
        "houston.establishments.invitation_email.schedule_establishment_invitation_email"
    ) as schedule_email:
        first_response = post_owner_invitation(
            api_client,
            establishment_id=active_a.id,
            actor=actor,
            payload=owner_invite_payload(email=email),
        )
        assert first_response.status_code == 201
        first_token = first_response.json()["invitation_token"]
        first_digest = auth_tokens.digest_token(first_token)
        first_invitation = EstablishmentInvitation.objects.get(token_digest=first_digest)
        assert first_invitation.revoked_at is None
        assert schedule_email.call_count == 1

        second_response = post_owner_invitation(
            api_client,
            establishment_id=active_a.id,
            actor=actor,
            payload=owner_invite_payload(email=email),
        )

    assert second_response.status_code == 201
    second_token = second_response.json()["invitation_token"]
    second_digest = auth_tokens.digest_token(second_token)
    assert second_digest != first_digest

    first_invitation.refresh_from_db()
    assert first_invitation.revoked_at is not None
    assert EstablishmentInvitation.objects.filter(
        token_digest=second_digest,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    ).exists()
    assert schedule_email.call_count == 2


def test_owner_invite_resumes_deactivated_anchor(api_client):
    organization = create_organization(name="Resume Org")
    active_a = create_establishment(name="Resume A", organization=organization)
    active_b = create_establishment(name="Resume B", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a, active_b],
        username="resume_actor",
    )
    pending = create_user(
        username="resume_pending",
        email="resume-owner@example.com",
        status=User.Status.PENDING,
    )
    create_membership(
        user=pending,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )
    create_membership(
        user=pending,
        establishment=active_b,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )

    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="resume-owner@example.com"),
    )

    assert response.status_code == 201
    statuses = set(
        EstablishmentMembership.objects.filter(user=pending).values_list("status", flat=True)
    )
    assert statuses == {EstablishmentMembership.Status.INVITED}


@pytest.mark.parametrize(
    "user_status",
    [User.Status.ACTIVE, User.Status.SUSPENDED, User.Status.ANONYMIZED],
)
def test_owner_invite_rejects_non_pending_user(api_client, user_status):
    establishment = create_establishment(name=f"Reject {user_status}")
    actor = setup_full_coverage_actor(
        establishments=[establishment],
        username=f"reject_{user_status}_actor",
    )
    create_user(
        username=f"existing_{user_status}",
        email=f"{user_status}-owner@example.com",
        status=user_status,
    )

    response = post_owner_invitation(
        api_client,
        establishment_id=establishment.id,
        actor=actor,
        payload=owner_invite_payload(email=f"{user_status}-owner@example.com"),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_user_exists"


def test_owner_invite_actor_without_full_coverage_returns_invariant(api_client):
    organization = create_organization(name="Partial Actor Org")
    active_a = create_establishment(name="Partial A", organization=organization)
    create_establishment(name="Partial B", organization=organization)
    actor = create_user(username="partial_actor")
    create_membership(user=actor, establishment=active_a, role=ROLE_OWNER)

    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="partial-invitee@example.com"),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "organizational_owner_invariant_conflict"
    assert not User.objects.filter(email__iexact="partial-invitee@example.com").exists()


def test_accept_owner_activates_all_org_invited_memberships(api_client):
    organization = create_organization(name="Accept Org")
    active_a = create_establishment(name="Accept A", organization=organization)
    draft_b = create_establishment(
        name="Accept B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    other_org = create_organization(name="Other Org")
    other_est = create_establishment(name="Other Est", organization=other_org)
    deactivated = create_establishment(
        name="Accept Deactivated",
        organization=organization,
        status=Establishment.Status.DEACTIVATED,
    )
    actor = setup_full_coverage_actor(
        establishments=[active_a, draft_b],
        username="accept_actor",
    )

    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="accept-owner@example.com"),
    )
    assert response.status_code == 201
    token = response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="accept-owner@example.com")
    create_membership(
        user=invitee,
        establishment=other_est,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )
    create_membership(
        user=invitee,
        establishment=deactivated,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        accept_response = post_accept(APIClient(enforce_csrf_checks=True), token=token)
    assert accept_response.status_code == 201, accept_response.json()
    assert str(accept_response.data["establishment_id"]) == str(active_a.id)

    invitee.refresh_from_db()
    assert invitee.status == User.Status.ACTIVE

    membership_a = EstablishmentMembership.objects.get(
        user=invitee,
        establishment=active_a,
        role=ROLE_OWNER,
    )
    membership_b = EstablishmentMembership.objects.get(
        user=invitee,
        establishment=draft_b,
    )
    assert membership_a.status == EstablishmentMembership.Status.ACTIVE
    assert membership_b.status == EstablishmentMembership.Status.ACTIVE
    assert (
        EstablishmentMembership.objects.get(
            user=invitee,
            establishment=other_est,
        ).status
        == EstablishmentMembership.Status.INVITED
    )
    assert (
        EstablishmentMembership.objects.get(
            user=invitee,
            establishment=deactivated,
        ).status
        == EstablishmentMembership.Status.INVITED
    )

    updated_calls = [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.updated"
    ]
    assert {
        (call.kwargs["membership_id"], call.kwargs["establishment_id"])
        for call in updated_calls
    } == {
        (membership_a.id, active_a.id),
        (membership_b.id, draft_b.id),
    }


def test_accept_owner_heals_missing_coverage_before_activate(api_client):
    organization = create_organization(name="Heal Accept Org")
    active_a = create_establishment(name="Heal A", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a],
        username="heal_actor",
    )
    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="heal-owner@example.com"),
    )
    assert response.status_code == 201
    token = response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="heal-owner@example.com")

    # Gap: new draft/active establishment after invite, without invitee membership.
    draft_b = create_establishment(
        name="Heal B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    create_membership(user=actor, establishment=draft_b, role=ROLE_OWNER)
    active_c = create_establishment(name="Heal C", organization=organization)
    create_membership(user=actor, establishment=active_c, role=ROLE_OWNER)

    assert not EstablishmentMembership.objects.filter(
        user=invitee,
        establishment__in=[draft_b, active_c],
    ).exists()

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        accept_response = post_accept(APIClient(enforce_csrf_checks=True), token=token)
    assert accept_response.status_code == 201, accept_response.json()

    invitee.refresh_from_db()
    assert invitee.status == User.Status.ACTIVE
    memberships = {
        membership.establishment_id: membership
        for membership in EstablishmentMembership.objects.filter(
            user=invitee,
            establishment__in=[active_a, draft_b, active_c],
        )
    }
    assert set(memberships) == {active_a.id, draft_b.id, active_c.id}
    assert {
        membership.status for membership in memberships.values()
    } == {EstablishmentMembership.Status.ACTIVE}
    assert {
        membership.role for membership in memberships.values()
    } == {ROLE_OWNER}

    updated_calls = [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.updated"
    ]
    assert {
        (call.kwargs["membership_id"], call.kwargs["establishment_id"])
        for call in updated_calls
    } == {
        (memberships[active_a.id].id, active_a.id),
        (memberships[draft_b.id].id, draft_b.id),
        (memberships[active_c.id].id, active_c.id),
    }


def test_accept_owner_heal_rolls_back_when_non_owner_conflict(api_client):
    organization = create_organization(name="Heal Rollback Org")
    active_a = create_establishment(name="Heal Rollback A", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a],
        username="heal_rollback_actor",
    )
    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="heal-rollback-owner@example.com"),
    )
    assert response.status_code == 201
    token = response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="heal-rollback-owner@example.com")
    invitation = EstablishmentInvitation.objects.get(
        token_digest=auth_tokens.digest_token(token),
    )

    # Repairable gap on draft_b, plus a non-owner conflict on active_c.
    draft_b = create_establishment(
        name="Heal Rollback B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    create_membership(user=actor, establishment=draft_b, role=ROLE_OWNER)
    active_c = create_establishment(name="Heal Rollback C", organization=organization)
    create_membership(user=actor, establishment=active_c, role=ROLE_OWNER)
    create_membership(
        user=invitee,
        establishment=active_c,
        role=EstablishmentMembership.Role.STAFF,
        membership_status=EstablishmentMembership.Status.INVITED,
    )

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        accept_response = post_accept(APIClient(enforce_csrf_checks=True), token=token)

    assert accept_response.status_code == 409
    assert accept_response.json()["code"] == "organizational_owner_invariant_conflict"
    invitee.refresh_from_db()
    assert invitee.status == User.Status.PENDING
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert invitation.revoked_at is None
    assert not EstablishmentMembership.objects.filter(
        user=invitee,
        establishment=draft_b,
    ).exists()
    assert (
        EstablishmentMembership.objects.get(
            user=invitee,
            establishment=active_a,
        ).status
        == EstablishmentMembership.Status.INVITED
    )
    assert (
        EstablishmentMembership.objects.get(
            user=invitee,
            establishment=active_c,
        ).role
        == EstablishmentMembership.Role.STAFF
    )
    assert not [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.updated"
    ]


def test_accept_owner_with_active_membership_under_pending_returns_invariant(api_client):
    organization = create_organization(name="Active Under Pending Org")
    active_a = create_establishment(name="AUP A", organization=organization)
    active_b = create_establishment(name="AUP B", organization=organization)
    pending = create_user(
        username="aup_pending",
        email="aup-owner@example.com",
        status=User.Status.PENDING,
    )
    anchor = create_membership(
        user=pending,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )
    create_membership(
        user=pending,
        establishment=active_b,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.ACTIVE,
    )
    create_pending_invitation(membership=anchor, raw_token="aup-token")

    with patch("houston.realtime.broadcast.schedule_access_event") as access_mock:
        accept_response = post_accept(api_client, token="aup-token")
    assert accept_response.status_code == 409
    assert accept_response.json()["code"] == "organizational_owner_invariant_conflict"
    assert not [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.updated"
    ]


def test_accept_owner_revokes_other_pending_tokens(api_client):
    organization = create_organization(name="Revoke Org")
    active_a = create_establishment(name="Revoke A", organization=organization)
    active_b = create_establishment(name="Revoke B", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a, active_b],
        username="revoke_actor",
    )
    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="revoke-owner@example.com"),
    )
    assert response.status_code == 201
    token = response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="revoke-owner@example.com")
    other_membership = EstablishmentMembership.objects.get(
        user=invitee,
        establishment=active_b,
    )
    residual = create_pending_invitation(
        membership=other_membership,
        raw_token="residual-token",
    )

    accept_response = post_accept(APIClient(enforce_csrf_checks=True), token=token)
    assert accept_response.status_code == 201

    residual.refresh_from_db()
    assert residual.revoked_at is not None
    anchor_invitation = EstablishmentInvitation.objects.get(
        token_digest=auth_tokens.digest_token(token),
    )
    assert anchor_invitation.accepted_at is not None
    assert anchor_invitation.revoked_at is None


def test_accept_owner_rejects_non_pending_user(api_client):
    organization = create_organization(name="Non Pending Accept Org")
    active_a = create_establishment(name="NPA A", organization=organization)
    actor = setup_full_coverage_actor(establishments=[active_a], username="npa_actor")
    response = post_owner_invitation(
        api_client,
        establishment_id=active_a.id,
        actor=actor,
        payload=owner_invite_payload(email="npa-owner@example.com"),
    )
    assert response.status_code == 201
    token = response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="npa-owner@example.com")
    invitee.status = User.Status.ACTIVE
    invitee.save(update_fields=["status"])

    accept_response = post_accept(APIClient(enforce_csrf_checks=True), token=token)
    assert accept_response.status_code == 400
    assert accept_response.json()["code"] == "invitation_invalid"


def test_accept_owner_invalid_when_organization_inactive(api_client):
    organization = create_organization(name="Inactive Org Accept")
    active_a = create_establishment(name="Inactive Org A", organization=organization)
    pending = create_user(
        username="inactive_org_pending",
        email="inactive-org-owner@example.com",
        status=User.Status.PENDING,
    )
    anchor = create_membership(
        user=pending,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )
    create_pending_invitation(membership=anchor, raw_token="inactive-org-token")
    organization.status = Organization.Status.SUSPENDED
    organization.save(update_fields=["status"])

    accept_response = post_accept(api_client, token="inactive-org-token")
    assert accept_response.status_code == 400
    assert accept_response.json()["code"] == "invitation_invalid"


def test_accept_owner_invalid_when_anchor_establishment_not_active(api_client):
    organization = create_organization(name="Draft Anchor Org")
    active_a = create_establishment(name="Draft Anchor A", organization=organization)
    pending = create_user(
        username="draft_anchor_pending",
        email="draft-anchor-owner@example.com",
        status=User.Status.PENDING,
    )
    anchor = create_membership(
        user=pending,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )
    create_pending_invitation(membership=anchor, raw_token="draft-anchor-token")
    active_a.status = Establishment.Status.DRAFT
    active_a.save(update_fields=["status"])

    accept_response = post_accept(api_client, token="draft-anchor-token")
    assert accept_response.status_code == 400
    assert accept_response.json()["code"] == "invitation_invalid"


@pytest.mark.django_db(transaction=True)
def test_concurrent_owner_invitations_same_email_same_org():
    organization = create_organization(name="Concurrent Owner Org")
    active_a = create_establishment(name="Concurrent A", organization=organization)
    active_b = create_establishment(name="Concurrent B", organization=organization)
    actor = setup_full_coverage_actor(
        establishments=[active_a, active_b],
        username="concurrent_owner_actor",
    )
    email = "concurrent-owner@example.com"
    payload = owner_invite_payload(email=email)

    with patch(
        "houston.establishments.invitation_email.schedule_establishment_invitation_email"
    ) as schedule_email:

        def invite(_: int) -> tuple[int, str | None]:
            close_old_connections()
            try:
                client = APIClient(enforce_csrf_checks=True)
                access_token = login(client, identifier=actor.email)
                csrf_token = ensure_csrf(client)
                response = client.post(
                    f"/api/v1/establishments/{active_a.id}/membership-invitations/",
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
    assert len(statuses) == 2
    assert all(status in {201, 409} for status in statuses)
    assert statuses.count(201) >= 1
    # True races may yield 201+409 after revalidation under lock; org-lock
    # serialization may yield create then reissue (201+201).
    if statuses.count(409) == 1:
        conflict_codes = [code for code in codes if code is not None]
        assert len(conflict_codes) == 1
        assert conflict_codes[0] in {
            "membership_invitation_duplicate",
            "membership_invitation_user_exists",
            "membership_invitation_owner_conflict",
            "organizational_owner_invariant_conflict",
        }
        assert schedule_email.call_count == 1
    else:
        assert statuses.count(201) == 2
        assert schedule_email.call_count == 2

    users = list(User.objects.filter(email__iexact=email))
    assert len(users) == 1
    invitee = users[0]
    for establishment in (active_a, active_b):
        assert (
            EstablishmentMembership.objects.filter(
                user=invitee,
                establishment=establishment,
                role=ROLE_OWNER,
            ).count()
            == 1
        )
        membership = EstablishmentMembership.objects.get(
            user=invitee,
            establishment=establishment,
            role=ROLE_OWNER,
        )
        assert membership.status == EstablishmentMembership.Status.INVITED

    assert (
        EstablishmentInvitation.objects.filter(
            membership__user=invitee,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        ).count()
        == 1
    )
