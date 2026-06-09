from __future__ import annotations

from datetime import date, datetime, time
from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.actions.tests.conftest import (
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    execution_feed_url,
    login,
)
from houston.checklists.constants import EXECUTION_STATUS_ASSIGNED, EXECUTION_STATUS_CANCELED
from houston.checklists.exceptions import ChecklistValidationError
from houston.checklists.materialization import (
    materialize_assignment_occurrences_in_horizon,
    materialize_execution_from_assignment,
)
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.selectors import checklist_execution_feed_queryset
from houston.checklists.services import (
    create_checklist_assignment,
    create_checklist_template,
    mark_task_done,
    update_checklist_assignment,
)
from houston.checklists.tests.conftest import add_task_template
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db

START_DATE = date(2026, 6, 9)
END_DATE = date(2026, 6, 19)
START_TIME = time(10, 0)
END_TIME = time(11, 0)
RECURRENCE_DAYS = ["monday", "tuesday", "thursday"]


def _aware(dt: datetime) -> datetime:
    return timezone.make_aware(dt, timezone.get_current_timezone())


def _active_registered_template(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        title="Routine",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    return template


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


def _create_product_assignment(owner, staff, business_unit):
    template = _active_registered_template(owner, business_unit)
    return create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=START_DATE,
        end_date=END_DATE,
        start_at=START_TIME,
        end_at=END_TIME,
        recurrence_days=RECURRENCE_DAYS,
    )


def test_create_assignment_persists_schedule_fields(
    owner_membership, staff_membership, business_unit
):
    assignment = _create_product_assignment(owner_membership, staff_membership, business_unit)
    assignment.refresh_from_db()
    assert assignment.start_date == START_DATE
    assert assignment.end_date == END_DATE
    assert assignment.start_at == START_TIME
    assert assignment.end_at == END_TIME
    assert assignment.recurrence_days == RECURRENCE_DAYS


def test_rejects_overnight_slot(owner_membership, staff_membership, business_unit):
    template = _active_registered_template(owner_membership, business_unit)
    with pytest.raises(ChecklistValidationError, match="overnight"):
        create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=staff_membership.id,
            start_date=START_DATE,
            end_date=END_DATE,
            start_at=time(22, 0),
            end_at=time(2, 0),
            recurrence_days=RECURRENCE_DAYS,
        )


def test_rejects_end_date_before_start_date(owner_membership, staff_membership, business_unit):
    template = _active_registered_template(owner_membership, business_unit)
    with pytest.raises(ChecklistValidationError, match="end_date"):
        create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=staff_membership.id,
            start_date=END_DATE,
            end_date=START_DATE,
            start_at=START_TIME,
            end_at=END_TIME,
            recurrence_days=RECURRENCE_DAYS,
        )


def test_tuesday_execution_datetimes(owner_membership, staff_membership, business_unit):
    assignment = _create_product_assignment(owner_membership, staff_membership, business_unit)
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=date(2026, 6, 9),
    )
    assert execution.start_at == _aware(datetime(2026, 6, 9, 10, 0))
    assert execution.end_at == _aware(datetime(2026, 6, 9, 11, 0))
    assert execution.visible_from == _aware(datetime(2026, 6, 9, 9, 0))


def test_wednesday_has_no_execution(owner_membership, staff_membership, business_unit):
    assignment = _create_product_assignment(owner_membership, staff_membership, business_unit)
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    materialize_assignment_occurrences_in_horizon(
        assignment=assignment,
        horizon_days=30,
        now=_aware(datetime(2026, 6, 9, 8, 0)),
    )
    occurrence_dates = set(
        ChecklistExecution.objects.filter(checklist_assignment=assignment).values_list(
            "occurrence_date",
            flat=True,
        ),
    )
    assert date(2026, 6, 10) not in occurrence_dates
    assert date(2026, 6, 9) in occurrence_dates
    assert date(2026, 6, 11) in occurrence_dates


def test_no_materialization_after_end_date(owner_membership, staff_membership, business_unit):
    assignment = _create_product_assignment(owner_membership, staff_membership, business_unit)
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    after_end = _aware(datetime(2026, 6, 20, 12, 0))
    materialize_assignment_occurrences_in_horizon(
        assignment=assignment,
        horizon_days=14,
        now=after_end,
    )
    assert not ChecklistExecution.objects.filter(
        checklist_assignment=assignment,
        occurrence_date__gt=END_DATE,
    ).exists()


@pytest.mark.parametrize(
    ("now_value", "visible"),
    [
        (datetime(2026, 6, 9, 8, 59, 59), False),
        (datetime(2026, 6, 9, 9, 0, 0), True),
    ],
)
def test_feed_visibility_boundaries(
    owner_membership,
    staff_membership,
    business_unit,
    now_value,
    visible,
):
    assignment = _create_product_assignment(owner_membership, staff_membership, business_unit)
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=date(2026, 6, 9),
    )
    aware_now = _aware(now_value)
    with patch.object(timezone, "now", return_value=aware_now):
        queryset = checklist_execution_feed_queryset(
            membership=staff_membership,
            view_mode="personal",
        )
    assert queryset.filter(id=execution.id).exists() is visible


def test_thursday_visible_at_nine(owner_membership, staff_membership, business_unit):
    assignment = _create_product_assignment(owner_membership, staff_membership, business_unit)
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=date(2026, 6, 11),
    )
    aware_now = _aware(datetime(2026, 6, 11, 9, 0))
    with patch.object(timezone, "now", return_value=aware_now):
        queryset = checklist_execution_feed_queryset(
            membership=staff_membership,
            view_mode="personal",
        )
    assert queryset.filter(id=execution.id).exists()


def test_done_execution_absent_from_feed(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff(owner, business_unit)
    assignment = _create_product_assignment(owner, staff, business_unit)
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=date(2026, 6, 9),
    )
    task = execution.task_executions.first()
    mark_task_done(task_execution=task, actor=staff)

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
    assert str(execution.id) not in checklist_ids


def test_update_end_date_cancels_assigned_outside_period(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_product_assignment(owner_membership, staff_membership, business_unit)
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    tuesday = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=date(2026, 6, 9),
    )
    thursday = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=date(2026, 6, 11),
    )

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        end_date=date(2026, 6, 10),
    )

    tuesday.refresh_from_db()
    thursday.refresh_from_db()
    assert tuesday.status == EXECUTION_STATUS_ASSIGNED
    assert thursday.status == EXECUTION_STATUS_CANCELED


def test_update_recurrence_days_cancels_removed_days(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_product_assignment(owner_membership, staff_membership, business_unit)
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    tuesday = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=date(2026, 6, 9),
    )
    thursday = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=date(2026, 6, 11),
    )

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        recurrence_days=["monday", "tuesday"],
    )

    tuesday.refresh_from_db()
    thursday.refresh_from_db()
    assert tuesday.status == EXECUTION_STATUS_ASSIGNED
    assert thursday.status == EXECUTION_STATUS_CANCELED


def test_update_times_resyncs_assigned_execution(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_product_assignment(owner_membership, staff_membership, business_unit)
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=date(2026, 6, 9),
    )

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        start_at=time(11, 0),
        end_at=time(12, 0),
    )

    execution.refresh_from_db()
    assert execution.start_at == _aware(datetime(2026, 6, 9, 11, 0))
    assert execution.end_at == _aware(datetime(2026, 6, 9, 12, 0))
    assert execution.visible_from == _aware(datetime(2026, 6, 9, 10, 0))
