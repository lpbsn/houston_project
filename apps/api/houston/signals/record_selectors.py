"""The evolving field record is a Signal, not a second copy of operational data."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.selectors import action_plan_execution_feed_queryset
from houston.establishments.models import EstablishmentMembership, MembershipScope
from houston.signals.constants import FEED_SIGNAL_STATUSES
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.selectors import resolve_signal_alias_id, signal_read_visibility_q


def record_stage(signal):
    if signal.status in (Signal.Status.RESOLVED, Signal.Status.CANCELED):
        return "closed"
    if signal.review_requested_at is not None:
        return "review"
    if signal.status == Signal.Status.IN_PROGRESS:
        return "doing"
    return "todo"


def stage_filter(stage):
    closed = Q(status__in=[Signal.Status.RESOLVED, Signal.Status.CANCELED])
    if stage == "closed":
        return closed
    if stage == "review":
        return ~closed & Q(review_requested_at__isnull=False)
    if stage == "doing":
        return Q(status=Signal.Status.IN_PROGRESS, review_requested_at__isnull=True)
    if stage == "todo":
        return Q(
            status__in=[Signal.Status.OPEN, Signal.Status.INTERESTING],
            review_requested_at__isnull=True,
        )
    return Q()


def record_queryset(membership):
    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return Signal.objects.none()
    base = Signal.objects.filter(
        establishment_id=membership.establishment_id, merged_into__isnull=True
    )
    reported = SignalSourceObservation.objects.filter(
        signal_id=OuterRef("pk"),
        observation__submitted_by_membership=membership,
        observation__establishment_id=membership.establishment_id,
    )
    visible = signal_read_visibility_q(
        membership=membership,
        view_mode="general",
        statuses=FEED_SIGNAL_STATUSES,
    )
    if membership.role == EstablishmentMembership.Role.STAFF:
        visible &= ~Q(record_kind=Signal.RecordKind.INTAKE)
    # A project never broadens access to the restricted execution it contains.
    executions = action_plan_execution_feed_queryset(membership=membership, view_mode="general")
    project_access = Q(work_links__execution_id__in=executions.values("pk"))
    if membership.role in ("owner", "director"):
        project_access = Q()
    else:
        # Ownership alone must not retain a revoked scope through a cached membership.
        scoped_units = MembershipScope.objects.filter(
            membership_id=membership.id,
            business_unit__establishment_id=membership.establishment_id,
            business_unit__active=True,
        ).values("business_unit_id")
        owner_scope = Q(responsible_business_unit_id__in=scoped_units) | Q(
            affected_business_unit_id__in=scoped_units
        )
        project_access |= Q(owner_membership=membership) & owner_scope
        if membership.role == "manager":
            project_access |= Q(responsible_business_unit_id__in=scoped_units)
    return (
        base.annotate(is_reporter=Exists(reported))
        .filter(
            (visible & ~Q(record_kind=Signal.RecordKind.PROJECT))
            | (Q(record_kind=Signal.RecordKind.PROJECT) & project_access)
            | Q(is_reporter=True)
        )
        .select_related(
            "establishment",
            "owner_membership__user",
            "waiting_for_membership__user",
            "affected_business_unit",
            "responsible_business_unit",
        )
        .annotate(
            observation_count=Count("source_observation_links__observation_id", distinct=True)
        )
        .distinct()
    )


def get_record(membership, record_id):
    canonical_id = resolve_signal_alias_id(
        establishment_id=membership.establishment_id, signal_id=record_id
    )
    return record_queryset(membership).filter(pk=canonical_id).first()


def linked_executions(signal):
    return (
        ActionPlanExecution.objects.filter(establishment_id=signal.establishment_id)
        .filter(Q(source_signal_id=signal.id) | Q(record_links__signal_id=signal.id))
        .distinct()
    )


def calendar_dates(signal, *, today=None):
    if signal.due_on is None:
        return None
    zone = ZoneInfo(signal.establishment.timezone)
    today = today or timezone.now().astimezone(zone).date()
    closed_at = signal.resolved_at or signal.canceled_at
    start = signal.created_at.astimezone(zone).date()
    end = closed_at.astimezone(zone).date() if closed_at else max(signal.due_on, today)
    # A future, on-time record stops at its due date; an overdue record extends to today.
    return {
        "start": start,
        "end": max(start, end),
        "due": signal.due_on,
        "overdue": not closed_at and signal.due_on < today,
    }


def calendar_filter(*, start_on, end_on, zone):
    start_at = datetime.combine(start_on, time.min, tzinfo=ZoneInfo(zone))
    end_exclusive = datetime.combine(end_on, time.max, tzinfo=ZoneInfo(zone))
    return Q(due_on__isnull=False, created_at__lte=end_exclusive) & (
        Q(resolved_at__gte=start_at)
        | Q(canceled_at__gte=start_at)
        | Q(status__in=["open", "interesting", "in_progress"])
    )


def day_records(actor, rows):
    from houston.action_plans.models import ActionPlanExecutionTask
    from houston.establishments.membership_scope import membership_business_unit_scope_ids

    tasks = ActionPlanExecutionTask.objects.filter(
        action_plan_execution__record_links__signal_id=OuterRef("pk"),
        assigned_membership=actor,
        status="pending",
        action_plan_execution__status="in_progress",
    )
    owned = Q(owner_membership=actor, has_own_tasks=False)
    review = Q(pk__in=[])
    if actor.role in ("owner", "director"):
        review = Q(review_requested_at__isnull=False)
    elif actor.role == "manager":
        review = Q(
            review_requested_at__isnull=False,
            responsible_business_unit_id__in=membership_business_unit_scope_ids(actor),
        )
    return (
        rows.annotate(has_own_tasks=Exists(tasks))
        .exclude(status__in=["resolved", "canceled"])
        .filter(owned | review)
    )
