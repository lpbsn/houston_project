from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
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

    Establishment.objects.filter(pk=membership.establishment_id).update(
        status=Establishment.Status.ACTIVE
    )
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
