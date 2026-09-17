from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.test import RequestFactory, override_settings
from django.utils import timezone

from houston.accounts.email_change_services import (
    confirm_email_change,
    request_email_change,
)
from houston.accounts.models import EmailChangeRequest, PasswordResetRequest, User, UserSession
from houston.accounts.password_services import (
    InvalidPasswordChangeCredentialsError,
    InvalidPasswordResetTokenError,
    PasswordResetUnavailableError,
    PasswordUnchangedError,
    change_password,
    confirm_password_reset,
    request_password_reset,
)
from houston.accounts.services import (
    InvalidCredentialsError,
    create_password_authenticated_session,
    create_user_session,
)
from houston.accounts.tokens import digest_token
from houston.testing.factories import TEST_PASSWORD

pytestmark = pytest.mark.django_db

NEW_PASSWORD = "AnotherSecurePass456!"


def _user(*, email: str = "live@example.com", username: str | None = None) -> User:
    return User.objects.create_user(
        username=username or email.split("@", 1)[0],
        email=email,
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
        first_name="Marie",
    )


def _session(user: User) -> UserSession:
    request = RequestFactory().post("/api/v1/auth/password-change/")
    return create_user_session(request=request, user=user)


def _enqueue_inline(*args, **kwargs):
    return None


def test_wrong_current_password_is_noop():
    user = _user()
    current = _session(user)
    other = _session(user)

    with pytest.raises(InvalidPasswordChangeCredentialsError):
        change_password(
            user=user,
            current_password="wrong-password",
            new_password=NEW_PASSWORD,
            current_session=current,
        )

    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)
    current.refresh_from_db()
    other.refresh_from_db()
    assert current.status == UserSession.Status.ACTIVE
    assert other.status == UserSession.Status.ACTIVE


def test_same_password_is_rejected_without_revoking_sessions():
    user = _user()
    current = _session(user)
    other = _session(user)

    with pytest.raises(PasswordUnchangedError):
        change_password(
            user=user,
            current_password=TEST_PASSWORD,
            new_password=TEST_PASSWORD,
            current_session=current,
        )

    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)
    other.refresh_from_db()
    assert other.status == UserSession.Status.ACTIVE


@override_settings(RESEND_API_KEY="re_test_key")
def test_change_password_revokes_other_sessions_and_live_proofs(monkeypatch):
    user = _user()
    current = _session(user)
    other = _session(user)
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "email-token")
    request_email_change(user=user, password=TEST_PASSWORD, new_email="next@example.com")
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "reset-token")
    request_password_reset(email=user.email)

    change_password(
        user=user,
        current_password=TEST_PASSWORD,
        new_password=NEW_PASSWORD,
        current_session=current,
    )

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    current.refresh_from_db()
    other.refresh_from_db()
    assert current.status == UserSession.Status.ACTIVE
    assert other.status == UserSession.Status.REVOKED
    assert not EmailChangeRequest.objects.filter(
        user=user, revoked_at__isnull=True, consumed_at__isnull=True
    ).exists()
    assert not PasswordResetRequest.objects.filter(
        user=user, revoked_at__isnull=True, consumed_at__isnull=True
    ).exists()


def test_change_password_locks_user_first(monkeypatch):
    user = _user()
    current = _session(user)
    lock_order: list[str] = []
    user_select_for_update = User.objects.select_for_update

    def _user_select_for_update(*args, **kwargs):
        lock_order.append("user")
        return user_select_for_update(*args, **kwargs)

    monkeypatch.setattr(User.objects, "select_for_update", _user_select_for_update)

    change_password(
        user=user,
        current_password=TEST_PASSWORD,
        new_password=NEW_PASSWORD,
        current_session=current,
    )

    assert lock_order[0] == "user"


def test_stale_login_does_not_create_session_after_password_change():
    user = _user()
    request = RequestFactory().post("/api/v1/auth/login/")
    user.set_password(NEW_PASSWORD)
    user.save(update_fields=["password"])

    with pytest.raises(InvalidCredentialsError):
        create_password_authenticated_session(
            request=request,
            user=user,
            password=TEST_PASSWORD,
        )

    assert UserSession.objects.filter(user=user).count() == 0


@override_settings(RESEND_API_KEY="re_test_key")
def test_reset_request_creates_live_row_for_eligible_user(monkeypatch):
    user = _user()
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "reset-token")
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )

    request_password_reset(email="LIVE@example.com")

    live = PasswordResetRequest.objects.get(token_digest=digest_token("reset-token"))
    assert live.user_id == user.id
    assert live.email_at_issue == "live@example.com"
    assert live.revoked_at is None


@override_settings(RESEND_API_KEY="re_test_key")
@pytest.mark.parametrize(
    "status",
    [User.Status.PENDING, User.Status.SUSPENDED, User.Status.ANONYMIZED],
)
def test_reset_request_skips_ineligible_status(monkeypatch, status):
    user = _user(username=f"skip-{status}")
    user.status = status
    user.save(update_fields=["status"])
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )

    request_password_reset(email=user.email)

    assert PasswordResetRequest.objects.count() == 0


@override_settings(RESEND_API_KEY="re_test_key")
def test_reset_request_unknown_email_is_noop(monkeypatch):
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )
    request_password_reset(email="missing@example.com")
    assert PasswordResetRequest.objects.count() == 0


@override_settings(RESEND_API_KEY="")
def test_reset_request_missing_resend_is_fail_closed():
    _user()
    with pytest.raises(PasswordResetUnavailableError):
        request_password_reset(email="live@example.com")
    assert PasswordResetRequest.objects.count() == 0


@override_settings(RESEND_API_KEY="re_test_key")
def test_second_reset_request_revokes_previous_token(monkeypatch):
    user = _user()
    tokens = iter(["token-one", "token-two"])
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: next(tokens))
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )

    request_password_reset(email=user.email)
    request_password_reset(email=user.email)

    live = PasswordResetRequest.objects.filter(revoked_at__isnull=True, consumed_at__isnull=True)
    assert live.count() == 1
    assert live.get().token_digest == digest_token("token-two")
    with pytest.raises(InvalidPasswordResetTokenError):
        confirm_password_reset(raw_token="token-one", new_password=NEW_PASSWORD)


@override_settings(RESEND_API_KEY="re_test_key")
def test_confirm_reset_revokes_all_sessions_and_email_change(monkeypatch):
    user = _user()
    first = _session(user)
    second = _session(user)
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "email-token")
    request_email_change(user=user, password=TEST_PASSWORD, new_email="next@example.com")
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "reset-token")
    request_password_reset(email=user.email)

    confirm_password_reset(raw_token="reset-token", new_password=NEW_PASSWORD)

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == UserSession.Status.REVOKED
    assert second.status == UserSession.Status.REVOKED
    assert not EmailChangeRequest.objects.filter(
        user=user, revoked_at__isnull=True, consumed_at__isnull=True
    ).exists()


@override_settings(RESEND_API_KEY="re_test_key")
def test_confirm_reset_rejects_same_secret(monkeypatch):
    user = _user()
    session = _session(user)
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "same-token")
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )
    request_password_reset(email=user.email)

    with pytest.raises(PasswordUnchangedError):
        confirm_password_reset(raw_token="same-token", new_password=TEST_PASSWORD)

    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)
    session.refresh_from_db()
    assert session.status == UserSession.Status.ACTIVE
    reset = PasswordResetRequest.objects.get(token_digest=digest_token("same-token"))
    assert reset.consumed_at is None
    assert reset.revoked_at is None


@override_settings(RESEND_API_KEY="re_test_key")
def test_confirm_reset_rejects_email_at_issue_mismatch(monkeypatch):
    user = _user()
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "stale-email")
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )
    request_password_reset(email=user.email)
    user.email = "moved@example.com"
    user.save(update_fields=["email"])

    with pytest.raises(InvalidPasswordResetTokenError):
        confirm_password_reset(raw_token="stale-email", new_password=NEW_PASSWORD)

    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)


def test_confirm_unknown_token_is_generic():
    with pytest.raises(InvalidPasswordResetTokenError):
        confirm_password_reset(raw_token="no-such-token", new_password=NEW_PASSWORD)


@override_settings(RESEND_API_KEY="re_test_key")
def test_confirm_expired_is_generic(monkeypatch):
    user = _user()
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "expired-token")
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )
    request_password_reset(email=user.email)
    PasswordResetRequest.objects.update(expires_at=timezone.now() - timedelta(minutes=1))

    with pytest.raises(InvalidPasswordResetTokenError):
        confirm_password_reset(raw_token="expired-token", new_password=NEW_PASSWORD)
    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)


@override_settings(RESEND_API_KEY="re_test_key")
def test_reset_confirm_locks_user_before_reset_row(monkeypatch):
    user = _user()
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "lock-token")
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )
    request_password_reset(email=user.email)

    lock_order: list[str] = []
    user_select_for_update = User.objects.select_for_update
    reset_select_for_update = PasswordResetRequest.objects.select_for_update

    def _user_select_for_update(*args, **kwargs):
        lock_order.append("user")
        return user_select_for_update(*args, **kwargs)

    def _reset_select_for_update(*args, **kwargs):
        lock_order.append("reset")
        return reset_select_for_update(*args, **kwargs)

    monkeypatch.setattr(User.objects, "select_for_update", _user_select_for_update)
    monkeypatch.setattr(
        PasswordResetRequest.objects,
        "select_for_update",
        _reset_select_for_update,
    )

    confirm_password_reset(raw_token="lock-token", new_password=NEW_PASSWORD)
    assert lock_order[0] == "user"
    assert "reset" in lock_order
    assert lock_order.index("user") < lock_order.index("reset")


@override_settings(RESEND_API_KEY="re_test_key")
def test_email_confirm_revokes_live_password_reset(monkeypatch):
    user = _user()
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "reset-token")
    request_password_reset(email=user.email)
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "email-token")
    request_email_change(user=user, password=TEST_PASSWORD, new_email="next@example.com")

    confirm_email_change(raw_token="email-token")

    reset = PasswordResetRequest.objects.get(token_digest=digest_token("reset-token"))
    assert reset.revoked_at is not None
    with pytest.raises(InvalidPasswordResetTokenError):
        confirm_password_reset(raw_token="reset-token", new_password=NEW_PASSWORD)


@override_settings(RESEND_API_KEY="re_test_key")
def test_failed_email_confirm_does_not_revoke_password_reset(monkeypatch):
    user = _user()
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        _enqueue_inline,
    )
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "reset-keep")
    request_password_reset(email=user.email)
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "email-fail")
    request_email_change(user=user, password=TEST_PASSWORD, new_email="next@example.com")

    original_save = User.save

    def _save(self, *args, **kwargs):
        if self.pk == user.pk and self.email == "next@example.com":
            raise IntegrityError("accounts_user_email_ci_uniq")
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(User, "save", _save)

    from houston.accounts.email_change_services import EmailChangeDuplicateError

    with pytest.raises(EmailChangeDuplicateError):
        confirm_email_change(raw_token="email-fail")

    reset = PasswordResetRequest.objects.get(token_digest=digest_token("reset-keep"))
    assert reset.revoked_at is None
    assert reset.consumed_at is None
