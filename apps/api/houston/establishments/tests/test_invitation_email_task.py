from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.test import override_settings
from django.utils import timezone
from resend.exceptions import ResendError

from houston.accounts import tokens as auth_tokens
from houston.accounts.models import User
from houston.establishments.invitation_email import (
    build_invitation_accept_url,
    build_invitation_idempotency_key,
    schedule_establishment_invitation_email,
    send_establishment_invitation_email,
)
from houston.establishments.models import EstablishmentInvitation, EstablishmentMembership
from houston.establishments.resend_client import (
    InvitationEmailTemporaryError,
)
from houston.establishments.tasks import send_establishment_invitation_email_task
from houston.testing.factories import build_membership, create_user

pytestmark = pytest.mark.django_db


INVITATION_FROM = "Spore <invitation@notify.spore-os.com>"
PUBLIC_APP_URL = "https://app.spore-os.com"


@pytest.fixture
def invitation_bundle():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    establishment = owner.establishment
    invitee = User.objects.create_user(
        username="invitee_user",
        email="invitee@example.com",
        password="unused",
        status=User.Status.PENDING,
        first_name="Jean",
        last_name="Dupont",
    )
    invitee.set_unusable_password()
    invitee.save(update_fields=["password"])
    membership = EstablishmentMembership.objects.create(
        user=invitee,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.INVITED,
    )
    raw_token = "raw-invitation-token-value"
    invitation = EstablishmentInvitation.objects.create(
        membership=membership,
        token_digest=auth_tokens.digest_token(raw_token),
        expires_at=timezone.now() + timedelta(days=7),
    )
    return invitation, raw_token, membership


def _resend_error(*, code: int, error_type: str) -> ResendError:
    return ResendError(
        code=code,
        error_type=error_type,
        message="resend failure",
        suggested_action="",
    )


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_task_calls_resend_with_correct_recipient(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch("houston.establishments.resend_client.resend.Emails.send") as send:
        send_establishment_invitation_email(
            invitation_id=str(invitation.id),
            raw_token=raw_token,
        )

    params = send.call_args.args[0]
    assert params["to"] == ["invitee@example.com"]


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_task_uses_exact_from_address(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch("houston.establishments.resend_client.resend.Emails.send") as send:
        send_establishment_invitation_email(
            invitation_id=str(invitation.id),
            raw_token=raw_token,
        )

    params = send.call_args.args[0]
    assert params["from"] == INVITATION_FROM


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_task_uses_exact_subject_template(invitation_bundle):
    invitation, raw_token, membership = invitation_bundle

    with patch("houston.establishments.resend_client.resend.Emails.send") as send:
        send_establishment_invitation_email(
            invitation_id=str(invitation.id),
            raw_token=raw_token,
        )

    params = send.call_args.args[0]
    assert params["subject"] == f"Invitation à rejoindre {membership.establishment.name} sur Spore"


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_task_builds_url_from_public_app_url(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle
    expected_url = build_invitation_accept_url(raw_token=raw_token)

    with patch("houston.establishments.resend_client.resend.Emails.send") as send:
        send_establishment_invitation_email(
            invitation_id=str(invitation.id),
            raw_token=raw_token,
        )

    params = send.call_args.args[0]
    assert expected_url.startswith(f"{PUBLIC_APP_URL}/invitations/")
    assert expected_url in params["html"]
    assert expected_url in params["text"]


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_task_uses_stable_idempotency_key(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch("houston.establishments.resend_client.resend.Emails.send") as send:
        send_establishment_invitation_email(
            invitation_id=str(invitation.id),
            raw_token=raw_token,
        )

    options = send.call_args.kwargs["options"]
    assert options["idempotency_key"] == build_invitation_idempotency_key(invitation.id)


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_retry_reuses_same_idempotency_key(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle
    captured_keys: list[str] = []

    def _send(*_args, **kwargs):
        captured_keys.append(kwargs["options"]["idempotency_key"])
        raise InvitationEmailTemporaryError("temporary")

    with patch("houston.establishments.resend_client.resend.Emails.send", side_effect=_send):
        with patch.object(
            send_establishment_invitation_email_task,
            "retry",
            side_effect=Retry(),
        ):
            with pytest.raises(Retry):
                send_establishment_invitation_email_task.run(str(invitation.id), raw_token)
            with pytest.raises(Retry):
                send_establishment_invitation_email_task.run(str(invitation.id), raw_token)

    assert len(captured_keys) == 2
    assert captured_keys[0] == captured_keys[1]


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_skips_revoked_invitation(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle
    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=["revoked_at", "updated_at"])

    with patch("houston.establishments.resend_client.resend.Emails.send") as send:
        send_establishment_invitation_email(
            invitation_id=str(invitation.id),
            raw_token=raw_token,
        )

    send.assert_not_called()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_skips_accepted_invitation(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at", "updated_at"])

    with patch("houston.establishments.resend_client.resend.Emails.send") as send:
        send_establishment_invitation_email(
            invitation_id=str(invitation.id),
            raw_token=raw_token,
        )

    send.assert_not_called()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_skips_expired_invitation(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle
    invitation.expires_at = timezone.now() - timedelta(minutes=1)
    invitation.save(update_fields=["expires_at", "updated_at"])

    with patch("houston.establishments.resend_client.resend.Emails.send") as send:
        send_establishment_invitation_email(
            invitation_id=str(invitation.id),
            raw_token=raw_token,
        )

    send.assert_not_called()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_retries_on_timeout(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch(
        "houston.establishments.invitation_email.send_invitation_email_via_resend",
        side_effect=InvitationEmailTemporaryError("network_error"),
    ):
        with patch.object(
            send_establishment_invitation_email_task,
            "retry",
            side_effect=Retry(),
        ) as mock_retry:
            with pytest.raises(Retry):
                send_establishment_invitation_email_task.run(str(invitation.id), raw_token)

    mock_retry.assert_called_once()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_retries_on_rate_limit_exceeded(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch(
        "houston.establishments.resend_client.resend.Emails.send",
        side_effect=_resend_error(code=429, error_type="rate_limit_exceeded"),
    ):
        with patch.object(
            send_establishment_invitation_email_task,
            "retry",
            side_effect=Retry(),
        ) as mock_retry:
            with pytest.raises(Retry):
                send_establishment_invitation_email_task.run(str(invitation.id), raw_token)

    mock_retry.assert_called_once()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_does_not_retry_daily_quota_exceeded(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch(
        "houston.establishments.resend_client.resend.Emails.send",
        side_effect=_resend_error(code=429, error_type="daily_quota_exceeded"),
    ):
        with patch.object(send_establishment_invitation_email_task, "retry") as mock_retry:
            send_establishment_invitation_email_task.run(str(invitation.id), raw_token)

    mock_retry.assert_not_called()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_does_not_retry_monthly_quota_exceeded(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch(
        "houston.establishments.resend_client.resend.Emails.send",
        side_effect=_resend_error(code=429, error_type="monthly_quota_exceeded"),
    ):
        with patch.object(send_establishment_invitation_email_task, "retry") as mock_retry:
            send_establishment_invitation_email_task.run(str(invitation.id), raw_token)

    mock_retry.assert_not_called()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_retries_on_5xx(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch(
        "houston.establishments.resend_client.resend.Emails.send",
        side_effect=_resend_error(code=503, error_type="application_error"),
    ):
        with patch.object(
            send_establishment_invitation_email_task,
            "retry",
            side_effect=Retry(),
        ) as mock_retry:
            with pytest.raises(Retry):
                send_establishment_invitation_email_task.run(str(invitation.id), raw_token)

    mock_retry.assert_called_once()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_retries_on_concurrent_idempotent_request(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch(
        "houston.establishments.resend_client.resend.Emails.send",
        side_effect=_resend_error(code=409, error_type="concurrent_idempotent_requests"),
    ):
        with patch.object(
            send_establishment_invitation_email_task,
            "retry",
            side_effect=Retry(),
        ) as mock_retry:
            with pytest.raises(Retry):
                send_establishment_invitation_email_task.run(str(invitation.id), raw_token)

    mock_retry.assert_called_once()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_does_not_retry_invalid_idempotent_request(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch(
        "houston.establishments.resend_client.resend.Emails.send",
        side_effect=_resend_error(code=409, error_type="invalid_idempotent_request"),
    ):
        with patch.object(send_establishment_invitation_email_task, "retry") as mock_retry:
            send_establishment_invitation_email_task.run(str(invitation.id), raw_token)

    mock_retry.assert_not_called()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_no_retry_on_permanent_4xx(invitation_bundle):
    invitation, raw_token, _membership = invitation_bundle

    with patch(
        "houston.establishments.resend_client.resend.Emails.send",
        side_effect=_resend_error(code=422, error_type="validation_error"),
    ):
        with patch.object(send_establishment_invitation_email_task, "retry") as mock_retry:
            send_establishment_invitation_email_task.run(str(invitation.id), raw_token)

    mock_retry.assert_not_called()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_no_token_or_full_url_in_logs(invitation_bundle, caplog: pytest.LogCaptureFixture):
    invitation, raw_token, _membership = invitation_bundle
    caplog.set_level(logging.INFO)

    with patch("houston.establishments.resend_client.resend.Emails.send"):
        send_establishment_invitation_email(
            invitation_id=str(invitation.id),
            raw_token=raw_token,
        )

    log_text = caplog.text
    assert raw_token not in log_text
    assert build_invitation_accept_url(raw_token=raw_token) not in log_text


def test_task_declares_ignore_result():
    assert send_establishment_invitation_email_task.ignore_result is True


@override_settings(HOUSTON_INVITATION_EMAIL_ENABLED=True)
def test_schedule_apply_async_passes_ignore_result():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    invitee = create_user(username="ignore_result_invitee")
    membership = EstablishmentMembership.objects.create(
        user=invitee,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.INVITED,
    )
    invitation = EstablishmentInvitation.objects.create(
        membership=membership,
        token_digest=auth_tokens.digest_token("token-for-ignore-result"),
        expires_at=timezone.now() + timedelta(days=7),
    )

    with patch(
        "houston.establishments.tasks.send_establishment_invitation_email_task.apply_async"
    ) as apply_async:
        with patch(
            "houston.establishments.invitation_email.transaction.on_commit",
            side_effect=lambda callback: callback(),
        ):
            schedule_establishment_invitation_email(
                invitation=invitation,
                membership=membership,
                raw_token="token-for-ignore-result",
            )

    _, kwargs = apply_async.call_args
    assert kwargs["ignore_result"] is True
