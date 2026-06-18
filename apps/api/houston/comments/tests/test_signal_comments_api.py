from __future__ import annotations

import uuid

import pytest

from houston.accounts.models import User
from houston.comments.constants import SIGNAL_COMMENT_PARENT_NOT_ALLOWED_ERROR_DETAIL
from houston.comments.tests.conftest import (
    auth_headers,
    build_api_membership,
    login,
    signal_comments_url,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.pipeline import signal_detail_url
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _signal(owner, *, status=Signal.Status.OPEN):
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    return create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=status,
    )


def test_list_and_create_signal_comments(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)
    token = login(api_client, user=owner.user)
    url = signal_comments_url(owner.establishment_id, signal.id)

    create_resp = api_client.post(
        url,
        {"body": "Premier commentaire"},
        format="json",
        **auth_headers(token),
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["origin"] == "signal"
    assert body["body"] == "Premier commentaire"
    assert body["author"]["membership_id"] == str(owner.id)
    assert body["mentions"] == []

    list_resp = api_client.get(url, **auth_headers(token))
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["id"] == body["id"]


def test_signal_comments_404_when_signal_invisible(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership()
    signal = _signal(owner)
    token = login(api_client, user=outsider.user)
    url = signal_comments_url(outsider.establishment_id, signal.id)

    response = api_client.get(url, **auth_headers(token))
    assert response.status_code == 404


def test_signal_comments_400_on_empty_body(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)
    token = login(api_client, user=owner.user)
    url = signal_comments_url(owner.establishment_id, signal.id)

    response = api_client.post(
        url,
        {"body": "   "},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


@pytest.mark.parametrize(
    "status",
    [Signal.Status.ARCHIVED, Signal.Status.CANCELED],
)
def test_signal_comments_404_when_signal_detail_would_404(api_client, status):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner, status=status)
    token = login(api_client, user=owner.user)
    detail_url = signal_detail_url(owner.establishment_id, signal.id)
    comments_url = signal_comments_url(owner.establishment_id, signal.id)

    detail_resp = api_client.get(detail_url, **auth_headers(token))
    assert detail_resp.status_code == 404

    get_resp = api_client.get(comments_url, **auth_headers(token))
    assert get_resp.status_code == 404

    post_resp = api_client.post(
        comments_url,
        {"body": "should not post"},
        format="json",
        **auth_headers(token),
    )
    assert post_resp.status_code == 404


def test_signal_comments_on_resolved_signal(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner, status=Signal.Status.RESOLVED)
    token = login(api_client, user=owner.user)
    url = signal_comments_url(owner.establishment_id, signal.id)

    response = api_client.post(
        url,
        {"body": "après résolution"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201


def test_signal_comments_rejects_invalid_mention(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)
    token = login(api_client, user=owner.user)
    url = signal_comments_url(owner.establishment_id, signal.id)

    response = api_client.post(
        url,
        {"body": "hello", "mentioned_membership_ids": [str(uuid.uuid4())]},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_signal_comments_with_valid_mention(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    mentioned_user = User.objects.create_user(
        username=f"m_{uuid.uuid4().hex[:8]}",
        password="secret",
        status=User.Status.ACTIVE,
    )
    mentioned = EstablishmentMembership.objects.create(
        user=mentioned_user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    signal = _signal(owner)
    token = login(api_client, user=owner.user)
    url = signal_comments_url(owner.establishment_id, signal.id)

    response = api_client.post(
        url,
        {"body": "ping", "mentioned_membership_ids": [str(mentioned.id)]},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["mentions"][0]["membership_id"] == str(mentioned.id)


def test_signal_comments_rejects_parent_comment_id(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)
    token = login(api_client, user=owner.user)
    url = signal_comments_url(owner.establishment_id, signal.id)

    response = api_client.post(
        url,
        {"body": "reply attempt", "parent_comment_id": str(uuid.uuid4())},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == SIGNAL_COMMENT_PARENT_NOT_ALLOWED_ERROR_DETAIL
