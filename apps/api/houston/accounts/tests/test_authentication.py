from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.test.utils import override_settings
from django.utils import timezone

from houston.accounts.authentication import (
    BearerAccessTokenAuthentication,
    should_update_session_last_used_at,
    touch_session_last_used_at_if_due,
)
from houston.accounts.models import User
from houston.accounts.services import create_user_session, issue_access_token

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="auth_throttle_user",
        email="auth-throttle@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )


@pytest.fixture
def request_factory():
    return RequestFactory()


def test_should_update_session_last_used_at_when_never_used():
    now = timezone.now()

    assert (
        should_update_session_last_used_at(
            last_used_at=None,
            now=now,
            interval_seconds=60,
        )
        is True
    )


def test_should_not_update_session_last_used_at_within_interval():
    now = timezone.now()

    assert (
        should_update_session_last_used_at(
            last_used_at=now - timedelta(seconds=30),
            now=now,
            interval_seconds=60,
        )
        is False
    )


def test_should_update_session_last_used_at_after_interval():
    now = timezone.now()

    assert (
        should_update_session_last_used_at(
            last_used_at=now - timedelta(seconds=61),
            now=now,
            interval_seconds=60,
        )
        is True
    )


@override_settings(HOUSTON_AUTH_SESSION_LAST_USED_UPDATE_INTERVAL_SECONDS=60)
def test_touch_session_last_used_at_if_due_skips_write_within_interval(user, request_factory):
    request = request_factory.get("/api/v1/auth/bootstrap/")
    session = create_user_session(request=request, user=user)
    previous_last_used_at = timezone.now() - timedelta(seconds=30)
    session.last_used_at = previous_last_used_at
    session.save(update_fields=["last_used_at", "updated_at"])
    previous_updated_at = session.updated_at

    now = timezone.now()
    touched = touch_session_last_used_at_if_due(session=session, now=now)

    session.refresh_from_db()
    assert touched is False
    assert session.last_used_at == previous_last_used_at
    assert session.updated_at == previous_updated_at


@override_settings(HOUSTON_AUTH_SESSION_LAST_USED_UPDATE_INTERVAL_SECONDS=60)
def test_touch_session_last_used_at_if_due_writes_after_interval(user, request_factory):
    request = request_factory.get("/api/v1/auth/bootstrap/")
    session = create_user_session(request=request, user=user)
    session.last_used_at = timezone.now() - timedelta(seconds=61)
    session.save(update_fields=["last_used_at", "updated_at"])

    now = timezone.now()
    touched = touch_session_last_used_at_if_due(session=session, now=now)

    session.refresh_from_db()
    assert touched is True
    assert session.last_used_at == now


@override_settings(HOUSTON_AUTH_SESSION_LAST_USED_UPDATE_INTERVAL_SECONDS=60)
def test_bearer_authentication_skips_last_used_at_write_within_interval(
    user,
    request_factory,
):
    request = request_factory.get("/api/v1/auth/bootstrap/")
    session = create_user_session(request=request, user=user)
    issued_token = issue_access_token(session=session)
    previous_last_used_at = timezone.now() - timedelta(seconds=30)
    session.last_used_at = previous_last_used_at
    session.save(update_fields=["last_used_at", "updated_at"])
    previous_updated_at = session.updated_at

    auth_request = request_factory.get(
        "/api/v1/auth/bootstrap/",
        HTTP_AUTHORIZATION=f"Bearer {issued_token.raw_token}",
    )
    BearerAccessTokenAuthentication().authenticate(auth_request)

    session.refresh_from_db()
    assert session.last_used_at == previous_last_used_at
    assert session.updated_at == previous_updated_at


@override_settings(HOUSTON_AUTH_SESSION_LAST_USED_UPDATE_INTERVAL_SECONDS=60)
def test_bearer_authentication_updates_last_used_at_after_interval(user, request_factory):
    request = request_factory.get("/api/v1/auth/bootstrap/")
    session = create_user_session(request=request, user=user)
    issued_token = issue_access_token(session=session)
    session.last_used_at = timezone.now() - timedelta(seconds=61)
    session.save(update_fields=["last_used_at", "updated_at"])

    auth_request = request_factory.get(
        "/api/v1/auth/bootstrap/",
        HTTP_AUTHORIZATION=f"Bearer {issued_token.raw_token}",
    )
    before_auth = timezone.now()
    BearerAccessTokenAuthentication().authenticate(auth_request)

    session.refresh_from_db()
    assert session.last_used_at >= before_auth
