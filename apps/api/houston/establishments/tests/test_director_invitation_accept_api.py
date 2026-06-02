from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.accounts.services import tokens as auth_tokens
from houston.establishments.models import EstablishmentInvitation, EstablishmentMembership
from houston.establishments.services import invite_director_during_onboarding
from houston.establishments.tests.test_onboarding_api import (
    auth_headers,
    create_onboarding_session,
    create_user,
    ensure_csrf,
    login,
)

pytestmark = pytest.mark.django_db

REGISTRATION_PASSWORD = "SecurePass123!"


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def post_accept(api_client: APIClient, csrf_token: str, token: str, payload: dict):
    return api_client.post(
        f"/api/v1/invitations/{token}/accept/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )


def invite_director_for_session(*, session, owner):
    return invite_director_during_onboarding(
        session=session,
        actor=owner,
        email="director-accept@example.com",
        first_name="Casey",
        last_name="Director",
    )


def test_director_invitation_response_includes_token(api_client):
    owner = create_user(username="director_token_owner")
    session = create_onboarding_session(actor=owner)
    access_token = login(api_client, user=owner)

    response = api_client.post(
        f"/api/v1/onboarding-sessions/{session.id}/director-invitations/",
        {
            "email": "director-token@example.com",
            "first_name": "Casey",
            "last_name": "Director",
        },
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["invitation_token"]
    assert body["invitation_expires_at"]
    assert body["invitation_accept_path"] == f"/invitations/{body['invitation_token']}"

    invitation = EstablishmentInvitation.objects.get(
        token_digest=auth_tokens.digest_token(body["invitation_token"]),
    )
    assert invitation.accepted_at is None
    assert invitation.revoked_at is None


def test_accept_valid_token_activates_user_and_membership(api_client):
    owner = create_user(username="director_accept_owner")
    session = create_onboarding_session(actor=owner)
    invitation_result = invite_director_for_session(session=session, owner=owner)
    csrf_token = ensure_csrf(api_client)

    response = post_accept(
        api_client,
        csrf_token,
        invitation_result.invitation_token,
        {
            "password": REGISTRATION_PASSWORD,
            "password_confirmation": REGISTRATION_PASSWORD,
        },
    )

    assert response.status_code == 201
    assert response.data["access_token"]
    assert str(response.data["establishment_id"]) == str(session.establishment_id)
    assert "csrftoken" in api_client.cookies

    membership = invitation_result.membership
    membership.refresh_from_db()
    user = membership.user
    user.refresh_from_db()

    assert membership.status == EstablishmentMembership.Status.ACTIVE
    assert user.status == User.Status.ACTIVE
    assert user.check_password(REGISTRATION_PASSWORD)

    invitation = EstablishmentInvitation.objects.get(
        token_digest=auth_tokens.digest_token(invitation_result.invitation_token),
    )
    assert invitation.accepted_at is not None


def test_accepted_director_can_log_in_with_password(api_client):
    owner = create_user(username="director_login_after_accept_owner")
    session = create_onboarding_session(actor=owner)
    invitation_result = invite_director_for_session(session=session, owner=owner)
    csrf_token = ensure_csrf(api_client)

    accept_response = post_accept(
        api_client,
        csrf_token,
        invitation_result.invitation_token,
        {
            "password": REGISTRATION_PASSWORD,
            "password_confirmation": REGISTRATION_PASSWORD,
        },
    )
    assert accept_response.status_code == 201

    api_client.cookies.clear()
    login_csrf_token = ensure_csrf(api_client)

    login_response = api_client.post(
        "/api/v1/auth/login/",
        {
            "identifier": "director-accept@example.com",
            "password": REGISTRATION_PASSWORD,
        },
        format="json",
        HTTP_X_CSRFTOKEN=login_csrf_token,
    )

    assert login_response.status_code == 200
    assert login_response.data["access_token"]


def test_invalid_token_returns_400(api_client):
    csrf_token = ensure_csrf(api_client)

    response = post_accept(
        api_client,
        csrf_token,
        "not-a-valid-invitation-token",
        {
            "password": REGISTRATION_PASSWORD,
            "password_confirmation": REGISTRATION_PASSWORD,
        },
    )

    assert response.status_code == 400
    assert response.data["code"] == "invitation_invalid"


@override_settings(HOUSTON_DIRECTOR_INVITATION_TTL=timedelta(days=-1))
def test_expired_token_returns_400(api_client):
    owner = create_user(username="director_expired_token_owner")
    session = create_onboarding_session(actor=owner)
    invitation_result = invite_director_for_session(session=session, owner=owner)
    EstablishmentInvitation.objects.filter(
        token_digest=auth_tokens.digest_token(invitation_result.invitation_token),
    ).update(expires_at=timezone.now() - timedelta(minutes=1))
    csrf_token = ensure_csrf(api_client)

    response = post_accept(
        api_client,
        csrf_token,
        invitation_result.invitation_token,
        {
            "password": REGISTRATION_PASSWORD,
            "password_confirmation": REGISTRATION_PASSWORD,
        },
    )

    assert response.status_code == 400
    assert response.data["code"] == "invitation_expired"


def test_password_mismatch_returns_400(api_client):
    owner = create_user(username="director_password_mismatch_owner")
    session = create_onboarding_session(actor=owner)
    invitation_result = invite_director_for_session(session=session, owner=owner)
    csrf_token = ensure_csrf(api_client)

    response = post_accept(
        api_client,
        csrf_token,
        invitation_result.invitation_token,
        {
            "password": REGISTRATION_PASSWORD,
            "password_confirmation": "DifferentPass123!",
        },
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert response.data["detail"] == "Request validation failed."
    assert "password_confirmation" in response.data["errors"]

    membership = invitation_result.membership
    membership.refresh_from_db()
    assert membership.status == EstablishmentMembership.Status.INVITED
    assert membership.user.status == User.Status.PENDING


def test_accept_already_used_token_returns_400(api_client):
    owner = create_user(username="director_accept_twice_owner")
    session = create_onboarding_session(actor=owner)
    invitation_result = invite_director_for_session(session=session, owner=owner)
    csrf_token = ensure_csrf(api_client)
    payload = {
        "password": REGISTRATION_PASSWORD,
        "password_confirmation": REGISTRATION_PASSWORD,
    }

    first_response = post_accept(
        api_client,
        csrf_token,
        invitation_result.invitation_token,
        payload,
    )
    second_response = post_accept(
        api_client,
        csrf_token,
        invitation_result.invitation_token,
        payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert second_response.data["code"] == "invitation_already_accepted"


def test_invitation_stores_digest_only(api_client):
    owner = create_user(username="director_digest_only_owner")
    session = create_onboarding_session(actor=owner)
    invitation_result = invite_director_for_session(session=session, owner=owner)

    invitation = EstablishmentInvitation.objects.get(
        membership_id=invitation_result.membership.id,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    )

    assert invitation.token_digest == auth_tokens.digest_token(
        invitation_result.invitation_token,
    )
    assert invitation.token_digest != invitation_result.invitation_token


def test_accept_staff_invitation_keeps_membership_scopes(api_client):
    import uuid

    from houston.establishments.membership_scope import MembershipScopeInput, MembershipScopeType
    from houston.establishments.models import (
        Establishment,
        MembershipScope,
        OperationalDomain,
        OperationalModule,
    )
    from houston.establishments.services import invite_membership_for_establishment
    from houston.organizations.models import Organization

    organization = Organization.objects.create(
        name=f"Scope Accept Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    establishment = Establishment.objects.create(
        name="Scope Accept Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    owner = create_user(username="scope_accept_owner")
    owner_membership = EstablishmentMembership.objects.create(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    module = OperationalModule.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
        active=True,
    )
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key="housekeeping",
        label="Housekeeping",
        active=True,
    )

    invitation = invite_membership_for_establishment(
        current_membership=owner_membership,
        establishment_id=establishment.id,
        email="scope-staff@example.com",
        first_name="Scope",
        last_name="Staff",
        role=EstablishmentMembership.Role.STAFF,
        scopes=[
            MembershipScopeInput(
                scope_type=MembershipScopeType.DOMAIN,
                scope_id=domain.id,
            )
        ],
    )
    membership_id = invitation.membership.id
    assert MembershipScope.objects.filter(membership_id=membership_id).count() == 1

    csrf_token = ensure_csrf(api_client)
    response = post_accept(
        api_client,
        csrf_token,
        invitation.invitation_token,
        {
            "password": REGISTRATION_PASSWORD,
            "password_confirmation": REGISTRATION_PASSWORD,
        },
    )

    assert response.status_code == 201
    assert MembershipScope.objects.filter(membership_id=membership_id).count() == 1
    membership = EstablishmentMembership.objects.get(id=membership_id)
    assert membership.status == EstablishmentMembership.Status.ACTIVE
