from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.invitation_email import schedule_establishment_invitation_email
from houston.establishments.models import (
    Establishment,
    EstablishmentInvitation,
    EstablishmentMembership,
)
from houston.establishments.tests.taxonomy_helpers import (
    business_unit_scope_payload,
    create_business_unit,
)
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_user
from houston.testing.onboarding import create_onboarding_session

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return api_client.cookies["csrftoken"].value


def _create_establishment(*, name: str = "Invite Hotel") -> Establishment:
    from houston.testing.factories import create_establishment

    return create_establishment(name=name)


def _create_membership(
    *,
    user: User,
    establishment: Establishment,
    role: str,
) -> EstablishmentMembership:
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )


def _create_owner_membership(
    *,
    user: User,
    establishment: Establishment,
) -> EstablishmentMembership:
    return _create_membership(
        user=user,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )


def _membership_invite_payload(*, business_unit) -> dict:
    return {
        "email": "new-staff@example.com",
        "first_name": "New",
        "last_name": "Staff",
        "role": EstablishmentMembership.Role.STAFF,
        "scopes": [business_unit_scope_payload(business_unit)],
    }


def _post_membership_invitation(
    api_client: APIClient,
    *,
    establishment_id,
    actor: User,
    payload: dict,
):
    access_token = login(api_client, user=actor)
    csrf_token = _ensure_csrf(api_client)
    return api_client.post(
        f"/api/v1/establishments/{establishment_id}/membership-invitations/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )


def _post_director_invitation(api_client: APIClient, *, session_id, actor: User):
    access_token = login(api_client, user=actor)
    csrf_token = _ensure_csrf(api_client)
    return api_client.post(
        f"/api/v1/onboarding-sessions/{session_id}/director-invitations/",
        {
            "email": "director@example.com",
            "first_name": "Casey",
            "last_name": "Director",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **auth_headers(access_token),
    )


def _patch_apply_async():
    return patch(
        "houston.establishments.tasks.send_establishment_invitation_email_task.apply_async"
    )


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_staff_invite_schedules_exactly_one_task(api_client):
    establishment = _create_establishment()
    owner = create_user(username="staff_schedule_owner")
    _create_owner_membership(user=owner, establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="housekeeping")

    with _patch_apply_async() as apply_async:
        response = _post_membership_invitation(
            api_client,
            establishment_id=establishment.id,
            actor=owner,
            payload=_membership_invite_payload(business_unit=business_unit),
        )

    assert response.status_code == 201
    apply_async.assert_called_once()


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_manager_invite_schedules_exactly_one_task(api_client):
    establishment = _create_establishment(name="Manager Hotel")
    owner = create_user(username="manager_schedule_owner")
    _create_owner_membership(user=owner, establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    payload = _membership_invite_payload(business_unit=business_unit)
    payload["role"] = EstablishmentMembership.Role.MANAGER
    payload["email"] = "new-manager@example.com"

    with _patch_apply_async() as apply_async:
        response = _post_membership_invitation(
            api_client,
            establishment_id=establishment.id,
            actor=owner,
            payload=payload,
        )

    assert response.status_code == 201
    apply_async.assert_called_once()


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_director_invite_schedules_exactly_one_task(api_client):
    owner = create_user(username="director_schedule_owner")
    session = create_onboarding_session(actor=owner)

    with _patch_apply_async() as apply_async:
        response = _post_director_invitation(
            api_client,
            session_id=session.id,
            actor=owner,
        )

    assert response.status_code == 201
    apply_async.assert_called_once()


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_apply_async_passes_real_args(api_client):
    establishment = _create_establishment(name="Args Hotel")
    owner = create_user(username="args_owner")
    _create_owner_membership(user=owner, establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="args")

    with _patch_apply_async() as apply_async:
        response = _post_membership_invitation(
            api_client,
            establishment_id=establishment.id,
            actor=owner,
            payload=_membership_invite_payload(business_unit=business_unit),
        )

    assert response.status_code == 201
    body = response.json()
    invitation = EstablishmentInvitation.objects.get(
        membership_id=body["membership"]["id"],
    )
    _, kwargs = apply_async.call_args
    assert kwargs["args"] == [str(invitation.id), body["invitation_token"]]
    assert kwargs["ignore_result"] is True


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_apply_async_masks_argsrepr(api_client):
    establishment = _create_establishment(name="Argsrepr Hotel")
    owner = create_user(username="argsrepr_owner")
    _create_owner_membership(user=owner, establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="argsrepr")

    with _patch_apply_async() as apply_async:
        response = _post_membership_invitation(
            api_client,
            establishment_id=establishment.id,
            actor=owner,
            payload=_membership_invite_payload(business_unit=business_unit),
        )

    assert response.status_code == 201
    body = response.json()
    invitation = EstablishmentInvitation.objects.get(
        membership_id=body["membership"]["id"],
    )
    _, kwargs = apply_async.call_args
    assert kwargs["argsrepr"] == f"('{invitation.id}', '<redacted>')"
    assert body["invitation_token"] not in kwargs["argsrepr"]


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_apply_async_sets_ignore_result(api_client):
    establishment = _create_establishment(name="Ignore Hotel")
    owner = create_user(username="ignore_owner")
    _create_owner_membership(user=owner, establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="ignore")

    with _patch_apply_async() as apply_async:
        response = _post_membership_invitation(
            api_client,
            establishment_id=establishment.id,
            actor=owner,
            payload=_membership_invite_payload(business_unit=business_unit),
        )

    assert response.status_code == 201
    _, kwargs = apply_async.call_args
    assert kwargs["ignore_result"] is True


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_apply_async_never_uses_delay(api_client):
    establishment = _create_establishment(name="Delay Hotel")
    owner = create_user(username="delay_owner")
    _create_owner_membership(user=owner, establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="delay")

    with patch(
        "houston.establishments.tasks.send_establishment_invitation_email_task.delay"
    ) as delay:
        with _patch_apply_async():
            response = _post_membership_invitation(
                api_client,
                establishment_id=establishment.id,
                actor=owner,
                payload=_membership_invite_payload(business_unit=business_unit),
            )

    assert response.status_code == 201
    delay.assert_not_called()


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_owner_role_schedules_task():
    establishment = _create_establishment(name="Owner Role Hotel")
    owner = create_user(username="owner_role_user")
    membership = _create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    invitation = EstablishmentInvitation.objects.create(
        membership=membership,
        token_digest="abc123",
        expires_at=timezone.now() + timedelta(days=7),
    )

    with _patch_apply_async() as apply_async:
        schedule_establishment_invitation_email(
            invitation=invitation,
            membership=membership,
            raw_token="secret-token",
        )

    apply_async.assert_called_once()


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_unexpected_role_never_schedules_task(caplog: pytest.LogCaptureFixture):
    establishment = _create_establishment(name="Unexpected Role Hotel")
    user = create_user(username="unexpected_role_user")
    membership = _create_membership(
        user=user,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    EstablishmentMembership.objects.filter(id=membership.id).update(role="vendor")
    membership.refresh_from_db()
    invitation = EstablishmentInvitation.objects.create(
        membership=membership,
        token_digest="def456",
        expires_at=timezone.now() + timedelta(days=7),
    )

    caplog.set_level(logging.INFO)
    with _patch_apply_async() as apply_async:
        schedule_establishment_invitation_email(
            invitation=invitation,
            membership=membership,
            raw_token="secret-token",
        )

    apply_async.assert_not_called()
    assert "invitation_email_skipped_unsupported_role" in caplog.text


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_duplicate_409_schedules_no_task(api_client):
    establishment = _create_establishment(name="Duplicate Hotel")
    owner = create_user(username="duplicate_owner")
    _create_owner_membership(user=owner, establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="duplicate")
    payload = _membership_invite_payload(business_unit=business_unit)

    with _patch_apply_async() as apply_async:
        first_response = _post_membership_invitation(
            api_client,
            establishment_id=establishment.id,
            actor=owner,
            payload=payload,
        )
        second_response = _post_membership_invitation(
            api_client,
            establishment_id=establishment.id,
            actor=owner,
            payload=payload,
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    apply_async.assert_called_once()


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_transaction_rollback_schedules_no_task():
    establishment = _create_establishment(name="Rollback Hotel")
    user = create_user(username="rollback_staff")
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.INVITED,
    )

    with _patch_apply_async() as apply_async:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                invitation = EstablishmentInvitation.objects.create(
                    membership=membership,
                    token_digest="ghi789",
                    expires_at=timezone.now() + timedelta(days=7),
                )
                schedule_establishment_invitation_email(
                    invitation=invitation,
                    membership=membership,
                    raw_token="secret-token",
                )
                raise RuntimeError("force rollback")

    apply_async.assert_not_called()


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_enqueue_failure_does_not_return_500(api_client):
    establishment = _create_establishment(name="Enqueue Fail Hotel")
    owner = create_user(username="enqueue_fail_owner")
    _create_owner_membership(user=owner, establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="enqueue")

    with _patch_apply_async() as apply_async:
        apply_async.side_effect = RuntimeError("broker unavailable")
        response = _post_membership_invitation(
            api_client,
            establishment_id=establishment.id,
            actor=owner,
            payload=_membership_invite_payload(business_unit=business_unit),
        )

    assert response.status_code == 201


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=False)
def test_feature_flag_disabled_schedules_no_task(api_client):
    establishment = _create_establishment(name="Flag Off Hotel")
    owner = create_user(username="flag_off_owner")
    _create_owner_membership(user=owner, establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="flag")

    with _patch_apply_async() as apply_async:
        response = _post_membership_invitation(
            api_client,
            establishment_id=establishment.id,
            actor=owner,
            payload=_membership_invite_payload(business_unit=business_unit),
        )

    assert response.status_code == 201
    apply_async.assert_not_called()
