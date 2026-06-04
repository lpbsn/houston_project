from __future__ import annotations

from rest_framework import serializers

from houston.actions.constants import ACTION_INSTRUCTION_MAX_LENGTH
from houston.actions.models import Action

INSTRUCTION_SHORT_MAX_LENGTH = 280


def instruction_short(text: str) -> str:
    normalized = (text or "").strip()
    if len(normalized) <= INSTRUCTION_SHORT_MAX_LENGTH:
        return normalized
    return normalized[: INSTRUCTION_SHORT_MAX_LENGTH - 1].rstrip() + "…"


def _membership_display_name(membership) -> str:
    user = membership.user
    return user.get_full_name() or user.email or user.username


class ActionPermissionHintsSerializer(serializers.Serializer):
    can_accept = serializers.BooleanField()
    can_mark_done = serializers.BooleanField()
    can_validate = serializers.BooleanField()
    can_reopen = serializers.BooleanField()
    can_cancel = serializers.BooleanField()
    can_reassign = serializers.BooleanField()
    can_update_due_at = serializers.BooleanField()


class ActionSignalSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    urgency = serializers.CharField()
    module_key = serializers.CharField()
    domain_key = serializers.CharField()
    subject_key = serializers.CharField()


class ActionFeedItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    instruction_short = serializers.CharField()
    status = serializers.CharField()
    due_at = serializers.DateTimeField()
    is_overdue = serializers.BooleanField()
    module_key = serializers.CharField()
    domain_key = serializers.CharField()
    subject_key = serializers.CharField()
    signal_summary = ActionSignalSummarySerializer(allow_null=True)
    assigned_to_display_name = serializers.CharField()
    created_by_display_name = serializers.CharField()
    last_activity_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    permission_hints = ActionPermissionHintsSerializer()


class ExecutionFeedItemSerializer(serializers.Serializer):
    item_type = serializers.CharField()
    action = ActionFeedItemSerializer()


class ExecutionFeedResponseSerializer(serializers.Serializer):
    items = ExecutionFeedItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()


class ActionDetailSerializer(ActionFeedItemSerializer):
    instruction = serializers.CharField()
    accepted_at = serializers.DateTimeField(allow_null=True)
    marked_done_at = serializers.DateTimeField(allow_null=True)
    validated_at = serializers.DateTimeField(allow_null=True)


class ActionCreateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    instruction = serializers.CharField(max_length=ACTION_INSTRUCTION_MAX_LENGTH)
    assigned_to = serializers.UUIDField()
    due_at = serializers.DateTimeField()
    module_key = serializers.CharField()
    domain_key = serializers.CharField()
    subject_key = serializers.CharField()
    signal = serializers.UUIDField(required=False, allow_null=True)


class ActionReassignRequestSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField()


class ActionDueAtRequestSerializer(serializers.Serializer):
    due_at = serializers.DateTimeField()


def serialize_action_permission_hints(*, action: Action, membership) -> dict:
    from houston.actions.permissions import (
        can_accept_action,
        can_cancel_action,
        can_mark_action_done,
        can_reassign_action,
        can_reopen_action,
        can_update_action_due_at,
        can_validate_action_on_object,
    )

    return {
        "can_accept": can_accept_action(membership, action),
        "can_mark_done": can_mark_action_done(membership, action),
        "can_validate": can_validate_action_on_object(membership, action),
        "can_reopen": can_reopen_action(membership, action),
        "can_cancel": can_cancel_action(membership, action),
        "can_reassign": can_reassign_action(membership, action),
        "can_update_due_at": can_update_action_due_at(membership, action),
    }


def serialize_signal_summary(action: Action) -> dict | None:
    signal = action.signal
    if signal is None:
        return None
    return {
        "id": signal.id,
        "title": signal.title,
        "status": signal.status,
        "urgency": signal.urgency,
        "module_key": signal.operational_module.key,
        "domain_key": signal.operational_domain.key,
        "subject_key": signal.operational_subject.key,
    }


def serialize_action_feed_item(*, action: Action, membership, is_overdue: bool = False) -> dict:
    return {
        "id": action.id,
        "title": action.title,
        "instruction_short": instruction_short(action.instruction),
        "status": action.status,
        "due_at": action.due_at,
        "is_overdue": is_overdue,
        "module_key": action.operational_module.key,
        "domain_key": action.operational_domain.key,
        "subject_key": action.operational_subject.key,
        "signal_summary": serialize_signal_summary(action),
        "assigned_to_display_name": _membership_display_name(action.assigned_to),
        "created_by_display_name": _membership_display_name(action.created_by),
        "last_activity_at": action.last_activity_at,
        "created_at": action.created_at,
        "permission_hints": serialize_action_permission_hints(
            action=action,
            membership=membership,
        ),
    }


def serialize_action_detail(*, action: Action, membership, is_overdue: bool = False) -> dict:
    payload = serialize_action_feed_item(
        action=action,
        membership=membership,
        is_overdue=is_overdue,
    )
    payload["instruction"] = action.instruction
    payload["accepted_at"] = action.accepted_at
    payload["marked_done_at"] = action.marked_done_at
    payload["validated_at"] = action.validated_at
    return payload
