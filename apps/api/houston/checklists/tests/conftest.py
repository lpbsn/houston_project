from __future__ import annotations

from datetime import date, time

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTaskTemplate,
    ChecklistTemplate,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership,
    create_membership_with_business_unit_scope,
)


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


__all__ = [
    "api_client",
    "establishment",
    "business_unit",
    "owner_membership",
    "director_membership",
    "manager_membership",
    "staff_membership",
    "other_staff_membership",
    "shared_template",
    "personal_template",
    "checklist_assignment",
    "shared_execution",
    "personal_execution",
]


@pytest.fixture
def establishment():
    return create_establishment(name="Checklist Hotel", timezone="UTC")


@pytest.fixture
def business_unit(establishment):
    return create_business_unit(establishment=establishment, key="restaurant")


@pytest.fixture
def owner_membership(establishment):
    return create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )


@pytest.fixture
def director_membership(establishment):
    return create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )


@pytest.fixture
def manager_membership(establishment, business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    membership = EstablishmentMembership.objects.prefetch_related("scope_links").get(
        pk=membership.pk
    )
    return membership


@pytest.fixture
def staff_membership(establishment, business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    return EstablishmentMembership.objects.prefetch_related("scope_links").get(
        pk=membership.pk
    )


@pytest.fixture
def other_staff_membership(establishment, business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    return EstablishmentMembership.objects.prefetch_related("scope_links").get(
        pk=membership.pk
    )


@pytest.fixture
def shared_template(establishment, owner_membership, business_unit):
    return ChecklistTemplate.objects.create(
        establishment=establishment,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        created_by=owner_membership,
        business_unit=business_unit,
        title="Opening checks",
        status=ChecklistTemplate.Status.ACTIVE,
    )


@pytest.fixture
def personal_template(establishment, staff_membership):
    return ChecklistTemplate.objects.create(
        establishment=establishment,
        checklist_type=ChecklistTemplate.ChecklistType.PERSONAL,
        created_by=staff_membership,
        business_unit=None,
        title="My routine",
        status=ChecklistTemplate.Status.ACTIVE,
    )


@pytest.fixture
def checklist_assignment(establishment, shared_template, owner_membership, staff_membership):
    today = timezone.now().date()
    return ChecklistAssignment.objects.create(
        checklist_template=shared_template,
        establishment=establishment,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit=shared_template.business_unit,
        start_date=today,
        end_date=today + timezone.timedelta(days=14),
        start_at=time(8, 0),
        end_at=time(10, 0),
        recurrence_days=["monday", "wednesday"],
    )


@pytest.fixture
def shared_execution(
    establishment,
    shared_template,
    checklist_assignment,
    staff_membership,
    owner_membership,
):
    now = timezone.now()
    return ChecklistExecution.objects.create(
        checklist_template=shared_template,
        checklist_assignment=checklist_assignment,
        checklist_type=ChecklistExecution.ChecklistType.SHARED,
        establishment=establishment,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit=shared_template.business_unit,
        template_title=shared_template.title,
        start_at=now,
        visible_from=now - timezone.timedelta(hours=1),
        end_at=now + timezone.timedelta(hours=2),
        occurrence_date=now.date(),
        status=ChecklistExecution.Status.ASSIGNED,
        last_activity_at=now,
    )


@pytest.fixture
def personal_execution(establishment, personal_template, staff_membership):
    now = timezone.now()
    return ChecklistExecution.objects.create(
        checklist_template=personal_template,
        checklist_assignment=None,
        checklist_type=ChecklistExecution.ChecklistType.PERSONAL,
        establishment=establishment,
        assigned_to=staff_membership,
        assigned_by=None,
        business_unit=None,
        template_title=personal_template.title,
        start_at=None,
        visible_from=None,
        end_at=None,
        occurrence_date=None,
        status=ChecklistExecution.Status.ASSIGNED,
        last_activity_at=now,
    )


def checklist_templates_url(establishment_id, query: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/checklist-templates/"
    return base + query


def checklist_template_url(establishment_id, template_id, suffix: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/"
    return base + suffix.lstrip("/")


def checklist_task_template_url(establishment_id, task_template_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/checklist-task-templates/{task_template_id}/"
    )


def checklist_assignments_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/checklist-assignments/"


def checklist_assignment_url(establishment_id, assignment_id, suffix: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/checklist-assignments/{assignment_id}/"
    return base + suffix.lstrip("/")


def checklist_execution_url(establishment_id, execution_id, suffix: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/checklist-executions/{execution_id}/"
    return base + suffix.lstrip("/")


def checklist_task_execution_url(establishment_id, task_execution_id, suffix: str = "") -> str:
    base = (
        f"/api/v1/establishments/{establishment_id}/checklist-task-executions/{task_execution_id}/"
    )
    return base + suffix.lstrip("/")


def assignment_schedule_from_datetime(
    dt,
    *,
    duration_hours: int = 1,
    period_days: int = 14,
) -> dict:
    end_time = dt + timezone.timedelta(hours=duration_hours)
    return {
        "start_date": dt.date(),
        "end_date": dt.date() + timezone.timedelta(days=period_days),
        "start_at": dt.time().replace(microsecond=0),
        "end_at": end_time.time().replace(microsecond=0),
    }


def assignment_api_payload(assigned_to_id, **overrides) -> dict:
    schedule = default_assignment_schedule()
    payload = {
        "assigned_to": str(assigned_to_id),
        "start_date": schedule["start_date"].isoformat(),
        "end_date": schedule["end_date"].isoformat(),
        "start_at": schedule["start_at"].strftime("%H:%M:%S"),
        "end_at": schedule["end_at"].strftime("%H:%M:%S"),
    }
    payload.update(overrides)
    return payload


def default_assignment_schedule(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    start_at: time | None = None,
    end_at: time | None = None,
) -> dict:
    today = timezone.now().date()
    resolved_start = start_date or today
    return {
        "start_date": resolved_start,
        "end_date": end_date or (resolved_start + timezone.timedelta(days=14)),
        "start_at": start_at or time(8, 0),
        "end_at": end_at or time(10, 0),
    }


def add_task_template(*, template: ChecklistTemplate, task: str = "Task", position: int = 1):
    return ChecklistTaskTemplate.objects.create(
        checklist_template=template,
        task=task,
        position=position,
    )
