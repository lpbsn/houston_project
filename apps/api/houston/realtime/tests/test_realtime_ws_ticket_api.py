from __future__ import annotations

import pytest
from houston.realtime.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    login,
    ws_realtime_ticket_url,
)
from houston.realtime.ws_ticket import WsTicketError, consume_ws_ticket, issue_ws_ticket

pytestmark = pytest.mark.django_db


def test_realtime_ws_ticket_requires_authentication(api_client):
    establishment = create_establishment()
    response = api_client.post(ws_realtime_ticket_url(establishment.id))
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_realtime_ws_ticket_success(api_client):
    establishment = create_establishment()
    user = create_user(username="realtime_ticket_user")
    create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)

    response = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 60
    assert isinstance(body["ticket"], str)
    assert body["ticket"]


def test_realtime_ws_ticket_allows_chat_disabled_establishment(api_client):
    establishment = create_establishment(chat_enabled=False)
    user = create_user(username="realtime_chat_disabled")
    create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)

    response = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200


def test_realtime_ws_ticket_rejects_foreign_establishment(api_client):
    first = create_establishment()
    second = create_establishment()
    user = create_user(username="realtime_foreign_est")
    create_membership(user=user, establishment=first)
    token = login(api_client, user=user)

    response = api_client.post(
        ws_realtime_ticket_url(second.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 403


def test_realtime_ws_ticket_one_time_use(api_client):
    establishment = create_establishment()
    user = create_user(username="realtime_one_time")
    membership = create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)

    response = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    raw_ticket = response.json()["ticket"]

    consume_ws_ticket(raw_ticket, establishment_id=establishment.id)

    with pytest.raises(WsTicketError):
        consume_ws_ticket(raw_ticket, establishment_id=establishment.id)

    assert membership.id is not None


def test_issue_ws_ticket_binds_membership(api_client):
    establishment = create_establishment()
    user = create_user(username="realtime_issue")
    membership = create_membership(user=user, establishment=establishment)
    login(api_client, user=user)
    from houston.accounts.models import UserSession

    session = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session is not None

    raw_ticket, _expires = issue_ws_ticket(membership=membership, session_id=session.id)
    payload = consume_ws_ticket(raw_ticket, establishment_id=establishment.id)

    assert payload.membership_id == membership.id
    assert payload.establishment_id == establishment.id
    assert payload.user_id == user.id
