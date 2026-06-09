from __future__ import annotations

from datetime import date, datetime, time
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.actions.tests.conftest import (
    auth_headers,
    build_api_membership_on_establishment,
    execution_feed_url,
    login,
)
from houston.checklists.materialization import ensure_visible_executions_materialized
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.selectors import (
    checklist_execution_feed_queryset,
    checklist_execution_overdue,
)
from houston.checklists.services import (
    create_checklist_assignment,
    create_checklist_template,
)
from houston.checklists.tests.conftest import add_task_template
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership,
    create_membership_with_business_unit_scope,
)
from houston.establishments.timezone_utils import establishment_local_date

pytestmark = pytest.mark.django_db

SUMMER_NOW = timezone.make_aware(datetime(2026, 6, 9, 12, 0, 0))
WINTER_NOW = timezone.make_aware(datetime(2026, 1, 9, 11, 0, 0))
LOCAL_DAY_BOUNDARY_NOW = timezone.make_aware(datetime(2026, 6, 9, 23, 30, 0))


def _scoped_staff(owner, business_unit):
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=staff,
        business_unit=business_unit,
    )
    return staff


def _active_shared_template(owner, business_unit):
    template = create_checklist_template(
        establishment_id=owner.establishment_id,
        actor=owner,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Opening routine",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    return template


def _create_paris_context():
    establishment = create_establishment(name="Paris Hotel", timezone="Europe/Paris")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    business_unit = create_business_unit(establishment=establishment, key="restaurant")
    staff = _scoped_staff(owner, business_unit)
    template = _active_shared_template(owner, business_unit)
    return owner, staff, template


def _utc_datetime(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=dt_timezone.utc)


def test_summer_assignment_visible_one_hour_before_local_start():
    owner, staff, template = _create_paris_context()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=date(2026, 6, 9),
        end_date=date(2026, 6, 9),
        start_at=time(14, 30),
        end_at=time(15, 30),
        recurrence_days=["tuesday"],
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)

    assert execution.start_at == _utc_datetime(2026, 6, 9, 12, 30)
    assert execution.visible_from == _utc_datetime(2026, 6, 9, 11, 30)

    with patch.object(timezone, "now", return_value=SUMMER_NOW):
        assert execution.visible_from <= SUMMER_NOW
        feed_ids = set(
            checklist_execution_feed_queryset(
                membership=staff,
                view_mode="personal",
            ).values_list("id", flat=True),
        )
        assert execution.id in feed_ids


def test_summer_assignment_invisible_when_local_start_more_than_one_hour_away():
    owner, staff, template = _create_paris_context()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=date(2026, 6, 9),
        end_date=date(2026, 6, 9),
        start_at=time(15, 30),
        end_at=time(16, 30),
        recurrence_days=["tuesday"],
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)

    assert execution.visible_from == _utc_datetime(2026, 6, 9, 12, 30)

    with patch.object(timezone, "now", return_value=SUMMER_NOW):
        assert execution.visible_from > SUMMER_NOW
        feed_ids = set(
            checklist_execution_feed_queryset(
                membership=staff,
                view_mode="personal",
            ).values_list("id", flat=True),
        )
        assert execution.id not in feed_ids


def test_yesterday_assignment_visible_and_overdue(api_client):
    owner, staff, template = _create_paris_context()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=date(2026, 6, 8),
        end_date=date(2026, 6, 8),
        start_at=time(14, 30),
        end_at=time(15, 30),
        recurrence_days=["monday"],
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)

    with patch.object(timezone, "now", return_value=SUMMER_NOW):
        assert execution.visible_from <= SUMMER_NOW
        assert checklist_execution_overdue(execution=execution, now=SUMMER_NOW) is True

        feed_ids = set(
            checklist_execution_feed_queryset(
                membership=staff,
                view_mode="personal",
            ).values_list("id", flat=True),
        )
        assert execution.id in feed_ids

        token = login(api_client, user=staff.user)
        response = api_client.get(
            execution_feed_url(staff.establishment_id) + "?view_mode=personal",
            **auth_headers(token),
        )
        checklist_ids = {
            item["checklist"]["id"]
            for item in response.json()["items"]
            if item["item_type"] == "checklist" and item["checklist"] is not None
        }
        assert str(execution.id) in checklist_ids
        overdue_entry = next(
            item["checklist"]
            for item in response.json()["items"]
            if item["item_type"] == "checklist"
            and item["checklist"]["id"] == str(execution.id)
        )
        assert overdue_entry["is_overdue"] is True


def test_winter_assignment_visible_one_hour_before_local_start():
    owner, staff, template = _create_paris_context()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=date(2026, 1, 9),
        end_date=date(2026, 1, 9),
        start_at=time(12, 0),
        end_at=time(13, 0),
        recurrence_days=["friday"],
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)

    assert execution.start_at == _utc_datetime(2026, 1, 9, 11, 0)
    assert execution.visible_from == _utc_datetime(2026, 1, 9, 10, 0)

    with patch.object(timezone, "now", return_value=WINTER_NOW):
        assert execution.visible_from <= WINTER_NOW
        feed_ids = set(
            checklist_execution_feed_queryset(
                membership=staff,
                view_mode="personal",
            ).values_list("id", flat=True),
        )
        assert execution.id in feed_ids


def test_ensure_visible_uses_establishment_local_date_at_utc_day_boundary():
    owner, staff, template = _create_paris_context()
    create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=date(2026, 6, 10),
        end_date=date(2026, 6, 10),
        start_at=time(2, 30),
        end_at=time(3, 30),
        recurrence_days=["wednesday"],
    )
    ChecklistExecution.objects.filter(checklist_template=template).delete()

    with patch.object(timezone, "now", return_value=LOCAL_DAY_BOUNDARY_NOW):
        local_today = establishment_local_date(
            establishment=owner.establishment,
            at=LOCAL_DAY_BOUNDARY_NOW,
        )
        assert local_today == date(2026, 6, 10)

        ensure_visible_executions_materialized(membership=staff)

        execution = ChecklistExecution.objects.get(checklist_template=template)
        assert execution.occurrence_date == date(2026, 6, 10)
        assert execution.start_at == _utc_datetime(2026, 6, 10, 0, 30)
        assert execution.visible_from == LOCAL_DAY_BOUNDARY_NOW

        feed_ids = set(
            checklist_execution_feed_queryset(
                membership=staff,
                view_mode="personal",
            ).values_list("id", flat=True),
        )
        assert execution.id in feed_ids
