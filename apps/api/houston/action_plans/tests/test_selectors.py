from __future__ import annotations

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from houston.action_plans.constants import (
    CONTRIBUTION_STATUS_DONE,
    CONTRIBUTION_STATUS_IN_PROGRESS,
)
from houston.action_plans.selectors import (
    compute_pole_contribution_status,
    execution_with_contribution_context,
    get_involved_poles,
)
from houston.action_plans.services import (
    create_action_plan_with_execution,
    mark_execution_task_done,
    skip_execution_task,
)
from houston.action_plans.tests.conftest import build_assignee_payload, build_task_payload

pytestmark = pytest.mark.django_db


def _multi_pole_execution(
    *,
    owner_membership,
    business_unit,
    maintenance_business_unit,
    staff_membership,
    out_of_scope_staff,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Selector plan",
        requires_validation=False,
        tasks=[
            build_task_payload(task="Pilot task", business_unit=business_unit, position=1),
            build_task_payload(
                task="Maintenance task",
                business_unit=maintenance_business_unit,
                position=2,
            ),
        ],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit),
            build_assignee_payload(
                membership=out_of_scope_staff,
                business_unit=maintenance_business_unit,
            ),
        ],
    )
    return execution


def test_partial_contribution_is_in_progress(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    staff_membership,
    out_of_scope_staff,
):
    execution = _multi_pole_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        maintenance_business_unit=maintenance_business_unit,
        staff_membership=staff_membership,
        out_of_scope_staff=out_of_scope_staff,
    )
    pilot_task = execution.task_executions.filter(
        execution_team__business_unit=business_unit,
    ).first()
    mark_execution_task_done(task_execution=pilot_task, actor=staff_membership)

    loaded = execution_with_contribution_context(execution_id=execution.id)
    poles = {pole.business_unit_id: pole.contribution_status for pole in get_involved_poles(loaded)}

    assert poles[business_unit.id] == CONTRIBUTION_STATUS_DONE
    assert poles[maintenance_business_unit.id] == CONTRIBUTION_STATUS_IN_PROGRESS


def test_mixed_terminal_tasks_are_done(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    staff_membership,
    out_of_scope_staff,
):
    execution = _multi_pole_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        maintenance_business_unit=maintenance_business_unit,
        staff_membership=staff_membership,
        out_of_scope_staff=out_of_scope_staff,
    )
    maintenance_task = execution.task_executions.filter(
        execution_team__business_unit=maintenance_business_unit,
    ).first()
    skip_execution_task(task_execution=maintenance_task, actor=out_of_scope_staff)

    loaded = execution_with_contribution_context(execution_id=execution.id)
    status = compute_pole_contribution_status(loaded, maintenance_business_unit.id)
    assert status == CONTRIBUTION_STATUS_DONE


def test_pole_with_assignee_but_no_tasks_has_no_contribution_status(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    staff_membership,
    out_of_scope_staff,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Assignee-only pole",
        requires_validation=False,
        tasks=[
            build_task_payload(task="Pilot task", business_unit=business_unit, position=1),
        ],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit),
            build_assignee_payload(
                membership=out_of_scope_staff,
                business_unit=maintenance_business_unit,
            ),
        ],
    )

    loaded = execution_with_contribution_context(execution_id=execution.id)
    poles = {pole.business_unit_id: pole.contribution_status for pole in get_involved_poles(loaded)}

    assert maintenance_business_unit.id in poles
    assert poles[maintenance_business_unit.id] is None
    assert poles[business_unit.id] == CONTRIBUTION_STATUS_IN_PROGRESS


def test_get_involved_poles_no_extra_queries(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    staff_membership,
    out_of_scope_staff,
):
    execution = _multi_pole_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        maintenance_business_unit=maintenance_business_unit,
        staff_membership=staff_membership,
        out_of_scope_staff=out_of_scope_staff,
    )
    loaded = execution_with_contribution_context(execution_id=execution.id)

    with CaptureQueriesContext(connection) as context:
        poles = get_involved_poles(loaded)

    assert len(poles) == 2
    assert len(context.captured_queries) == 0
