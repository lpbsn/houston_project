from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from houston.action_plans.constants import (
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.exceptions import (
    ActionPlanExecutionFeedPinLimitError,
    ActionPlanValidationError,
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
    create_execution,
    feed_execution_ids,
    feed_query,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import (
    auth_headers,
    login,
)
from houston.testing.auth import (
    build_api_membership as build_foreign_membership,
)

pytestmark = pytest.mark.django_db


def _pin_url(establishment_id, execution_id) -> str:
    return action_plan_execution_url(establishment_id, execution_id, "pin/")


def _unpin_url(establishment_id, execution_id) -> str:
    return action_plan_execution_url(establishment_id, execution_id, "unpin/")


def test_pin_unpin_idempotent(api_client, owner_membership, business_unit):
    execution = create_execution(
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


def test_fourth_pin_requires_explicit_replacement(
    api_client,
    owner_membership,
    business_unit,
):
    executions = [
        create_execution(
            owner_membership,
            business_unit=business_unit,
            title=f"Pinned {index}",
        )
        for index in range(4)
    ]
    token = login(api_client, user=owner_membership.user)
    for execution in executions[:3]:
        response = api_client.post(
            _pin_url(owner_membership.establishment_id, execution.id),
            data={},
            format="json",
            **auth_headers(token),
        )
        assert response.status_code == 200

    response = api_client.post(
        _pin_url(owner_membership.establishment_id, executions[3].id),
        data={},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "action_plan_execution_feed_pin_limit_reached",
        "detail": "Three executions are already pinned.",
        "replacement_candidates": [
            {"execution_id": str(execution.id), "title": execution.title}
            for execution in executions[:3]
        ],
    }
    assert ActionPlanExecutionFeedPin.objects.filter(
        membership=owner_membership,
    ).count() == 3

    already_pinned = api_client.post(
        _pin_url(owner_membership.establishment_id, executions[0].id),
        data={},
        format="json",
        **auth_headers(token),
    )
    assert already_pinned.status_code == 200
    assert already_pinned.json() == {"is_pinned": True}


def test_pin_replacement_is_explicit_and_atomic(
    api_client,
    owner_membership,
    business_unit,
):
    executions = [
        create_execution(
            owner_membership,
            business_unit=business_unit,
            title=f"Replacement {index}",
        )
        for index in range(4)
    ]
    for execution in executions[:3]:
        pin_action_plan_execution_for_membership(
            membership=owner_membership,
            execution_id=execution.id,
        )
    token = login(api_client, user=owner_membership.user)

    response = api_client.post(
        _pin_url(owner_membership.establishment_id, executions[3].id),
        data={"replace_execution_id": str(executions[1].id)},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {"is_pinned": True}
    pinned_ids = set(
        ActionPlanExecutionFeedPin.objects.filter(
            membership=owner_membership,
        ).values_list("action_plan_execution_id", flat=True)
    )
    assert pinned_ids == {executions[0].id, executions[2].id, executions[3].id}


def test_invalid_pin_replacement_keeps_existing_pins(
    api_client,
    owner_membership,
    business_unit,
):
    executions = [
        create_execution(
            owner_membership,
            business_unit=business_unit,
            title=f"Atomic {index}",
        )
        for index in range(4)
    ]
    for execution in executions[:3]:
        pin_action_plan_execution_for_membership(
            membership=owner_membership,
            execution_id=execution.id,
        )
    token = login(api_client, user=owner_membership.user)

    response = api_client.post(
        _pin_url(owner_membership.establishment_id, executions[3].id),
        data={"replace_execution_id": str(uuid.uuid4())},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 404
    pinned_ids = set(
        ActionPlanExecutionFeedPin.objects.filter(
            membership=owner_membership,
        ).values_list("action_plan_execution_id", flat=True)
    )
    assert pinned_ids == {execution.id for execution in executions[:3]}


@pytest.mark.django_db(transaction=True)
def test_concurrent_pins_at_limit_allow_only_one(
    owner_membership,
    business_unit,
):
    executions = [
        create_execution(
            owner_membership,
            business_unit=business_unit,
            title=f"Concurrent {index}",
        )
        for index in range(4)
    ]
    for execution in executions[:2]:
        pin_action_plan_execution_for_membership(
            membership=owner_membership,
            execution_id=execution.id,
        )
    start = Barrier(2)

    def pin(execution_id):
        close_old_connections()
        try:
            membership = EstablishmentMembership.objects.get(pk=owner_membership.pk)
            start.wait()
            try:
                pin_action_plan_execution_for_membership(
                    membership=membership,
                    execution_id=execution_id,
                )
            except ActionPlanExecutionFeedPinLimitError:
                return "limit"
            return "created"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(pin, [executions[2].id, executions[3].id]))

    assert sorted(outcomes) == ["created", "limit"]
    assert ActionPlanExecutionFeedPin.objects.filter(
        membership_id=owner_membership.id,
    ).count() == 3


def test_pin_rejects_inactive_membership_at_write_time(
    owner_membership,
    business_unit,
):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Inactive membership",
    )
    owner_membership.status = EstablishmentMembership.Status.DEACTIVATED
    owner_membership.save(update_fields=["status", "updated_at"])

    with pytest.raises(ActionPlanValidationError, match="Execution not found"):
        pin_action_plan_execution_for_membership(
            membership=owner_membership,
            execution_id=execution.id,
        )

    assert not ActionPlanExecutionFeedPin.objects.filter(
        membership=owner_membership,
        action_plan_execution=execution,
    ).exists()


def test_pin_is_personal(api_client, owner_membership, manager_membership, business_unit):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Shared execution",
    )
    pending = create_execution(
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
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(owner_token),
    )
    manager_feed = api_client.get(
        action_plan_execution_feed_url(manager_membership.establishment_id)
        + feed_query("general"),
        **auth_headers(manager_token),
    )
    assert owner_feed.status_code == 200
    assert manager_feed.status_code == 200
    assert owner_feed.json()["pins"][0]["action_plan_execution"]["id"] == str(execution.id)
    assert str(execution.id) not in feed_execution_ids(owner_feed.json())
    assert manager_feed.json()["pins"] == []
    assert feed_execution_ids(manager_feed.json())[0] == str(pending.id)


def test_pinned_cross_status_at_top(api_client, owner_membership, business_unit):
    pending = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pending validation",
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        requires_validation=True,
    )
    in_progress = create_execution(
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
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pins"][0]["action_plan_execution"]["id"] == str(in_progress.id)
    assert feed_execution_ids(body)[0] == str(pending.id)


def test_pinned_fifo(api_client, owner_membership, business_unit):
    first = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="First pin",
    )
    second = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Second pin",
    )
    third = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Unpinned",
    )
    token = login(api_client, user=owner_membership.user)
    api_client.post(_pin_url(owner_membership.establishment_id, first.id), **auth_headers(token))
    time.sleep(0.01)
    api_client.post(_pin_url(owner_membership.establishment_id, second.id), **auth_headers(token))

    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert [item["action_plan_execution"]["id"] for item in body["pins"]] == [
        str(first.id),
        str(second.id),
    ]
    assert feed_execution_ids(body)[0] == str(third.id)


def test_pin_visible_in_personal_and_general(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = create_execution(
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
            + feed_query(view_mode),
            **auth_headers(staff_token),
        )
        assert response.status_code == 200
        body = response.json()
        payload = body["pins"][0]["action_plan_execution"]
        assert payload["id"] == str(execution.id)
        assert payload["is_pinned"] is True
        assert str(execution.id) not in feed_execution_ids(body)


def test_pin_not_visible_returns_404(api_client, owner_membership, business_unit):
    foreign = build_foreign_membership()
    execution = create_execution(
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


@pytest.mark.parametrize(
    "execution_status",
    [EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_DONE, EXECUTION_STATUS_CANCELED],
)
def test_pin_rejects_execution_without_remaining_work(
    api_client,
    owner_membership,
    business_unit,
    execution_status,
):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Not pinnable",
        status=execution_status,
    )
    token = login(api_client, user=owner_membership.user)

    response = api_client.post(
        _pin_url(owner_membership.establishment_id, execution.id),
        data={},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 404
    assert not ActionPlanExecutionFeedPin.objects.filter(
        membership=owner_membership,
        action_plan_execution=execution,
    ).exists()


def test_staff_can_pin_for_self(api_client, owner_membership, staff_membership, business_unit):
    execution = create_execution(
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
    execution = create_execution(
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

    execution_cancel = create_execution(
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
        create_execution(
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
        + feed_query("general")
        + "&page_size=2",
        **auth_headers(token),
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    second = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + f"&page_size=2&cursor={first_body['next_cursor']}",
        **auth_headers(token),
    )
    assert second.status_code == 200
    first_ids = feed_execution_ids(first_body)
    second_ids = feed_execution_ids(second.json())
    pin_ids = [item["action_plan_execution"]["id"] for item in first_body["pins"]]
    assert len(first_ids) == 2
    assert len(second_ids) == 1
    assert pin_ids == [str(executions[2].id)]
    assert str(executions[2].id) not in first_ids
    assert not set(first_ids).intersection(second_ids)


def test_feed_item_contract_includes_is_pinned_and_can_pin(
    api_client,
    owner_membership,
    business_unit,
):
    execution = create_execution(
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
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    payload = body["pins"][0]["action_plan_execution"]
    assert payload["is_pinned"] is True
    assert payload["permission_hints"]["can_pin"] is True
    assert str(execution.id) not in feed_execution_ids(body)
