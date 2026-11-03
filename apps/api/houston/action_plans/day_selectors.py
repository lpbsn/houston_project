"""Personal work queue; never equate managerial visibility with assignment."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Case, F, IntegerField, Q, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from houston.action_plans.constants import EXECUTION_STATUS_IN_PROGRESS
from houston.action_plans.models import ActionPlanExecutionTask
from houston.action_plans.selectors import action_plan_execution_feed_queryset


def my_day_tasks(*, membership, now=None):
    now = now or timezone.now()
    zone = ZoneInfo(membership.establishment.timezone)
    today = now.astimezone(zone).date()
    tomorrow = datetime.combine(today + timedelta(days=1), time.min, tzinfo=zone)
    day_start = datetime.combine(today, time.min, tzinfo=zone)
    scope_ids = membership.scope_links.values_list("business_unit_id", flat=True)
    # Named assignments take precedence. Unassigned work remains shared within
    # the member's pole when they are assigned to the plan or contribute to it.
    shared = (
        Q(assigned_membership__isnull=True)
        & Q(
            execution_team__business_unit_id__in=scope_ids,
        )
        & (
            Q(action_plan_execution__assignees__membership_id=membership.id)
            | ~Q(
                execution_team__business_unit_id=F("action_plan_execution__pilot_business_unit_id")
            )
        )
    )
    visible = action_plan_execution_feed_queryset(
        membership=membership, view_mode="personal", now=now
    )
    tasks = (
        ActionPlanExecutionTask.objects.filter(
            action_plan_execution_id__in=visible.values("id"),
            action_plan_execution__establishment_id=membership.establishment_id,
            action_plan_execution__status=EXECUTION_STATUS_IN_PROGRESS,
            status=ActionPlanExecutionTask.Status.PENDING,
        )
        .filter(Q(assigned_membership_id=membership.id) | shared)
        .annotate(due_at=Coalesce("deadline_at", "action_plan_execution__end_at"))
    )
    # A task's explicit deadline is timed. An inherited all-day plan deadline
    # becomes late only on the following local day.
    inherited_all_day = Q(deadline_at__isnull=True, action_plan_execution__all_day=True)
    overdue = (inherited_all_day & Q(due_at__lt=day_start)) | (
        ~inherited_all_day & Q(due_at__lt=now)
    )
    return (
        tasks.annotate(
            day_bucket=Case(
                When(due_at__isnull=True, then=Value(3)),
                When(overdue, then=Value(0)),
                When(due_at__lt=tomorrow, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            ),
        )
        .select_related("action_plan_execution", "execution_team__business_unit")
        .distinct()
        .order_by("day_bucket", F("due_at").asc(nulls_last=True), "id")
    )
