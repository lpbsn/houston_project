"""Minimal action-plan fixtures for observation pipeline context tests."""

from __future__ import annotations

from django.utils import timezone

from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
)
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.observations.models import Observation, ObservationProcessing


def create_action_plan_task_observation(
    *,
    membership: EstablishmentMembership,
    task_business_unit: BusinessUnit,
    pilot_business_unit: BusinessUnit,
    text: str = "Toujours en panne au bar.",
) -> Observation:
    """Create ACTION_PLAN_TASK observation with task/pilot BUs (bypasses feed RBAC)."""
    now = timezone.now()
    plan = ActionPlan.objects.create(
        establishment=membership.establishment,
        created_by=membership,
        title="Plan contexte pipeline",
        description="",
        pilot_business_unit=pilot_business_unit,
        requires_validation=False,
    )
    execution = ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        title=plan.title,
        description=plan.description,
        pilot_business_unit=pilot_business_unit,
        requires_validation=False,
        last_activity_at=now,
        use_shared_chronology=True,
    )
    task_team = ActionPlanExecutionTeam.objects.create(
        action_plan_execution=execution,
        business_unit=task_business_unit,
        is_pilot=task_business_unit.id == pilot_business_unit.id,
    )
    if task_business_unit.id != pilot_business_unit.id:
        ActionPlanExecutionTeam.objects.create(
            action_plan_execution=execution,
            business_unit=pilot_business_unit,
            is_pilot=True,
        )
    task_execution = ActionPlanExecutionTask.objects.create(
        action_plan_execution=execution,
        execution_team=task_team,
        task="Vérifier panne",
        position=1,
        status=ActionPlanExecutionTask.Status.PENDING,
    )
    observation = Observation.objects.create(
        establishment=membership.establishment,
        submitted_by_membership=membership,
        raw_text=text,
        origin=Observation.Origin.ACTION_PLAN_TASK,
        action_plan_execution=execution,
        action_plan_execution_task=task_execution,
        submitted_at=now,
    )
    ObservationProcessing.objects.create(
        observation=observation,
        status=ObservationProcessing.Status.QUEUED,
        queued_at=now,
    )
    return observation
