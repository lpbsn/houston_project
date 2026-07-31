from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db.models import Q, Sum
from django.utils import timezone

from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.timezone_utils import establishment_timezone
from houston.gamification.constants import (
    BADGE_DISPLAY_ORDER,
    BADGE_LABELS,
    BADGE_THRESHOLDS,
    EXPOSABLE_SOURCE_TYPES,
    POINTS_RULE_CATALOG,
    REASON_LABELS_FR,
    UNKNOWN_REASON_LABEL,
    badge_for_score,
)
from houston.gamification.models import BadgeAward, GamificationSeason, PointTransaction
from houston.gamification.transaction_cursor import (
    decode_transaction_cursor,
    encode_transaction_cursor,
)


@dataclass(frozen=True)
class PointTransactionsPage:
    items: list[PointTransaction]
    next_cursor: str | None
    has_more: bool


def get_active_season(establishment: Establishment) -> GamificationSeason | None:
    return (
        GamificationSeason.objects.filter(
            establishment_id=establishment.id,
            status=GamificationSeason.Status.ACTIVE,
        )
        .order_by("-starts_at")
        .first()
    )


def get_season_for_occurred_at(
    establishment: Establishment,
    occurred_at: datetime,
) -> GamificationSeason | None:
    return (
        GamificationSeason.objects.filter(
            establishment_id=establishment.id,
            starts_at__lte=occurred_at,
            ends_at__gt=occurred_at,
        )
        .order_by("-starts_at")
        .first()
    )


def get_season_by_starts_at(
    establishment: Establishment,
    starts_at: datetime,
) -> GamificationSeason | None:
    return GamificationSeason.objects.filter(
        establishment_id=establishment.id,
        starts_at=starts_at,
    ).first()


def sum_points_for_membership_season(
    membership: EstablishmentMembership,
    season: GamificationSeason,
) -> int:
    total = (
        PointTransaction.objects.filter(
            membership_id=membership.id,
            season_id=season.id,
        ).aggregate(total=Sum("delta"))["total"]
    )
    return int(total or 0)


def provisional_badge_for_membership_season(
    membership: EstablishmentMembership,
    season: GamificationSeason,
) -> str | None:
    return badge_for_score(sum_points_for_membership_season(membership, season))


def list_badge_awards_for_season(season: GamificationSeason):
    return BadgeAward.objects.filter(season_id=season.id).order_by("awarded_at", "id")


def get_badge_award(
    membership: EstablishmentMembership,
    season: GamificationSeason,
) -> BadgeAward | None:
    return BadgeAward.objects.filter(
        membership_id=membership.id,
        season_id=season.id,
    ).first()


def month_bounds_for_occurred_at(
    *,
    establishment: Establishment,
    occurred_at: datetime,
) -> tuple[datetime, datetime]:
    """Return [starts_at, ends_at) for the civil month of occurred_at in establishment TZ."""
    tz = establishment_timezone(establishment)
    local = occurred_at.astimezone(tz)
    starts_at = datetime(local.year, local.month, 1, 0, 0, 0, tzinfo=tz)
    if local.month == 12:
        ends_at = datetime(local.year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
    else:
        ends_at = datetime(local.year, local.month + 1, 1, 0, 0, 0, tzinfo=tz)
    return starts_at, ends_at


def reason_label(reason_code: str) -> str:
    return REASON_LABELS_FR.get(reason_code, UNKNOWN_REASON_LABEL)


def grade_rules_payload() -> list[dict]:
    return [
        {
            "code": badge_code,
            "label": BADGE_LABELS[badge_code],
            "threshold": BADGE_THRESHOLDS[badge_code],
        }
        for badge_code in BADGE_DISPLAY_ORDER
    ]


def points_rules_payload() -> list[dict]:
    return [dict(rule) for rule in POINTS_RULE_CATALOG]


def gamification_rules_payload() -> dict:
    return {
        "grades": grade_rules_payload(),
        "points": points_rules_payload(),
    }


def next_badge_for_score(score: int) -> str | None:
    for badge_code in BADGE_DISPLAY_ORDER:
        if score < BADGE_THRESHOLDS[badge_code]:
            return badge_code
    return None


def grade_progress_payload(score: int) -> dict:
    grade = badge_for_score(score)
    next_grade = next_badge_for_score(score)
    if next_grade is None:
        return {
            "grade": grade,
            "next_grade": None,
            "next_grade_threshold": None,
            "points_to_next_grade": 0,
            "progress_ratio": 1,
            "is_max_grade": True,
        }

    threshold = BADGE_THRESHOLDS[next_grade]
    progress = max(0, min(score / threshold, 1))
    return {
        "grade": grade,
        "next_grade": next_grade,
        "next_grade_threshold": threshold,
        "points_to_next_grade": max(threshold - score, 0),
        "progress_ratio": round(progress, 4),
        "is_max_grade": False,
    }


def _season_payload(
    *,
    season_id,
    starts_at: datetime,
    ends_at: datetime,
    status: str,
    closed_at: datetime | None,
    score: int,
    grade: str | None,
) -> dict:
    return {
        "season_id": season_id,
        "period": {
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        "status": status,
        "score": score,
        "grade": grade,
        "closed_at": closed_at,
    }


def _closed_grade_for_membership_season(
    *,
    membership: EstablishmentMembership,
    season: GamificationSeason,
) -> str | None:
    award = get_badge_award(membership, season)
    if award is None:
        return None
    return award.badge_code


def _grade_for_membership_season(
    *,
    membership: EstablishmentMembership,
    season: GamificationSeason,
    score: int,
) -> str | None:
    if season.status == GamificationSeason.Status.CLOSED:
        return _closed_grade_for_membership_season(membership=membership, season=season)
    return badge_for_score(score)


def current_gamification_summary(
    *,
    membership: EstablishmentMembership,
    establishment: Establishment,
    now: datetime | None = None,
) -> dict:
    moment = now or timezone.now()
    starts_at, ends_at = month_bounds_for_occurred_at(
        establishment=establishment,
        occurred_at=moment,
    )
    season = get_season_by_starts_at(establishment, starts_at)

    score = 0
    season_id = None
    if season is not None:
        score = sum_points_for_membership_season(membership, season)
        season_id = season.id

    return {
        "season_id": season_id,
        "period": {
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        "score": score,
        **grade_progress_payload(score),
    }


def list_personal_gamification_seasons(
    *,
    membership: EstablishmentMembership,
    establishment: Establishment,
    now: datetime | None = None,
) -> list[dict]:
    moment = now or timezone.now()
    current_starts_at, current_ends_at = month_bounds_for_occurred_at(
        establishment=establishment,
        occurred_at=moment,
    )
    seasons = list(
        GamificationSeason.objects.filter(establishment_id=establishment.id).order_by(
            "-starts_at",
            "-id",
        )
    )
    season_ids = [season.id for season in seasons]
    totals_by_season_id = {
        row["season_id"]: int(row["total"] or 0)
        for row in PointTransaction.objects.filter(
            membership_id=membership.id,
            season_id__in=season_ids,
        )
        .values("season_id")
        .annotate(total=Sum("delta"))
    }
    awards_by_season_id = {
        award.season_id: award
        for award in BadgeAward.objects.filter(
            membership_id=membership.id,
            season_id__in=season_ids,
        )
    }

    items: list[dict] = []
    has_current_month = False
    for season in seasons:
        if season.starts_at == current_starts_at:
            has_current_month = True
        score = totals_by_season_id.get(season.id, 0)
        if season.status == GamificationSeason.Status.CLOSED:
            award = awards_by_season_id.get(season.id)
            grade = None if award is None else award.badge_code
        else:
            grade = badge_for_score(score)
        items.append(
            _season_payload(
                season_id=season.id,
                starts_at=season.starts_at,
                ends_at=season.ends_at,
                status=season.status,
                closed_at=season.closed_at,
                score=score,
                grade=grade,
            )
        )

    if not has_current_month:
        items.append(
            _season_payload(
                season_id=None,
                starts_at=current_starts_at,
                ends_at=current_ends_at,
                status=GamificationSeason.Status.ACTIVE,
                closed_at=None,
                score=0,
                grade=None,
            )
        )
        items.sort(key=lambda item: item["period"]["starts_at"], reverse=True)

    return items


def gamification_overview_payload(
    *,
    membership: EstablishmentMembership,
    establishment: Establishment,
    now: datetime | None = None,
) -> dict:
    return {
        "current": current_gamification_summary(
            membership=membership,
            establishment=establishment,
            now=now,
        ),
        "rules": gamification_rules_payload(),
        "seasons": {
            "items": list_personal_gamification_seasons(
                membership=membership,
                establishment=establishment,
                now=now,
            )
        },
    }


def point_transactions_queryset_for_membership(
    *,
    membership: EstablishmentMembership,
    establishment_id: UUID,
    season_id: UUID | None = None,
):
    queryset = (
        PointTransaction.objects.filter(
            membership_id=membership.id,
            establishment_id=establishment_id,
        )
        .select_related("season")
        .order_by("-occurred_at", "-id")
    )
    if season_id is not None:
        queryset = queryset.filter(season_id=season_id)
    return queryset


def build_point_transactions_page(
    *,
    membership: EstablishmentMembership,
    establishment_id: UUID,
    season_id: UUID | None,
    cursor: str | None,
    page_size: int,
) -> PointTransactionsPage:
    queryset = point_transactions_queryset_for_membership(
        membership=membership,
        establishment_id=establishment_id,
        season_id=season_id,
    )
    cursor_values = decode_transaction_cursor(
        cursor,
        expected_season_id=season_id,
    )
    if cursor_values is not None:
        queryset = queryset.filter(
            Q(occurred_at__lt=cursor_values.occurred_at)
            | Q(
                occurred_at=cursor_values.occurred_at,
                id__lt=cursor_values.transaction_id,
            )
        )

    rows = list(queryset[: page_size + 1])
    has_more = len(rows) > page_size
    page = rows[:page_size]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_transaction_cursor(
            occurred_at=last.occurred_at,
            transaction_id=last.id,
            season_id=season_id,
        )

    return PointTransactionsPage(
        items=page,
        next_cursor=next_cursor,
        has_more=has_more,
    )


def serialize_transaction_source(transaction: PointTransaction) -> dict | None:
    if transaction.source_type not in EXPOSABLE_SOURCE_TYPES:
        return None
    return {
        "type": transaction.source_type,
        "id": transaction.source_id,
    }


def serialize_point_transaction(transaction: PointTransaction) -> dict:
    return {
        "id": transaction.id,
        "occurred_at": transaction.occurred_at,
        "delta": transaction.delta,
        "reason_code": transaction.reason_code,
        "reason_label": reason_label(transaction.reason_code),
        "season": {
            "season_id": transaction.season_id,
            "period": {
                "starts_at": transaction.season.starts_at,
                "ends_at": transaction.season.ends_at,
            },
            "status": transaction.season.status,
        },
        "source": serialize_transaction_source(transaction),
        "is_correction": transaction.delta < 0,
        "is_reversal": transaction.reversed_transaction_id is not None,
        "reversed_transaction_id": transaction.reversed_transaction_id,
    }
