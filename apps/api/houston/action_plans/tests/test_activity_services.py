from __future__ import annotations

from datetime import timedelta

import pytest

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import touch_execution_activity

pytestmark = pytest.mark.django_db


def test_touch_execution_activity_does_not_regress_from_stale_instance(
    execution_with_assignee,
):
    stale_execution = ActionPlanExecution.objects.get(pk=execution_with_assignee.pk)
    older_at = execution_with_assignee.last_activity_at + timedelta(minutes=1)
    newer_at = older_at + timedelta(minutes=1)

    touch_execution_activity(execution=execution_with_assignee, at=newer_at)
    touch_execution_activity(execution=stale_execution, at=older_at)

    execution_with_assignee.refresh_from_db()
    assert execution_with_assignee.last_activity_at == newer_at
