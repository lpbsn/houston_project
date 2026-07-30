from __future__ import annotations

from datetime import datetime

from django.db.models import Sum

from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.timezone_utils import establishment_timezone
from houston.gamification.constants import badge_for_score
from houston.gamification.models import BadgeAward, GamificationSeason, PointTransaction


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
