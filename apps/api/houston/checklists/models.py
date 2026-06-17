from __future__ import annotations

from django.db import models
from django.db.models import Q

from houston.checklists.constants import (
    CHECKLIST_DESCRIPTION_MAX_LENGTH,
    CHECKLIST_SKIPPED_REASON_MAX_LENGTH,
    CHECKLIST_TASK_MAX_LENGTH,
    CHECKLIST_TITLE_MAX_LENGTH,
    EXECUTION_SOURCE_ASSIGNMENT,
    EXECUTION_SOURCE_TEMPLATE,
    TERMINAL_EXECUTION_STATUSES,
)
from houston.core.models import BaseModel


class ChecklistTemplate(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="checklist_templates",
    )
    created_by = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="checklist_templates_created",
    )
    business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="checklist_templates",
    )
    title = models.CharField(max_length=CHECKLIST_TITLE_MAX_LENGTH)
    description = models.TextField(
        max_length=CHECKLIST_DESCRIPTION_MAX_LENGTH,
        blank=True,
        default="",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.INACTIVE,
    )

    class Meta:
        indexes = [
            models.Index(fields=["establishment", "created_by"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(business_unit__isnull=False),
                name="checklist_template_business_unit_required",
            ),
        ]


class ChecklistTaskTemplate(BaseModel):
    checklist_template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.CASCADE,
        related_name="task_templates",
    )
    task = models.CharField(max_length=CHECKLIST_TASK_MAX_LENGTH)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["checklist_template", "position"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["checklist_template", "position"],
                name="uniq_checklist_task_template_position",
            ),
        ]


class ChecklistAssignment(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    checklist_template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.SET_NULL,
        related_name="assignments",
        null=True,
        blank=True,
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="checklist_assignments",
    )
    assigned_to = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="checklist_assignments_received",
    )
    assigned_by = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="checklist_assignments_created",
    )
    business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="checklist_assignments",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    start_at = models.TimeField()
    end_at = models.TimeField()
    recurrence_days = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    last_materialized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["establishment", "status"]),
            models.Index(fields=["assigned_to", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="checklist_assignment_end_date_on_or_after_start",
            ),
            models.CheckConstraint(
                condition=Q(end_at__gt=models.F("start_at")),
                name="checklist_assignment_end_after_start_time",
            ),
        ]


class ChecklistExecution(BaseModel):
    class ExecutionSource(models.TextChoices):
        TEMPLATE = EXECUTION_SOURCE_TEMPLATE, "Template"
        ASSIGNMENT = EXECUTION_SOURCE_ASSIGNMENT, "Assignment"

    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        CANCELED = "canceled", "Canceled"

    checklist_template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.PROTECT,
        related_name="executions",
        null=True,
        blank=True,
    )
    checklist_assignment = models.ForeignKey(
        ChecklistAssignment,
        on_delete=models.PROTECT,
        related_name="executions",
        null=True,
        blank=True,
    )
    execution_source = models.CharField(
        max_length=16,
        choices=ExecutionSource.choices,
        default=EXECUTION_SOURCE_TEMPLATE,
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="checklist_executions",
    )
    assigned_to = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="checklist_executions_assigned",
    )
    assigned_by = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="checklist_executions_assigned_by",
        null=True,
        blank=True,
    )
    business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="checklist_executions",
    )
    template_title = models.CharField(max_length=CHECKLIST_TITLE_MAX_LENGTH)
    template_description = models.TextField(
        max_length=CHECKLIST_DESCRIPTION_MAX_LENGTH,
        blank=True,
        default="",
    )
    start_at = models.DateTimeField(null=True, blank=True)
    visible_from = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    occurrence_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ASSIGNED,
    )
    last_activity_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["establishment", "status", "visible_from", "last_activity_at"],
                name="checklist_exec_feed_idx",
            ),
            models.Index(fields=["assigned_to", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        execution_source=EXECUTION_SOURCE_ASSIGNMENT,
                        business_unit__isnull=False,
                        checklist_assignment__isnull=False,
                    )
                    | Q(
                        execution_source=EXECUTION_SOURCE_TEMPLATE,
                        business_unit__isnull=False,
                        checklist_template__isnull=False,
                        checklist_assignment__isnull=True,
                    )
                    | Q(
                        execution_source=EXECUTION_SOURCE_TEMPLATE,
                        business_unit__isnull=False,
                        checklist_template__isnull=True,
                        checklist_assignment__isnull=True,
                        status__in=TERMINAL_EXECUTION_STATUSES,
                    )
                ),
                name="checklist_execution_source_shape",
            ),
            models.UniqueConstraint(
                fields=["checklist_assignment", "occurrence_date"],
                condition=Q(checklist_assignment__isnull=False),
                name="uniq_checklist_execution_assignment_occurrence",
            ),
        ]


class ChecklistTaskExecution(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        SKIPPED = "skipped", "Skipped"
        OBSERVATION_CREATED = "observation_created", "Observation created"

    checklist_execution = models.ForeignKey(
        ChecklistExecution,
        on_delete=models.CASCADE,
        related_name="task_executions",
    )
    checklist_task_template = models.ForeignKey(
        ChecklistTaskTemplate,
        on_delete=models.SET_NULL,
        related_name="task_executions",
        null=True,
        blank=True,
    )
    task = models.CharField(max_length=CHECKLIST_TASK_MAX_LENGTH)
    position = models.PositiveIntegerField()
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    observation = models.ForeignKey(
        "observations.Observation",
        on_delete=models.SET_NULL,
        related_name="checklist_task_executions",
        null=True,
        blank=True,
    )
    skipped_reason = models.CharField(
        max_length=CHECKLIST_SKIPPED_REASON_MAX_LENGTH,
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    skipped_at = models.DateTimeField(null=True, blank=True)
    observation_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["checklist_execution", "position"]),
        ]
