from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.timezone_utils import (
    establishment_local_date,
    establishment_timezone,
)
from houston.gamification.constants import (
    CURRENT_RULE_VERSION,
    DELTA_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
    DELTA_RECURRING_EXECUTION_DONE,
    DELTA_RESOLUTION_REQUEST_APPROVED,
    REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
    REASON_RECURRING_EXECUTION_DONE,
    REASON_RESOLUTION_REQUEST_APPROVED,
    SIGNAL_PROGRESS_REWARDS,
    SOURCE_TYPE_ACTION_PLAN_EXECUTION,
    SOURCE_TYPE_SIGNAL,
    SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST,
    badge_for_score,
    build_idempotency_key,
    sanitize_award_metadata_safe,
)
from houston.gamification.exceptions import (
    GamificationIdempotencyConflictError,
    GamificationSeasonClosedError,
    GamificationValidationError,
)
from houston.gamification.models import BadgeAward, GamificationSeason, PointTransaction
from houston.gamification.selectors import (
    get_active_season,
    get_season_by_starts_at,
    month_bounds_for_occurred_at,
)


def _lock_establishment(establishment_id: UUID) -> Establishment:
    """Return the establishment row locked for update (reloaded from DB)."""
    return Establishment.objects.select_for_update().get(pk=establishment_id)


def _month_start_date(value: date | datetime, *, establishment: Establishment) -> date:
    if isinstance(value, datetime):
        local = value.astimezone(establishment_timezone(establishment)).date()
        return local.replace(day=1)
    return value.replace(day=1)


def _bounds_for_month_start(
    *,
    establishment: Establishment,
    month_start_local: date,
) -> tuple[datetime, datetime]:
    tz = establishment_timezone(establishment)
    starts_at = datetime(
        month_start_local.year,
        month_start_local.month,
        1,
        0,
        0,
        0,
        tzinfo=tz,
    )
    if month_start_local.month == 12:
        ends_at = datetime(month_start_local.year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
    else:
        ends_at = datetime(
            month_start_local.year,
            month_start_local.month + 1,
            1,
            0,
            0,
            0,
            tzinfo=tz,
        )
    return starts_at, ends_at


@transaction.atomic
def open_season(
    establishment: Establishment,
    *,
    month_start_local: date | datetime | None = None,
    rule_version: str | None = None,
) -> GamificationSeason:
    establishment = _lock_establishment(establishment.id)

    if month_start_local is None:
        month_start = establishment_local_date(establishment=establishment).replace(day=1)
    else:
        month_start = _month_start_date(month_start_local, establishment=establishment)

    starts_at, ends_at = _bounds_for_month_start(
        establishment=establishment,
        month_start_local=month_start,
    )
    existing = get_season_by_starts_at(establishment, starts_at)
    if existing is not None:
        raise GamificationValidationError(
            "A season already exists for this establishment month.",
            code="gamification_season_already_exists",
        )

    active = get_active_season(establishment)
    if active is not None:
        raise GamificationValidationError(
            "An active season already exists for this establishment.",
            code="gamification_active_season_exists",
        )

    return GamificationSeason.objects.create(
        establishment=establishment,
        starts_at=starts_at,
        ends_at=ends_at,
        timezone=establishment.timezone,
        rule_version=rule_version or CURRENT_RULE_VERSION,
        status=GamificationSeason.Status.ACTIVE,
        closed_at=None,
    )


@transaction.atomic
def close_season(
    season: GamificationSeason,
    *,
    closed_at: datetime | None = None,
) -> GamificationSeason:
    """Close an active season and persist final badge awards."""
    _lock_establishment(season.establishment_id)
    locked = (
        GamificationSeason.objects.select_for_update()
        .filter(pk=season.pk)
        .get()
    )
    if locked.status != GamificationSeason.Status.ACTIVE:
        raise GamificationValidationError(
            "Only an active season can be closed.",
            code="gamification_season_not_active",
        )

    moment = closed_at or timezone.now()
    scores = (
        PointTransaction.objects.filter(season_id=locked.id)
        .values("membership_id")
        .annotate(total=Sum("delta"))
    )
    for row in scores:
        total = int(row["total"] or 0)
        badge_code = badge_for_score(total)
        if badge_code is None:
            continue
        BadgeAward.objects.create(
            membership_id=row["membership_id"],
            establishment_id=locked.establishment_id,
            season_id=locked.id,
            badge_code=badge_code,
            points_total=total,
            awarded_at=moment,
        )

    locked.status = GamificationSeason.Status.CLOSED
    locked.closed_at = moment
    locked.save(update_fields=["status", "closed_at", "updated_at"])
    return locked


def _close_and_open_next(
    *,
    establishment: Establishment,
    active: GamificationSeason,
    target_month_start: date,
    closed_at: datetime,
    rule_version: str | None = None,
) -> GamificationSeason:
    close_season(active, closed_at=closed_at)
    return open_season(
        establishment,
        month_start_local=target_month_start,
        rule_version=rule_version,
    )


@transaction.atomic
def ensure_season_for_occurred_at(
    establishment: Establishment,
    occurred_at: datetime,
    *,
    rule_version: str | None = None,
) -> GamificationSeason:
    """Ensure a season row exists for occurred_at's local civil month.

    Closes a due active season and opens the target month in the same atomic block.
    Never reopens or mutates a closed season.
    """
    if timezone.is_naive(occurred_at):
        raise GamificationValidationError(
            "occurred_at must be timezone-aware.",
            code="gamification_occurred_at_naive",
        )

    establishment = _lock_establishment(establishment.id)

    starts_at, _ends_at = month_bounds_for_occurred_at(
        establishment=establishment,
        occurred_at=occurred_at,
    )
    target_month_start = starts_at.astimezone(
        establishment_timezone(establishment)
    ).date()

    active = (
        GamificationSeason.objects.select_for_update()
        .filter(
            establishment_id=establishment.id,
            status=GamificationSeason.Status.ACTIVE,
        )
        .first()
    )

    covering = (
        GamificationSeason.objects.select_for_update()
        .filter(
            establishment_id=establishment.id,
            starts_at=starts_at,
        )
        .first()
    )
    if covering is not None:
        return covering

    if active is not None:
        if active.ends_at <= occurred_at:
            return _close_and_open_next(
                establishment=establishment,
                active=active,
                target_month_start=target_month_start,
                closed_at=occurred_at,
                rule_version=rule_version,
            )
        if occurred_at < active.starts_at:
            raise GamificationValidationError(
                "Cannot create a season for a past month after later seasons exist.",
                code="gamification_season_past_gap",
            )
        raise GamificationValidationError(
            "No season covers occurred_at and the active season is not due for rollover.",
            code="gamification_season_missing_for_occurred_at",
        )

    later_exists = GamificationSeason.objects.filter(
        establishment_id=establishment.id,
        starts_at__gt=starts_at,
    ).exists()
    if later_exists:
        raise GamificationValidationError(
            "Cannot create a season for a past month after later seasons exist.",
            code="gamification_season_past_gap",
        )

    return open_season(
        establishment,
        month_start_local=target_month_start,
        rule_version=rule_version,
    )


@transaction.atomic
def rollover_establishment_if_due(
    establishment: Establishment,
    *,
    now: datetime | None = None,
    rule_version: str | None = None,
) -> GamificationSeason | None:
    """Lock, close (with badges), and open the current local month in one atomic block."""
    moment = now or timezone.now()
    if timezone.is_naive(moment):
        raise GamificationValidationError(
            "now must be timezone-aware.",
            code="gamification_now_naive",
        )

    establishment = _lock_establishment(establishment.id)

    local_today = establishment_local_date(establishment=establishment, at=moment)
    target_month_start = local_today.replace(day=1)
    target_starts, _target_ends = _bounds_for_month_start(
        establishment=establishment,
        month_start_local=target_month_start,
    )

    active = (
        GamificationSeason.objects.select_for_update()
        .filter(
            establishment_id=establishment.id,
            status=GamificationSeason.Status.ACTIVE,
        )
        .first()
    )

    if active is not None:
        if active.starts_at == target_starts:
            return active
        if active.ends_at <= moment:
            return _close_and_open_next(
                establishment=establishment,
                active=active,
                target_month_start=target_month_start,
                closed_at=moment,
                rule_version=rule_version,
            )
        # Active season still covers `moment` but is not the target month — leave as-is.
        return active

    existing_target = get_season_by_starts_at(establishment, target_starts)
    if existing_target is not None:
        return existing_target

    return open_season(
        establishment,
        month_start_local=target_month_start,
        rule_version=rule_version,
    )


def _normalize_source_event_id(source_event_id: str | UUID | None) -> str:
    if source_event_id is None:
        return ""
    return str(source_event_id)


def _payload_matches(
    existing: PointTransaction,
    *,
    membership_id: UUID,
    establishment_id: UUID,
    delta: int,
    reason_code: str,
    source_type: str,
    source_id: str,
    source_event_id: str,
    occurred_at: datetime,
    season_id: UUID | None = None,
) -> bool:
    if not (
        existing.membership_id == membership_id
        and existing.establishment_id == establishment_id
        and existing.delta == delta
        and existing.reason_code == reason_code
        and existing.source_type == source_type
        and existing.source_id == source_id
        and existing.source_event_id == source_event_id
        and existing.occurred_at == occurred_at
    ):
        return False
    if season_id is not None:
        return existing.season_id == season_id
    season = existing.season
    return season.starts_at <= occurred_at < season.ends_at


def _resolve_existing_idempotent(
    *,
    idempotency_key: str,
    membership_id: UUID,
    establishment_id: UUID,
    delta: int,
    reason_code: str,
    source_type: str,
    source_id: str,
    source_event_id: str,
    occurred_at: datetime,
    season_id: UUID | None = None,
    existing: PointTransaction | None = None,
) -> PointTransaction:
    if existing is None:
        existing = (
            PointTransaction.objects.select_related("season")
            .get(idempotency_key=idempotency_key)
        )
    if _payload_matches(
        existing,
        membership_id=membership_id,
        establishment_id=establishment_id,
        delta=delta,
        reason_code=reason_code,
        source_type=source_type,
        source_id=source_id,
        source_event_id=source_event_id,
        occurred_at=occurred_at,
        season_id=season_id,
    ):
        return existing
    raise GamificationIdempotencyConflictError(
        "Idempotency key already used with a different payload.",
    )


@transaction.atomic
def award_points(
    *,
    membership: EstablishmentMembership,
    establishment: Establishment,
    delta: int,
    reason_code: str,
    source_type: str,
    source_id: str | UUID,
    occurred_at: datetime,
    idempotency_key: str,
    source_event_id: str | UUID | None = None,
    metadata_safe: dict[str, Any] | None = None,
) -> PointTransaction:
    if delta == 0:
        raise GamificationValidationError(
            "delta must be non-zero.",
            code="gamification_delta_zero",
        )
    if not idempotency_key:
        raise GamificationValidationError(
            "idempotency_key must be non-empty.",
            code="gamification_idempotency_key_empty",
        )
    if membership.establishment_id != establishment.id:
        raise GamificationValidationError(
            "Membership establishment does not match award establishment.",
            code="gamification_cross_establishment",
        )
    if timezone.is_naive(occurred_at):
        raise GamificationValidationError(
            "occurred_at must be timezone-aware.",
            code="gamification_occurred_at_naive",
        )

    source_id_str = str(source_id)
    source_event_id_str = _normalize_source_event_id(source_event_id)

    existing = (
        PointTransaction.objects.select_related("season")
        .filter(idempotency_key=idempotency_key)
        .first()
    )
    if existing is not None:
        return _resolve_existing_idempotent(
            idempotency_key=idempotency_key,
            membership_id=membership.id,
            establishment_id=establishment.id,
            delta=delta,
            reason_code=reason_code,
            source_type=source_type,
            source_id=source_id_str,
            source_event_id=source_event_id_str,
            occurred_at=occurred_at,
            existing=existing,
        )

    season = ensure_season_for_occurred_at(establishment, occurred_at)
    season = (
        GamificationSeason.objects.select_for_update()
        .filter(pk=season.pk)
        .get()
    )

    if season.status != GamificationSeason.Status.ACTIVE:
        raise GamificationSeasonClosedError(
            "Cannot award points on a closed season.",
        )

    if season.establishment_id != establishment.id:
        raise GamificationValidationError(
            "Season establishment does not match award establishment.",
            code="gamification_cross_establishment",
        )
    if not (season.starts_at <= occurred_at < season.ends_at):
        raise GamificationValidationError(
            "occurred_at is outside the resolved season window.",
            code="gamification_occurred_at_outside_season",
        )

    try:
        with transaction.atomic():
            return PointTransaction.objects.create(
                membership=membership,
                establishment=establishment,
                season=season,
                delta=delta,
                reason_code=reason_code,
                source_type=source_type,
                source_id=source_id_str,
                source_event_id=source_event_id_str,
                rule_version=season.rule_version,
                occurred_at=occurred_at,
                idempotency_key=idempotency_key,
                metadata_safe=sanitize_award_metadata_safe(metadata_safe),
            )
    except IntegrityError:
        raced = (
            PointTransaction.objects.select_related("season")
            .filter(idempotency_key=idempotency_key)
            .first()
        )
        if raced is None:
            raise
        return _resolve_existing_idempotent(
            idempotency_key=idempotency_key,
            membership_id=membership.id,
            establishment_id=establishment.id,
            delta=delta,
            reason_code=reason_code,
            source_type=source_type,
            source_id=source_id_str,
            source_event_id=source_event_id_str,
            occurred_at=occurred_at,
            season_id=season.id,
            existing=raced,
        )


def award_signal_progress_points(
    *,
    signal,
    lifecycle_event,
) -> None:
    """Award Signal progress points for the first eligible lifecycle of each type.

    Must run in the same transaction.atomic as the Signal status transition and
    lifecycle write. Non-rewarded event types and non-first episodes are no-ops.
    """
    from houston.signals.models import SignalLifecycleEvent, SignalSourceObservation

    reward = SIGNAL_PROGRESS_REWARDS.get(lifecycle_event.event_type)
    if reward is None:
        return
    reason_code, delta = reward

    first_id = (
        SignalLifecycleEvent.objects.filter(
            signal_id=signal.id,
            event_type=lifecycle_event.event_type,
        )
        .order_by("occurred_at", "id")
        .values_list("id", flat=True)
        .first()
    )
    if first_id != lifecycle_event.id:
        return

    eligible_link_types = (
        SignalSourceObservation.LinkType.CREATED_FROM,
        SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )
    membership_ids = (
        SignalSourceObservation.objects.filter(
            signal_id=signal.id,
            link_type__in=eligible_link_types,
            created_at__lte=lifecycle_event.occurred_at,
            observation__submitted_by_membership__establishment_id=signal.establishment_id,
        )
        .values_list("observation__submitted_by_membership_id", flat=True)
        .distinct()
    )
    memberships = EstablishmentMembership.objects.filter(id__in=membership_ids)
    if not memberships:
        return

    establishment = Establishment.objects.get(pk=signal.establishment_id)
    for membership in memberships:
        award_points(
            membership=membership,
            establishment=establishment,
            delta=delta,
            reason_code=reason_code,
            source_type=SOURCE_TYPE_SIGNAL,
            source_id=signal.id,
            occurred_at=lifecycle_event.occurred_at,
            idempotency_key=build_idempotency_key(
                reason_code=reason_code,
                subject_id=signal.id,
                membership_id=membership.id,
            ),
            source_event_id=lifecycle_event.id,
        )


def _action_plan_execution_assigned_membership_ids(*, execution) -> set[UUID]:
    from houston.action_plans.models import ActionPlanAssignee, ActionPlanExecutionTask

    direct_ids = ActionPlanAssignee.objects.filter(
        action_plan_execution_id=execution.id,
    ).values_list("membership_id", flat=True)
    task_ids = ActionPlanExecutionTask.objects.filter(
        action_plan_execution_id=execution.id,
        assigned_membership_id__isnull=False,
    ).values_list("assigned_membership_id", flat=True)
    return set(direct_ids) | set(task_ids)


def _canonical_recurring_execution_done_lifecycle_event(*, execution):
    from houston.action_plans.constants import EXECUTION_LIFECYCLE_EVENT_MARKED_DONE
    from houston.action_plans.models import ActionPlanExecutionLifecycleEvent

    return (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution_id=execution.id,
            event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
        )
        .order_by("occurred_at", "id")
        .first()
    )


def _recurring_execution_done_participant_memberships(
    *,
    execution,
    canonical_lifecycle_event,
) -> list[EstablishmentMembership]:
    from houston.action_plans.models import ActionPlanAssignee, ActionPlanExecutionTask
    from houston.comments.models import CommentMention

    direct_ids = ActionPlanAssignee.objects.filter(
        action_plan_execution_id=execution.id,
    ).values_list("membership_id", flat=True)
    task_ids = ActionPlanExecutionTask.objects.filter(
        action_plan_execution_id=execution.id,
        assigned_membership_id__isnull=False,
    ).values_list("assigned_membership_id", flat=True)
    mention_ids = CommentMention.objects.filter(
        comment__action_plan_execution_id=execution.id,
        comment__created_at__lte=canonical_lifecycle_event.occurred_at,
    ).values_list("mentioned_membership_id", flat=True)
    membership_ids = set(direct_ids) | set(task_ids) | set(mention_ids)

    if execution.action_plan_id is not None:
        membership_ids.discard(execution.action_plan.created_by_id)
    if not membership_ids:
        return []

    return list(
        EstablishmentMembership.objects.filter(
            id__in=membership_ids,
            establishment_id=execution.establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
        ).order_by("id")
    )


def award_recurring_execution_done_points(*, execution) -> None:
    """Award +2 to eligible participants when a recurring execution is done.

    Must run in the same transaction.atomic as the in_progress → done transition
    and marked_done lifecycle write.
    """
    from houston.action_plans.constants import EXECUTION_STATUS_DONE

    if execution.status != EXECUTION_STATUS_DONE:
        return
    if execution.action_plan_schedule_id is None:
        return
    if execution.requires_validation:
        return

    canonical_lifecycle_event = _canonical_recurring_execution_done_lifecycle_event(
        execution=execution,
    )
    if canonical_lifecycle_event is None:
        raise GamificationValidationError(
            "Recurring action plan execution is done without a canonical "
            "marked_done lifecycle event.",
            code="gamification_recurring_execution_done_lifecycle_missing",
        )

    memberships = _recurring_execution_done_participant_memberships(
        execution=execution,
        canonical_lifecycle_event=canonical_lifecycle_event,
    )
    if not memberships:
        return

    establishment = Establishment.objects.get(pk=execution.establishment_id)
    for membership in memberships:
        award_points(
            membership=membership,
            establishment=establishment,
            delta=DELTA_RECURRING_EXECUTION_DONE,
            reason_code=REASON_RECURRING_EXECUTION_DONE,
            source_type=SOURCE_TYPE_ACTION_PLAN_EXECUTION,
            source_id=execution.id,
            occurred_at=canonical_lifecycle_event.occurred_at,
            idempotency_key=build_idempotency_key(
                reason_code=REASON_RECURRING_EXECUTION_DONE,
                subject_id=execution.id,
                membership_id=membership.id,
            ),
            source_event_id=canonical_lifecycle_event.id,
        )


def _action_plan_execution_started_is_eligible(*, execution) -> bool:
    assigned_membership_ids = _action_plan_execution_assigned_membership_ids(
        execution=execution,
    )
    if not assigned_membership_ids:
        return False

    creator_id = execution.created_by_id
    if execution.source_signal_id is not None:
        return any(membership_id != creator_id for membership_id in assigned_membership_ids)
    return creator_id not in assigned_membership_ids


def _canonical_action_plan_execution_started_lifecycle_event(*, execution):
    from houston.action_plans.constants import (
        EXECUTION_LIFECYCLE_EVENT_CREATED,
        EXECUTION_LIFECYCLE_EVENT_STARTED,
        EXECUTION_STATUS_IN_PROGRESS,
    )

    created = (
        execution.lifecycle_events.filter(
            event_type=EXECUTION_LIFECYCLE_EVENT_CREATED,
            metadata_safe__initial_status=EXECUTION_STATUS_IN_PROGRESS,
        )
        .order_by("occurred_at", "id")
        .first()
    )
    if created is not None:
        return created

    return (
        execution.lifecycle_events.filter(event_type=EXECUTION_LIFECYCLE_EVENT_STARTED)
        .order_by("occurred_at", "id")
        .first()
    )


def award_action_plan_execution_started_points(
    *,
    execution,
    lifecycle_event,
) -> None:
    """Award +2 to the execution creator when an eligible execution starts.

    Must run in the same transaction.atomic as the execution creation or
    scheduled → in_progress transition. Reopens/reactivations are intentionally
    not rewarded.
    """
    from houston.action_plans.constants import EXECUTION_STATUS_IN_PROGRESS

    if execution.status != EXECUTION_STATUS_IN_PROGRESS:
        return

    canonical_lifecycle_event = _canonical_action_plan_execution_started_lifecycle_event(
        execution=execution,
    )
    if canonical_lifecycle_event is None:
        raise GamificationValidationError(
            "Action plan execution has started without a canonical lifecycle event.",
            code="gamification_action_plan_execution_started_lifecycle_missing",
        )

    if not _action_plan_execution_started_is_eligible(execution=execution):
        return

    establishment = Establishment.objects.get(pk=execution.establishment_id)
    award_points(
        membership=execution.created_by,
        establishment=establishment,
        delta=DELTA_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
        reason_code=REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
        source_type=SOURCE_TYPE_ACTION_PLAN_EXECUTION,
        source_id=execution.id,
        occurred_at=canonical_lifecycle_event.occurred_at,
        idempotency_key=build_idempotency_key(
            reason_code=REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
            subject_id=execution.id,
            membership_id=execution.created_by_id,
        ),
        source_event_id=canonical_lifecycle_event.id,
    )


def award_resolution_request_approved_points(*, resolution_request) -> None:
    """Award +2 to the requester for an approved resolution request.

    Must run in the same transaction.atomic as the pending → approved
    transition. The approved request is the source of truth (not signal.resolved).
    """
    from houston.signals.models import SignalResolutionRequest

    if resolution_request.status != SignalResolutionRequest.Status.APPROVED:
        raise GamificationValidationError(
            "Resolution request must be approved to award points.",
            code="gamification_resolution_request_not_approved",
        )
    if resolution_request.reviewed_at is None:
        raise GamificationValidationError(
            "Resolution request reviewed_at is required to award points.",
            code="gamification_resolution_request_reviewed_at_missing",
        )

    membership = resolution_request.requested_by_membership
    establishment = Establishment.objects.get(
        pk=resolution_request.signal.establishment_id,
    )
    award_points(
        membership=membership,
        establishment=establishment,
        delta=DELTA_RESOLUTION_REQUEST_APPROVED,
        reason_code=REASON_RESOLUTION_REQUEST_APPROVED,
        source_type=SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST,
        source_id=resolution_request.id,
        occurred_at=resolution_request.reviewed_at,
        idempotency_key=build_idempotency_key(
            reason_code=REASON_RESOLUTION_REQUEST_APPROVED,
            subject_id=resolution_request.id,
            membership_id=membership.id,
        ),
        source_event_id=resolution_request.id,
    )
