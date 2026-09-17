from __future__ import annotations

import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from houston.accounts.email_change_services import _email_change_skip_reason
from houston.accounts.models import EmailChangeRequest
from houston.establishments.resend_client import send_invitation_email_via_resend

logger = logging.getLogger(__name__)


def build_email_change_confirm_path(*, raw_token: str) -> str:
    return f"/email-change#{raw_token}"


def build_email_change_confirm_url(*, raw_token: str) -> str:
    base_url = settings.HOUSTON_PUBLIC_APP_URL.rstrip("/")
    return f"{base_url}{build_email_change_confirm_path(raw_token=raw_token)}"


def send_email_change_confirmation_email(*, change_id: str, raw_token: str) -> None:
    change = (
        EmailChangeRequest.objects.select_related("user")
        .filter(id=change_id)
        .first()
    )
    if change is None:
        logger.info(
            "email_change_email_task_skipped",
            extra={
                "event": "email_change_email_task_skipped",
                "email_change_id": change_id,
                "reason": "not_found",
            },
        )
        return

    skip_reason = _email_change_skip_reason(change)
    if skip_reason is not None:
        logger.info(
            "email_change_email_task_skipped",
            extra={
                "event": "email_change_email_task_skipped",
                "email_change_id": change_id,
                "reason": skip_reason,
            },
        )
        return

    if not settings.RESEND_API_KEY:
        logger.info(
            "email_change_email_task_skipped",
            extra={
                "event": "email_change_email_task_skipped",
                "email_change_id": change_id,
                "reason": "missing_api_key",
            },
        )
        return

    confirm_url = build_email_change_confirm_url(raw_token=raw_token)
    localized = timezone.localtime(change.expires_at)
    context = {
        "first_name": change.user.first_name,
        "confirm_url": confirm_url,
        "expires_at_label": localized.strftime("%d/%m/%Y à %H:%M"),
    }
    html_body = render_to_string("accounts/email/email_change.html", context)
    text_body = render_to_string("accounts/email/email_change.txt", context)
    send_invitation_email_via_resend(
        to_email=change.new_email,
        from_email=settings.HOUSTON_INVITATION_EMAIL_FROM,
        subject="Confirmez votre nouvelle adresse e-mail Spore",
        html_body=html_body,
        text_body=text_body,
        idempotency_key=f"email-change/{change.id}",
    )
