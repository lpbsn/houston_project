from rest_framework import serializers

from houston.accounts.display import membership_display_name
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
    owner = RecordPersonSerializer(allow_null=True)
    waiting_for = RecordPersonSerializer(allow_null=True)
    due_on = serializers.DateField(allow_null=True)
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


class FieldRecordUpdateSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    title = serializers.CharField(max_length=200, required=False)
    structured_summary = serializers.CharField(max_length=5000, allow_blank=True, required=False)
    owner_membership_id = serializers.UUIDField(allow_null=True, required=False)
    waiting_for_membership_id = serializers.UUIDField(allow_null=True, required=False)
    due_on = serializers.DateField(allow_null=True, required=False)
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


def person(member):
    return {"id": member.id, "name": membership_display_name(member)} if member else None


def serialize_record(record, actor):
    pole = record.responsible_business_unit or record.affected_business_unit
    return {
        "id": record.id,
        "title": record.title,
        "summary": record.structured_summary,
        "kind": record.record_kind,
        "stage": record_stage(record),
        "closure_reason": record.closure_reason,
        "pole": pole.specific_name if pole else "À orienter",
        "pole_id": pole.id if pole else None,
        "color_index": pole.color_index if pole else None,
        "owner": person(record.owner_membership),
        "waiting_for": person(record.waiting_for_membership),
        "due_on": record.due_on,
        "blocked_reason": record.blocked_reason,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "observation_count": getattr(record, "observation_count", 0),
        "calendar": calendar_dates(record),
        "can_manage": can_manage_record(actor, record),
        "can_progress": can_progress_record(actor, record),
        "can_use_brain": actor.role in ("owner", "director"),
    }
