from __future__ import annotations

import pytest

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.comments.tests.conftest import (
    auth_headers,
    build_api_membership,
    execution_comments_url,
    login,
    signal_comments_url,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.testing.auth import build_api_membership as build_foreign_membership
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _signal(owner):
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    return create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.OPEN,
    )


def test_signal_comments_list_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)
    token = login(api_client, user=foreign.user)

    response = api_client.get(
        signal_comments_url(foreign.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_signal_comments_create_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)
    token = login(api_client, user=foreign.user)

    response = api_client.post(
        signal_comments_url(foreign.establishment_id, signal.id),
        {"body": "Should not post"},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 404


def _execution(owner, staff):
    hotel, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Tenant execution",
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    return execution


def test_execution_comments_list_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    execution = _execution(owner, staff)
    token = login(api_client, user=foreign.user)

    response = api_client.get(
        execution_comments_url(foreign.establishment_id, execution.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_execution_comments_create_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    execution = _execution(owner, staff)
    token = login(api_client, user=foreign.user)

    response = api_client.post(
        execution_comments_url(foreign.establishment_id, execution.id),
        {"body": "Should not post"},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 404
