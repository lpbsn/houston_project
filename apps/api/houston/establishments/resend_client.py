from __future__ import annotations

import resend
from django.conf import settings
from resend.exceptions import ResendError


class InvitationEmailTemporaryError(Exception):
    """Resend or network failure that may succeed on retry."""


class InvitationEmailPermanentError(Exception):
    """Resend or configuration failure that should not be retried."""


def _http_status_code(exc: ResendError) -> int | None:
    try:
        return int(exc.code)
    except (TypeError, ValueError):
        return None


def classify_resend_error(exc: ResendError) -> Exception:
    error_type = exc.error_type
    status_code = _http_status_code(exc)

    if error_type == "concurrent_idempotent_requests":
        return InvitationEmailTemporaryError(error_type)
    if error_type == "invalid_idempotent_request":
        return InvitationEmailPermanentError(error_type)
    if error_type in {"daily_quota_exceeded", "monthly_quota_exceeded"}:
        return InvitationEmailPermanentError(error_type)
    if error_type == "rate_limit_exceeded":
        return InvitationEmailTemporaryError(error_type)
    if status_code is not None and status_code >= 500:
        return InvitationEmailTemporaryError(error_type or "server_error")
    if status_code == 409:
        return InvitationEmailTemporaryError(error_type or "conflict")
    if status_code is not None and 400 <= status_code < 500:
        return InvitationEmailPermanentError(error_type or "client_error")
    return InvitationEmailTemporaryError(error_type or "unknown")


def send_invitation_email_via_resend(
    *,
    to_email: str,
    from_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    idempotency_key: str,
) -> None:
    if not settings.RESEND_API_KEY:
        raise InvitationEmailPermanentError("missing_api_key")

    resend.api_key = settings.RESEND_API_KEY
    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    options: resend.Emails.SendOptions = {"idempotency_key": idempotency_key}

    try:
        resend.Emails.send(params, options=options)
    except ResendError as exc:
        raise classify_resend_error(exc) from exc
    except OSError as exc:
        raise InvitationEmailTemporaryError("network_error") from exc
