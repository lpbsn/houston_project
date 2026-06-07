from __future__ import annotations

from django.db import models

from houston.actions.constants import (
    ACTION_INSTRUCTION_MAX_LENGTH,
    ACTION_TITLE_MAX_LENGTH,
)
from houston.core.models import BaseModel


class Action(BaseModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        PENDING_VALIDATION = "pending_validation", "Pending validation"
        REOPENED = "reopened", "Reopened"
        DONE = "done", "Done"
        CANCELED = "canceled", "Canceled"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="actions",
    )
    signal = models.ForeignKey(
        "signals.Signal",
        on_delete=models.PROTECT,
        related_name="actions",
        null=True,
        blank=True,
    )
    affected_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="affected_actions",
        null=True,
        blank=True,
    )
    responsible_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="responsible_actions",
        null=True,
        blank=True,
    )
    activity_subject = models.ForeignKey(
        "establishments.ActivitySubject",
        on_delete=models.PROTECT,
        related_name="actions",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=ACTION_TITLE_MAX_LENGTH)
    instruction = models.TextField(max_length=ACTION_INSTRUCTION_MAX_LENGTH)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_by = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="actions_created",
    )
    assigned_to = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="actions_assigned",
    )
    due_at = models.DateTimeField()
    last_activity_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    marked_done_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["establishment", "status", "due_at", "last_activity_at"],
                name="action_exec_feed_sort_idx",
            ),
            models.Index(
                fields=["signal", "status"],
                name="action_signal_status_idx",
            ),
            models.Index(
                fields=["establishment", "assigned_to"],
                name="action_est_assignee_idx",
            ),
            models.Index(
                fields=["establishment", "created_by"],
                name="action_est_creator_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Action {self.id} [{self.status}]"
