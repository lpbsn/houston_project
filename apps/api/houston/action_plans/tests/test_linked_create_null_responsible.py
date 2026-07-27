"""Linked action-plan create when signal.responsible_business_unit is null."""

from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.exceptions import (
    ActionPlanPermissionError,
    ActionPlanValidationError,
)
from houston.action_plans.models import ActionPlan, ActionPlanExecution
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.services import normalize_issue_focus
from houston.testing.auth import build_api_membership_on_establishment
from houston.testing.taxonomy import (
    create_membership_with_business_unit_scope,
    create_restaurant_v3_taxonomy,
    create_v3_signal,
)

pytestmark = pytest.mark.django_db


def _total_unclassified(membership, *, title: str = "Unclassified") -> Signal:
    return Signal.objects.create(
        establishment=membership.establishment,
        title=title,
        structured_summary="Needs triage.",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        issue_focus="",
        last_activity_at=timezone.now(),
    )


def _partial_with_subject_no_responsible(membership, taxonomy) -> Signal:
    """Edge row: subject set without responsible (no DB check constraint)."""
    assert taxonomy.lighting_subject is not None
    assert taxonomy.maintenance is not None
    return Signal.objects.create(
        establishment=membership.establishment,
        title="Subject without responsible",
        structured_summary="Partial.",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=None,
        activity_subject=taxonomy.lighting_subject,
        issue_focus="",
        last_activity_at=timezone.now(),
    )


def test_unassigned_final_without_focus_allows_create(owner_membership, maintenance_business_unit):
    signal = _total_unclassified(owner_membership)
    plan, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Triage plan",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    assert execution.source_signal_id == signal.id
    signal.refresh_from_db()
    assert signal.responsible_business_unit_id == maintenance_business_unit.id
    assert signal.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert signal.status == Signal.Status.IN_PROGRESS
    assert plan.responsible_business_unit_id == maintenance_business_unit.id


def test_resolved_final_reuses_existing_focus(owner_membership, maintenance_business_unit):
    taxonomy = create_restaurant_v3_taxonomy(owner_membership.establishment)
    focus = normalize_issue_focus("existing focus")
    signal = _partial_with_subject_no_responsible(owner_membership, taxonomy)
    signal.issue_focus = focus
    signal.save(update_fields=["issue_focus", "updated_at"])

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Plan with existing focus",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    assert execution.source_signal_id == signal.id
    signal.refresh_from_db()
    assert signal.routing_status == Signal.RoutingStatus.RESOLVED
    assert signal.issue_focus == focus
    assert signal.responsible_business_unit_id == maintenance_business_unit.id


def test_resolved_final_accepts_form_issue_focus(owner_membership, maintenance_business_unit):
    taxonomy = create_restaurant_v3_taxonomy(owner_membership.establishment)
    signal = _partial_with_subject_no_responsible(owner_membership, taxonomy)
    focus = normalize_issue_focus("form focus")

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Plan with form focus",
        source_signal_id=signal.id,
        issue_focus=focus,
        tasks=[
            build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    assert execution.source_signal_id == signal.id
    signal.refresh_from_db()
    assert signal.routing_status == Signal.RoutingStatus.RESOLVED
    assert signal.issue_focus == focus


def test_resolved_final_without_focus_rejects_without_partial_plan(
    owner_membership,
    maintenance_business_unit,
):
    taxonomy = create_restaurant_v3_taxonomy(owner_membership.establishment)
    signal = _partial_with_subject_no_responsible(owner_membership, taxonomy)

    with pytest.raises(ActionPlanValidationError, match="issue_focus") as exc_info:
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=maintenance_business_unit.id,
            title="Missing focus",
            source_signal_id=signal.id,
            tasks=[
                build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
            ],
            assignees=[
                build_assignee_payload(
                    membership=owner_membership,
                    business_unit=maintenance_business_unit,
                )
            ],
        )

    assert exc_info.value.code == "invalid_issue_focus"
    assert ActionPlan.objects.filter(title="Missing focus").count() == 0
    assert ActionPlanExecution.objects.filter(source_signal_id=signal.id).count() == 0
    signal.refresh_from_db()
    assert signal.responsible_business_unit_id is None


def test_subject_constrains_pilot_to_subject_business_unit(
    owner_membership,
    business_unit,
    maintenance_business_unit,
):
    taxonomy = create_restaurant_v3_taxonomy(owner_membership.establishment)
    signal = _partial_with_subject_no_responsible(owner_membership, taxonomy)

    with pytest.raises(ActionPlanValidationError, match="activity subject"):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="Wrong pilot",
            source_signal_id=signal.id,
            issue_focus="lampe",
            tasks=[build_task_payload(task="Inspect", business_unit=business_unit)],
            assignees=[
                build_assignee_payload(
                    membership=owner_membership,
                    business_unit=business_unit,
                )
            ],
        )

    assert ActionPlanExecution.objects.filter(source_signal_id=signal.id).count() == 0


def test_manager_out_of_scope_pilot_denied_on_null_responsible(
    owner_membership,
    maintenance_business_unit,
):
    taxonomy = create_restaurant_v3_taxonomy(owner_membership.establishment)
    manager = build_api_membership_on_establishment(
        owner_membership,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=taxonomy.bar,
    )
    signal = _total_unclassified(owner_membership)

    with pytest.raises(ActionPlanPermissionError):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=manager,
            pilot_business_unit_id=maintenance_business_unit.id,
            title="Out of scope pilot",
            source_signal_id=signal.id,
            tasks=[
                build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
            ],
            assignees=[],
        )


def test_manager_in_scope_pilot_on_null_responsible_succeeds(
    owner_membership,
    maintenance_business_unit,
):
    manager = build_api_membership_on_establishment(
        owner_membership,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=maintenance_business_unit,
    )
    signal = _total_unclassified(owner_membership)

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=manager,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Scoped triage plan",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=manager,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    assert execution.source_signal_id == signal.id
    signal.refresh_from_db()
    assert signal.responsible_business_unit_id == maintenance_business_unit.id


def test_merge_binds_execution_to_surviving_signal(
    owner_membership,
    maintenance_business_unit,
):
    taxonomy = create_restaurant_v3_taxonomy(owner_membership.establishment)
    focus = normalize_issue_focus("collision focus")
    survivor = create_v3_signal(
        owner_membership.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        routing_status=Signal.RoutingStatus.RESOLVED,
        issue_focus=focus,
        title="Survivor",
    )
    source = _partial_with_subject_no_responsible(owner_membership, taxonomy)

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Merged plan",
        source_signal_id=source.id,
        issue_focus=focus,
        tasks=[
            build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    source.refresh_from_db()
    survivor.refresh_from_db()
    assert source.status == Signal.Status.ARCHIVED
    assert source.merged_into_id == survivor.id
    assert execution.source_signal_id == survivor.id
    assert ActionPlanExecution.objects.filter(source_signal_id=source.id).count() == 0


def test_existing_responsible_preserved(owner_membership, maintenance_business_unit, signal):
    original_responsible_id = signal.responsible_business_unit_id
    assert original_responsible_id == maintenance_business_unit.id

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Existing responsible",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    signal.refresh_from_db()
    assert signal.responsible_business_unit_id == original_responsible_id
    assert execution.source_signal_id == signal.id


def test_zero_authorized_poles_manager_without_scope(owner_membership, maintenance_business_unit):
    manager = build_api_membership_on_establishment(
        owner_membership,
        role=EstablishmentMembership.Role.MANAGER,
    )
    signal = _total_unclassified(owner_membership)

    with pytest.raises(ActionPlanPermissionError):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=manager,
            pilot_business_unit_id=maintenance_business_unit.id,
            title="No scope",
            source_signal_id=signal.id,
            tasks=[
                build_task_payload(task="Inspect", business_unit=maintenance_business_unit)
            ],
            assignees=[],
        )
