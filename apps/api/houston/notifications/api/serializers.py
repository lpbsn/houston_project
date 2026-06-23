from __future__ import annotations

from rest_framework import serializers

from houston.notifications.models import Notification


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


def serialize_notification(notification: Notification) -> dict:
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
        "created_at": notification.created_at,
        "read_at": notification.read_at,
        "archived_at": notification.archived_at,
    }


class NotificationActorSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()


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


class NotificationPreferencesUpdateSerializer(serializers.Serializer):
    notifications_enabled = serializers.BooleanField(required=True)
