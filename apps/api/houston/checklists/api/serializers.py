from __future__ import annotations

from rest_framework import serializers

from houston.checklists.constants import (
    CHECKLIST_DESCRIPTION_MAX_LENGTH,
    CHECKLIST_SKIPPED_REASON_MAX_LENGTH,
    CHECKLIST_TASK_MAX_LENGTH,
    CHECKLIST_TITLE_MAX_LENGTH,
    CHECKLIST_TYPES,
)
from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTaskExecution,
    ChecklistTaskTemplate,
    ChecklistTemplate,
)
from houston.observations.constants import (
    MAX_OBSERVATION_PHOTOS,
    OBSERVATION_RAW_TEXT_MAX_LENGTH,
    OBSERVATION_RAW_TEXT_MIN_LENGTH,
)


def _membership_display_name(membership) -> str:
    user = membership.user
    return user.get_full_name() or user.email or user.username


def _serialize_business_unit(business_unit) -> dict | None:
    if business_unit is None:
        return None
    return {
        "id": business_unit.id,
        "key": business_unit.key,
        "label": business_unit.label,
    }


class ChecklistBusinessUnitSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    key = serializers.CharField()
    label = serializers.CharField()


class ChecklistTaskTemplateSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    task = serializers.CharField()
    position = serializers.IntegerField()


class ChecklistTemplatePermissionHintsSerializer(serializers.Serializer):
    can_update = serializers.BooleanField()
    can_manage_tasks = serializers.BooleanField()
    can_activate = serializers.BooleanField()
    can_deactivate = serializers.BooleanField()
    can_delete = serializers.BooleanField()
    can_create_assignment = serializers.BooleanField()
    can_create_personal_execution = serializers.BooleanField()


class ChecklistAssignmentPermissionHintsSerializer(serializers.Serializer):
    can_update = serializers.BooleanField()
    can_deactivate = serializers.BooleanField()


class ChecklistTemplateListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    checklist_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    business_unit = ChecklistBusinessUnitSerializer(allow_null=True)
    task_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    permission_hints = ChecklistTemplatePermissionHintsSerializer()


class ChecklistTemplateDetailSerializer(ChecklistTemplateListItemSerializer):
    tasks = ChecklistTaskTemplateSerializer(many=True)


class ChecklistTemplateCreateRequestSerializer(serializers.Serializer):
    checklist_type = serializers.ChoiceField(choices=sorted(CHECKLIST_TYPES))
    title = serializers.CharField(max_length=CHECKLIST_TITLE_MAX_LENGTH)
    description = serializers.CharField(
        max_length=CHECKLIST_DESCRIPTION_MAX_LENGTH,
        required=False,
        allow_blank=True,
        default="",
    )
    business_unit_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class ChecklistTemplateUpdateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=CHECKLIST_TITLE_MAX_LENGTH, required=False)
    description = serializers.CharField(
        max_length=CHECKLIST_DESCRIPTION_MAX_LENGTH,
        required=False,
        allow_blank=True,
    )


class ChecklistTaskTemplateCreateRequestSerializer(serializers.Serializer):
    task = serializers.CharField(max_length=CHECKLIST_TASK_MAX_LENGTH)
    position = serializers.IntegerField(required=False, min_value=1)


class ChecklistTaskTemplateUpdateRequestSerializer(serializers.Serializer):
    task = serializers.CharField(max_length=CHECKLIST_TASK_MAX_LENGTH, required=False)
    position = serializers.IntegerField(required=False, min_value=1)


class ChecklistTaskReorderRequestSerializer(serializers.Serializer):
    ordered_task_template_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
    )


class ChecklistAssignmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    checklist_template_id = serializers.UUIDField(allow_null=True)
    assigned_to_id = serializers.UUIDField()
    assigned_to_display_name = serializers.CharField()
    assigned_by_id = serializers.UUIDField()
    assigned_by_display_name = serializers.CharField()
    business_unit = ChecklistBusinessUnitSerializer()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_at = serializers.TimeField()
    end_at = serializers.TimeField()
    recurrence_days = serializers.ListField(child=serializers.CharField())
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    permission_hints = ChecklistAssignmentPermissionHintsSerializer()


class ChecklistAssignmentCreateRequestSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_at = serializers.TimeField()
    end_at = serializers.TimeField()
    recurrence_days = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        default=None,
    )


class ChecklistAssignmentUpdateRequestSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    start_at = serializers.TimeField(required=False)
    end_at = serializers.TimeField(required=False)
    recurrence_days = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )


class ChecklistExecutionPermissionHintsSerializer(serializers.Serializer):
    can_execute_tasks = serializers.BooleanField()
    can_cancel = serializers.BooleanField()


class ChecklistTaskExecutionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    task = serializers.CharField()
    position = serializers.IntegerField()
    status = serializers.CharField()
    observation_id = serializers.UUIDField(allow_null=True)
    skipped_reason = serializers.CharField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    skipped_at = serializers.DateTimeField(allow_null=True)
    observation_created_at = serializers.DateTimeField(allow_null=True)


class ChecklistExecutionDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    checklist_type = serializers.CharField()
    checklist_template_id = serializers.UUIDField(allow_null=True)
    checklist_assignment_id = serializers.UUIDField(allow_null=True)
    status = serializers.CharField()
    template_title = serializers.CharField()
    template_description = serializers.CharField()
    business_unit = ChecklistBusinessUnitSerializer(allow_null=True)
    assigned_to_id = serializers.UUIDField()
    assigned_to_display_name = serializers.CharField()
    assigned_by_id = serializers.UUIDField(allow_null=True)
    assigned_by_display_name = serializers.CharField(allow_null=True)
    start_at = serializers.DateTimeField(allow_null=True)
    visible_from = serializers.DateTimeField(allow_null=True)
    end_at = serializers.DateTimeField(allow_null=True)
    occurrence_date = serializers.DateField(allow_null=True)
    last_activity_at = serializers.DateTimeField()
    started_at = serializers.DateTimeField(allow_null=True)
    done_at = serializers.DateTimeField(allow_null=True)
    canceled_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    task_executions = ChecklistTaskExecutionSerializer(many=True)
    permission_hints = ChecklistExecutionPermissionHintsSerializer()


class ChecklistTaskSkipRequestSerializer(serializers.Serializer):
    skipped_reason = serializers.CharField(
        max_length=CHECKLIST_SKIPPED_REASON_MAX_LENGTH,
        required=False,
        allow_null=True,
        allow_blank=True,
    )


class ChecklistTaskCreateObservationRequestSerializer(serializers.Serializer):
    text = serializers.CharField(
        min_length=OBSERVATION_RAW_TEXT_MIN_LENGTH,
        max_length=OBSERVATION_RAW_TEXT_MAX_LENGTH,
    )
    temporary_upload_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        max_length=MAX_OBSERVATION_PHOTOS,
    )


class ChecklistTaskCreateObservationResponseSerializer(serializers.Serializer):
    task_execution_id = serializers.UUIDField()
    observation_id = serializers.UUIDField()
    status = serializers.CharField()
    processing_status = serializers.CharField()


class ChecklistPersonalExecutionConflictSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    active_execution_id = serializers.UUIDField(required=False, allow_null=True)


def serialize_task_template(task_template: ChecklistTaskTemplate) -> dict:
    return {
        "id": task_template.id,
        "task": task_template.task,
        "position": task_template.position,
    }


def serialize_template_list_item(
    template: ChecklistTemplate,
    *,
    membership,
) -> dict:
    from houston.checklists.permission_hints import (
        build_checklist_template_list_permission_hints,
    )

    task_count = getattr(template, "task_count", None)
    if task_count is None:
        task_count = template.task_templates.count()
    return {
        "id": template.id,
        "checklist_type": template.checklist_type,
        "title": template.title,
        "description": template.description,
        "status": template.status,
        "business_unit": _serialize_business_unit(template.business_unit),
        "task_count": task_count,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "permission_hints": build_checklist_template_list_permission_hints(
            membership=membership,
            template=template,
        ),
    }


def serialize_template_detail(
    template: ChecklistTemplate,
    *,
    membership,
) -> dict:
    from houston.checklists.permission_hints import (
        build_checklist_template_detail_permission_hints,
    )

    payload = serialize_template_list_item(template, membership=membership)
    payload["permission_hints"] = build_checklist_template_detail_permission_hints(
        membership=membership,
        template=template,
    )
    payload["tasks"] = [
        serialize_task_template(task)
        for task in template.task_templates.order_by("position", "created_at")
    ]
    return payload


def serialize_assignment(
    assignment: ChecklistAssignment,
    *,
    membership,
) -> dict:
    from houston.checklists.permission_hints import (
        build_checklist_assignment_permission_hints,
    )

    return {
        "id": assignment.id,
        "checklist_template_id": assignment.checklist_template_id,
        "assigned_to_id": assignment.assigned_to_id,
        "assigned_to_display_name": _membership_display_name(assignment.assigned_to),
        "assigned_by_id": assignment.assigned_by_id,
        "assigned_by_display_name": _membership_display_name(assignment.assigned_by),
        "business_unit": _serialize_business_unit(assignment.business_unit),
        "start_date": assignment.start_date,
        "end_date": assignment.end_date,
        "start_at": assignment.start_at,
        "end_at": assignment.end_at,
        "recurrence_days": assignment.recurrence_days or [],
        "status": assignment.status,
        "created_at": assignment.created_at,
        "updated_at": assignment.updated_at,
        "permission_hints": build_checklist_assignment_permission_hints(
            membership=membership,
            assignment=assignment,
        ),
    }


def serialize_task_execution(task_execution: ChecklistTaskExecution) -> dict:
    return {
        "id": task_execution.id,
        "task": task_execution.task,
        "position": task_execution.position,
        "status": task_execution.status,
        "observation_id": task_execution.observation_id,
        "skipped_reason": task_execution.skipped_reason,
        "completed_at": task_execution.completed_at,
        "skipped_at": task_execution.skipped_at,
        "observation_created_at": task_execution.observation_created_at,
    }


def serialize_execution_detail(
    execution: ChecklistExecution,
    *,
    membership,
) -> dict:
    from houston.checklists.permission_hints import (
        build_checklist_execution_permission_hints,
    )

    assigned_by = execution.assigned_by
    return {
        "id": execution.id,
        "checklist_type": execution.checklist_type,
        "checklist_template_id": execution.checklist_template_id,
        "checklist_assignment_id": execution.checklist_assignment_id,
        "status": execution.status,
        "template_title": execution.template_title,
        "template_description": execution.template_description,
        "business_unit": _serialize_business_unit(execution.business_unit),
        "assigned_to_id": execution.assigned_to_id,
        "assigned_to_display_name": _membership_display_name(execution.assigned_to),
        "assigned_by_id": execution.assigned_by_id,
        "assigned_by_display_name": (
            _membership_display_name(assigned_by) if assigned_by is not None else None
        ),
        "start_at": execution.start_at,
        "visible_from": execution.visible_from,
        "end_at": execution.end_at,
        "occurrence_date": execution.occurrence_date,
        "last_activity_at": execution.last_activity_at,
        "started_at": execution.started_at,
        "done_at": execution.done_at,
        "canceled_at": execution.canceled_at,
        "created_at": execution.created_at,
        "updated_at": execution.updated_at,
        "task_executions": [
            serialize_task_execution(task)
            for task in execution.task_executions.order_by("position", "created_at")
        ],
        "permission_hints": build_checklist_execution_permission_hints(
            membership=membership,
            execution=execution,
        ),
    }
