from __future__ import annotations

from rest_framework import serializers

from houston.checklists.models import ChecklistExecution
from houston.checklists.selectors import checklist_execution_overdue


def _membership_display_name(membership) -> str:
    user = membership.user
    return user.get_full_name() or user.email or user.username


class ChecklistFeedItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    checklist_type = serializers.CharField()
    status = serializers.CharField()
    end_at = serializers.DateTimeField(allow_null=True)
    is_overdue = serializers.BooleanField()
    business_unit_key = serializers.CharField(allow_null=True)
    business_unit_label = serializers.CharField(allow_null=True)
    assigned_to_display_name = serializers.CharField()
    last_activity_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    progress_treated_count = serializers.IntegerField()
    progress_total_count = serializers.IntegerField()


def serialize_checklist_feed_item(
    *,
    execution: ChecklistExecution,
    is_overdue: bool | None = None,
) -> dict:
    business_unit = execution.business_unit
    overdue = (
        is_overdue
        if is_overdue is not None
        else checklist_execution_overdue(execution=execution)
    )
    treated_count = getattr(execution, "progress_treated_count", None)
    total_count = getattr(execution, "progress_total_count", None)
    if treated_count is None or total_count is None:
        tasks = execution.task_executions.all()
        total_count = tasks.count()
        treated_count = tasks.filter(
            status__in=[
                "done",
                "skipped",
                "observation_created",
            ],
        ).count()

    return {
        "id": execution.id,
        "title": execution.template_title,
        "checklist_type": execution.checklist_type,
        "status": execution.status,
        "end_at": execution.end_at,
        "is_overdue": overdue,
        "business_unit_key": business_unit.key if business_unit else None,
        "business_unit_label": business_unit.label if business_unit else None,
        "assigned_to_display_name": _membership_display_name(execution.assigned_to),
        "last_activity_at": execution.last_activity_at,
        "created_at": execution.created_at,
        "progress_treated_count": treated_count,
        "progress_total_count": total_count,
    }
