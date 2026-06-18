from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.services import create_action
from houston.actions.tests.conftest import build_api_membership_on_establishment
from houston.comments.services import create_action_comment, create_signal_comment
from houston.comments.tests.conftest import (
    action_comments_url,
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


def _setup_linked_action(*, status=Action.Status.OPEN):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked",
        instruction="Do it",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timedelta(days=1),
        signal_id=signal.id,
    )
    if status != Action.Status.OPEN:
        action.status = status
        action.save(update_fields=["status", "updated_at"])
    return owner, staff, signal, action


def test_action_comments_include_inherited_signal_comments(api_client):
    owner, staff, signal, action = _setup_linked_action()
    create_signal_comment(author_membership=owner, signal=signal, body="signal note")
    create_action_comment(author_membership=staff, action=action, body="action note")

    token = login(api_client, user=staff.user)
    url = action_comments_url(staff.establishment_id, action.id)
    response = api_client.get(url, **auth_headers(token))
    assert response.status_code == 200

    items = response.json()
    assert len(items) == 2
    assert items[0]["origin"] == "signal"
    assert items[0]["body"] == "signal note"
    assert items[1]["origin"] == "action"
    assert items[1]["body"] == "action note"


def test_action_comments_include_inherited_when_signal_archived(api_client):
    owner, staff, signal, action = _setup_linked_action()
    create_signal_comment(author_membership=owner, signal=signal, body="signal note before archive")

    signal.status = Signal.Status.ARCHIVED
    signal.save(update_fields=["status", "updated_at"])

    token = login(api_client, user=staff.user)
    detail_url = signal_detail_url(staff.establishment_id, signal.id)
    signal_comments = signal_comments_url(staff.establishment_id, signal.id)
    action_url = action_comments_url(staff.establishment_id, action.id)

    assert api_client.get(detail_url, **auth_headers(token)).status_code == 404
    assert api_client.get(signal_comments, **auth_headers(token)).status_code == 404

    response = api_client.get(action_url, **auth_headers(token))
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["origin"] == "signal"
    assert items[0]["body"] == "signal note before archive"


def test_action_comments_not_visible_on_signal_endpoint(api_client):
    owner, staff, signal, action = _setup_linked_action()
    create_action_comment(author_membership=staff, action=action, body="action only")

    token = login(api_client, user=owner.user)
    url = signal_comments_url(owner.establishment_id, signal.id)
    response = api_client.get(url, **auth_headers(token))
    assert response.status_code == 200
    assert response.json() == []


def test_create_action_comment_on_done_action(api_client):
    owner, staff, signal, action = _setup_linked_action(status=Action.Status.DONE)
    token = login(api_client, user=staff.user)
    url = action_comments_url(staff.establishment_id, action.id)

    response = api_client.post(
        url,
        {"body": "done but commentable"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["origin"] == "action"


def test_action_comments_404_for_out_of_scope_user(api_client):
    owner, staff, signal, action = _setup_linked_action()
    outsider = build_api_membership()
    token = login(api_client, user=outsider.user)
    url = action_comments_url(outsider.establishment_id, action.id)

    response = api_client.get(url, **auth_headers(token))
    assert response.status_code == 404
