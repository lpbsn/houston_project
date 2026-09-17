from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.test import override_settings
from django.utils import timezone

from houston.accounts.email_change_services import (
    EmailChangeDuplicateError,
    EmailChangeUnavailableError,
    EmailChangeUnchangedError,
    InvalidEmailChangeCredentialsError,
    InvalidEmailChangeTokenError,
    confirm_email_change,
    request_email_change,
)
from houston.accounts.models import EmailChangeRequest, User
from houston.accounts.tokens import digest_token
from houston.testing.factories import TEST_PASSWORD

pytestmark = pytest.mark.django_db


def _user(*, email: str = "live@example.com", username: str | None = None) -> User:
    return User.objects.create_user(
        username=username or email.split("@", 1)[0],
        email=email,
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
        first_name="Marie",
    )


def _enqueue_inline(change_id, raw_token):
    return None


@override_settings(RESEND_API_KEY="re_test_key")
def test_wrong_password_is_noop(monkeypatch):
    user = _user()
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )

    with pytest.raises(InvalidEmailChangeCredentialsError):
        request_email_change(
            user=user,
            password="wrong-password",
            new_email="next@example.com",
        )

    assert EmailChangeRequest.objects.count() == 0
    user.refresh_from_db()
    assert user.email == "live@example.com"


@override_settings(RESEND_API_KEY="re_test_key")
def test_duplicate_email_is_rejected(monkeypatch):
    _user(email="taken@example.com", username="other")
    user = _user()
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )

    with pytest.raises(EmailChangeDuplicateError):
        request_email_change(
            user=user,
            password=TEST_PASSWORD,
            new_email="taken@example.com",
        )

    assert EmailChangeRequest.objects.count() == 0


@override_settings(RESEND_API_KEY="")
def test_missing_resend_key_is_fail_closed():
    user = _user()

    with pytest.raises(EmailChangeUnavailableError):
        request_email_change(
            user=user,
            password=TEST_PASSWORD,
            new_email="next@example.com",
        )

    assert EmailChangeRequest.objects.count() == 0


@override_settings(RESEND_API_KEY="re_test_key")
def test_same_email_is_rejected(monkeypatch):
    user = _user()
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )

    with pytest.raises(EmailChangeUnchangedError):
        request_email_change(
            user=user,
            password=TEST_PASSWORD,
            new_email="LIVE@example.com",
        )

    assert EmailChangeRequest.objects.count() == 0


@override_settings(RESEND_API_KEY="re_test_key")
def test_second_request_revokes_previous_token(monkeypatch):
    user = _user()
    tokens = iter(["token-one", "token-two"])
    monkeypatch.setattr(
        "houston.accounts.tokens.generate_raw_token",
        lambda: next(tokens),
    )
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )

    first = request_email_change(
        user=user,
        password=TEST_PASSWORD,
        new_email="first@example.com",
    )
    second = request_email_change(
        user=user,
        password=TEST_PASSWORD,
        new_email="second@example.com",
    )

    assert first.pending_email == "first@example.com"
    assert second.pending_email == "second@example.com"
    live = EmailChangeRequest.objects.filter(revoked_at__isnull=True, consumed_at__isnull=True)
    assert live.count() == 1
    assert live.get().new_email == "second@example.com"

    with pytest.raises(InvalidEmailChangeTokenError):
        confirm_email_change(raw_token="token-one")
    user.refresh_from_db()
    assert user.email == "live@example.com"


@override_settings(RESEND_API_KEY="re_test_key")
def test_confirm_applies_new_email(monkeypatch):
    user = _user()
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "confirm-token")
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )

    request_email_change(user=user, password=TEST_PASSWORD, new_email="next@example.com")
    confirmed = confirm_email_change(raw_token="confirm-token")

    confirmed.refresh_from_db()
    assert confirmed.email == "next@example.com"
    change = EmailChangeRequest.objects.get(token_digest=digest_token("confirm-token"))
    assert change.consumed_at is not None

    with pytest.raises(InvalidEmailChangeTokenError):
        confirm_email_change(raw_token="confirm-token")


@override_settings(RESEND_API_KEY="re_test_key")
def test_confirm_expired_is_generic(monkeypatch):
    user = _user()
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "expired-token")
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )
    request_email_change(user=user, password=TEST_PASSWORD, new_email="next@example.com")
    EmailChangeRequest.objects.update(expires_at=timezone.now() - timedelta(minutes=1))

    with pytest.raises(InvalidEmailChangeTokenError):
        confirm_email_change(raw_token="expired-token")
    user.refresh_from_db()
    assert user.email == "live@example.com"


@override_settings(RESEND_API_KEY="re_test_key")
def test_confirm_integrity_error_keeps_pending(monkeypatch):
    user = _user()
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "race-token")
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )
    request_email_change(user=user, password=TEST_PASSWORD, new_email="next@example.com")

    original_save = User.save

    def _save(self, *args, **kwargs):
        if self.pk == user.pk and self.email == "next@example.com":
            raise IntegrityError("accounts_user_email_ci_uniq")
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(User, "save", _save)

    with pytest.raises(EmailChangeDuplicateError):
        confirm_email_change(raw_token="race-token")

    user.refresh_from_db()
    assert user.email == "live@example.com"
    change = EmailChangeRequest.objects.get(token_digest=digest_token("race-token"))
    assert change.consumed_at is None
    assert change.revoked_at is None


@override_settings(RESEND_API_KEY="re_test_key")
def test_initiate_and_confirm_lock_user_before_change_row(monkeypatch):
    user = _user()
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "lock-token")
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        _enqueue_inline,
    )

    lock_order: list[str] = []
    user_select_for_update = User.objects.select_for_update
    change_select_for_update = EmailChangeRequest.objects.select_for_update

    def _user_select_for_update(*args, **kwargs):
        lock_order.append("user")
        return user_select_for_update(*args, **kwargs)

    def _change_select_for_update(*args, **kwargs):
        lock_order.append("change")
        return change_select_for_update(*args, **kwargs)

    monkeypatch.setattr(User.objects, "select_for_update", _user_select_for_update)
    monkeypatch.setattr(
        EmailChangeRequest.objects,
        "select_for_update",
        _change_select_for_update,
    )

    lock_order.clear()
    request_email_change(user=user, password=TEST_PASSWORD, new_email="next@example.com")
    assert lock_order[0] == "user"

    lock_order.clear()
    confirm_email_change(raw_token="lock-token")
    assert lock_order[0] == "user"
    assert "change" in lock_order
    assert lock_order.index("user") < lock_order.index("change")
