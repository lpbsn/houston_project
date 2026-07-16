from __future__ import annotations

from rest_framework import serializers

from houston.action_plans.api.serializers import (
    ActionPlanBusinessUnitSerializer,
    _serialize_business_unit,
)
from houston.action_plans.models import ActionPlanExecution
from houston.observations.media_access import build_observation_media_preview_url
from houston.signals.models import Signal
from houston.signals.reporter_display import (
    created_from_observation_media_items,
    created_from_source_observation_link,
    media_count_for_signal,
    observation_media_count,
    reporter_display_name_for_signal,
)
from houston.signals.services import structured_summary_short


class PermissionHintsSerializer(serializers.Serializer):
    can_pin = serializers.BooleanField()
    can_cancel = serializers.BooleanField()
    can_resolve = serializers.BooleanField()
    can_create_linked_action_plan = serializers.BooleanField()


class SignalFeedItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    structured_summary_short = serializers.CharField()
    status = serializers.CharField()
    is_pinned = serializers.BooleanField()
    affected_business_unit_id = serializers.UUIDField(allow_null=True, required=False)
    affected_business_unit_key = serializers.CharField(allow_null=True, required=False)
    affected_business_unit_label = serializers.CharField(allow_null=True, required=False)
    responsible_business_unit_id = serializers.UUIDField(allow_null=True, required=False)
    responsible_business_unit_key = serializers.CharField(allow_null=True, required=False)
    responsible_business_unit_label = serializers.CharField(allow_null=True, required=False)
    activity_subject_id = serializers.UUIDField(allow_null=True, required=False)
    activity_subject_normalized_name = serializers.CharField(allow_null=True, required=False)
    activity_subject_label = serializers.CharField(allow_null=True, required=False)
    operational_unit_key = serializers.CharField(allow_null=True)
    location_text = serializers.CharField()
    media_count = serializers.IntegerField()
    last_activity_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    reporter_display_name = serializers.CharField(allow_null=True, required=False)
    aggregation_count = serializers.IntegerField()
    permission_hints = PermissionHintsSerializer()


class SignalFeedResponseSerializer(serializers.Serializer):
    items = SignalFeedItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()
    applied_filters = serializers.DictField()


class SourceContextSerializer(serializers.Serializer):
    submitted_at = serializers.DateTimeField(allow_null=True)
    reporter_display_name = serializers.CharField(allow_blank=True)
    media_count = serializers.IntegerField()


class SignalDetailMediaItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    preview_url = serializers.URLField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    position = serializers.IntegerField()
    observation_id = serializers.UUIDField()


class SignalLinkedActionPlanExecutionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    requires_validation = serializers.BooleanField()
    pilot_business_unit = ActionPlanBusinessUnitSerializer()
    last_activity_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()


class SignalDetailSerializer(SignalFeedItemSerializer):
    structured_summary = serializers.CharField()
    source_context = SourceContextSerializer()
    media_items = SignalDetailMediaItemSerializer(many=True)
    linked_action_plan_executions = SignalLinkedActionPlanExecutionSerializer(many=True)


def serialize_signal_feed_item(*, signal: Signal, membership) -> dict:
    from houston.action_plans.permissions import can_create_linked_action_plan
    from houston.signals.permissions import (
        can_cancel_signal,
        can_pin_signal,
        can_resolve_signal,
    )

    return {
        "id": signal.id,
        "title": signal.title,
        "structured_summary_short": structured_summary_short(signal.structured_summary),
        "status": signal.status,
        "is_pinned": signal.is_pinned,
        "affected_business_unit_id": signal.affected_business_unit_id,
        "affected_business_unit_key": (
            signal.affected_business_unit.key if signal.affected_business_unit_id else None
        ),
        "affected_business_unit_label": (
            signal.affected_business_unit.label if signal.affected_business_unit_id else None
        ),
        "responsible_business_unit_id": signal.responsible_business_unit_id,
        "responsible_business_unit_key": (
            signal.responsible_business_unit.key if signal.responsible_business_unit_id else None
        ),
        "responsible_business_unit_label": (
            signal.responsible_business_unit.label if signal.responsible_business_unit_id else None
        ),
        "activity_subject_id": signal.activity_subject_id,
        "activity_subject_normalized_name": (
            signal.activity_subject.normalized_name if signal.activity_subject_id else None
        ),
        "activity_subject_label": (
            signal.activity_subject.label if signal.activity_subject_id else None
        ),
        "operational_unit_key": signal.operational_unit.key if signal.operational_unit else None,
        "location_text": signal.location_text,
        "media_count": media_count_for_signal(signal),
        "last_activity_at": signal.last_activity_at,
        "created_at": signal.created_at,
        "reporter_display_name": reporter_display_name_for_signal(signal),
        "aggregation_count": getattr(signal, "aggregation_count", 0) or 0,
        "permission_hints": {
            "can_pin": can_pin_signal(membership, signal),
            "can_cancel": can_cancel_signal(membership, signal),
            "can_resolve": can_resolve_signal(membership, signal),
            "can_create_linked_action_plan": can_create_linked_action_plan(
                membership,
                signal=signal,
            ),
        },
    }


def _serialize_signal_detail_media_items(*, signal: Signal, request) -> list[dict]:
    link = created_from_source_observation_link(signal)
    if link is None:
        return []

    observation_id = link.observation_id
    return [
        {
            "id": media.id,
            "preview_url": build_observation_media_preview_url(
                request=request,
                establishment_id=signal.establishment_id,
                media_id=media.id,
            ),
            "content_type": media.content_type,
            "size_bytes": media.size_bytes,
            "position": media.position,
            "observation_id": observation_id,
        }
        for media in created_from_observation_media_items(signal)
    ]


def serialize_linked_action_plan_execution_for_signal_detail(
    execution: ActionPlanExecution,
) -> dict:
    return {
        "id": execution.id,
        "title": execution.title,
        "status": execution.status,
        "requires_validation": execution.requires_validation,
        "pilot_business_unit": _serialize_business_unit(execution.pilot_business_unit),
        "last_activity_at": execution.last_activity_at,
        "created_at": execution.created_at,
    }


def serialize_signal_detail(*, signal: Signal, membership, request) -> dict:
    from houston.action_plans.selectors import linked_action_plan_executions_for_signal_detail

    payload = serialize_signal_feed_item(signal=signal, membership=membership)
    payload["structured_summary"] = signal.structured_summary

    link = created_from_source_observation_link(signal)
    if link is None:
        payload["source_context"] = {
            "submitted_at": None,
            "reporter_display_name": "",
            "media_count": 0,
        }
        payload["media_items"] = []
    else:
        observation = link.observation
        user = observation.submitted_by_membership.user
        display = user.get_full_name() or user.email or user.username
        payload["source_context"] = {
            "submitted_at": observation.submitted_at,
            "reporter_display_name": display,
            "media_count": observation_media_count(observation),
        }
        payload["media_items"] = _serialize_signal_detail_media_items(
            signal=signal,
            request=request,
        )
    payload["linked_action_plan_executions"] = [
        serialize_linked_action_plan_execution_for_signal_detail(execution)
        for execution in linked_action_plan_executions_for_signal_detail(
            membership=membership,
            signal=signal,
        )
    ]
    return payload
