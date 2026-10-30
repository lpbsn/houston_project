from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

import pytest

from houston.action_plans.day_selectors import my_day_tasks
from houston.action_plans.tests.helpers import build_assignee_payload, create_execution
from houston.testing.factories import create_establishment, create_membership

pytestmark = pytest.mark.django_db


def assigned_execution(owner, business_unit, member, title="Préparer le service"):
    return create_execution(
        owner,
        business_unit=business_unit,
        title=title,
        assignees=[build_assignee_payload(membership=member, business_unit=business_unit)],
    )


def test_personal_queue_does_not_show_everything_to_owner(
    owner_membership, staff_membership, business_unit
):
    execution = assigned_execution(owner_membership, business_unit, staff_membership)
    task = execution.task_executions.get()
    task.assigned_membership = staff_membership
    task.save(update_fields=["assigned_membership"])
    assert list(my_day_tasks(membership=owner_membership)) == []
    assert list(my_day_tasks(membership=staff_membership).values_list("id", flat=True)) == [task.id]


def test_explicit_other_assignee_excluded_from_shared_work(
    owner_membership, staff_membership, business_unit
):
    execution = assigned_execution(owner_membership, business_unit, staff_membership)
    task = execution.task_executions.get()
    assert my_day_tasks(membership=staff_membership).filter(id=task.id).exists()
    task.assigned_membership = owner_membership
    task.save(update_fields=["assigned_membership"])
    assert not my_day_tasks(membership=staff_membership).filter(id=task.id).exists()


def test_terminal_tasks_and_hidden_plans_are_excluded(
    owner_membership, staff_membership, business_unit
):
    execution = assigned_execution(owner_membership, business_unit, staff_membership)
    task = execution.task_executions.get()
    task.status = "done"
    task.save(update_fields=["status"])
    assert not my_day_tasks(membership=staff_membership).exists()
    task.status = "pending"
    task.save(update_fields=["status"])
    execution.visible_from = datetime.now(dt_timezone.utc) + timedelta(days=1)
    execution.save(update_fields=["visible_from"])
    assert not my_day_tasks(membership=staff_membership).exists()


def test_named_task_overdue_and_all_day_use_establishment_timezone(
    owner_membership, staff_membership, business_unit
):
    establishment = staff_membership.establishment
    establishment.timezone = "Europe/Paris"
    establishment.save(update_fields=["timezone"])
    execution = assigned_execution(owner_membership, business_unit, staff_membership)
    task = execution.task_executions.get()
    # UTC 23:30 = next local calendar day in Paris.
    now = datetime(2026, 10, 30, 23, 30, tzinfo=dt_timezone.utc)
    execution.all_day = True
    execution.end_at = datetime(2026, 10, 30, 23, 0, tzinfo=dt_timezone.utc)
    execution.start_at = execution.end_at - timedelta(days=1)
    execution.save(update_fields=["all_day", "start_at", "end_at"])
    assert my_day_tasks(membership=staff_membership, now=now).get(id=task.id).day_bucket == 1
    task.deadline_at = now - timedelta(minutes=5)
    task.save(update_fields=["deadline_at"])
    assert my_day_tasks(membership=staff_membership, now=now).get(id=task.id).day_bucket == 0


def test_other_establishment_cannot_read_tasks(owner_membership, staff_membership, business_unit):
    assigned_execution(owner_membership, business_unit, staff_membership)
    other = create_membership(establishment=create_establishment(), role="owner")
    assert not my_day_tasks(membership=other).exists()


def test_api_contract_and_tenant_boundary(
    api_client, owner_membership, staff_membership, business_unit
):
    from houston.testing.auth import auth_headers, login

    assigned_execution(owner_membership, business_unit, staff_membership)
    token = login(api_client, user=staff_membership.user)
    url = f"/api/v1/establishments/{staff_membership.establishment_id}/my-day/"
    response = api_client.get(url, **auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["next_offset"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["shared"] is True
    assert body["items"][0]["pole"] == business_unit.specific_name
    assert api_client.get(url + "?offset=-1", **auth_headers(token)).status_code == 400
    other_site = create_establishment()
    assert (
        api_client.get(
            f"/api/v1/establishments/{other_site.id}/my-day/",
            **auth_headers(token),
        ).status_code
        == 404
    )


def test_api_page_is_bounded(api_client, owner_membership, staff_membership, business_unit):
    from houston.testing.auth import auth_headers, login

    for i in range(31):
        assigned_execution(owner_membership, business_unit, staff_membership, title=f"Plan {i}")
    token = login(api_client, user=staff_membership.user)
    url = f"/api/v1/establishments/{staff_membership.establishment_id}/my-day/"
    first = api_client.get(url, **auth_headers(token)).json()
    second = api_client.get(url + "?offset=30", **auth_headers(token)).json()
    assert len(first["items"]) == 30
    assert first["next_offset"] == 30
    assert len(second["items"]) == 1
    assert second["next_offset"] is None
    assert {r["id"] for r in first["items"]}.isdisjoint({r["id"] for r in second["items"]})
