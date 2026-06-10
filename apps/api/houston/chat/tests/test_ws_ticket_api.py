from __future__ import annotations

import time
import uuid

import pytest
from django.core.cache import cache
from django.test import override_settings
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    login,
    ws_ticket_url,
)
from houston.chat.ws_ticket import WsTicketError, consume_ws_ticket, issue_ws_ticket
from houston.establishments.models import EstablishmentMembership

pytestmark = pytest.mark.django_db


def test_ws_ticket_requires_authentication(api_client):
    establishment = create_establishment()
    response = api_client.post(ws_ticket_url(establishment.id))
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_ws_ticket_success(api_client):
    establishment = create_establishment()
    user = create_user(username="chat_ticket_user")
    create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)

    response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 60
    assert isinstance(body["ticket"], str)
    assert body["ticket"]


def test_ws_ticket_rejects_foreign_establishment(api_client):
    first = create_establishment()
    second = create_establishment()
    user = create_user(username="chat_foreign_est")
    create_membership(user=user, establishment=first)
    token = login(api_client, user=user)

    response = api_client.post(
        ws_ticket_url(second.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_ws_ticket_rejects_chat_disabled(api_client):
    establishment = create_establishment(chat_enabled=False)
    user = create_user(username="chat_disabled")
    create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)

    response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_ws_ticket_rejects_inactive_membership(api_client):
    establishment = create_establishment()
    user = create_user(username="chat_inactive_member")
    create_membership(
        user=user,
        establishment=establishment,
        status=EstablishmentMembership.Status.DEACTIVATED,
    )
    token = login(api_client, user=user)

    response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_ws_ticket_one_time_use():
    establishment = create_establishment()
    user = create_user(username="chat_one_time")
    membership = create_membership(user=user, establishment=establishment)
    session_id = uuid.uuid4()

    ticket, _ = issue_ws_ticket(membership=membership, session_id=session_id)
    consume_ws_ticket(ticket, establishment_id=establishment.id)

    with pytest.raises(WsTicketError):
        consume_ws_ticket(ticket, establishment_id=establishment.id)

    cache.clear()


def test_issue_and_consume_ws_ticket_unit():
    establishment = create_establishment()
    user = create_user(username="chat_unit")
    membership = create_membership(user=user, establishment=establishment)
    session_id = uuid.uuid4()

    ticket, expires_in = issue_ws_ticket(membership=membership, session_id=session_id)
    assert expires_in == 60

    payload = consume_ws_ticket(ticket, establishment_id=establishment.id)
    assert payload.membership_id == membership.id
    assert payload.user_id == user.id
    assert payload.session_id == session_id

    cache.clear()


@pytest.mark.slow
@override_settings(HOUSTON_CHAT_WS_TICKET_TTL_SECONDS=1)
def test_ws_ticket_expired_rejected():
    establishment = create_establishment()
    user = create_user(username="chat_expired_ticket")
    membership = create_membership(user=user, establishment=establishment)
    session_id = uuid.uuid4()

    ticket, expires_in = issue_ws_ticket(membership=membership, session_id=session_id)
    assert expires_in == 1

    time.sleep(1.1)

    with pytest.raises(WsTicketError):
        consume_ws_ticket(ticket, establishment_id=establishment.id)

    cache.clear()
