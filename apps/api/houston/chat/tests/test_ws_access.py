from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone
from houston.accounts.models import User, UserSession
from houston.accounts.services import create_user_session
from houston.chat.tests.conftest import create_establishment, create_membership, create_user
from houston.chat.ws_access import validate_ws_connection_access
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


def _session_for(*, user, establishment) -> UserSession:
    request = RequestFactory().get("/api/v1/auth/login/")
    session = create_user_session(request=request, user=user)
    session.selected_establishment = establishment
    session.save(update_fields=["selected_establishment", "updated_at"])
    return session


def _validate(*, session: UserSession, establishment, membership):
    return validate_ws_connection_access(
        session_id=session.id,
        establishment_id=establishment.id,
        membership_id=membership.id,
    )


def test_validate_ws_connection_access_ok():
    establishment = create_establishment()
    user = create_user(username="ws_access_ok")
    membership = create_membership(user=user, establishment=establishment)
    session = _session_for(user=user, establishment=establishment)

    access = _validate(session=session, establishment=establishment, membership=membership)

    assert access.ok is True
    assert access.reason is None


def test_validate_ws_connection_access_revoked_session():
    establishment = create_establishment()
    user = create_user(username="ws_access_revoked")
    membership = create_membership(user=user, establishment=establishment)
    session = _session_for(user=user, establishment=establishment)
    session.status = UserSession.Status.REVOKED
    session.revoked_at = timezone.now()
    session.save(update_fields=["status", "revoked_at", "updated_at"])

    access = _validate(session=session, establishment=establishment, membership=membership)

    assert access.ok is False
    assert access.reason == "session_revoked"


def test_validate_ws_connection_access_refresh_expired():
    establishment = create_establishment()
    user = create_user(username="ws_access_refresh_expired")
    membership = create_membership(user=user, establishment=establishment)
    session = _session_for(user=user, establishment=establishment)
    session.refresh_expires_at = timezone.now() - timedelta(seconds=1)
    session.save(update_fields=["refresh_expires_at", "updated_at"])

    access = _validate(session=session, establishment=establishment, membership=membership)

    assert access.ok is False
    assert access.reason == "session_revoked"


def test_validate_ws_connection_access_absolute_expired():
    establishment = create_establishment()
    user = create_user(username="ws_access_absolute_expired")
    membership = create_membership(user=user, establishment=establishment)
    session = _session_for(user=user, establishment=establishment)
    session.absolute_expires_at = timezone.now() - timedelta(seconds=1)
    session.save(update_fields=["absolute_expires_at", "updated_at"])

    access = _validate(session=session, establishment=establishment, membership=membership)

    assert access.ok is False
    assert access.reason == "session_revoked"


def test_validate_ws_connection_access_wrong_selected_establishment():
    establishment_a = create_establishment()
    establishment_b = Establishment.objects.create(
        name="Other site",
        organization=establishment_a.organization,
        status=Establishment.Status.ACTIVE,
        chat_enabled=True,
    )
    user = create_user(username="ws_access_wrong_selection")
    membership_a = create_membership(user=user, establishment=establishment_a)
    create_membership(user=user, establishment=establishment_b)
    session = _session_for(user=user, establishment=establishment_b)

    access = _validate(session=session, establishment=establishment_a, membership=membership_a)

    assert access.ok is False
    assert access.reason == "establishment_switched"


def test_validate_ws_connection_access_inactive_user():
    establishment = create_establishment()
    user = create_user(username="ws_access_inactive_user")
    membership = create_membership(user=user, establishment=establishment)
    session = _session_for(user=user, establishment=establishment)
    user.status = User.Status.SUSPENDED
    user.save(update_fields=["status"])

    access = _validate(session=session, establishment=establishment, membership=membership)

    assert access.ok is False
    assert access.reason == "access_denied"


def test_validate_ws_connection_access_inactive_membership():
    establishment = create_establishment()
    user = create_user(username="ws_access_inactive_membership")
    membership = create_membership(user=user, establishment=establishment)
    session = _session_for(user=user, establishment=establishment)
    membership.status = EstablishmentMembership.Status.DEACTIVATED
    membership.save(update_fields=["status", "updated_at"])

    access = _validate(session=session, establishment=establishment, membership=membership)

    assert access.ok is False
    assert access.reason == "access_denied"


def test_validate_ws_connection_access_inactive_establishment():
    establishment = create_establishment()
    user = create_user(username="ws_access_inactive_est")
    membership = create_membership(user=user, establishment=establishment)
    session = _session_for(user=user, establishment=establishment)
    establishment.status = Establishment.Status.DEACTIVATED
    establishment.save(update_fields=["status", "updated_at"])

    access = _validate(session=session, establishment=establishment, membership=membership)

    assert access.ok is False
    assert access.reason == "access_denied"


def test_validate_ws_connection_access_inactive_organization():
    establishment = create_establishment()
    user = create_user(username="ws_access_inactive_org")
    membership = create_membership(user=user, establishment=establishment)
    session = _session_for(user=user, establishment=establishment)
    organization = establishment.organization
    organization.status = Organization.Status.SUSPENDED
    organization.save(update_fields=["status", "updated_at"])

    access = _validate(session=session, establishment=establishment, membership=membership)

    assert access.ok is False
    assert access.reason == "access_denied"


def test_validate_ws_connection_access_chat_disabled():
    establishment = create_establishment()
    user = create_user(username="ws_access_chat_disabled")
    membership = create_membership(user=user, establishment=establishment)
    session = _session_for(user=user, establishment=establishment)
    establishment.chat_enabled = False
    establishment.save(update_fields=["chat_enabled", "updated_at"])

    access = _validate(session=session, establishment=establishment, membership=membership)

    assert access.ok is False
    assert access.reason == "chat_disabled"
