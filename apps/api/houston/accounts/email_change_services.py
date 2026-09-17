from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.accounts import tokens
from houston.accounts.models import EmailChangeRequest, User

logger = logging.getLogger(__name__)

INVALID_EMAIL_CHANGE_TOKEN_DETAIL = "This email change request is not valid."
EMAIL_CHANGE_DUPLICATE_DETAIL = "An account with this email already exists."
EMAIL_CHANGE_UNCHANGED_DETAIL = "This is already your email address."
EMAIL_CHANGE_UNAVAILABLE_DETAIL = "Email change is temporarily unavailable."
INVALID_CREDENTIALS_DETAIL = "Invalid credentials."


class InvalidEmailChangeCredentialsError(Exception):
    pass


class EmailChangeUnchangedError(Exception):
    pass


class EmailChangeUnavailableError(Exception):
    pass


class EmailChangeDuplicateError(Exception):
    pass


class InvalidEmailChangeTokenError(Exception):
    pass


@dataclass(frozen=True)
class EmailChangeRequestResult:
    pending_email: str
    expires_at: datetime


def request_email_change(*, user: User, password: str, new_email: str) -> EmailChangeRequestResult:
    if not user.check_password(password):
        raise InvalidEmailChangeCredentialsError

    normalized_email = User.normalize_email_value(new_email)
    if normalized_email is None:
        raise EmailChangeUnchangedError
    if not settings.RESEND_API_KEY:
        raise EmailChangeUnavailableError

    raw_token = tokens.generate_raw_token()
    token_digest = tokens.digest_token(raw_token)
    now = timezone.now()
    expires_at = now + settings.HOUSTON_EMAIL_CHANGE_TTL

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if locked_user.status != User.Status.ACTIVE:
            raise InvalidEmailChangeCredentialsError
        if not locked_user.check_password(password):
            raise InvalidEmailChangeCredentialsError
        if normalized_email == locked_user.email:
            raise EmailChangeUnchangedError
        if User.objects.filter(email__iexact=normalized_email).exclude(pk=locked_user.pk).exists():
            raise EmailChangeDuplicateError
        EmailChangeRequest.objects.filter(
            user=locked_user,
            revoked_at__isnull=True,
            consumed_at__isnull=True,
        ).update(revoked_at=now, updated_at=now)
        change = EmailChangeRequest.objects.create(
            user=locked_user,
            new_email=normalized_email,
            token_digest=token_digest,
            expires_at=expires_at,
        )
        change_id = change.id
        transaction.on_commit(lambda: _enqueue_email_change_email(change_id, raw_token))

    return EmailChangeRequestResult(pending_email=normalized_email, expires_at=expires_at)


def confirm_email_change(*, raw_token: str) -> User:
    token = raw_token.strip()
    if not token:
        raise InvalidEmailChangeTokenError
    token_digest = tokens.digest_token(token)
    now = timezone.now()

    with transaction.atomic():
        change = EmailChangeRequest.objects.filter(token_digest=token_digest).first()
        if change is None:
            raise InvalidEmailChangeTokenError

        # Same order as initiate: user row, then the EmailChangeRequest row.
        locked_user = User.objects.select_for_update().get(pk=change.user_id)
        change = (
            EmailChangeRequest.objects.select_for_update()
            .filter(pk=change.pk)
            .first()
        )
        if change is None or _email_change_skip_reason(change, now=now) is not None:
            raise InvalidEmailChangeTokenError
        if locked_user.status != User.Status.ACTIVE:
            raise InvalidEmailChangeTokenError

        if (
            User.objects.filter(email__iexact=change.new_email)
            .exclude(pk=locked_user.pk)
            .exists()
        ):
            raise EmailChangeDuplicateError

        locked_user.email = change.new_email
        try:
            locked_user.save(update_fields=["email", "updated_at"])
        except IntegrityError as exc:
            raise EmailChangeDuplicateError from exc

        change.consumed_at = now
        change.save(update_fields=["consumed_at", "updated_at"])
        from houston.accounts.password_services import revoke_live_password_reset_requests

        revoke_live_password_reset_requests(user=locked_user, now=now)
        return locked_user


def revoke_live_email_change_requests(*, user: User, now: datetime | None = None) -> None:
    stamp = now or timezone.now()
    EmailChangeRequest.objects.filter(
        user=user,
        revoked_at__isnull=True,
        consumed_at__isnull=True,
    ).update(revoked_at=stamp, updated_at=stamp)


def _email_change_skip_reason(
    change: EmailChangeRequest,
    *,
    now: datetime | None = None,
) -> str | None:
    if change.revoked_at is not None:
        return "revoked"
    if change.consumed_at is not None:
        return "consumed"
    if change.expires_at <= (now or timezone.now()):
        return "expired"
    return None


def _enqueue_email_change_email(change_id, raw_token: str) -> None:
    from houston.accounts.tasks import send_email_change_email_task

    try:
        send_email_change_email_task.apply_async(
            args=[str(change_id), raw_token],
            argsrepr=f"('{change_id}', '<redacted>')",
            ignore_result=True,
        )
    except Exception:
        logger.exception(
            "email_change_email_enqueue_failed",
            extra={
                "event": "email_change_email_enqueue_failed",
                "email_change_id": str(change_id),
            },
        )
