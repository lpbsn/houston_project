from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User, UserSession
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


def setup_full_coverage_owner(
    *,
    establishments: list[Establishment],
    username: str,
    membership_status: str = EstablishmentMembership.Status.ACTIVE,
) -> User:
    user = create_user(username=username)
    for establishment in establishments:
        create_membership(
            user=user,
            establishment=establishment,
            role=ROLE_OWNER,
            membership_status=membership_status,
        )
    return user


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


def membership_url(*, establishment_id, membership_id, action: str) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/memberships/"
        f"{membership_id}/{action}/"
    )


def switch_establishment(
    api_client: APIClient,
    *,
    access_token: str,
    establishment_id,
) -> str:
    response = api_client.post(
        "/api/v1/auth/switch_establishment/",
        {"establishment_id": str(establishment_id)},
        format="json",
        **auth_headers(access_token),
    )
    assert response.status_code == 200, response.json()
    return response.json().get("access_token", access_token)


def post_membership_action(
    api_client: APIClient,
    *,
    actor: User,
    establishment_id,
    membership_id,
    action: str,
):
    access_token = login(api_client, identifier=actor.email)
    access_token = switch_establishment(
        api_client,
        access_token=access_token,
        establishment_id=establishment_id,
    )
    return api_client.post(
        membership_url(
            establishment_id=establishment_id,
            membership_id=membership_id,
            action=action,
        ),
        format="json",
        **auth_headers(access_token),
    )


def create_session(*, user: User, selected_establishment: Establishment | None) -> UserSession:
    return UserSession.objects.create(
        user=user,
        selected_establishment=selected_establishment,
        refresh_token_family_id=uuid.uuid4(),
        refresh_expires_at=timezone.now() + timedelta(hours=1),
        absolute_expires_at=timezone.now() + timedelta(days=1),
    )


def owner_statuses_for_user(*, user: User, establishments: list[Establishment]) -> set[str]:
    return {
        EstablishmentMembership.objects.get(
            user=user,
            establishment=establishment,
        ).status
        for establishment in establishments
    }


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


def owner_invite_payload(*, email: str = "new-owner@example.com") -> dict:
    return {
        "email": email,
        "first_name": "Nora",
        "last_name": "Owner",
    }


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


def test_owner_deactivate_fanout_across_draft_and_active(api_client):
    organization = create_organization(name="Deactivate Fanout Org")
    active_a = create_establishment(name="Deactivate A", organization=organization)
    draft_b = create_establishment(
        name="Deactivate B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    deactivated = create_establishment(
        name="Deactivate C",
        organization=organization,
        status=Establishment.Status.DEACTIVATED,
    )
    other_org = create_organization(name="Other Org")
    other_est = create_establishment(name="Other Est", organization=other_org)

    actor = setup_full_coverage_owner(
        establishments=[active_a, draft_b],
        username="deactivate_actor",
    )
    target = setup_full_coverage_owner(
        establishments=[active_a, draft_b],
        username="deactivate_target",
    )
    create_membership(user=target, establishment=other_est, role=ROLE_OWNER)
    create_membership(
        user=target,
        establishment=deactivated,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.ACTIVE,
    )
    path_membership = EstablishmentMembership.objects.get(
        user=target,
        establishment=active_a,
    )

    with (
        patch("houston.chat.services.handle_membership_chat_deactivation") as chat_mock,
        patch("houston.realtime.broadcast.schedule_access_event") as access_mock,
        patch(
            "houston.establishments.invitation_email.schedule_establishment_invitation_email"
        ) as email_mock,
    ):
        response = post_membership_action(
            api_client,
            actor=actor,
            establishment_id=active_a.id,
            membership_id=path_membership.id,
            action="deactivate",
        )

    assert response.status_code == 200, response.json()
    assert response.json()["status"] == EstablishmentMembership.Status.DEACTIVATED
    assert owner_statuses_for_user(user=target, establishments=[active_a, draft_b]) == {
        EstablishmentMembership.Status.DEACTIVATED
    }
    assert (
        EstablishmentMembership.objects.get(
            user=target,
            establishment=deactivated,
        ).status
        == EstablishmentMembership.Status.ACTIVE
    )
    assert (
        EstablishmentMembership.objects.get(
            user=target,
            establishment=other_est,
        ).status
        == EstablishmentMembership.Status.ACTIVE
    )
    assert chat_mock.call_count == 2
    assert access_mock.call_count == 2
    email_mock.assert_not_called()


def test_owner_reactivate_fanout_without_token_or_email(api_client):
    organization = create_organization(name="Reactivate Fanout Org")
    active_a = create_establishment(name="Reactivate A", organization=organization)
    draft_b = create_establishment(
        name="Reactivate B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    actor = setup_full_coverage_owner(
        establishments=[active_a, draft_b],
        username="reactivate_actor",
    )
    target = setup_full_coverage_owner(
        establishments=[active_a, draft_b],
        username="reactivate_target",
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )
    path_membership = EstablishmentMembership.objects.get(
        user=target,
        establishment=active_a,
    )
    invitations_before = EstablishmentInvitation.objects.count()

    with (
        patch(
            "houston.establishments.invitation_email.schedule_establishment_invitation_email"
        ) as email_mock,
        patch("houston.realtime.broadcast.schedule_access_event") as access_mock,
    ):
        response = post_membership_action(
            api_client,
            actor=actor,
            establishment_id=active_a.id,
            membership_id=path_membership.id,
            action="activate",
        )

    assert response.status_code == 200, response.json()
    assert response.json()["status"] == EstablishmentMembership.Status.ACTIVE
    assert owner_statuses_for_user(user=target, establishments=[active_a, draft_b]) == {
        EstablishmentMembership.Status.ACTIVE
    }
    assert EstablishmentInvitation.objects.count() == invitations_before
    email_mock.assert_not_called()
    assert access_mock.call_count == 2


def test_owner_deactivate_blocks_last_full_coverage_owner(api_client):
    organization = create_organization(name="Last Owner Org")
    active_a = create_establishment(name="Last A", organization=organization)
    draft_b = create_establishment(
        name="Last B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    actor = setup_full_coverage_owner(
        establishments=[active_a, draft_b],
        username="last_owner_actor",
    )
    path_membership = EstablishmentMembership.objects.get(
        user=actor,
        establishment=active_a,
    )

    response = post_membership_action(
        api_client,
        actor=actor,
        establishment_id=active_a.id,
        membership_id=path_membership.id,
        action="deactivate",
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "The last active owner cannot be deactivated."}
    assert owner_statuses_for_user(user=actor, establishments=[active_a, draft_b]) == {
        EstablishmentMembership.Status.ACTIVE
    }


def test_owner_deactivate_blocks_when_other_owner_lacks_full_coverage(api_client):
    organization = create_organization(name="Partial Other Org")
    active_a = create_establishment(name="Partial A", organization=organization)
    active_b = create_establishment(name="Partial B", organization=organization)
    actor = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="partial_actor",
    )
    partial = create_user(username="partial_other")
    create_membership(user=partial, establishment=active_a, role=ROLE_OWNER)
    path_membership = EstablishmentMembership.objects.get(
        user=actor,
        establishment=active_a,
    )

    response = post_membership_action(
        api_client,
        actor=actor,
        establishment_id=active_a.id,
        membership_id=path_membership.id,
        action="deactivate",
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "The last active owner cannot be deactivated."}
    assert owner_statuses_for_user(user=actor, establishments=[active_a, active_b]) == {
        EstablishmentMembership.Status.ACTIVE
    }


def test_owner_deactivate_actor_without_full_coverage_returns_invariant(api_client):
    organization = create_organization(name="Actor Gap Org")
    active_a = create_establishment(name="Actor Gap A", organization=organization)
    active_b = create_establishment(name="Actor Gap B", organization=organization)
    actor = create_user(username="gap_actor")
    create_membership(user=actor, establishment=active_a, role=ROLE_OWNER)
    target = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="gap_target",
    )
    # Keep a second full-coverage owner so last-owner is not the failure mode.
    setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="gap_survivor",
    )
    path_membership = EstablishmentMembership.objects.get(
        user=target,
        establishment=active_a,
    )

    response = post_membership_action(
        api_client,
        actor=actor,
        establishment_id=active_a.id,
        membership_id=path_membership.id,
        action="deactivate",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "organizational_owner_invariant_conflict"
    assert owner_statuses_for_user(user=target, establishments=[active_a, active_b]) == {
        EstablishmentMembership.Status.ACTIVE
    }


@pytest.mark.parametrize("user_status", [User.Status.SUSPENDED, User.Status.ANONYMIZED])
def test_owner_lifecycle_rejects_non_active_target_user(api_client, user_status):
    organization = create_organization(name="Target User Status Org")
    active_a = create_establishment(name="Target Status A", organization=organization)
    active_b = create_establishment(name="Target Status B", organization=organization)
    actor = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username=f"status_actor_{user_status}",
    )
    target = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username=f"status_target_{user_status}",
    )
    target.status = user_status
    target.save(update_fields=["status", "updated_at"])
    path_membership = EstablishmentMembership.objects.get(
        user=target,
        establishment=active_a,
    )

    response = post_membership_action(
        api_client,
        actor=actor,
        establishment_id=active_a.id,
        membership_id=path_membership.id,
        action="deactivate",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "organizational_owner_invariant_conflict"
    assert owner_statuses_for_user(user=target, establishments=[active_a, active_b]) == {
        EstablishmentMembership.Status.ACTIVE
    }


def test_owner_deactivate_missing_target_membership_rolls_back(api_client):
    organization = create_organization(name="Missing Target Org")
    active_a = create_establishment(name="Missing A", organization=organization)
    active_b = create_establishment(name="Missing B", organization=organization)
    actor = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="missing_actor",
    )
    setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="missing_survivor",
    )
    target = create_user(username="missing_target")
    path_membership = create_membership(
        user=target,
        establishment=active_a,
        role=ROLE_OWNER,
    )

    response = post_membership_action(
        api_client,
        actor=actor,
        establishment_id=active_a.id,
        membership_id=path_membership.id,
        action="deactivate",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "organizational_owner_invariant_conflict"
    path_membership.refresh_from_db()
    assert path_membership.status == EstablishmentMembership.Status.ACTIVE


def test_owner_deactivate_non_owner_sibling_rolls_back(api_client):
    organization = create_organization(name="Non Owner Sibling Org")
    active_a = create_establishment(name="Sibling A", organization=organization)
    active_b = create_establishment(name="Sibling B", organization=organization)
    actor = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="sibling_actor",
    )
    setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="sibling_survivor",
    )
    target = create_user(username="sibling_target")
    path_membership = create_membership(
        user=target,
        establishment=active_a,
        role=ROLE_OWNER,
    )
    create_membership(
        user=target,
        establishment=active_b,
        role=EstablishmentMembership.Role.STAFF,
    )

    response = post_membership_action(
        api_client,
        actor=actor,
        establishment_id=active_a.id,
        membership_id=path_membership.id,
        action="deactivate",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "organizational_owner_invariant_conflict"
    path_membership.refresh_from_db()
    assert path_membership.status == EstablishmentMembership.Status.ACTIVE
    assert (
        EstablishmentMembership.objects.get(
            user=target,
            establishment=active_b,
        ).status
        == EstablishmentMembership.Status.ACTIVE
    )


def test_owner_deactivate_mixed_statuses_rolls_back(api_client):
    organization = create_organization(name="Mixed Status Org")
    active_a = create_establishment(name="Mixed A", organization=organization)
    active_b = create_establishment(name="Mixed B", organization=organization)
    actor = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="mixed_actor",
    )
    setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="mixed_survivor",
    )
    target = create_user(username="mixed_target")
    path_membership = create_membership(
        user=target,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        user=target,
        establishment=active_b,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )

    response = post_membership_action(
        api_client,
        actor=actor,
        establishment_id=active_a.id,
        membership_id=path_membership.id,
        action="deactivate",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "organizational_owner_invariant_conflict"
    assert owner_statuses_for_user(user=target, establishments=[active_a, active_b]) == {
        EstablishmentMembership.Status.ACTIVE,
        EstablishmentMembership.Status.DEACTIVATED,
    }


def test_owner_deactivate_withdraws_pending_invite(api_client):
    organization = create_organization(name="Withdraw Invite Org")
    active_a = create_establishment(name="Withdraw A", organization=organization)
    draft_b = create_establishment(
        name="Withdraw B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    actor = setup_full_coverage_owner(
        establishments=[active_a, draft_b],
        username="withdraw_actor",
    )

    invite_response = post_owner_invitation(
        api_client,
        organization_id=organization.id,
        actor=actor,
        payload=owner_invite_payload(email="withdraw-owner@example.com"),
    )
    assert invite_response.status_code == 201, invite_response.json()
    token = invite_response.json()["invitation_token"]
    invitee = User.objects.get(email__iexact="withdraw-owner@example.com")
    path_membership = EstablishmentMembership.objects.get(
        user=invitee,
        establishment=active_a,
    )

    with (
        patch("houston.chat.services.handle_membership_chat_deactivation") as chat_mock,
        patch("houston.realtime.broadcast.schedule_access_event") as access_mock,
        patch(
            "houston.establishments.invitation_email.schedule_establishment_invitation_email"
        ) as email_mock,
    ):
        response = post_membership_action(
            api_client,
            actor=actor,
            establishment_id=active_a.id,
            membership_id=path_membership.id,
            action="deactivate",
        )

    assert response.status_code == 200, response.json()
    assert response.json()["status"] == EstablishmentMembership.Status.DEACTIVATED
    assert owner_statuses_for_user(user=invitee, establishments=[active_a, draft_b]) == {
        EstablishmentMembership.Status.DEACTIVATED,
    }
    assert not EstablishmentMembership.objects.filter(
        user=invitee,
        establishment__in=[active_a, draft_b],
        status=EstablishmentMembership.Status.ACTIVE,
    ).exists()

    invitation = EstablishmentInvitation.objects.get(
        token_digest=auth_tokens.digest_token(token),
    )
    assert invitation.revoked_at is not None
    assert invitation.accepted_at is None
    assert (
        EstablishmentInvitation.objects.filter(
            membership__user=invitee,
            membership__establishment__in=[active_a, draft_b],
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        ).count()
        == 0
    )

    assert chat_mock.call_count == 2
    membership_access_calls = [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.deactivated"
    ]
    assert len(membership_access_calls) == 2
    email_mock.assert_not_called()

    accept_response = post_accept(APIClient(enforce_csrf_checks=True), token=token)
    assert accept_response.status_code == 400
    assert accept_response.json()["code"] == "invitation_invalid"
    invitee.refresh_from_db()
    assert invitee.status == User.Status.PENDING
    assert not EstablishmentMembership.objects.filter(
        user=invitee,
        status=EstablishmentMembership.Status.ACTIVE,
    ).exists()


def test_owner_reactivate_invited_or_mixed_returns_invariant(api_client):
    organization = create_organization(name="Reactivate Mix Org")
    active_a = create_establishment(name="Reactivate Mix A", organization=organization)
    active_b = create_establishment(name="Reactivate Mix B", organization=organization)
    actor = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="reactivate_mix_actor",
    )
    target = create_user(username="reactivate_mix_target")
    path_membership = create_membership(
        user=target,
        establishment=active_a,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )
    create_membership(
        user=target,
        establishment=active_b,
        role=ROLE_OWNER,
        membership_status=EstablishmentMembership.Status.INVITED,
    )

    response = post_membership_action(
        api_client,
        actor=actor,
        establishment_id=active_a.id,
        membership_id=path_membership.id,
        action="activate",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "organizational_owner_invariant_conflict"
    assert owner_statuses_for_user(user=target, establishments=[active_a, active_b]) == {
        EstablishmentMembership.Status.DEACTIVATED,
        EstablishmentMembership.Status.INVITED,
    }


def test_owner_deactivate_noop_when_already_deactivated(api_client):
    organization = create_organization(name="Deactivate Noop Org")
    active_a = create_establishment(name="Noop A", organization=organization)
    active_b = create_establishment(name="Noop B", organization=organization)
    actor = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="noop_deactivate_actor",
    )
    target = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="noop_deactivate_target",
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )
    path_membership = EstablishmentMembership.objects.get(
        user=target,
        establishment=active_a,
    )

    with (
        patch("houston.chat.services.handle_membership_chat_deactivation") as chat_mock,
        patch("houston.realtime.broadcast.schedule_access_event") as access_mock,
        patch(
            "houston.establishments.invitation_email.schedule_establishment_invitation_email"
        ) as email_mock,
    ):
        response = post_membership_action(
            api_client,
            actor=actor,
            establishment_id=active_a.id,
            membership_id=path_membership.id,
            action="deactivate",
        )

    assert response.status_code == 200
    assert response.json()["status"] == EstablishmentMembership.Status.DEACTIVATED
    chat_mock.assert_not_called()
    assert not [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") in {"membership.deactivated", "membership.updated"}
    ]
    email_mock.assert_not_called()


def test_owner_reactivate_noop_when_already_active(api_client):
    organization = create_organization(name="Reactivate Noop Org")
    active_a = create_establishment(name="Noop Reactivate A", organization=organization)
    active_b = create_establishment(name="Noop Reactivate B", organization=organization)
    actor = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="noop_reactivate_actor",
    )
    target = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="noop_reactivate_target",
    )
    path_membership = EstablishmentMembership.objects.get(
        user=target,
        establishment=active_a,
    )

    with (
        patch("houston.realtime.broadcast.schedule_access_event") as access_mock,
        patch(
            "houston.establishments.invitation_email.schedule_establishment_invitation_email"
        ) as email_mock,
    ):
        response = post_membership_action(
            api_client,
            actor=actor,
            establishment_id=active_a.id,
            membership_id=path_membership.id,
            action="activate",
        )

    assert response.status_code == 200
    assert response.json()["status"] == EstablishmentMembership.Status.ACTIVE
    assert not [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") in {"membership.deactivated", "membership.updated"}
    ]
    email_mock.assert_not_called()


def test_owner_deactivate_clears_org_sessions_only(api_client):
    organization = create_organization(name="Session Org")
    active_a = create_establishment(name="Session A", organization=organization)
    draft_b = create_establishment(
        name="Session B",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    other_org = create_organization(name="Foreign Session Org")
    other_est = create_establishment(name="Foreign Session Est", organization=other_org)

    actor = setup_full_coverage_owner(
        establishments=[active_a, draft_b],
        username="session_actor",
    )
    target = setup_full_coverage_owner(
        establishments=[active_a, draft_b],
        username="session_target",
    )
    create_membership(user=target, establishment=other_est, role=ROLE_OWNER)
    path_membership = EstablishmentMembership.objects.get(
        user=target,
        establishment=active_a,
    )
    touched_session = create_session(user=target, selected_establishment=active_a)
    foreign_session = create_session(user=target, selected_establishment=other_est)

    response = post_membership_action(
        api_client,
        actor=actor,
        establishment_id=active_a.id,
        membership_id=path_membership.id,
        action="deactivate",
    )

    assert response.status_code == 200
    touched_session.refresh_from_db()
    foreign_session.refresh_from_db()
    assert touched_session.selected_establishment is None
    assert foreign_session.selected_establishment_id == other_est.id
    assert foreign_session.status == UserSession.Status.ACTIVE


@pytest.mark.django_db(transaction=True)
def test_concurrent_owner_deactivations_preserve_last_full_coverage_owner():
    organization = create_organization(name="Concurrent Deactivate Org")
    active_a = create_establishment(name="Concurrent A", organization=organization)
    active_b = create_establishment(name="Concurrent B", organization=organization)
    owner_one = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="concurrent_owner_one",
    )
    owner_two = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="concurrent_owner_two",
    )
    membership_one = EstablishmentMembership.objects.get(
        user=owner_one,
        establishment=active_a,
    )
    membership_two = EstablishmentMembership.objects.get(
        user=owner_two,
        establishment=active_a,
    )

    with (
        patch("houston.chat.services.handle_membership_chat_deactivation") as chat_mock,
        patch("houston.realtime.broadcast.schedule_access_event") as access_mock,
    ):

        def deactivate(pair: tuple[User, EstablishmentMembership]) -> tuple[int, str | None]:
            actor, target_membership = pair
            close_old_connections()
            try:
                client = APIClient(enforce_csrf_checks=True)
                access_token = login(client, identifier=actor.email)
                access_token = switch_establishment(
                    client,
                    access_token=access_token,
                    establishment_id=active_a.id,
                )
                response = client.post(
                    membership_url(
                        establishment_id=active_a.id,
                        membership_id=target_membership.id,
                        action="deactivate",
                    ),
                    format="json",
                    **auth_headers(access_token),
                )
                body = response.json()
                return response.status_code, body.get("code")
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    deactivate,
                    [
                        (owner_one, membership_two),
                        (owner_two, membership_one),
                    ],
                )
            )

    statuses = [status for status, _ in results]
    codes = [code for _, code in results]
    assert statuses.count(200) == 1
    assert statuses.count(409) == 1
    assert "organizational_owner_invariant_conflict" in codes

    owner_one_statuses = owner_statuses_for_user(
        user=owner_one,
        establishments=[active_a, active_b],
    )
    owner_two_statuses = owner_statuses_for_user(
        user=owner_two,
        establishments=[active_a, active_b],
    )
    assert owner_one_statuses in (
        {EstablishmentMembership.Status.ACTIVE},
        {EstablishmentMembership.Status.DEACTIVATED},
    )
    assert owner_two_statuses in (
        {EstablishmentMembership.Status.ACTIVE},
        {EstablishmentMembership.Status.DEACTIVATED},
    )
    assert {
        owner_one_statuses == {EstablishmentMembership.Status.ACTIVE},
        owner_two_statuses == {EstablishmentMembership.Status.ACTIVE},
    } == {True, False}

    assert chat_mock.call_count == 2
    membership_access_calls = [
        call
        for call in access_mock.call_args_list
        if call.kwargs.get("reason") == "membership.deactivated"
    ]
    assert len(membership_access_calls) == 2


def test_stale_owner_deactivation_returns_invariant_after_actor_was_deactivated(api_client):
    organization = create_organization(name="Stale Owner Deactivate Org")
    active_a = create_establishment(name="Stale Owner A", organization=organization)
    active_b = create_establishment(name="Stale Owner B", organization=organization)
    owner_one = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="stale_owner_one",
    )
    owner_two = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="stale_owner_two",
    )
    membership_one = EstablishmentMembership.objects.get(
        user=owner_one,
        establishment=active_a,
    )
    membership_two = EstablishmentMembership.objects.get(
        user=owner_two,
        establishment=active_a,
    )
    stale_access_token = login(api_client, identifier=owner_one.email)
    stale_access_token = switch_establishment(
        api_client,
        access_token=stale_access_token,
        establishment_id=active_a.id,
    )

    deactivate_owner_one = post_membership_action(
        api_client,
        actor=owner_two,
        establishment_id=active_a.id,
        membership_id=membership_one.id,
        action="deactivate",
    )
    assert deactivate_owner_one.status_code == 200, deactivate_owner_one.json()

    response = api_client.post(
        membership_url(
            establishment_id=active_a.id,
            membership_id=membership_two.id,
            action="deactivate",
        ),
        format="json",
        **auth_headers(stale_access_token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "organizational_owner_invariant_conflict"
    assert owner_statuses_for_user(user=owner_one, establishments=[active_a, active_b]) == {
        EstablishmentMembership.Status.DEACTIVATED
    }
    assert owner_statuses_for_user(user=owner_two, establishments=[active_a, active_b]) == {
        EstablishmentMembership.Status.ACTIVE
    }


def test_stale_owner_deactivation_cannot_manage_non_owner_membership(api_client):
    organization = create_organization(name="Stale Owner Non Owner Org")
    active_a = create_establishment(name="Stale Non Owner A", organization=organization)
    active_b = create_establishment(name="Stale Non Owner B", organization=organization)
    owner_one = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="stale_non_owner_one",
    )
    owner_two = setup_full_coverage_owner(
        establishments=[active_a, active_b],
        username="stale_non_owner_two",
    )
    director = create_user(username="stale_non_owner_director")
    director_membership = create_membership(
        user=director,
        establishment=active_a,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    membership_one = EstablishmentMembership.objects.get(
        user=owner_one,
        establishment=active_a,
    )
    stale_access_token = login(api_client, identifier=owner_one.email)
    stale_access_token = switch_establishment(
        api_client,
        access_token=stale_access_token,
        establishment_id=active_a.id,
    )

    deactivate_owner_one = post_membership_action(
        api_client,
        actor=owner_two,
        establishment_id=active_a.id,
        membership_id=membership_one.id,
        action="deactivate",
    )
    assert deactivate_owner_one.status_code == 200, deactivate_owner_one.json()

    response = api_client.post(
        membership_url(
            establishment_id=active_a.id,
            membership_id=director_membership.id,
            action="deactivate",
        ),
        format="json",
        **auth_headers(stale_access_token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "membership_management_forbidden"
    director_membership.refresh_from_db()
    assert director_membership.status == EstablishmentMembership.Status.ACTIVE


def test_membership_patch_demote_owner_remains_forbidden(api_client):
    organization = create_organization(name="Patch Demote Org")
    active_a = create_establishment(name="Patch Demote A", organization=organization)
    actor = setup_full_coverage_owner(
        establishments=[active_a],
        username="patch_demote_actor",
    )
    target = setup_full_coverage_owner(
        establishments=[active_a],
        username="patch_demote_target",
    )
    path_membership = EstablishmentMembership.objects.get(
        user=target,
        establishment=active_a,
    )

    access_token = login(api_client, identifier=actor.email)
    access_token = switch_establishment(
        api_client,
        access_token=access_token,
        establishment_id=active_a.id,
    )
    response = api_client.patch(
        f"/api/v1/establishments/{active_a.id}/memberships/{path_membership.id}/",
        {"role": EstablishmentMembership.Role.STAFF},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "membership_role_change_forbidden"
    path_membership.refresh_from_db()
    assert path_membership.role == ROLE_OWNER
