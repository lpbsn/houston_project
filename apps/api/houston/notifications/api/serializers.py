from __future__ import annotations

import uuid

from rest_framework import serializers

from houston.notifications.models import Notification
from houston.notifications.navigation import build_comment_navigation_index


def _membership_display_name(membership) -> str:
    user = membership.user
    return user.get_full_name() or user.email or user.username


def serialize_notification_actor(notification: Notification) -> dict | None:
    if notification.actor_membership_id is None:
        return None
    return {
        "membership_id": notification.actor_membership_id,
        "display_name": _membership_display_name(notification.actor_membership),
    }


def _resolve_notification_navigation(
    notification: Notification,
    *,
    comment_navigation_by_subject_id: dict[uuid.UUID, dict] | None = None,
) -> dict | None:
    if notification.subject_type != Notification.SubjectType.COMMENT:
        return None
    if comment_navigation_by_subject_id is None:
        index = build_comment_navigation_index(
            establishment_id=notification.establishment_id,
            notifications=[notification],
        )
        return index.get(notification.subject_id)
    return comment_navigation_by_subject_id.get(notification.subject_id)


def serialize_notification(
    notification: Notification,
    *,
    comment_navigation_by_subject_id: dict[uuid.UUID, dict] | None = None,
) -> dict:
    return {
        "id": notification.id,
        "event_key": notification.event_key,
        "subject_type": notification.subject_type,
        "subject_id": notification.subject_id,
        "priority": notification.priority,
        "status": notification.status,
        "title": notification.title,
        "body": notification.body,
        "actor": serialize_notification_actor(notification),
        "navigation": _resolve_notification_navigation(
            notification,
            comment_navigation_by_subject_id=comment_navigation_by_subject_id,
        ),
        "created_at": notification.created_at,
        "read_at": notification.read_at,
        "archived_at": notification.archived_at,
    }


class NotificationActorSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()


class NotificationNavigationSerializer(serializers.Serializer):
    parent_subject_type = serializers.ChoiceField(choices=Notification.SubjectType.choices)
    parent_subject_id = serializers.UUIDField()


class NotificationItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    event_key = serializers.CharField()
    subject_type = serializers.ChoiceField(choices=Notification.SubjectType.choices)
    subject_id = serializers.UUIDField()
    priority = serializers.ChoiceField(choices=Notification.Priority.choices)
    status = serializers.ChoiceField(choices=Notification.Status.choices)
    title = serializers.CharField()
    body = serializers.CharField()
    actor = NotificationActorSerializer(allow_null=True)
    navigation = NotificationNavigationSerializer(allow_null=True)
    created_at = serializers.DateTimeField()
    read_at = serializers.DateTimeField(allow_null=True)
    archived_at = serializers.DateTimeField(allow_null=True)


class NotificationListCountsSerializer(serializers.Serializer):
    unread = serializers.IntegerField()


class NotificationListAppliedFiltersSerializer(serializers.Serializer):
    status = serializers.CharField(allow_null=True)


class NotificationListResponseSerializer(serializers.Serializer):
    items = NotificationItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()
    applied_filters = NotificationListAppliedFiltersSerializer()
    counts = NotificationListCountsSerializer()


class MarkAllNotificationsReadResponseSerializer(serializers.Serializer):
    updated_count = serializers.IntegerField()


class NotificationPreferencesSerializer(serializers.Serializer):
    notifications_enabled = serializers.BooleanField()
    push_enabled = serializers.BooleanField()


class NotificationPreferencesUpdateSerializer(serializers.Serializer):
    notifications_enabled = serializers.BooleanField(required=False)
    push_enabled = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one preference field is required.")
        return attrs


class VapidPublicKeySerializer(serializers.Serializer):
    public_key = serializers.CharField()


class WebPushSubscriptionUpsertSerializer(serializers.Serializer):
    endpoint = serializers.CharField(max_length=512)
    p256dh = serializers.CharField(max_length=255)
    auth = serializers.CharField(max_length=255)
    user_agent = serializers.CharField(max_length=512, required=False, allow_blank=True, default="")


class WebPushSubscriptionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    endpoint = serializers.CharField()
    created_at = serializers.DateTimeField()
    last_seen_at = serializers.DateTimeField(allow_null=True)
