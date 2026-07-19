from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


def _execution_url(establishment_id, execution_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/"
        f"action-plan-executions/{execution_id}/"
    )


def test_patch_execution_updates_title_and_returns_can_update(api_client):
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    _plan, execution = create_action_plan_with_execution(
        establishment_id=establishment.id,
        created_by=owner,
        pilot_business_unit_id=pilot.id,
        title="Original",
        requires_validation=False,
        tasks=[build_task_payload(task="Task", business_unit=pilot)],
        assignees=[build_assignee_payload(membership=owner, business_unit=pilot)],
        use_shared_chronology=True,
        start_at=timezone.now() - timedelta(hours=1),
    )
    token = login(api_client, user=owner.user)
    detail = api_client.get(
        _execution_url(establishment.id, execution.id),
        **auth_headers(token),
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["permission_hints"]["can_update"] is True
    assert "start_at" in body["assignees_by_pole"][0]["assignees"][0]

    response = api_client.patch(
        _execution_url(establishment.id, execution.id),
        {
            "expected_updated_at": body["updated_at"],
            "title": "Patched title",
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Patched title"


def test_patch_execution_stale_returns_409(api_client):
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    _plan, execution = create_action_plan_with_execution(
        establishment_id=establishment.id,
        created_by=owner,
        pilot_business_unit_id=pilot.id,
        title="Original",
        requires_validation=False,
        tasks=[build_task_payload(task="Task", business_unit=pilot)],
        assignees=[build_assignee_payload(membership=owner, business_unit=pilot)],
        use_shared_chronology=True,
        start_at=timezone.now() - timedelta(hours=1),
    )
    token = login(api_client, user=owner.user)
    stale = execution.updated_at.isoformat().replace("+00:00", "Z")
    execution.title = "Changed elsewhere"
    execution.save(update_fields=["title", "updated_at"])

    response = api_client.patch(
        _execution_url(establishment.id, execution.id),
        {
            "expected_updated_at": stale,
            "title": "Conflict",
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "stale_execution"
