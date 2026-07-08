from __future__ import annotations

import pytest

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.comments.constants import (
    CANNOT_REPLY_TO_SIGNAL_COMMENT_FROM_EXECUTION_ERROR_DETAIL,
    NOT_EXECUTION_ROOT_COMMENT_ERROR_DETAIL,
)
from houston.comments.services import (
    create_action_plan_execution_comment,
    create_signal_comment,
)
from houston.comments.tests.conftest import (
    auth_headers,
    build_api_membership,
    execution_comment_resolve_url,
    execution_comment_unresolve_url,
    execution_comments_url,
    login,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _setup_linked_execution(*, status=Signal.Status.OPEN):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=status,
    )
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Linked execution",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Inspect", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    return owner, staff, signal, execution


def test_execution_comments_include_inherited_signal_comments(api_client):
    owner, staff, signal, execution = _setup_linked_execution()
    create_signal_comment(author_membership=owner, signal=signal, body="signal note")
    create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="execution note",
    )

    token = login(api_client, user=staff.user)
    url = execution_comments_url(staff.establishment_id, execution.id)
    response = api_client.get(url, **auth_headers(token))
    assert response.status_code == 200

    items = response.json()
    assert len(items) == 2
    assert items[0]["item_type"] == "inherited_signal"
    assert items[0]["origin"] == "signal"
    assert items[0]["body"] == "signal note"
    assert items[1]["item_type"] == "execution_thread"
    assert items[1]["origin"] == "action_plan_execution"
    assert items[1]["body"] == "execution note"
    assert items[1]["replies"] == []
    assert items[1]["is_resolved"] is False


def test_execution_comments_include_inherited_when_signal_archived(api_client):
    owner, staff, signal, execution = _setup_linked_execution()
    create_signal_comment(author_membership=owner, signal=signal, body="signal note before archive")

    signal.status = Signal.Status.ARCHIVED
    signal.save(update_fields=["status", "updated_at"])

    token = login(api_client, user=staff.user)
    action_url = execution_comments_url(staff.establishment_id, execution.id)

    response = api_client.get(action_url, **auth_headers(token))
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["item_type"] == "inherited_signal"
    assert items[0]["origin"] == "signal"


def test_create_execution_comment_via_api(api_client):
    owner, staff, _, execution = _setup_linked_execution()
    token = login(api_client, user=staff.user)
    response = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {"body": "posted via API"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["origin"] == "action_plan_execution"
    assert body["body"] == "posted via API"


def test_execution_comment_threading(api_client):
    owner, staff, _, execution = _setup_linked_execution()
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="root",
    )
    token = login(api_client, user=owner.user)
    response = api_client.post(
        execution_comments_url(owner.establishment_id, execution.id),
        {"body": "reply", "parent_comment_id": str(root.id)},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201

    list_response = api_client.get(
        execution_comments_url(owner.establishment_id, execution.id),
        **auth_headers(token),
    )
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["item_type"] == "execution_thread"
    assert len(items[0]["replies"]) == 1
    assert items[0]["replies"][0]["body"] == "reply"


def test_mentioned_out_of_scope_staff_can_reply_to_execution_thread(api_client):
    owner, staff, _, execution = _setup_linked_execution()
    outsider = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    root = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="please chime in",
        mentioned_membership_ids=[outsider.id],
    )

    token = login(api_client, user=outsider.user)
    response = api_client.post(
        execution_comments_url(outsider.establishment_id, execution.id),
        {"body": "reply from mention", "parent_comment_id": str(root.id)},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["body"] == "reply from mention"


def test_mentioned_out_of_scope_staff_can_list_execution_comments(api_client):
    owner, staff, _, execution = _setup_linked_execution()
    outsider = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="please chime in",
        mentioned_membership_ids=[outsider.id],
    )

    token = login(api_client, user=outsider.user)
    response = api_client.get(
        execution_comments_url(outsider.establishment_id, execution.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_cannot_reply_to_inherited_signal_comment(api_client):
    owner, staff, signal, execution = _setup_linked_execution()
    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="signal root",
    )
    token = login(api_client, user=staff.user)
    response = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {"body": "nope", "parent_comment_id": str(signal_comment.id)},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == CANNOT_REPLY_TO_SIGNAL_COMMENT_FROM_EXECUTION_ERROR_DETAIL


def test_resolve_execution_comment(api_client):
    owner, staff, _, execution = _setup_linked_execution()
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="resolve me",
    )
    token = login(api_client, user=owner.user)
    response = api_client.post(
        execution_comment_resolve_url(owner.establishment_id, execution.id, root.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["is_resolved"] is True


def test_unresolve_execution_comment(api_client):
    owner, staff, _, execution = _setup_linked_execution()
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="resolve me",
    )
    token = login(api_client, user=owner.user)
    api_client.post(
        execution_comment_resolve_url(owner.establishment_id, execution.id, root.id),
        **auth_headers(token),
    )
    response = api_client.post(
        execution_comment_unresolve_url(owner.establishment_id, execution.id, root.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["is_resolved"] is False


def test_resolve_rejects_signal_root(api_client):
    owner, staff, signal, execution = _setup_linked_execution()
    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="signal",
    )
    token = login(api_client, user=owner.user)
    response = api_client.post(
        execution_comment_resolve_url(owner.establishment_id, execution.id, signal_comment.id),
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == NOT_EXECUTION_ROOT_COMMENT_ERROR_DETAIL


def test_out_of_scope_staff_cannot_create_execution_comment(api_client):
    owner, staff, _, execution = _setup_linked_execution()
    outsider = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=outsider.user)
    response = api_client.post(
        execution_comments_url(outsider.establishment_id, execution.id),
        {"body": "forbidden"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 404
