from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from django.utils import timezone
from houston.checklists.materialization import (
    ensure_visible_executions_materialized,
    materialize_execution_from_assignment,
)
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.services import create_checklist_assignment, create_checklist_template
from houston.checklists.tasks import materialize_checklist_assignments_horizon_task
from houston.checklists.tests.conftest import (
    add_task_template,
    assignment_schedule_from_datetime,
    stable_assignment_times,
)
from houston.realtime.ws_payloads import build_invalidate_payload

pytestmark = pytest.mark.django_db(transaction=True)

ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "type",
        "subject_type",
        "reason",
        "establishment_id",
        "entity_id",
        "occurred_at",
    }
)


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


def _count_execution_created_calls(mock_notify) -> int:
    return sum(
        1
        for call in mock_notify.call_args_list
        if call.kwargs.get("reason") == "execution.created"
    )


def test_materialize_execution_from_assignment_emits_execution_created(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    now = timezone.now()
    start_at, end_at = stable_assignment_times(duration_hours=2)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=start_at,
        end_at=end_at,
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    occurrence_date = now.date()

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        execution = materialize_execution_from_assignment(
            assignment=assignment,
            occurrence_date=occurrence_date,
        )

        assert _count_execution_created_calls(mock_notify) == 1
        mock_notify.assert_called_with(
            establishment_id=execution.establishment_id,
            subject_type="execution",
            reason="execution.created",
            entity_id=execution.id,
        )


def test_materialize_execution_from_assignment_idempotent_skips_second_emission(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    now = timezone.now()
    start_at, end_at = stable_assignment_times(duration_hours=2)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=start_at,
        end_at=end_at,
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    occurrence_date = now.date()

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        materialize_execution_from_assignment(
            assignment=assignment,
            occurrence_date=occurrence_date,
        )
        materialize_execution_from_assignment(
            assignment=assignment,
            occurrence_date=occurrence_date,
        )

        assert _count_execution_created_calls(mock_notify) == 1


def test_horizon_task_emits_execution_created_for_new_materializations(
    owner_membership,
    staff_membership,
    business_unit,
):
    """TS-E1 / ROADMAP-15 — beat-only materialization emits execution.created.

    Without prior execution-feed GET.
    """
    template = _active_registered_template(owner_membership, business_unit)
    start_at = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        recurrence_days=["monday", "wednesday", "friday"],
        **assignment_schedule_from_datetime(start_at, duration_hours=1, period_days=14),
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()

    with (
        patch("houston.actions.execution_feed.build_execution_feed_page") as mock_feed,
        patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify,
    ):
        mock_feed.side_effect = AssertionError(
            "execution-feed GET must not run before beat materialization",
        )
        materialize_checklist_assignments_horizon_task.run()

        assert _count_execution_created_calls(mock_notify) >= 1
        mock_feed.assert_not_called()


def test_ensure_visible_executions_materialized_emits_execution_created(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    fixed_now = timezone.make_aware(datetime(2026, 6, 24, 10, 0, 0))
    with patch.object(timezone, "now", return_value=fixed_now):
        start_at = fixed_now.replace(hour=9, minute=0, second=0, microsecond=0)
        assignment = create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=staff_membership.id,
            recurrence_days=["monday", "wednesday", "friday"],
            **assignment_schedule_from_datetime(start_at, duration_hours=1, period_days=14),
        )
        ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
        assignment.last_materialized_at = None
        assignment.save(update_fields=["last_materialized_at", "updated_at"])

        with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
            ensure_visible_executions_materialized(
                membership=staff_membership,
                view_mode="personal",
            )

            assert _count_execution_created_calls(mock_notify) >= 1


def test_execution_created_invalidate_payload_allowlist():
    establishment_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    payload = build_invalidate_payload(
        subject_type="execution",
        reason="execution.created",
        establishment_id=establishment_id,
        entity_id=entity_id,
    )
    assert set(payload.keys()) == ALLOWED_PAYLOAD_KEYS
