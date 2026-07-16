from __future__ import annotations

from collections import defaultdict

from rest_framework import serializers

from houston.action_plans.constants import (
    ACTION_PLAN_DESCRIPTION_MAX_LENGTH,
    ACTION_PLAN_SKIPPED_REASON_MAX_LENGTH,
    ACTION_PLAN_TASK_MAX_LENGTH,
    ACTION_PLAN_TITLE_MAX_LENGTH,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanSchedule,
    ActionPlanTask,
)
from houston.action_plans.selectors import get_involved_poles
from houston.establishments.api.serializers import BusinessUnitGenericSerializer
from houston.establishments.business_unit_identity import (
    business_unit_public_key,
    business_unit_public_label,
)
from houston.establishments.public_serialization import (
    resolve_activity_subject_public_label,
    serialize_activity_subject_ref,
    serialize_business_unit_ref,
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
    return serialize_business_unit_ref(business_unit=business_unit)


def _serialize_activity_subject(activity_subject) -> dict | None:
    return serialize_activity_subject_ref(activity_subject=activity_subject)


def _serialize_signal_summary(execution: ActionPlanExecution) -> dict | None:
    signal = execution.source_signal
    if signal is None:
        return None
    affected = signal.affected_business_unit
    responsible = signal.responsible_business_unit
    subject = signal.activity_subject
    return {
        "id": signal.id,
        "title": signal.title,
        "status": signal.status,
        "affected_business_unit_id": signal.affected_business_unit_id,
        "affected_business_unit_key": (
            business_unit_public_key(business_unit=affected)
            if affected is not None
            else None
        ),
        "affected_business_unit_label": (
            business_unit_public_label(business_unit=affected)
            if affected is not None
            else None
        ),
        "responsible_business_unit_id": signal.responsible_business_unit_id,
        "responsible_business_unit_key": (
            business_unit_public_key(business_unit=responsible)
            if responsible is not None
            else None
        ),
        "responsible_business_unit_label": (
            business_unit_public_label(business_unit=responsible)
            if responsible is not None
            else None
        ),
        "activity_subject_id": signal.activity_subject_id,
        "activity_subject_normalized_name": (
            subject.normalized_name if subject is not None else None
        ),
        "activity_subject_label": resolve_activity_subject_public_label(
            activity_subject=subject
        ),
        "location_text": signal.location_text,
    }


class ActionSignalSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    affected_business_unit_id = serializers.UUIDField(allow_null=True)
    affected_business_unit_key = serializers.CharField(allow_null=True)
    affected_business_unit_label = serializers.CharField(allow_null=True)
    responsible_business_unit_id = serializers.UUIDField(allow_null=True)
    responsible_business_unit_key = serializers.CharField(allow_null=True)
    responsible_business_unit_label = serializers.CharField(allow_null=True)
    activity_subject_id = serializers.UUIDField(allow_null=True)
    activity_subject_normalized_name = serializers.CharField(allow_null=True)
    activity_subject_label = serializers.CharField(allow_null=True)
    location_text = serializers.CharField(allow_blank=True)


class ActionPlanBusinessUnitSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    specific_name = serializers.CharField()
    instance_description = serializers.CharField()
    active = serializers.BooleanField()
    generic = BusinessUnitGenericSerializer()


class ActionPlanActivitySubjectSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    catalog_key = serializers.CharField(required=False)
    label = serializers.CharField()
    description = serializers.CharField()
    source = serializers.CharField()
    active = serializers.BooleanField()
    is_generic = serializers.BooleanField()


class ActionPlanTaskTemplateSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    task = serializers.CharField()
    description = serializers.CharField()
    deadline_at = serializers.DateTimeField(allow_null=True)
    assigned_membership_id = serializers.UUIDField(allow_null=True)
    assigned_display_name = serializers.CharField(allow_null=True)
    position = serializers.IntegerField()
    business_unit = ActionPlanBusinessUnitSerializer()


class ActionPlanPermissionHintsSerializer(serializers.Serializer):
    can_update = serializers.BooleanField()
    can_activate = serializers.BooleanField()
    can_deactivate = serializers.BooleanField()
    can_use = serializers.BooleanField()
    can_schedule = serializers.BooleanField()


class ActionPlanListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    catalog_status = serializers.CharField(allow_null=True)
    pilot_business_unit = ActionPlanBusinessUnitSerializer()
    task_count = serializers.IntegerField()
    involved_pole_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    permission_hints = ActionPlanPermissionHintsSerializer()


class ActionPlanDetailSerializer(ActionPlanListItemSerializer):
    created_by_id = serializers.UUIDField()
    created_by_display_name = serializers.CharField()
    tasks = ActionPlanTaskTemplateSerializer(many=True)
    requires_validation = serializers.BooleanField()
    is_reusable = serializers.BooleanField()


class ActionPlanTaskInputSerializer(serializers.Serializer):
    task = serializers.CharField(max_length=ACTION_PLAN_TASK_MAX_LENGTH)
    business_unit_id = serializers.UUIDField()
    position = serializers.IntegerField(required=False, min_value=1)
    description = serializers.CharField(
        max_length=ACTION_PLAN_DESCRIPTION_MAX_LENGTH,
        required=False,
        allow_blank=True,
        default="",
    )
    deadline_at = serializers.DateTimeField(required=False, allow_null=True)
    assigned_membership_id = serializers.UUIDField(required=False, allow_null=True)


class ActionPlanAssigneeInputSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    business_unit_id = serializers.UUIDField()
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    visible_from = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False, allow_null=True)


class ActionPlanScheduleAssigneeInputSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    business_unit_id = serializers.UUIDField()
    start_at = serializers.TimeField(required=False, allow_null=True)
    end_at = serializers.TimeField(required=False, allow_null=True)


class ActionPlanScheduleCreateRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField()
    start_at = serializers.TimeField()
    end_at = serializers.TimeField()
    recurrence_days = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
    )
    assignees = ActionPlanScheduleAssigneeInputSerializer(
        many=True,
        required=False,
        default=list,
    )
    use_shared_chronology = serializers.BooleanField(required=False, default=False)


class ActionPlanCreateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=ACTION_PLAN_TITLE_MAX_LENGTH)
    description = serializers.CharField(
        max_length=ACTION_PLAN_DESCRIPTION_MAX_LENGTH,
        required=False,
        allow_blank=True,
        default="",
    )
    pilot_business_unit_id = serializers.UUIDField()
    requires_validation = serializers.BooleanField(required=False, default=True)
    is_reusable = serializers.BooleanField(required=False, default=False)
    tasks = ActionPlanTaskInputSerializer(
        many=True,
        required=False,
        default=list,
        help_text=(
            "Optional for reusable catalog plans. Direct execution or schedule create "
            "still requires at least one task or assignee."
        ),
    )
    assignees = ActionPlanAssigneeInputSerializer(many=True, required=False, default=list)
    source_signal_id = serializers.UUIDField(required=False, allow_null=True)
    use_shared_chronology = serializers.BooleanField(required=False, default=False)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False, allow_null=True)
    visible_from = serializers.DateTimeField(required=False, allow_null=True)
    occurrence_date = serializers.DateField(required=False, allow_null=True)
    schedule = ActionPlanScheduleCreateRequestSerializer(required=False, allow_null=True)


class ActionPlanUpdateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=ACTION_PLAN_TITLE_MAX_LENGTH, required=False)
    description = serializers.CharField(
        max_length=ACTION_PLAN_DESCRIPTION_MAX_LENGTH,
        required=False,
        allow_blank=True,
    )
    requires_validation = serializers.BooleanField(required=False)
    tasks = ActionPlanTaskInputSerializer(many=True, required=False)


class ActionPlanUseRequestSerializer(serializers.Serializer):
    assignees = ActionPlanAssigneeInputSerializer(many=True, required=False, default=list)
    use_shared_chronology = serializers.BooleanField(required=False, default=False)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False, allow_null=True)
    visible_from = serializers.DateTimeField(required=False, allow_null=True)
    occurrence_date = serializers.DateField(required=False, allow_null=True)


class ActionPlanMixedSubmitRequestSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    schedule_body = ActionPlanScheduleCreateRequestSerializer()
    use_body = ActionPlanUseRequestSerializer()


class ActionPlanScheduleUpdateRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    start_at = serializers.TimeField(required=False)
    end_at = serializers.TimeField(required=False)
    recurrence_days = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    assignees = ActionPlanScheduleAssigneeInputSerializer(
        many=True,
        required=False,
    )
    use_shared_chronology = serializers.BooleanField(required=False)


class ActionPlanSchedulePermissionHintsSerializer(serializers.Serializer):
    can_update = serializers.BooleanField()
    can_deactivate = serializers.BooleanField()


class ActionPlanScheduleAssigneeSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()
    business_unit = ActionPlanBusinessUnitSerializer()
    start_at = serializers.TimeField(allow_null=True)
    end_at = serializers.TimeField(allow_null=True)


class ActionPlanScheduleDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action_plan_id = serializers.UUIDField()
    status = serializers.CharField()
    use_shared_chronology = serializers.BooleanField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_at = serializers.TimeField()
    end_at = serializers.TimeField()
    recurrence_days = serializers.ListField(child=serializers.CharField())
    created_by_id = serializers.UUIDField()
    created_by_display_name = serializers.CharField()
    last_materialized_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    assignees = ActionPlanScheduleAssigneeSerializer(many=True)
    permission_hints = ActionPlanSchedulePermissionHintsSerializer()


class ActionPlanActiveExecutionConflictSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    active_execution_id = serializers.UUIDField()


class ActionPlanExecutionPermissionHintsSerializer(serializers.Serializer):
    can_mark_done = serializers.BooleanField()
    can_validate = serializers.BooleanField()
    can_reopen = serializers.BooleanField()
    can_cancel = serializers.BooleanField()
    is_pilot_pole_assignee = serializers.BooleanField()
    can_pin = serializers.BooleanField()


class ActionPlanExecutionPinStateSerializer(serializers.Serializer):
    is_pinned = serializers.BooleanField()


class ActionPlanTaskExecutionPermissionHintsSerializer(serializers.Serializer):
    can_mark_done = serializers.BooleanField()
    can_unmark_done = serializers.BooleanField()
    can_skip = serializers.BooleanField()
    can_create_observation = serializers.BooleanField()


class ActionPlanAssigneeRefSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()


class ActionPlanAssigneesByPoleSerializer(serializers.Serializer):
    business_unit = ActionPlanBusinessUnitSerializer()
    assignees = ActionPlanAssigneeRefSerializer(many=True)


class ActionPlanInvolvedPoleSerializer(serializers.Serializer):
    business_unit = ActionPlanBusinessUnitSerializer()
    contribution_status = serializers.CharField(allow_null=True)


class ActionPlanTaskExecutionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    task = serializers.CharField()
    description = serializers.CharField()
    deadline_at = serializers.DateTimeField(allow_null=True)
    assigned_membership_id = serializers.UUIDField(allow_null=True)
    assigned_display_name = serializers.CharField(allow_null=True)
    position = serializers.IntegerField()
    status = serializers.CharField()
    business_unit = ActionPlanBusinessUnitSerializer()
    observation_id = serializers.UUIDField(allow_null=True)
    skipped_reason = serializers.CharField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    skipped_at = serializers.DateTimeField(allow_null=True)
    observation_created_at = serializers.DateTimeField(allow_null=True)
    permission_hints = ActionPlanTaskExecutionPermissionHintsSerializer()


class ActionPlanExecutionDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action_plan_id = serializers.UUIDField(allow_null=True)
    status = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    requires_validation = serializers.BooleanField()
    pilot_business_unit = ActionPlanBusinessUnitSerializer()
    affected_business_unit = ActionPlanBusinessUnitSerializer(allow_null=True)
    responsible_business_unit = ActionPlanBusinessUnitSerializer(allow_null=True)
    activity_subject = ActionPlanActivitySubjectSerializer(allow_null=True)
    signal_summary = ActionSignalSummarySerializer(allow_null=True)
    created_by_id = serializers.UUIDField()
    created_by_display_name = serializers.CharField()
    use_shared_chronology = serializers.BooleanField()
    start_at = serializers.DateTimeField(allow_null=True)
    visible_from = serializers.DateTimeField(allow_null=True)
    end_at = serializers.DateTimeField(allow_null=True)
    occurrence_date = serializers.DateField(allow_null=True)
    last_activity_at = serializers.DateTimeField()
    marked_done_at = serializers.DateTimeField(allow_null=True)
    validated_at = serializers.DateTimeField(allow_null=True)
    canceled_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    assignees_by_pole = ActionPlanAssigneesByPoleSerializer(many=True)
    involved_poles = ActionPlanInvolvedPoleSerializer(many=True)
    task_executions = ActionPlanTaskExecutionSerializer(many=True)
    permission_hints = ActionPlanExecutionPermissionHintsSerializer()


class ActionPlanMixedSubmitResponseSerializer(serializers.Serializer):
    execution = ActionPlanExecutionDetailSerializer()
    schedule_id = serializers.UUIDField()
    replayed = serializers.BooleanField()


class ActionPlanTaskSkipRequestSerializer(serializers.Serializer):
    skipped_reason = serializers.CharField(
        max_length=ACTION_PLAN_SKIPPED_REASON_MAX_LENGTH,
        required=False,
        allow_null=True,
        allow_blank=True,
    )


class ActionPlanTaskCreateObservationRequestSerializer(serializers.Serializer):
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


class ActionPlanTaskCreateObservationResponseSerializer(serializers.Serializer):
    task_execution_id = serializers.UUIDField()
    observation_id = serializers.UUIDField()
    status = serializers.CharField()
    processing_status = serializers.CharField()


def serialize_task_template(task: ActionPlanTask) -> dict:
    assigned_display_name = None
    if task.assigned_membership is not None:
        assigned_display_name = _membership_display_name(task.assigned_membership)
    return {
        "id": task.id,
        "task": task.task,
        "description": task.description,
        "deadline_at": task.deadline_at,
        "assigned_membership_id": task.assigned_membership_id,
        "assigned_display_name": assigned_display_name,
        "position": task.position,
        "business_unit": _serialize_business_unit(task.business_unit),
    }


def serialize_action_plan_list_item(
    action_plan: ActionPlan,
    *,
    membership,
) -> dict:
    from houston.action_plans.permission_hints import (
        build_action_plan_list_permission_hints,
    )

    task_count = getattr(action_plan, "task_count", None)
    if task_count is None:
        task_count = action_plan.tasks.count()
    involved_pole_count = getattr(action_plan, "involved_pole_count", None)
    if involved_pole_count is None:
        involved_pole_count = action_plan.tasks.values("business_unit_id").distinct().count()
    involved_pole_count = max(involved_pole_count, 1)
    return {
        "id": action_plan.id,
        "title": action_plan.title,
        "description": action_plan.description,
        "catalog_status": action_plan.catalog_status,
        "pilot_business_unit": _serialize_business_unit(action_plan.pilot_business_unit),
        "task_count": task_count,
        "involved_pole_count": involved_pole_count,
        "created_at": action_plan.created_at,
        "updated_at": action_plan.updated_at,
        "permission_hints": build_action_plan_list_permission_hints(
            membership=membership,
            action_plan=action_plan,
        ),
    }


def serialize_action_plan_detail(
    action_plan: ActionPlan,
    *,
    membership,
) -> dict:
    from houston.action_plans.permission_hints import (
        build_action_plan_detail_permission_hints,
    )

    payload = serialize_action_plan_list_item(action_plan, membership=membership)
    payload["permission_hints"] = build_action_plan_detail_permission_hints(
        membership=membership,
        action_plan=action_plan,
    )
    payload["requires_validation"] = action_plan.requires_validation
    payload["is_reusable"] = action_plan.is_reusable
    payload["created_by_id"] = action_plan.created_by_id
    payload["created_by_display_name"] = _membership_display_name(action_plan.created_by)
    payload["tasks"] = [serialize_task_template(task) for task in action_plan.tasks.all()]
    return payload


def _serialize_assignees_by_pole(execution: ActionPlanExecution) -> list[dict]:
    grouped: dict = defaultdict(list)
    business_units: dict = {}
    for assignee in execution.assignees.all():
        business_unit = assignee.execution_team.business_unit
        business_units[business_unit.id] = business_unit
        grouped[business_unit.id].append(
            {
                "membership_id": assignee.membership_id,
                "display_name": _membership_display_name(assignee.membership),
            }
        )
    return [
        {
            "business_unit": _serialize_business_unit(business_units[bu_id]),
            "assignees": grouped[bu_id],
        }
        for bu_id in sorted(grouped.keys(), key=str)
    ]


def _serialize_involved_poles(execution: ActionPlanExecution) -> list[dict]:
    teams_by_bu_id = {
        team.business_unit_id: team.business_unit for team in execution.execution_teams.all()
    }
    snapshots = get_involved_poles(execution)
    return [
        {
            "business_unit": _serialize_business_unit(teams_by_bu_id[snapshot.business_unit_id]),
            "contribution_status": snapshot.contribution_status,
        }
        for snapshot in snapshots
        if snapshot.business_unit_id in teams_by_bu_id
    ]


def serialize_task_execution(
    task_execution: ActionPlanExecutionTask,
    *,
    membership,
) -> dict:
    from houston.action_plans.permission_hints import (
        build_action_plan_task_execution_permission_hints,
    )

    return {
        "id": task_execution.id,
        "task": task_execution.task,
        "description": task_execution.description,
        "deadline_at": task_execution.deadline_at,
        "assigned_membership_id": task_execution.assigned_membership_id,
        "assigned_display_name": task_execution.assigned_display_name or None,
        "position": task_execution.position,
        "status": task_execution.status,
        "business_unit": _serialize_business_unit(task_execution.execution_team.business_unit),
        "observation_id": task_execution.observation_id,
        "skipped_reason": task_execution.skipped_reason,
        "completed_at": task_execution.completed_at,
        "skipped_at": task_execution.skipped_at,
        "observation_created_at": task_execution.observation_created_at,
        "permission_hints": build_action_plan_task_execution_permission_hints(
            membership=membership,
            task_execution=task_execution,
        ),
    }


def serialize_execution_detail(
    execution: ActionPlanExecution,
    *,
    membership,
) -> dict:
    from houston.action_plans.permission_hints import (
        build_action_plan_execution_permission_hints,
    )

    return {
        "id": execution.id,
        "action_plan_id": execution.action_plan_id,
        "status": execution.status,
        "title": execution.title,
        "description": execution.description,
        "requires_validation": execution.requires_validation,
        "pilot_business_unit": _serialize_business_unit(execution.pilot_business_unit),
        "affected_business_unit": _serialize_business_unit(execution.affected_business_unit),
        "responsible_business_unit": _serialize_business_unit(
            execution.responsible_business_unit,
        ),
        "activity_subject": _serialize_activity_subject(execution.activity_subject),
        "signal_summary": _serialize_signal_summary(execution),
        "created_by_id": execution.created_by_id,
        "created_by_display_name": _membership_display_name(execution.created_by),
        "use_shared_chronology": execution.use_shared_chronology,
        "start_at": execution.start_at,
        "visible_from": execution.visible_from,
        "end_at": execution.end_at,
        "occurrence_date": execution.occurrence_date,
        "last_activity_at": execution.last_activity_at,
        "marked_done_at": execution.marked_done_at,
        "validated_at": execution.validated_at,
        "canceled_at": execution.canceled_at,
        "created_at": execution.created_at,
        "updated_at": execution.updated_at,
        "assignees_by_pole": _serialize_assignees_by_pole(execution),
        "involved_poles": _serialize_involved_poles(execution),
        "task_executions": [
            serialize_task_execution(task, membership=membership)
            for task in execution.task_executions.all()
        ],
        "permission_hints": build_action_plan_execution_permission_hints(
            membership=membership,
            execution=execution,
        ),
    }


def serialize_schedule_detail(
    schedule: ActionPlanSchedule,
    *,
    membership,
) -> dict:
    from houston.action_plans.permission_hints import (
        build_action_plan_schedule_permission_hints,
    )

    return {
        "id": schedule.id,
        "action_plan_id": schedule.action_plan_id,
        "status": schedule.status,
        "use_shared_chronology": schedule.use_shared_chronology,
        "start_date": schedule.start_date,
        "end_date": schedule.end_date,
        "start_at": schedule.start_at,
        "end_at": schedule.end_at,
        "recurrence_days": schedule.recurrence_days or [],
        "created_by_id": schedule.created_by_id,
        "created_by_display_name": _membership_display_name(schedule.created_by),
        "last_materialized_at": schedule.last_materialized_at,
        "created_at": schedule.created_at,
        "updated_at": schedule.updated_at,
        "assignees": [
            {
                "membership_id": assignee.membership_id,
                "display_name": _membership_display_name(assignee.membership),
                "business_unit": _serialize_business_unit(assignee.business_unit),
                "start_at": assignee.start_at,
                "end_at": assignee.end_at,
            }
            for assignee in schedule.schedule_assignees.all()
        ],
        "permission_hints": build_action_plan_schedule_permission_hints(
            membership=membership,
            schedule=schedule,
        ),
    }
