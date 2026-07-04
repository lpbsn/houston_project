from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.tests.helpers import (
    action_plan_schedule_detail_url,
    api_recurring_schedule_payload,
    build_schedule_assignee_payload,
    schedule_window_from_datetime,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import auth_headers, login
from houston.testing.auth import build_api_membership as build_foreign_membership

pytestmark = pytest.mark.django_db


def _schedule(owner, catalog_action_plan, staff, business_unit):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    return create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner,
        recurrence_days=["monday"],
        assignees=[build_schedule_assignee_payload(membership=staff, business_unit=business_unit)],
        **schedule_window_from_datetime(now),
    )


def test_schedule_detail_cross_establishment_returns_404(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)
    response = api_client.get(
        action_plan_schedule_detail_url(foreign.establishment_id, schedule.id),
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_schedule_create_cross_establishment_returns_404(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)
    response = api_client.post(
        f"/api/v1/establishments/{foreign.establishment_id}/action-plans/{catalog_action_plan.id}/schedule/",
        api_recurring_schedule_payload(
            staff_membership=staff_membership,
            business_unit=business_unit,
        ),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 404
