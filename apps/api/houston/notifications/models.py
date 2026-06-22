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
        ACTION_CREATED = "action.created", "Action created"
        ACTION_REASSIGNED = "action.reassigned", "Action reassigned"
        ACTION_PENDING_VALIDATION = "action.pending_validation", "Action pending validation"
        ACTION_REOPENED = "action.reopened", "Action reopened"
        ACTION_CANCELED = "action.canceled", "Action canceled"
        CHECKLIST_EXECUTION_CREATED = (
            "checklist.execution.created",
            "Checklist execution created",
        )
        CHECKLIST_EXECUTION_CANCELED = (
            "checklist.execution.canceled",
            "Checklist execution canceled",
        )
        COMMENT_MENTION_CREATED = "comment.mention.created", "Comment mention created"

    class SubjectType(models.TextChoices):
        ACTION = "action", "Action"
        CHECKLIST_EXECUTION = "checklist_execution", "Checklist execution"
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
