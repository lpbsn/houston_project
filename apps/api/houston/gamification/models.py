from __future__ import annotations

from django.db import models
from django.db.models import Q

from houston.core.models import BaseModel
from houston.establishments.models import ESTABLISHMENT_TIMEZONE_MAX_LENGTH
from houston.gamification.constants import (
    BADGE_CODE_BRONZE,
    BADGE_CODE_GOLD,
    BADGE_CODE_MAX_LENGTH,
    BADGE_CODE_SILVER,
    CURRENT_RULE_VERSION,
    IDEMPOTENCY_KEY_MAX_LENGTH,
    REASON_CODE_MAX_LENGTH,
    RULE_VERSION_MAX_LENGTH,
    SEASON_STATUS_ACTIVE,
    SEASON_STATUS_CLOSED,
    SOURCE_EVENT_ID_MAX_LENGTH,
    SOURCE_ID_MAX_LENGTH,
    SOURCE_TYPE_MAX_LENGTH,
)


class GamificationSeason(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = SEASON_STATUS_ACTIVE, "Active"
        CLOSED = SEASON_STATUS_CLOSED, "Closed"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="gamification_seasons",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    timezone = models.CharField(max_length=ESTABLISHMENT_TIMEZONE_MAX_LENGTH)
    rule_version = models.CharField(
        max_length=RULE_VERSION_MAX_LENGTH,
        default=CURRENT_RULE_VERSION,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["establishment", "status"]),
            models.Index(fields=["establishment", "starts_at", "ends_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["establishment", "starts_at"],
                name="gamification_season_estab_starts_uniq",
            ),
            models.UniqueConstraint(
                fields=["establishment"],
                condition=Q(status=SEASON_STATUS_ACTIVE),
                name="gamification_season_one_active_per_estab",
            ),
            models.CheckConstraint(
                condition=Q(starts_at__lt=models.F("ends_at")),
                name="gamification_season_starts_before_ends",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status=SEASON_STATUS_ACTIVE, closed_at__isnull=True)
                    | Q(status=SEASON_STATUS_CLOSED, closed_at__isnull=False)
                ),
                name="gamification_season_status_closed_at",
            ),
        ]

    def __str__(self) -> str:
        return f"GamificationSeason {self.id} [{self.status}]"


class PointTransaction(BaseModel):
    """Append-only points ledger. Never update or delete rows from domain services."""

    membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="point_transactions",
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="point_transactions",
    )
    season = models.ForeignKey(
        GamificationSeason,
        on_delete=models.PROTECT,
        related_name="point_transactions",
    )
    delta = models.IntegerField()
    reason_code = models.CharField(max_length=REASON_CODE_MAX_LENGTH)
    source_type = models.CharField(max_length=SOURCE_TYPE_MAX_LENGTH)
    source_id = models.CharField(max_length=SOURCE_ID_MAX_LENGTH)
    source_event_id = models.CharField(
        max_length=SOURCE_EVENT_ID_MAX_LENGTH,
        blank=True,
        default="",
    )
    rule_version = models.CharField(max_length=RULE_VERSION_MAX_LENGTH)
    occurred_at = models.DateTimeField()
    idempotency_key = models.CharField(max_length=IDEMPOTENCY_KEY_MAX_LENGTH)
    reversed_transaction = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="reversals",
        null=True,
        blank=True,
    )
    metadata_safe = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["season", "membership"]),
            models.Index(fields=["establishment", "occurred_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                name="gamification_point_tx_idempotency_uniq",
            ),
            models.CheckConstraint(
                condition=~Q(delta=0),
                name="gamification_point_tx_delta_nonzero",
            ),
            models.CheckConstraint(
                condition=~Q(idempotency_key=""),
                name="gamification_point_tx_idempotency_nonempty",
            ),
        ]

    def __str__(self) -> str:
        return f"PointTransaction {self.id} [{self.delta}]"


class BadgeAward(BaseModel):
    class BadgeCode(models.TextChoices):
        BRONZE = BADGE_CODE_BRONZE, "Bronze"
        SILVER = BADGE_CODE_SILVER, "Silver"
        GOLD = BADGE_CODE_GOLD, "Gold"

    membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="badge_awards",
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="badge_awards",
    )
    season = models.ForeignKey(
        GamificationSeason,
        on_delete=models.PROTECT,
        related_name="badge_awards",
    )
    badge_code = models.CharField(max_length=BADGE_CODE_MAX_LENGTH, choices=BadgeCode.choices)
    points_total = models.IntegerField()
    awarded_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["establishment", "season"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "season"],
                name="gamification_badge_award_membership_season_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"BadgeAward {self.id} [{self.badge_code}]"
