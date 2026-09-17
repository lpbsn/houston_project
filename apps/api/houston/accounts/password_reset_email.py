from __future__ import annotations

import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from houston.accounts.models import PasswordResetRequest
from houston.accounts.password_services import _password_reset_skip_reason
from houston.establishments.resend_client import send_invitation_email_via_resend

logger = logging.getLogger(__name__)


def build_password_reset_confirm_path(*, raw_token: str) -> str:
    return f"/password-reset#{raw_token}"


def build_password_reset_confirm_url(*, raw_token: str) -> str:
    base_url = settings.HOUSTON_PUBLIC_APP_URL.rstrip("/")
    return f"{base_url}{build_password_reset_confirm_path(raw_token=raw_token)}"


def send_password_reset_email(*, reset_id: str, raw_token: str) -> None:
    reset = (
        PasswordResetRequest.objects.select_related("user")
        .filter(id=reset_id)
        .first()
    )
    if reset is None:
        logger.info(
            "password_reset_email_task_skipped",
            extra={
                "event": "password_reset_email_task_skipped",
                "password_reset_id": reset_id,
                "reason": "not_found",
            },
        )
        return

    skip_reason = _password_reset_skip_reason(reset)
    if skip_reason is not None:
        logger.info(
            "password_reset_email_task_skipped",
            extra={
                "event": "password_reset_email_task_skipped",
                "password_reset_id": reset_id,
                "reason": skip_reason,
            },
        )
        return

    if not settings.RESEND_API_KEY:
        logger.info(
            "password_reset_email_task_skipped",
            extra={
                "event": "password_reset_email_task_skipped",
                "password_reset_id": reset_id,
                "reason": "missing_api_key",
            },
        )
        return

    confirm_url = build_password_reset_confirm_url(raw_token=raw_token)
    localized = timezone.localtime(reset.expires_at)
    context = {
        "first_name": reset.user.first_name,
        "confirm_url": confirm_url,
        "expires_at_label": localized.strftime("%d/%m/%Y à %H:%M"),
    }
    html_body = render_to_string("accounts/email/password_reset.html", context)
    text_body = render_to_string("accounts/email/password_reset.txt", context)
    send_invitation_email_via_resend(
        to_email=reset.email_at_issue,
        from_email=settings.HOUSTON_INVITATION_EMAIL_FROM,
        subject="Réinitialisez votre mot de passe Spore",
        html_body=html_body,
        text_body=text_body,
        idempotency_key=f"password-reset/{reset.id}",
    )
