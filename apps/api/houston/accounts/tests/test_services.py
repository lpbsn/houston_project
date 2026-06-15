from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import IntegrityError, close_old_connections
from django.utils import timezone

from houston.accounts import tokens
from houston.accounts.models import AccessToken, SessionRefreshToken, User, UserSession
from houston.accounts.services import (
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
    create_user_session,
    issue_access_token,
    issue_refresh_token,
    refresh_session,
    resolve_or_create_pending_user_for_invite,
    revoke_session,
    switch_selected_establishment,
    validate_refresh_token,
)
from houston.testing.factories import create_establishment, create_membership, create_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="manager_01",
        email="manager@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )


@pytest.fixture
def request_factory():
    from django.test import RequestFactory

    return RequestFactory()


def test_issue_access_token_retries_on_digest_collision(monkeypatch, user, request_factory):
    request = request_factory.get("/api/v1/auth/login/")
    session = create_user_session(request=request, user=user)
    first_token = issue_access_token(session=session)
    second_raw_token = "second-raw-token"
    generated_tokens = iter([first_token.raw_token, second_raw_token])

    monkeypatch.setattr(tokens, "generate_raw_token", lambda: next(generated_tokens))

    second_token = issue_access_token(session=session)

    assert second_token.raw_token == second_raw_token
    assert second_token.record.token_digest != first_token.record.token_digest
    assert AccessToken.objects.filter(session=session).count() == 2


def test_issue_refresh_token_retries_on_digest_collision(monkeypatch, user, request_factory):
    request = request_factory.get("/api/v1/auth/login/")
    session = create_user_session(request=request, user=user)
    first_token = issue_refresh_token(session=session, family_id=session.refresh_token_family_id)
    second_raw_token = "second-refresh-token"
    generated_tokens = iter([first_token.raw_token, second_raw_token])

    monkeypatch.setattr(tokens, "generate_raw_token", lambda: next(generated_tokens))

    second_token = issue_refresh_token(session=session, family_id=session.refresh_token_family_id)

    assert second_token.raw_token == second_raw_token
    assert second_token.record.token_digest != first_token.record.token_digest
    assert SessionRefreshToken.objects.filter(session=session).count() == 2


def test_validate_refresh_token_uses_timestamp_expiration(user, request_factory):
    request = request_factory.get("/api/v1/auth/login/")
    session = create_user_session(request=request, user=user)
    issued_token = issue_refresh_token(session=session, family_id=session.refresh_token_family_id)
    refresh_token = issued_token.record
    refresh_token.expires_at = timezone.now() - timedelta(seconds=1)
    refresh_token.save(update_fields=["expires_at", "updated_at"])

    with pytest.raises(InvalidRefreshTokenError):
        validate_refresh_token(raw_refresh_token=issued_token.raw_token)

    refresh_token.refresh_from_db()
    assert refresh_token.status == SessionRefreshToken.Status.EXPIRED


def test_refresh_session_marks_rotated_token_used(user, request_factory):
    request = request_factory.get("/api/v1/auth/login/")
    session = create_user_session(request=request, user=user)
    issued_token = issue_refresh_token(session=session, family_id=session.refresh_token_family_id)
    initial_access_count = AccessToken.objects.filter(session=session).count()

    bundle = refresh_session(raw_refresh_token=issued_token.raw_token)

    issued_token.record.refresh_from_db()
    assert issued_token.record.status == SessionRefreshToken.Status.USED
    assert issued_token.record.used_at is not None
    assert bundle.refresh_token.record.family_id == issued_token.record.family_id
    assert bundle.refresh_token.record.status == SessionRefreshToken.Status.ACTIVE
    assert bundle.refresh_token.raw_token != issued_token.raw_token
    assert bundle.access_token.record.session_id == session.id
    assert AccessToken.objects.filter(session=session).count() == initial_access_count + 1


def test_refresh_session_reuse_detection_revokes_session(user, request_factory):
    request = request_factory.get("/api/v1/auth/login/")
    session = create_user_session(request=request, user=user)
    issued_token = issue_refresh_token(session=session, family_id=session.refresh_token_family_id)

    refresh_session(raw_refresh_token=issued_token.raw_token)

    with pytest.raises(RefreshTokenReuseError):
        refresh_session(raw_refresh_token=issued_token.raw_token)

    session.refresh_from_db()
    assert session.status == session.Status.REVOKED
    assert session.revoked_at is not None


@pytest.mark.django_db(transaction=True)
def test_refresh_session_concurrent_rotation_only_one_succeeds(user, request_factory):
    request = request_factory.get("/api/v1/auth/login/")
    session = create_user_session(request=request, user=user)
    issued_token = issue_refresh_token(session=session, family_id=session.refresh_token_family_id)
    family_id = issued_token.record.family_id
    raw_refresh_token = issued_token.raw_token

    def try_refresh(_: int) -> str:
        close_old_connections()
        try:
            refresh_session(raw_refresh_token=raw_refresh_token)
            return "ok"
        except RefreshTokenReuseError:
            return "reuse"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(try_refresh, range(2)))

    assert results.count("ok") == 1
    assert results.count("reuse") == 1

    session.refresh_from_db()
    assert session.status == UserSession.Status.REVOKED

    family_tokens = SessionRefreshToken.objects.filter(session=session, family_id=family_id)
    assert family_tokens.count() == 2

    original_token = family_tokens.get(token_digest=issued_token.record.token_digest)
    assert original_token.used_at is not None
    assert all(
        token.status == SessionRefreshToken.Status.REVOKED for token in family_tokens
    )


def test_revoke_session_revokes_active_access_and_refresh_tokens(user, request_factory):
    request = request_factory.get("/api/v1/auth/login/")
    session = create_user_session(request=request, user=user)
    access_token = issue_access_token(session=session)
    refresh_token = issue_refresh_token(session=session, family_id=session.refresh_token_family_id)

    revoke_session(session=session)

    access_token.record.refresh_from_db()
    refresh_token.record.refresh_from_db()
    session.refresh_from_db()

    assert session.status == session.Status.REVOKED
    assert access_token.record.revoked_at is not None
    assert refresh_token.record.revoked_at is not None


def test_resolve_or_create_pending_user_returns_existing_on_email_race():
    existing_user = User.objects.create_user(
        username="pending_staff",
        email="pending-staff@example.com",
        password="unused",
        status=User.Status.PENDING,
    )
    existing_user.set_unusable_password()
    existing_user.save(update_fields=["password"])

    resolved_user = resolve_or_create_pending_user_for_invite(
        email="pending-staff@example.com",
        first_name="Updated",
        last_name="Name",
    )

    assert resolved_user.id == existing_user.id
    assert User.objects.filter(email__iexact="pending-staff@example.com").count() == 1


def test_resolve_or_create_pending_user_succeeds_when_username_taken_by_other_email():
    User.objects.create_user(
        username="alice",
        email="alice@other.com",
        password="secret",
        status=User.Status.ACTIVE,
    )

    resolved_user = resolve_or_create_pending_user_for_invite(
        email="alice@example.com",
        first_name="Alice",
        last_name="Example",
    )

    assert resolved_user.email == "alice@example.com"
    assert resolved_user.username != "alice"
    assert resolved_user.status == User.Status.PENDING
    assert User.objects.filter(email__iexact="alice@example.com").count() == 1


def test_resolve_or_create_pending_user_retries_after_save_integrity_error_without_email_match(
    monkeypatch,
):
    save_calls = {"count": 0}
    original_save = User.save

    def patched_save(self, *args, **kwargs):
        save_calls["count"] += 1
        if save_calls["count"] == 1:
            raise IntegrityError("simulated username race")
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(User, "save", patched_save)

    resolved_user = resolve_or_create_pending_user_for_invite(
        email="alice@example.com",
        first_name="Alice",
        last_name="Example",
    )

    assert save_calls["count"] == 2
    assert resolved_user.email == "alice@example.com"
    assert resolved_user.username != "alice"
    assert resolved_user.status == User.Status.PENDING
    assert User.objects.filter(email__iexact="alice@example.com").count() == 1


@pytest.mark.django_db(transaction=True)
def test_switch_selected_establishment_same_establishment_does_not_revoke_session(request_factory):
    user = create_user(username="switch_same_establishment")
    establishment = create_establishment(name="Same Establishment")
    membership = create_membership(user=user, establishment=establishment)
    request = request_factory.get("/api/v1/auth/login/")
    session = create_user_session(request=request, user=user)
    session.selected_establishment = membership.establishment
    session.save(update_fields=["selected_establishment", "updated_at"])

    with (
        patch("houston.chat.ws_notify.schedule_session_access_revoked") as mock_schedule,
        patch("houston.chat.ws_notify.notify_session_access_revoked") as mock_notify,
    ):
        payload = switch_selected_establishment(
            session=session,
            establishment_id=membership.establishment_id,
        )

    assert payload["authenticated"] is True
    assert payload["active_membership"]["establishment_id"] == str(membership.establishment_id)
    mock_schedule.assert_not_called()
    mock_notify.assert_not_called()

    session.refresh_from_db()
    assert session.selected_establishment_id == membership.establishment_id
