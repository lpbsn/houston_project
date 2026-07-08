from __future__ import annotations

from django.db import models

from houston.core.models import BaseModel
from houston.notifications.constants import (
    DEDUPE_KEY_MAX_LENGTH,
    NOTIFICATION_BODY_MAX_LENGTH,
    NOTIFICATION_TITLE_MAX_LENGTH,
)


class Notification(BaseModel):
    class EventKey(models.TextChoices):
        ACTION_PLAN_EXECUTION_CREATED = (
            "action_plan.execution.created",
            "Action plan execution created",
        )
        ACTION_PLAN_EXECUTION_PENDING_VALIDATION = (
            "action_plan.execution.pending_validation",
            "Action plan execution pending validation",
        )
        ACTION_PLAN_EXECUTION_CANCELED = (
            "action_plan.execution.canceled",
            "Action plan execution canceled",
        )
        ACTION_PLAN_EXECUTION_REOPENED = (
            "action_plan.execution.reopened",
            "Action plan execution reopened",
        )
        COMMENT_MENTION_CREATED = "comment.mention.created", "Comment mention created"
        SIGNAL_CREATED = "signal.created", "Signal created"
        SIGNAL_URGENCY_CHANGED = "signal.urgency_changed", "Signal urgency changed"
        SIGNAL_PINNED = "signal.pinned", "Signal pinned"
        SIGNAL_RESOLVED = "signal.resolved", "Signal resolved"
        SIGNAL_CANCELED = "signal.canceled", "Signal canceled"
        CHAT_MESSAGE_RECEIVED = "chat.message.received", "Chat message received"

    class SubjectType(models.TextChoices):
        ACTION_PLAN_EXECUTION = "action_plan_execution", "Action plan execution"
        CHAT_CONVERSATION = "chat_conversation", "Chat conversation"
        COMMENT = "comment", "Comment"
        SIGNAL = "signal", "Signal"

    class Priority(models.TextChoices):
        INFO = "info", "Info"
        ACTION_REQUIRED = "action_required", "Action required"
        URGENT = "urgent", "Urgent"
        SYSTEM = "system", "System"

    class Status(models.TextChoices):
        UNREAD = "unread", "Unread"
        READ = "read", "Read"
        ARCHIVED = "archived", "Archived"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    recipient_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="notifications_received",
    )
    actor_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="notifications_sent",
        null=True,
        blank=True,
    )
    event_key = models.CharField(max_length=64, choices=EventKey.choices)
    subject_type = models.CharField(max_length=32, choices=SubjectType.choices)
    subject_id = models.UUIDField()
    priority = models.CharField(max_length=32, choices=Priority.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.UNREAD,
    )
    title = models.CharField(max_length=NOTIFICATION_TITLE_MAX_LENGTH)
    body = models.CharField(max_length=NOTIFICATION_BODY_MAX_LENGTH)
    dedupe_key = models.CharField(max_length=DEDUPE_KEY_MAX_LENGTH, blank=True, default="")
    read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=[
                    "establishment",
                    "recipient_membership",
                    "status",
                    "created_at",
                    "id",
                ],
            ),
            models.Index(fields=["recipient_membership", "status"]),
            models.Index(fields=["recipient_membership", "dedupe_key", "created_at"]),
        ]
