from __future__ import annotations

from django.db import models
from django.db.models import Q

from houston.action_plans.constants import (
    ACTION_PLAN_DESCRIPTION_MAX_LENGTH,
    ACTION_PLAN_SKIPPED_REASON_MAX_LENGTH,
    ACTION_PLAN_TASK_MAX_LENGTH,
    ACTION_PLAN_TITLE_MAX_LENGTH,
    CATALOG_STATUS_ACTIVE,
    CATALOG_STATUS_INACTIVE,
    EXECUTION_STATUS_IN_PROGRESS,
    MAX_TASK_POSITION,
    MIN_TASK_POSITION,
    SCHEDULE_STATUS_ACTIVE,
    SCHEDULE_STATUS_INACTIVE,
    TASK_STATUS_PENDING,
)
from houston.core.models import BaseModel


class ActionPlan(BaseModel):
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="action_plans",
    )
    created_by = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="action_plans_created",
    )
    pilot_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="pilot_action_plans",
    )
    affected_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="affected_action_plans",
        null=True,
        blank=True,
    )
    responsible_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="responsible_action_plans",
        null=True,
        blank=True,
    )
    activity_subject = models.ForeignKey(
        "establishments.ActivitySubject",
        on_delete=models.PROTECT,
        related_name="action_plans",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=ACTION_PLAN_TITLE_MAX_LENGTH)
    description = models.TextField(
        max_length=ACTION_PLAN_DESCRIPTION_MAX_LENGTH,
        blank=True,
        default="",
    )
    requires_validation = models.BooleanField(default=True)
    is_reusable = models.BooleanField(default=False)
    catalog_status = models.CharField(
        max_length=16,
        choices=[
            (CATALOG_STATUS_ACTIVE, "Active"),
            (CATALOG_STATUS_INACTIVE, "Inactive"),
        ],
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["establishment", "pilot_business_unit", "catalog_status"],
                name="ap_plan_catalog_idx",
            ),
            models.Index(
                fields=["establishment", "created_by"],
                name="ap_plan_est_creator_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(pilot_business_unit__isnull=False),
                name="action_plan_pilot_business_unit_required",
            ),
            models.CheckConstraint(
                condition=~Q(is_reusable=True, catalog_status__isnull=True),
                name="action_plan_reusable_requires_catalog_status",
            ),
            models.CheckConstraint(
                condition=~Q(is_reusable=False, catalog_status__isnull=False),
                name="action_plan_non_reusable_null_catalog_status",
            ),
        ]

    def __str__(self) -> str:
        return f"ActionPlan {self.id} [{self.title}]"


class ActionPlanTask(BaseModel):
    action_plan = models.ForeignKey(
        ActionPlan,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="action_plan_tasks",
    )
    task = models.CharField(max_length=ACTION_PLAN_TASK_MAX_LENGTH)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["action_plan", "position"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["action_plan", "position"],
                name="uniq_action_plan_task_position",
            ),
            models.CheckConstraint(
                condition=Q(
                    position__gte=MIN_TASK_POSITION,
                    position__lte=MAX_TASK_POSITION,
                ),
                name="action_plan_task_position_bounds",
            ),
            models.CheckConstraint(
                condition=Q(business_unit__isnull=False),
                name="action_plan_task_business_unit_required",
            ),
        ]

    def __str__(self) -> str:
        return f"ActionPlanTask plan={self.action_plan_id} pos={self.position}"


class ActionPlanSchedule(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = SCHEDULE_STATUS_ACTIVE, "Active"
        INACTIVE = SCHEDULE_STATUS_INACTIVE, "Inactive"

    action_plan = models.ForeignKey(
        ActionPlan,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="action_plan_schedules",
    )
    created_by = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="action_plan_schedules_created",
    )
    use_shared_chronology = models.BooleanField(default=False)
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
            models.Index(fields=["action_plan", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="action_plan_schedule_end_date_on_or_after_start",
            ),
            models.CheckConstraint(
                condition=Q(end_at__gt=models.F("start_at")),
                name="action_plan_schedule_end_after_start_time",
            ),
        ]

    def __str__(self) -> str:
        return f"ActionPlanSchedule plan={self.action_plan_id} [{self.status}]"


class ActionPlanScheduleAssignee(BaseModel):
    action_plan_schedule = models.ForeignKey(
        ActionPlanSchedule,
        on_delete=models.CASCADE,
        related_name="schedule_assignees",
    )
    membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="action_plan_schedule_assignments",
    )
    business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="action_plan_schedule_assignees",
    )
    start_at = models.TimeField(null=True, blank=True)
    end_at = models.TimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["action_plan_schedule", "membership"],
                name="uniq_action_plan_schedule_assignee",
            ),
            models.CheckConstraint(
                condition=(
                    Q(start_at__isnull=True)
                    | Q(end_at__isnull=True)
                    | Q(end_at__gt=models.F("start_at"))
                ),
                name="action_plan_schedule_assignee_end_after_start",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"ActionPlanScheduleAssignee schedule={self.action_plan_schedule_id} "
            f"membership={self.membership_id}"
        )


class ActionPlanExecution(BaseModel):
    class Status(models.TextChoices):
        IN_PROGRESS = EXECUTION_STATUS_IN_PROGRESS, "In progress"
        PENDING_VALIDATION = "pending_validation", "Pending validation"
        DONE = "done", "Done"
        CANCELED = "canceled", "Canceled"

    action_plan = models.ForeignKey(
        ActionPlan,
        on_delete=models.PROTECT,
        related_name="executions",
        null=True,
        blank=True,
    )
    action_plan_schedule = models.ForeignKey(
        ActionPlanSchedule,
        on_delete=models.PROTECT,
        related_name="executions",
        null=True,
        blank=True,
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="action_plan_executions",
    )
    source_signal = models.ForeignKey(
        "signals.Signal",
        on_delete=models.PROTECT,
        related_name="action_plan_executions",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="action_plan_executions_created",
    )
    title = models.CharField(max_length=ACTION_PLAN_TITLE_MAX_LENGTH)
    description = models.TextField(
        max_length=ACTION_PLAN_DESCRIPTION_MAX_LENGTH,
        blank=True,
        default="",
    )
    pilot_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="pilot_action_plan_executions",
    )
    affected_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="affected_action_plan_executions",
        null=True,
        blank=True,
    )
    responsible_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="responsible_action_plan_executions",
        null=True,
        blank=True,
    )
    activity_subject = models.ForeignKey(
        "establishments.ActivitySubject",
        on_delete=models.PROTECT,
        related_name="action_plan_executions",
        null=True,
        blank=True,
    )
    requires_validation = models.BooleanField(default=True)
    use_shared_chronology = models.BooleanField(default=False)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    occurrence_date = models.DateField(null=True, blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    visible_from = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField()
    marked_done_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["establishment", "status", "visible_from", "last_activity_at"],
                name="ap_exec_feed_idx",
            ),
            models.Index(
                fields=["source_signal", "status"],
                name="ap_exec_signal_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(pilot_business_unit__isnull=False),
                name="action_plan_execution_pilot_business_unit_required",
            ),
        ]

    def __str__(self) -> str:
        return f"ActionPlanExecution {self.id} [{self.status}]"


class ActionPlanExecutionTeam(BaseModel):
    action_plan_execution = models.ForeignKey(
        ActionPlanExecution,
        on_delete=models.CASCADE,
        related_name="execution_teams",
    )
    business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="action_plan_execution_teams",
    )
    is_pilot = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["action_plan_execution", "business_unit"],
                name="uniq_action_plan_execution_team_business_unit",
            ),
            models.UniqueConstraint(
                fields=["action_plan_execution"],
                condition=Q(is_pilot=True),
                name="uniq_action_plan_execution_team_pilot",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"ActionPlanExecutionTeam execution={self.action_plan_execution_id} "
            f"bu={self.business_unit_id} pilot={self.is_pilot}"
        )


class ActionPlanAssignee(BaseModel):
    action_plan_execution = models.ForeignKey(
        ActionPlanExecution,
        on_delete=models.CASCADE,
        related_name="assignees",
    )
    execution_team = models.ForeignKey(
        ActionPlanExecutionTeam,
        on_delete=models.CASCADE,
        related_name="assignees",
    )
    membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="action_plan_execution_assignments",
    )
    start_at = models.DateTimeField(null=True, blank=True)
    visible_from = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["action_plan_execution", "membership"],
                name="uniq_action_plan_execution_assignee",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"ActionPlanAssignee execution={self.action_plan_execution_id} "
            f"membership={self.membership_id}"
        )


class ActionPlanExecutionTask(BaseModel):
    class Status(models.TextChoices):
        PENDING = TASK_STATUS_PENDING, "Pending"
        DONE = "done", "Done"
        SKIPPED = "skipped", "Skipped"
        OBSERVATION_CREATED = "observation_created", "Observation created"

    action_plan_execution = models.ForeignKey(
        ActionPlanExecution,
        on_delete=models.CASCADE,
        related_name="task_executions",
    )
    execution_team = models.ForeignKey(
        ActionPlanExecutionTeam,
        on_delete=models.CASCADE,
        related_name="task_executions",
    )
    action_plan_task = models.ForeignKey(
        ActionPlanTask,
        on_delete=models.SET_NULL,
        related_name="execution_tasks",
        null=True,
        blank=True,
    )
    task = models.CharField(max_length=ACTION_PLAN_TASK_MAX_LENGTH)
    position = models.PositiveIntegerField()
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    observation = models.ForeignKey(
        "observations.Observation",
        on_delete=models.SET_NULL,
        related_name="action_plan_execution_tasks",
        null=True,
        blank=True,
    )
    skipped_reason = models.CharField(
        max_length=ACTION_PLAN_SKIPPED_REASON_MAX_LENGTH,
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    skipped_at = models.DateTimeField(null=True, blank=True)
    observation_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["action_plan_execution", "position"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["action_plan_execution", "position"],
                name="uniq_action_plan_execution_task_position",
            ),
            models.CheckConstraint(
                condition=Q(
                    position__gte=MIN_TASK_POSITION,
                    position__lte=MAX_TASK_POSITION,
                ),
                name="action_plan_execution_task_position_bounds",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"ActionPlanExecutionTask execution={self.action_plan_execution_id} "
            f"pos={self.position} [{self.status}]"
        )
