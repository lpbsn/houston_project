from __future__ import annotations

from rest_framework import serializers

from houston.signals.models import Signal
from houston.signals.reporter_display import reporter_display_name_for_signal
from houston.signals.services import structured_summary_short


class PermissionHintsSerializer(serializers.Serializer):
    can_pin = serializers.BooleanField()
    can_set_urgency = serializers.BooleanField()
    can_cancel = serializers.BooleanField()
    can_resolve = serializers.BooleanField()


class SignalFeedItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    structured_summary_short = serializers.CharField()
    status = serializers.CharField()
    urgency = serializers.CharField()
    is_pinned = serializers.BooleanField()
    module_key = serializers.CharField()
    domain_key = serializers.CharField()
    subject_key = serializers.CharField()
    operational_unit_key = serializers.CharField(allow_null=True)
    location_text = serializers.CharField()
    media_count = serializers.IntegerField()
    last_activity_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    reporter_display_name = serializers.CharField(allow_null=True, required=False)
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


class SignalDetailSerializer(SignalFeedItemSerializer):
    structured_summary = serializers.CharField()
    source_context = SourceContextSerializer()


class SignalUrgencyRequestSerializer(serializers.Serializer):
    urgency = serializers.ChoiceField(choices=Signal.Urgency.values)


def serialize_signal_feed_item(*, signal: Signal, membership) -> dict:
    from houston.signals.permissions import (
        can_cancel_signal,
        can_pin_signal,
        can_resolve_signal,
        can_set_signal_urgency,
    )

    media_count = 0
    link = signal.source_observation_links.select_related("observation").first()
    if link is not None:
        media_count = link.observation.media_items.count()

    return {
        "id": signal.id,
        "title": signal.title,
        "structured_summary_short": structured_summary_short(signal.structured_summary),
        "status": signal.status,
        "urgency": signal.urgency,
        "is_pinned": signal.is_pinned,
        "module_key": signal.operational_module.key,
        "domain_key": signal.operational_domain.key,
        "subject_key": signal.operational_subject.key,
        "operational_unit_key": signal.operational_unit.key if signal.operational_unit else None,
        "location_text": signal.location_text,
        "media_count": media_count,
        "last_activity_at": signal.last_activity_at,
        "created_at": signal.created_at,
        "reporter_display_name": reporter_display_name_for_signal(signal),
        "permission_hints": {
            "can_pin": can_pin_signal(membership, signal),
            "can_set_urgency": can_set_signal_urgency(membership, signal),
            "can_cancel": can_cancel_signal(membership, signal),
            "can_resolve": can_resolve_signal(membership, signal),
        },
    }


def serialize_signal_detail(*, signal: Signal, membership) -> dict:
    payload = serialize_signal_feed_item(signal=signal, membership=membership)
    payload["structured_summary"] = signal.structured_summary

    link = (
        signal.source_observation_links.select_related(
            "observation",
            "observation__submitted_by_membership__user",
        )
        .order_by("created_at")
        .first()
    )
    if link is None:
        payload["source_context"] = {
            "submitted_at": None,
            "reporter_display_name": "",
            "media_count": 0,
        }
    else:
        observation = link.observation
        user = observation.submitted_by_membership.user
        display = user.get_full_name() or user.email or user.username
        payload["source_context"] = {
            "submitted_at": observation.submitted_at,
            "reporter_display_name": display,
            "media_count": observation.media_items.count(),
        }
    return payload
