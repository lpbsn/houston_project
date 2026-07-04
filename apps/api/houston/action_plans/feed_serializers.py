from __future__ import annotations

from rest_framework import serializers

from houston.action_plans.api.serializers import (
    ActionPlanBusinessUnitSerializer,
    ActionPlanExecutionPermissionHintsSerializer,
    _serialize_business_unit,
    _serialize_involved_poles,
    _serialize_signal_summary,
)
from houston.action_plans.constants import ACTION_PLAN_DESCRIPTION_MAX_LENGTH
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.permission_hints import build_action_plan_execution_permission_hints
from houston.action_plans.selectors import action_plan_execution_overdue

FEED_TASK_PREVIEW_LIMIT = 3
DESCRIPTION_SHORT_MAX_LENGTH = min(ACTION_PLAN_DESCRIPTION_MAX_LENGTH, 280)


def _truncate_short(text: str, *, max_length: int) -> str:
    normalized = (text or "").strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 1].rstrip() + "…"


def _membership_display_name(membership) -> str:
    user = membership.user
    return user.get_full_name() or user.email or user.username


def description_short(text: str) -> str:
    return _truncate_short(text, max_length=DESCRIPTION_SHORT_MAX_LENGTH)


class ActionPlanExecutionFeedAssigneeSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()


class ActionPlanExecutionFeedTaskPreviewSerializer(serializers.Serializer):
    position = serializers.IntegerField()
    task = serializers.CharField()
    status = serializers.CharField()
    business_unit = ActionPlanBusinessUnitSerializer()


class ActionPlanExecutionFeedItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description_short = serializers.CharField()
    status = serializers.CharField()
    requires_validation = serializers.BooleanField()
    pilot_business_unit = ActionPlanBusinessUnitSerializer()
    involved_poles = serializers.ListField(child=serializers.DictField())
    signal_summary = serializers.DictField(allow_null=True)
    assignees = ActionPlanExecutionFeedAssigneeSerializer(many=True)
    end_at = serializers.DateTimeField(allow_null=True)
    is_overdue = serializers.BooleanField()
    task_executions = ActionPlanExecutionFeedTaskPreviewSerializer(many=True)
    last_activity_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    permission_hints = ActionPlanExecutionPermissionHintsSerializer()


class ActionPlanExecutionFeedItemWrapperSerializer(serializers.Serializer):
    item_type = serializers.CharField()
    action_plan_execution = ActionPlanExecutionFeedItemSerializer()


class ActionPlanExecutionFeedResponseSerializer(serializers.Serializer):
    items = ActionPlanExecutionFeedItemWrapperSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()


def serialize_action_plan_execution_feed_item(
    *,
    execution: ActionPlanExecution,
    membership,
    is_overdue: bool | None = None,
) -> dict:
    overdue = (
        is_overdue if is_overdue is not None else action_plan_execution_overdue(execution=execution)
    )
    task_executions = list(execution.task_executions.all())[:FEED_TASK_PREVIEW_LIMIT]
    assignees = [
        {
            "membership_id": assignee.membership_id,
            "display_name": _membership_display_name(assignee.membership),
        }
        for assignee in execution.assignees.all()
    ]
    return {
        "id": execution.id,
        "title": execution.title,
        "description_short": description_short(execution.description),
        "status": execution.status,
        "requires_validation": execution.requires_validation,
        "pilot_business_unit": _serialize_business_unit(execution.pilot_business_unit),
        "involved_poles": _serialize_involved_poles(execution),
        "signal_summary": _serialize_signal_summary(execution),
        "assignees": assignees,
        "end_at": execution.end_at,
        "is_overdue": overdue,
        "task_executions": [
            {
                "position": task_execution.position,
                "task": task_execution.task,
                "status": task_execution.status,
                "business_unit": _serialize_business_unit(
                    task_execution.execution_team.business_unit,
                ),
            }
            for task_execution in task_executions
        ],
        "last_activity_at": execution.last_activity_at,
        "created_at": execution.created_at,
        "permission_hints": build_action_plan_execution_permission_hints(
            membership=membership,
            execution=execution,
        ),
    }
