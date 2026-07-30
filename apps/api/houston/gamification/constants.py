"""Gamification domain constants.

Future award_* hooks (GAM-02+) must run synchronously in the same
transaction.atomic as the owning business transition and lifecycle write.
Notifications and realtime invalidation stay after_commit.
"""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

SEASON_STATUS_ACTIVE = "active"
SEASON_STATUS_CLOSED = "closed"
SEASON_STATUSES = frozenset({SEASON_STATUS_ACTIVE, SEASON_STATUS_CLOSED})

BADGE_CODE_BRONZE = "bronze"
BADGE_CODE_SILVER = "silver"
BADGE_CODE_GOLD = "gold"
BADGE_CODES = frozenset({BADGE_CODE_BRONZE, BADGE_CODE_SILVER, BADGE_CODE_GOLD})

BADGE_THRESHOLD_BRONZE = 30
BADGE_THRESHOLD_SILVER = 50
BADGE_THRESHOLD_GOLD = 70

BADGE_THRESHOLDS: dict[str, int] = {
    BADGE_CODE_BRONZE: BADGE_THRESHOLD_BRONZE,
    BADGE_CODE_SILVER: BADGE_THRESHOLD_SILVER,
    BADGE_CODE_GOLD: BADGE_THRESHOLD_GOLD,
}

CURRENT_RULE_VERSION = "gamification_rules_v1"

REASON_CODE_MAX_LENGTH = 64
SOURCE_TYPE_MAX_LENGTH = 64
SOURCE_ID_MAX_LENGTH = 64
SOURCE_EVENT_ID_MAX_LENGTH = 64
IDEMPOTENCY_KEY_MAX_LENGTH = 255
RULE_VERSION_MAX_LENGTH = 64
BADGE_CODE_MAX_LENGTH = 16

# Empty for GAM-01; GAM-02+ hooks must add keys explicitly before persisting.
AWARD_METADATA_SAFE_KEYS: frozenset[str] = frozenset()

# Payload fields compared on idempotent award_points retries.
# metadata_safe is intentionally excluded from the identity payload.
AWARD_IDEMPOTENCY_PAYLOAD_FIELDS = frozenset(
    {
        "membership_id",
        "establishment_id",
        "season_id",
        "delta",
        "reason_code",
        "source_type",
        "source_id",
        "source_event_id",
        "occurred_at",
    }
)


def badge_for_score(points: int) -> str | None:
    if points >= BADGE_THRESHOLD_GOLD:
        return BADGE_CODE_GOLD
    if points >= BADGE_THRESHOLD_SILVER:
        return BADGE_CODE_SILVER
    if points >= BADGE_THRESHOLD_BRONZE:
        return BADGE_CODE_BRONZE
    return None


def build_idempotency_key(
    *,
    reason_code: str,
    subject_id: uuid.UUID | str,
    membership_id: uuid.UUID | str,
) -> str:
    """Build ledger idempotency key (rule_version is audit-only, not in the key)."""
    return f"{reason_code}:{subject_id}:{membership_id}"


def sanitize_award_metadata_safe(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only allowlisted structured keys; stringify UUID-like values."""
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if key not in AWARD_METADATA_SAFE_KEYS:
            continue
        if value is None:
            continue
        if isinstance(value, UUID):
            safe[key] = str(value)
        elif isinstance(value, (str, int, float, bool)):
            safe[key] = value
        else:
            continue
    return safe
