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

# Canonical source_type for Signal progress awards (GAM-02).
SOURCE_TYPE_SIGNAL = "signal"

# Canonical source_type for resolution-request awards (GAM-03).
SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST = "signal_resolution_request"

# Canonical source_type for ActionPlanExecution launch awards (GAM-04).
SOURCE_TYPE_ACTION_PLAN_EXECUTION = "action_plan_execution"

# Reason codes aligned with SignalLifecycleEvent.event_type (GAM-02).
REASON_SIGNAL_MARKED_INTERESTING = "signal.marked_interesting"
REASON_SIGNAL_MOVED_IN_PROGRESS = "signal.moved_in_progress"
REASON_SIGNAL_RESOLVED = "signal.resolved"

# Reason code for approved SignalResolutionRequest (GAM-03).
REASON_RESOLUTION_REQUEST_APPROVED = "resolution_request.approved"

# Reason code for eligible ActionPlanExecution launch (GAM-04).
REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE = "action_plan.execution_started_eligible"

DELTA_SIGNAL_MARKED_INTERESTING = 1
DELTA_SIGNAL_MOVED_IN_PROGRESS = 1
DELTA_SIGNAL_RESOLVED = 2
DELTA_RESOLUTION_REQUEST_APPROVED = 2
DELTA_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE = 2

# event_type → (reason_code, delta). Only rewarded Signal progress types.
SIGNAL_PROGRESS_REWARDS: dict[str, tuple[str, int]] = {
    REASON_SIGNAL_MARKED_INTERESTING: (
        REASON_SIGNAL_MARKED_INTERESTING,
        DELTA_SIGNAL_MARKED_INTERESTING,
    ),
    REASON_SIGNAL_MOVED_IN_PROGRESS: (
        REASON_SIGNAL_MOVED_IN_PROGRESS,
        DELTA_SIGNAL_MOVED_IN_PROGRESS,
    ),
    REASON_SIGNAL_RESOLVED: (
        REASON_SIGNAL_RESOLVED,
        DELTA_SIGNAL_RESOLVED,
    ),
}

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
