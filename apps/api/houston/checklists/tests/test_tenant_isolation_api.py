from __future__ import annotations

import pytest

from houston.actions.tests.conftest import auth_headers, login
from houston.checklists.models import ChecklistExecution
from houston.checklists.tests.conftest import (
    assignment_api_payload,
    checklist_execution_url,
    checklist_template_url,
)
from houston.checklists.tests.test_assignment_api import _active_registered_template
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import build_api_membership as build_foreign_membership

pytestmark = pytest.mark.django_db


def test_template_detail_cross_establishment_returns_404(
    api_client,
    owner_membership,
    business_unit,
):
    template, _ = _active_registered_template(api_client, owner_membership, business_unit)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)

    response = api_client.get(
        checklist_template_url(foreign.establishment_id, template["id"]),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_assignment_create_cross_establishment_returns_404(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, _ = _active_registered_template(api_client, owner_membership, business_unit)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)

    response = api_client.post(
        checklist_template_url(foreign.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id),
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_execution_detail_cross_establishment_returns_404(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    assignment = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id),
        format="json",
        **auth_headers(owner_token),
    )
    assert assignment.status_code == 201
    execution = ChecklistExecution.objects.get(checklist_assignment_id=assignment.json()["id"])

    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)

    response = api_client.get(
        checklist_execution_url(foreign.establishment_id, execution.id),
        **auth_headers(token),
    )

    assert response.status_code == 404
