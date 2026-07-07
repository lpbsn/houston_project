from __future__ import annotations

import time

import pytest

from houston.action_plans.constants import (
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
)
from houston.action_plans.feed_pin_services import pin_action_plan_execution_for_membership
from houston.action_plans.models import ActionPlanExecutionFeedPin
from houston.action_plans.services import (
    cancel_action_plan_execution,
    mark_action_plan_execution_done,
)
from houston.action_plans.tests.helpers import (
    action_plan_execution_feed_url,
    action_plan_execution_url,
    build_assignee_payload,
)
from houston.action_plans.tests.test_execution_feed_api import (
    _create_execution,
    _feed_execution_ids,
    _feed_query,
)
from houston.testing.auth import auth_headers, login
from houston.testing.auth import build_api_membership as build_foreign_membership

pytestmark = pytest.mark.django_db


def _pin_url(establishment_id, execution_id) -> str:
    return action_plan_execution_url(establishment_id, execution_id, "pin/")


def _unpin_url(establishment_id, execution_id) -> str:
    return action_plan_execution_url(establishment_id, execution_id, "unpin/")


def test_pin_unpin_idempotent(api_client, owner_membership, business_unit):
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pin target",
    )
    token = login(api_client, user=owner_membership.user)
    pin_url = _pin_url(owner_membership.establishment_id, execution.id)

    first = api_client.post(pin_url, **auth_headers(token))
    second = api_client.post(pin_url, **auth_headers(token))
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["is_pinned"] is True
    assert second.json()["is_pinned"] is True

    unpin_url = _unpin_url(owner_membership.establishment_id, execution.id)
    third = api_client.post(unpin_url, **auth_headers(token))
    fourth = api_client.post(unpin_url, **auth_headers(token))
    assert third.status_code == 200
    assert fourth.status_code == 200
    assert third.json()["is_pinned"] is False
    assert fourth.json()["is_pinned"] is False


def test_pin_is_personal(api_client, owner_membership, manager_membership, business_unit):
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Shared execution",
    )
    pending = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pending validation",
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        requires_validation=True,
    )
    owner_token = login(api_client, user=owner_membership.user)
    manager_token = login(api_client, user=manager_membership.user)

    response = api_client.post(
        _pin_url(owner_membership.establishment_id, execution.id),
        **auth_headers(owner_token),
    )
    assert response.status_code == 200

    owner_feed = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + _feed_query("general"),
        **auth_headers(owner_token),
    )
    manager_feed = api_client.get(
        action_plan_execution_feed_url(manager_membership.establishment_id)
        + _feed_query("general"),
        **auth_headers(manager_token),
    )
    assert owner_feed.status_code == 200
    assert manager_feed.status_code == 200
    assert _feed_execution_ids(owner_feed.json())[0] == str(execution.id)
    assert str(execution.id) not in _feed_execution_ids(manager_feed.json())[:1]
    assert _feed_execution_ids(manager_feed.json())[0] == str(pending.id)


def test_pinned_cross_status_at_top(api_client, owner_membership, business_unit):
    pending = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pending validation",
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        requires_validation=True,
    )
    in_progress = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="In progress",
        status=EXECUTION_STATUS_IN_PROGRESS,
    )
    token = login(api_client, user=owner_membership.user)
    api_client.post(
        _pin_url(owner_membership.establishment_id, in_progress.id),
        **auth_headers(token),
    )

    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert _feed_execution_ids(response.json())[:2] == [str(in_progress.id), str(pending.id)]


def test_pinned_fifo(api_client, owner_membership, business_unit):
    first = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="First pin",
    )
    second = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Second pin",
    )
    third = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Unpinned",
    )
    token = login(api_client, user=owner_membership.user)
    api_client.post(_pin_url(owner_membership.establishment_id, first.id), **auth_headers(token))
    time.sleep(0.01)
    api_client.post(_pin_url(owner_membership.establishment_id, second.id), **auth_headers(token))

    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert _feed_execution_ids(response.json())[:3] == [
        str(first.id),
        str(second.id),
        str(third.id),
    ]


def test_pin_visible_in_personal_and_general(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Both views",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    staff_token = login(api_client, user=staff_membership.user)
    api_client.post(
        _pin_url(staff_membership.establishment_id, execution.id),
        **auth_headers(staff_token),
    )

    for view_mode in ("personal", "general"):
        response = api_client.get(
            action_plan_execution_feed_url(staff_membership.establishment_id)
            + _feed_query(view_mode),
            **auth_headers(staff_token),
        )
        assert response.status_code == 200
        payload = response.json()["items"][0]["action_plan_execution"]
        assert payload["id"] == str(execution.id)
        assert payload["is_pinned"] is True


def test_pin_not_visible_returns_404(api_client, owner_membership, business_unit):
    foreign = build_foreign_membership()
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Local only",
    )
    foreign_token = login(api_client, user=foreign.user)
    response = api_client.post(
        _pin_url(foreign.establishment_id, execution.id),
        **auth_headers(foreign_token),
    )
    assert response.status_code == 404


def test_staff_can_pin_for_self(api_client, owner_membership, staff_membership, business_unit):
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Staff pin",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    staff_token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        _pin_url(staff_membership.establishment_id, execution.id),
        **auth_headers(staff_token),
    )
    assert response.status_code == 200
    assert response.json()["is_pinned"] is True


def test_pins_deleted_on_done_and_cancel(api_client, owner_membership, business_unit):
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Lifecycle cleanup",
        requires_validation=False,
    )
    pin_action_plan_execution_for_membership(
        membership=owner_membership,
        execution_id=execution.id,
    )
    assert ActionPlanExecutionFeedPin.objects.filter(
        action_plan_execution_id=execution.id,
    ).exists()

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )
    assert not ActionPlanExecutionFeedPin.objects.filter(
        action_plan_execution_id=execution.id,
    ).exists()

    execution_cancel = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Cancel cleanup",
    )
    pin_action_plan_execution_for_membership(
        membership=owner_membership,
        execution_id=execution_cancel.id,
    )
    cancel_action_plan_execution(
        execution_id=execution_cancel.id,
        actor=owner_membership,
    )
    assert not ActionPlanExecutionFeedPin.objects.filter(
        action_plan_execution_id=execution_cancel.id,
    ).exists()


def test_feed_cursor_stable_with_pins(api_client, owner_membership, business_unit):
    executions = [
        _create_execution(
            owner_membership,
            business_unit=business_unit,
            title=f"Feed item {index}",
        )
        for index in range(4)
    ]
    token = login(api_client, user=owner_membership.user)
    api_client.post(
        _pin_url(owner_membership.establishment_id, executions[2].id),
        **auth_headers(token),
    )

    first = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general")
        + "&page_size=2",
        **auth_headers(token),
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    second = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general")
        + f"&page_size=2&cursor={first_body['next_cursor']}",
        **auth_headers(token),
    )
    assert second.status_code == 200
    first_ids = _feed_execution_ids(first_body)
    second_ids = _feed_execution_ids(second.json())
    assert len(first_ids) == 2
    assert len(second_ids) == 2
    assert first_ids[0] == str(executions[2].id)
    assert not set(first_ids).intersection(second_ids)


def test_feed_item_contract_includes_is_pinned_and_can_pin(
    api_client,
    owner_membership,
    business_unit,
):
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Contract pin fields",
    )
    token = login(api_client, user=owner_membership.user)
    api_client.post(
        _pin_url(owner_membership.establishment_id, execution.id),
        **auth_headers(token),
    )
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()["items"][0]["action_plan_execution"]
    assert payload["is_pinned"] is True
    assert payload["permission_hints"]["can_pin"] is True
