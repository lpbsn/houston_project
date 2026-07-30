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
    badge_for_score,
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


def open_season(
    establishment: Establishment,
    *,
    month_start_local: date | datetime | None = None,
    rule_version: str | None = None,
) -> GamificationSeason:
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


def close_season(
    season: GamificationSeason,
    *,
    closed_at: datetime | None = None,
) -> GamificationSeason:
    """Close an active season and persist final badge awards.

    Caller should hold select_for_update on the season when racing with award_points.
    """
    if season.status != GamificationSeason.Status.ACTIVE:
        raise GamificationValidationError(
            "Only an active season can be closed.",
            code="gamification_season_not_active",
        )

    moment = closed_at or timezone.now()
    scores = (
        PointTransaction.objects.filter(season_id=season.id)
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
            establishment_id=season.establishment_id,
            season_id=season.id,
            badge_code=badge_code,
            points_total=total,
            awarded_at=moment,
        )

    season.status = GamificationSeason.Status.CLOSED
    season.closed_at = moment
    season.save(update_fields=["status", "closed_at", "updated_at"])
    return season


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

    starts_at, _ends_at = month_bounds_for_occurred_at(
        establishment=establishment,
        occurred_at=occurred_at,
    )
    target_month_start = starts_at.astimezone(
        establishment_timezone(establishment)
    ).date()

    # Serialize with close/award on the active season row when present.
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
    season_id: UUID,
    delta: int,
    reason_code: str,
    source_type: str,
    source_id: str,
    source_event_id: str,
    occurred_at: datetime,
) -> bool:
    return (
        existing.membership_id == membership_id
        and existing.establishment_id == establishment_id
        and existing.season_id == season_id
        and existing.delta == delta
        and existing.reason_code == reason_code
        and existing.source_type == source_type
        and existing.source_id == source_id
        and existing.source_event_id == source_event_id
        and existing.occurred_at == occurred_at
    )


def _resolve_existing_idempotent(
    *,
    idempotency_key: str,
    membership_id: UUID,
    establishment_id: UUID,
    season_id: UUID,
    delta: int,
    reason_code: str,
    source_type: str,
    source_id: str,
    source_event_id: str,
    occurred_at: datetime,
) -> PointTransaction:
    existing = PointTransaction.objects.get(idempotency_key=idempotency_key)
    if _payload_matches(
        existing,
        membership_id=membership_id,
        establishment_id=establishment_id,
        season_id=season_id,
        delta=delta,
        reason_code=reason_code,
        source_type=source_type,
        source_id=source_id,
        source_event_id=source_event_id,
        occurred_at=occurred_at,
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

    existing = PointTransaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        return _resolve_existing_idempotent(
            idempotency_key=idempotency_key,
            membership_id=membership.id,
            establishment_id=establishment.id,
            season_id=season.id,
            delta=delta,
            reason_code=reason_code,
            source_type=source_type,
            source_id=source_id_str,
            source_event_id=source_event_id_str,
            occurred_at=occurred_at,
        )

    sid = transaction.savepoint()
    try:
        created = PointTransaction.objects.create(
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
            metadata_safe=metadata_safe or {},
        )
    except IntegrityError:
        transaction.savepoint_rollback(sid)
        return _resolve_existing_idempotent(
            idempotency_key=idempotency_key,
            membership_id=membership.id,
            establishment_id=establishment.id,
            season_id=season.id,
            delta=delta,
            reason_code=reason_code,
            source_type=source_type,
            source_id=source_id_str,
            source_event_id=source_event_id_str,
            occurred_at=occurred_at,
        )
    transaction.savepoint_commit(sid)
    return created
