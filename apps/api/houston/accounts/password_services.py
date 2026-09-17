from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from houston.accounts import tokens
from houston.accounts.models import PasswordResetRequest, User, UserSession

logger = logging.getLogger(__name__)

INVALID_PASSWORD_RESET_TOKEN_DETAIL = "This password reset request is not valid."
PASSWORD_RESET_UNAVAILABLE_DETAIL = "Password reset is temporarily unavailable."
PASSWORD_RESET_REQUEST_DETAIL = (
    "If an account exists for this email, a reset link has been sent."
)
PASSWORD_UNCHANGED_DETAIL = "New password must be different from the current password."
INVALID_CREDENTIALS_DETAIL = "Invalid credentials."


class InvalidPasswordChangeCredentialsError(Exception):
    pass


class PasswordUnchangedError(Exception):
    pass


class PasswordRejectedError(Exception):
    def __init__(self, messages: list[str]):
        self.messages = messages
        super().__init__(messages[0] if messages else "Invalid password.")


class PasswordResetUnavailableError(Exception):
    pass


class InvalidPasswordResetTokenError(Exception):
    pass


def change_password(
    *,
    user: User,
    current_password: str,
    new_password: str,
    current_session: UserSession,
) -> None:
    if not user.check_password(current_password):
        raise InvalidPasswordChangeCredentialsError

    now = timezone.now()
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if not locked_user.check_password(current_password):
            raise InvalidPasswordChangeCredentialsError
        _ensure_new_password_acceptable(user=locked_user, new_password=new_password)
        locked_user.set_password(new_password)
        locked_user.save(update_fields=["password", "updated_at"])
        _revoke_live_password_reset_requests(user=locked_user, now=now)
        _revoke_live_email_change_requests(user=locked_user, now=now)
        from houston.accounts.services import revoke_user_sessions

        revoke_user_sessions(user=locked_user, exclude_session=current_session)


def request_password_reset(*, email: str) -> None:
    if not settings.RESEND_API_KEY:
        raise PasswordResetUnavailableError

    normalized_email = User.normalize_email_value(email)
    if normalized_email is None:
        return

    user = User.objects.filter(email__iexact=normalized_email).first()
    if user is None:
        return

    raw_token = tokens.generate_raw_token()
    token_digest = tokens.digest_token(raw_token)
    now = timezone.now()
    expires_at = now + settings.HOUSTON_PASSWORD_RESET_TTL

    with transaction.atomic():
        try:
            locked_user = User.objects.select_for_update().get(pk=user.pk)
        except User.DoesNotExist:
            return
        if not _is_password_reset_eligible(locked_user, email=normalized_email):
            return
        _revoke_live_password_reset_requests(user=locked_user, now=now)
        reset = PasswordResetRequest.objects.create(
            user=locked_user,
            email_at_issue=locked_user.email,
            token_digest=token_digest,
            expires_at=expires_at,
        )
        reset_id = reset.id
        transaction.on_commit(lambda: _enqueue_password_reset_email(reset_id, raw_token))


def confirm_password_reset(*, raw_token: str, new_password: str) -> User:
    token = raw_token.strip()
    if not token:
        raise InvalidPasswordResetTokenError
    token_digest = tokens.digest_token(token)
    now = timezone.now()

    with transaction.atomic():
        reset = PasswordResetRequest.objects.filter(token_digest=token_digest).first()
        if reset is None:
            raise InvalidPasswordResetTokenError

        locked_user = User.objects.select_for_update().get(pk=reset.user_id)
        reset = (
            PasswordResetRequest.objects.select_for_update()
            .filter(pk=reset.pk)
            .first()
        )
        if reset is None or _password_reset_skip_reason(reset, now=now) is not None:
            raise InvalidPasswordResetTokenError
        if not _is_password_reset_confirmable(locked_user, reset=reset):
            raise InvalidPasswordResetTokenError

        _ensure_new_password_acceptable(user=locked_user, new_password=new_password)
        locked_user.set_password(new_password)
        locked_user.save(update_fields=["password", "updated_at"])
        reset.consumed_at = now
        reset.save(update_fields=["consumed_at", "updated_at"])
        _revoke_live_password_reset_requests(user=locked_user, now=now)
        _revoke_live_email_change_requests(user=locked_user, now=now)
        from houston.accounts.services import revoke_user_sessions

        revoke_user_sessions(user=locked_user)
        return locked_user


def revoke_live_password_reset_requests(*, user: User, now: datetime | None = None) -> None:
    _revoke_live_password_reset_requests(user=user, now=now or timezone.now())


def _revoke_live_password_reset_requests(*, user: User, now: datetime) -> None:
    PasswordResetRequest.objects.filter(
        user=user,
        revoked_at__isnull=True,
        consumed_at__isnull=True,
    ).update(revoked_at=now, updated_at=now)


def _revoke_live_email_change_requests(*, user: User, now: datetime) -> None:
    from houston.accounts.email_change_services import revoke_live_email_change_requests

    revoke_live_email_change_requests(user=user, now=now)


def _ensure_new_password_acceptable(*, user: User, new_password: str) -> None:
    if user.check_password(new_password):
        raise PasswordUnchangedError
    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        raise PasswordRejectedError(list(exc.messages)) from exc


def _is_password_reset_eligible(user: User, *, email: str) -> bool:
    return (
        user.email == email
        and user.status == User.Status.ACTIVE
        and user.has_usable_password()
    )


def _is_password_reset_confirmable(user: User, *, reset: PasswordResetRequest) -> bool:
    return (
        user.status == User.Status.ACTIVE
        and user.has_usable_password()
        and user.email == reset.email_at_issue
    )


def _password_reset_skip_reason(
    reset: PasswordResetRequest,
    *,
    now: datetime | None = None,
) -> str | None:
    if reset.revoked_at is not None:
        return "revoked"
    if reset.consumed_at is not None:
        return "consumed"
    if reset.expires_at <= (now or timezone.now()):
        return "expired"
    return None


def _enqueue_password_reset_email(reset_id, raw_token: str) -> None:
    from houston.accounts.tasks import send_password_reset_email_task

    try:
        send_password_reset_email_task.apply_async(
            args=[str(reset_id), raw_token],
            argsrepr=f"('{reset_id}', '<redacted>')",
            ignore_result=True,
        )
    except Exception:
        logger.exception(
            "password_reset_email_enqueue_failed",
            extra={
                "event": "password_reset_email_enqueue_failed",
                "password_reset_id": str(reset_id),
            },
        )
