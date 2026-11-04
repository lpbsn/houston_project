from rest_framework import serializers

from houston.accounts.display import membership_display_name
from houston.comments.api.serializers import CommentAttachmentSerializer
from houston.signals.record_permissions import can_manage_record, can_progress_record
from houston.signals.record_selectors import calendar_dates, record_stage


class RecordPersonSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class RecordCalendarSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    due = serializers.DateField()
    overdue = serializers.BooleanField()


class FieldRecordSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    summary = serializers.CharField()
    kind = serializers.ChoiceField(choices=["observation", "project", "intake"])
    stage = serializers.ChoiceField(choices=["todo", "doing", "review", "closed"])
    closure_reason = serializers.CharField()
    pole = serializers.CharField()
    pole_id = serializers.UUIDField(allow_null=True)
    color_index = serializers.IntegerField(allow_null=True)
    is_pinned = serializers.BooleanField()
    owner = RecordPersonSerializer(allow_null=True)
    waiting_for = RecordPersonSerializer(allow_null=True)
    due_on = serializers.DateField(allow_null=True)
    planned_start_on = serializers.DateField(allow_null=True)
    is_project = serializers.BooleanField()
    is_milestone = serializers.BooleanField()
    parent_project = RecordPersonSerializer(allow_null=True)
    planning_predecessor = RecordPersonSerializer(allow_null=True)
    visible_child_count = serializers.IntegerField()
    visible_closed_child_count = serializers.IntegerField()
    blocked_reason = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    observation_count = serializers.IntegerField()
    calendar = RecordCalendarSerializer(allow_null=True)
    can_manage = serializers.BooleanField()
    can_progress = serializers.BooleanField()
    can_use_brain = serializers.BooleanField()
    participants = RecordPersonSerializer(many=True, required=False)


class FieldRecordPageSerializer(serializers.Serializer):
    items = FieldRecordSerializer(many=True)
    next_offset = serializers.IntegerField(allow_null=True)
    timezone = serializers.CharField()


class FieldRecordCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    business_unit_id = serializers.UUIDField()
    owner_membership_id = serializers.UUIDField(allow_null=True, required=False)
    due_on = serializers.DateField(allow_null=True, required=False)
    is_project = serializers.BooleanField(default=False)
    is_milestone = serializers.BooleanField(default=False)
    parent_project_id = serializers.UUIDField(allow_null=True, required=False)


class RecordOrganizationSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    parent_project_id = serializers.UUIDField(allow_null=True)
    is_project = serializers.BooleanField()
    is_milestone = serializers.BooleanField()


class RecordPredecessorSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    predecessor_id = serializers.UUIDField(allow_null=True)


class PlanningVersionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    updated_at = serializers.DateTimeField()


class RecordPlanningRequestSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    start_on = serializers.DateField()
    due_on = serializers.DateField()
    apply = serializers.BooleanField(default=False)
    expected_versions = PlanningVersionSerializer(many=True, required=False, max_length=200)


class PlanningChangeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    before_start = serializers.DateField()
    before_due = serializers.DateField(allow_null=True)
    start_on = serializers.DateField()
    due_on = serializers.DateField()


class RecordPlanningResponseSerializer(serializers.Serializer):
    changes = PlanningChangeSerializer(many=True)
    versions = PlanningVersionSerializer(many=True)
    applied = serializers.BooleanField()


class RecordDocumentSerializer(CommentAttachmentSerializer):
    execution_id = serializers.UUIDField()
    execution_title = serializers.CharField()


class RecordDocumentPageSerializer(serializers.Serializer):
    items = RecordDocumentSerializer(many=True)
    next_offset = serializers.IntegerField(allow_null=True)


class FieldRecordUpdateSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    title = serializers.CharField(max_length=200, required=False)
    structured_summary = serializers.CharField(max_length=5000, allow_blank=True, required=False)
    owner_membership_id = serializers.UUIDField(allow_null=True, required=False)
    waiting_for_membership_id = serializers.UUIDField(allow_null=True, required=False)
    due_on = serializers.DateField(allow_null=True, required=False)
    planned_start_on = serializers.DateField(allow_null=True, required=False)
    blocked_reason = serializers.CharField(max_length=500, allow_blank=True, required=False)
    stage = serializers.ChoiceField(choices=["todo", "doing", "review", "closed"], required=False)
    closure_reason = serializers.ChoiceField(
        choices=["resolved", "acknowledged", "abandoned"], required=False
    )


class FieldRecordCommandSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    command = serializers.ChoiceField(
        choices=["participants", "work", "link_work", "dependency", "follow", "link_objective"]
    )
    membership_ids = serializers.ListField(
        child=serializers.UUIDField(), max_length=50, required=False
    )
    title = serializers.CharField(max_length=200, allow_blank=True, required=False)
    tasks = serializers.ListField(
        child=serializers.CharField(max_length=500), max_length=50, required=False
    )
    assignee_id = serializers.UUIDField(allow_null=True, required=False)
    due_on = serializers.DateField(allow_null=True, required=False)
    quick = serializers.BooleanField(required=False)
    execution_id = serializers.UUIDField(required=False)
    task_id = serializers.UUIDField(required=False)
    depends_on_id = serializers.UUIDField(allow_null=True, required=False)
    enabled = serializers.BooleanField(required=False)
    objective_id = serializers.UUIDField(required=False)


class FieldRecordSectionItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    text = serializers.CharField(allow_blank=True)
    author = serializers.CharField(allow_blank=True)
    date = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField(allow_blank=True)


class FieldRecordSectionSerializer(serializers.Serializer):
    items = FieldRecordSectionItemSerializer(many=True)
    next_offset = serializers.IntegerField(allow_null=True)


class FieldRecordOptionsSerializer(serializers.Serializer):
    poles = RecordPersonSerializer(many=True)
    members = RecordPersonSerializer(many=True)
    more_members = serializers.BooleanField()
    objectives = RecordPersonSerializer(many=True)
    executions = RecordPersonSerializer(many=True)
    projects = RecordPersonSerializer(many=True)
    records = RecordPersonSerializer(many=True)


def person(member):
    return {"id": member.id, "name": membership_display_name(member)} if member else None


def serialize_record(record, actor):
    pole = record.responsible_business_unit or record.affected_business_unit
    return {
        "id": record.id,
        "title": record.title,
        "summary": record.structured_summary,
        "kind": record.record_kind,
        "is_pinned": record.is_pinned,
        "stage": record_stage(record),
        "closure_reason": record.closure_reason,
        "pole": pole.specific_name if pole else "À orienter",
        "pole_id": pole.id if pole else None,
        "color_index": pole.color_index if pole else None,
        "owner": person(record.owner_membership),
        "waiting_for": person(record.waiting_for_membership),
        "due_on": record.due_on,
        "planned_start_on": record.planned_start_on,
        "is_project": record.is_project,
        "is_milestone": record.is_milestone,
        "parent_project": {"id": record.parent_project_id, "name": record.parent_project.title}
        if getattr(record, "parent_visible", False)
        else None,
        "planning_predecessor": {
            "id": record.planning_predecessor_id,
            "name": record.planning_predecessor.title,
        }
        if getattr(record, "predecessor_visible", False)
        else None,
        "visible_child_count": getattr(record, "visible_child_count", 0),
        "visible_closed_child_count": getattr(record, "visible_closed_child_count", 0),
        "blocked_reason": record.blocked_reason,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "observation_count": getattr(record, "observation_count", 0),
        "calendar": calendar_dates(record),
        "can_manage": can_manage_record(actor, record),
        "can_progress": can_progress_record(actor, record),
        "can_use_brain": actor.role in ("owner", "director"),
    }
