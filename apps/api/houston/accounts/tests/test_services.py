from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.accounts import tokens
from houston.accounts.models import AccessToken, SessionRefreshToken, User
from houston.accounts.services import (
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
    create_user_session,
    issue_access_token,
    issue_refresh_token,
    refresh_session,
    revoke_session,
    validate_refresh_token,
)

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

    bundle = refresh_session(raw_refresh_token=issued_token.raw_token)

    issued_token.record.refresh_from_db()
    assert issued_token.record.status == SessionRefreshToken.Status.USED
    assert bundle.refresh_token.record.family_id == issued_token.record.family_id


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
