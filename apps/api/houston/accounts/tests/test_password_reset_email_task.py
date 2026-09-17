from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from houston.accounts import tokens as auth_tokens
from houston.accounts.models import PasswordResetRequest, User
from houston.accounts.password_reset_email import (
    build_password_reset_confirm_url,
    send_password_reset_email,
)
from houston.accounts.tasks import send_password_reset_email_task
from houston.testing.factories import TEST_PASSWORD

pytestmark = pytest.mark.django_db

PUBLIC_APP_URL = "https://app.spore-os.com"
INVITATION_FROM = "Spore <invitation@notify.spore-os.com>"


def _create_reset(*, raw_token: str, revoked=False, consumed=False, expired=False):
    user = User.objects.create_user(
        username=f"reset-{raw_token[:8]}",
        email=f"{raw_token[:8]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
        first_name="Marie",
    )
    now = timezone.now()
    return PasswordResetRequest.objects.create(
        user=user,
        email_at_issue=user.email,
        token_digest=auth_tokens.digest_token(raw_token),
        expires_at=now - timedelta(hours=1) if expired else now + timedelta(hours=1),
        revoked_at=now if revoked else None,
        consumed_at=now if consumed else None,
    )


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_task_skips_revoked_and_expired():
    revoked = _create_reset(raw_token="revoked-token", revoked=True)
    expired = _create_reset(raw_token="expired-token", expired=True)

    with patch(
        "houston.accounts.password_reset_email.send_invitation_email_via_resend"
    ) as send_mail:
        send_password_reset_email(reset_id=str(revoked.id), raw_token="revoked-token")
        send_password_reset_email(reset_id=str(expired.id), raw_token="expired-token")

    send_mail.assert_not_called()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="",
)
def test_task_skips_when_api_key_missing():
    reset = _create_reset(raw_token="live-token")
    with patch(
        "houston.accounts.password_reset_email.send_invitation_email_via_resend"
    ) as send_mail:
        send_password_reset_email(reset_id=str(reset.id), raw_token="live-token")
    send_mail.assert_not_called()


@override_settings(
    HOUSTON_PUBLIC_APP_URL=PUBLIC_APP_URL,
    HOUSTON_INVITATION_EMAIL_FROM=INVITATION_FROM,
    RESEND_API_KEY="re_test_key",
)
def test_task_sends_to_live_email_without_logging_secret(caplog):
    raw_token = "mail-secret-token"
    reset = _create_reset(raw_token=raw_token)
    caplog.set_level(logging.INFO)

    with patch(
        "houston.accounts.password_reset_email.send_invitation_email_via_resend"
    ) as send_mail:
        send_password_reset_email(reset_id=str(reset.id), raw_token=raw_token)

    send_mail.assert_called_once()
    kwargs = send_mail.call_args.kwargs
    assert kwargs["to_email"] == reset.email_at_issue
    assert kwargs["idempotency_key"] == f"password-reset/{reset.id}"
    expected_url = build_password_reset_confirm_url(raw_token=raw_token)
    assert expected_url in kwargs["html_body"]
    assert expected_url in kwargs["text_body"]
    assert raw_token not in caplog.text
    assert expected_url not in caplog.text


def test_task_declares_ignore_result():
    assert send_password_reset_email_task.ignore_result is True
