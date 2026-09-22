from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    Establishment,
    EstablishmentInvitation,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.establishments.services import (
    complete_onboarding_session_core,
    upsert_onboarding_draft_core,
)
from houston.testing.auth import auth_headers, ensure_csrf, login
from houston.testing.factories import create_user
from houston.testing.platform import grant_operator

pytestmark = pytest.mark.django_db

ACCEPT_PASSWORD = "SecurePass123!"


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _valid_payload(*, establishment_name: str, director_email: str) -> dict:
    bu_key = str(uuid.uuid4())
    subject_key = str(uuid.uuid4())
    return {
        "current_step": "team",
        "establishment": {
            "name": establishment_name,
            "description": "D" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        },
        "business_units": [
            {
                "client_key": bu_key,
                "catalog_key": "coworking",
                "specific_name": "Coworking Nord",
                "instance_description": "",
            }
        ],
        "activity_subjects": [
            {
                "client_key": subject_key,
                "business_unit_client_key": bu_key,
                "catalog_key": "coworking__proprete",
                "label": "",
                "description": "",
            }
        ],
        "team": {
            "director": {
                "email": director_email,
                "first_name": "Dir",
                "last_name": "Ector",
            },
            "members": [],
        },
    }


def _start_onboarding(api_client, token):
    created = api_client.post(
        "/api/v1/platform/onboardings/",
        {"organization_name": "Invite Org", "establishment_name": "Invite Site"},
        format="json",
        **auth_headers(token),
    )
    assert created.status_code == 201
    return created.json()


def _activate_owner_membership(membership: EstablishmentMembership) -> User:
    membership.status = EstablishmentMembership.Status.ACTIVE
    membership.save(update_fields=["status", "updated_at"])
    owner = membership.user
    owner.status = User.Status.ACTIVE
    owner.save(update_fields=["status", "updated_at"])
    return owner


def test_http_owner_invitation_creates_membership_without_operator_row(api_client):
    sync_catalog_from_normalized_rows()
    operator = create_user(username="plat_owner_invite_op")
    grant_operator(operator)
    token = login(api_client, user=operator)
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    owner_email = f"owner_{uuid.uuid4().hex[:8]}@example.com"
    captured: dict[str, str] = {}

    def _capture_token(*, invitation, membership, raw_token):
        captured["token"] = raw_token
        return "queued"

    with patch(
        "houston.establishments.invitation_email.schedule_establishment_invitation_email",
        side_effect=_capture_token,
    ):
        invited = api_client.post(
            f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
            {"email": owner_email, "first_name": "Own", "last_name": "Er"},
            format="json",
            **auth_headers(token),
        )
    assert invited.status_code == 201
    membership = EstablishmentMembership.objects.get(pk=invited.json()["membership_id"])
    assert membership.role == EstablishmentMembership.Role.OWNER
    assert membership.status == EstablishmentMembership.Status.INVITED
    assert EstablishmentMembership.objects.filter(user=operator).count() == 0

    assert membership.establishment.status == Establishment.Status.DRAFT
    csrf_token = ensure_csrf(api_client)
    accepted = api_client.post(
        "/api/v1/invitations/accept/",
        {
            "token": captured["token"],
            "password": ACCEPT_PASSWORD,
            "password_confirmation": ACCEPT_PASSWORD,
            "refresh_token_transport": "cookie",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert accepted.status_code == 201
    membership.refresh_from_db()
    assert membership.status == EstablishmentMembership.Status.ACTIVE
    assert EstablishmentMembership.objects.filter(user=operator).count() == 0


def test_expired_owner_invitation_can_be_reissued_accepted_then_completed(api_client):
    sync_catalog_from_normalized_rows()
    operator = create_user(username="plat_owner_reinvite_op")
    grant_operator(operator)
    token = login(api_client, user=operator)
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    session = OnboardingSession.objects.get(pk=session_id)
    owner_email = f"owner_{uuid.uuid4().hex[:8]}@example.com"
    director_email = f"director_{uuid.uuid4().hex[:8]}@example.com"
    issued_tokens: list[str] = []

    upsert_onboarding_draft_core(
        session=session,
        actor=operator,
        payload=_valid_payload(
            establishment_name=session.establishment.name,
            director_email=director_email,
        ),
    )

    def _capture_token(*, invitation, membership, raw_token):
        issued_tokens.append(raw_token)
        return "queued"

    invite_path = f"/api/v1/platform/onboardings/{session_id}/owner-invitations/"
    invite_payload = {
        "email": owner_email,
        "first_name": "Own",
        "last_name": "Er",
    }
    with patch(
        "houston.establishments.invitation_email.schedule_establishment_invitation_email",
        side_effect=_capture_token,
    ):
        first_invite = api_client.post(
            invite_path,
            invite_payload,
            format="json",
            **auth_headers(token),
        )
        assert first_invite.status_code == 201
        membership = EstablishmentMembership.objects.get(
            pk=first_invite.json()["membership_id"]
        )
        first_invitation = EstablishmentInvitation.objects.get(
            membership=membership,
            revoked_at__isnull=True,
        )
        first_invitation.expires_at = timezone.now() - timedelta(minutes=1)
        first_invitation.save(update_fields=["expires_at", "updated_at"])

        second_invite = api_client.post(
            invite_path,
            invite_payload,
            format="json",
            **auth_headers(token),
        )

    assert second_invite.status_code == 201
    assert len(issued_tokens) == 2
    first_invitation.refresh_from_db()
    assert first_invitation.revoked_at is not None

    accepted = api_client.post(
        "/api/v1/invitations/accept/",
        {
            "token": issued_tokens[-1],
            "password": ACCEPT_PASSWORD,
            "password_confirmation": ACCEPT_PASSWORD,
            "refresh_token_transport": "cookie",
        },
        format="json",
        HTTP_X_CSRFTOKEN=ensure_csrf(api_client),
    )
    assert accepted.status_code == 201, accepted.json()

    complete = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert complete.status_code == 200, complete.json()
    assert complete.json()["activated"] is True
    membership.refresh_from_db()
    session.refresh_from_db()
    assert membership.status == EstablishmentMembership.Status.ACTIVE
    assert session.status == OnboardingSession.Status.ACTIVATED


def test_http_director_invite_and_complete_from_draft(api_client):
    sync_catalog_from_normalized_rows()
    operator = create_user(username="plat_dir_invite_op")
    grant_operator(operator)
    token = login(api_client, user=operator)
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    session = OnboardingSession.objects.get(pk=session_id)
    director_email = f"director_{uuid.uuid4().hex[:8]}@example.com"

    upsert_onboarding_draft_core(
        session=session,
        actor=operator,
        payload=_valid_payload(
            establishment_name=session.establishment.name,
            director_email=director_email,
        ),
    )

    invited = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/director-invitations/",
        {"email": director_email, "first_name": "Dir", "last_name": "Ector"},
        format="json",
        **auth_headers(token),
    )
    assert invited.status_code == 201
    assert EstablishmentMembership.objects.filter(
        establishment_id=session.establishment_id,
        role=EstablishmentMembership.Role.DIRECTOR,
    ).count() == 1

    owner_invite = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
        {
            "email": f"owner_{uuid.uuid4().hex[:8]}@example.com",
            "first_name": "Own",
            "last_name": "Er",
        },
        format="json",
        **auth_headers(token),
    )
    assert owner_invite.status_code == 201
    _activate_owner_membership(
        EstablishmentMembership.objects.get(pk=owner_invite.json()["membership_id"])
    )

    complete = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert complete.status_code == 200
    assert complete.json()["activated"] is True
    assert EstablishmentMembership.objects.filter(user=operator).count() == 0


def test_http_owner_invite_after_activation_is_409(api_client):
    sync_catalog_from_normalized_rows()
    operator = create_user(username="plat_owner_after_activation_op")
    grant_operator(operator)
    token = login(api_client, user=operator)
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    session = OnboardingSession.objects.get(pk=session_id)
    director_email = f"director_{uuid.uuid4().hex[:8]}@example.com"

    upsert_onboarding_draft_core(
        session=session,
        actor=operator,
        payload=_valid_payload(
            establishment_name=session.establishment.name,
            director_email=director_email,
        ),
    )
    initial_owner_invite = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
        {
            "email": f"owner_{uuid.uuid4().hex[:8]}@example.com",
            "first_name": "Initial",
            "last_name": "Owner",
        },
        format="json",
        **auth_headers(token),
    )
    assert initial_owner_invite.status_code == 201
    _activate_owner_membership(
        EstablishmentMembership.objects.get(pk=initial_owner_invite.json()["membership_id"])
    )

    complete = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert complete.status_code == 200

    owner_count = EstablishmentMembership.objects.filter(
        establishment_id=session.establishment_id,
        role=EstablishmentMembership.Role.OWNER,
    ).count()
    new_owner_email = f"owner_{uuid.uuid4().hex[:8]}@example.com"
    invited = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
        {"email": new_owner_email, "first_name": "New", "last_name": "Owner"},
        format="json",
        **auth_headers(token),
    )

    assert invited.status_code == 409
    assert invited.json()["code"] == "invalid_onboarding_state"
    assert not User.objects.filter(email__iexact=new_owner_email).exists()
    assert (
        EstablishmentMembership.objects.filter(
            establishment_id=session.establishment_id,
            role=EstablishmentMembership.Role.OWNER,
        ).count()
        == owner_count
    )


def test_complete_invites_director_from_draft(api_client):
    sync_catalog_from_normalized_rows()
    operator = create_user(username="plat_complete_dir_op")
    grant_operator(operator)
    token = login(api_client, user=operator)
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    session = OnboardingSession.objects.get(pk=session_id)
    director_email = f"director_{uuid.uuid4().hex[:8]}@example.com"
    upsert_onboarding_draft_core(
        session=session,
        actor=operator,
        payload=_valid_payload(
            establishment_name=session.establishment.name,
            director_email=director_email,
        ),
    )
    owner_invite = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
        {
            "email": f"owner_{uuid.uuid4().hex[:8]}@example.com",
            "first_name": "Own",
            "last_name": "Er",
        },
        format="json",
        **auth_headers(token),
    )
    _activate_owner_membership(
        EstablishmentMembership.objects.get(pk=owner_invite.json()["membership_id"])
    )

    assert not EstablishmentMembership.objects.filter(
        establishment_id=session.establishment_id,
        role=EstablishmentMembership.Role.DIRECTOR,
    ).exists()

    complete = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert complete.status_code == 200
    assert complete.json()["activated"] is True
    director = EstablishmentMembership.objects.get(
        establishment_id=session.establishment_id,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    assert director.user.email.lower() == director_email.lower()
    assert director.status == EstablishmentMembership.Status.INVITED


def test_director_invite_then_complete_is_idempotent(api_client):
    sync_catalog_from_normalized_rows()
    operator = create_user(username="plat_dir_idem_op")
    grant_operator(operator)
    token = login(api_client, user=operator)
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    session = OnboardingSession.objects.get(pk=session_id)
    director_email = f"director_{uuid.uuid4().hex[:8]}@example.com"
    upsert_onboarding_draft_core(
        session=session,
        actor=operator,
        payload=_valid_payload(
            establishment_name=session.establishment.name,
            director_email=director_email,
        ),
    )
    owner_invite = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
        {
            "email": f"owner_{uuid.uuid4().hex[:8]}@example.com",
            "first_name": "Own",
            "last_name": "Er",
        },
        format="json",
        **auth_headers(token),
    )
    _activate_owner_membership(
        EstablishmentMembership.objects.get(pk=owner_invite.json()["membership_id"])
    )

    with patch(
        "houston.establishments.invitation_email.schedule_establishment_invitation_email"
    ) as scheduled:
        invited = api_client.post(
            f"/api/v1/platform/onboardings/{session_id}/director-invitations/",
            {"email": director_email, "first_name": "Dir", "last_name": "Ector"},
            format="json",
            **auth_headers(token),
        )
        assert invited.status_code == 201
        assert scheduled.call_count == 1

        result = complete_onboarding_session_core(session=session, actor=operator)
        assert result["activated"] is True
        assert scheduled.call_count == 1

    assert (
        EstablishmentMembership.objects.filter(
            establishment_id=session.establishment_id,
            role=EstablishmentMembership.Role.DIRECTOR,
        ).count()
        == 1
    )
    assert (
        EstablishmentInvitation.objects.filter(
            membership__establishment_id=session.establishment_id,
            membership__role=EstablishmentMembership.Role.DIRECTOR,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        ).count()
        == 1
    )
