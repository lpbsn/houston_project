from __future__ import annotations

from houston.core.exceptions import DomainConflictError, DomainValidationError


class GamificationValidationError(DomainValidationError):
    default_code = "gamification_validation_error"


class GamificationConflictError(DomainConflictError):
    default_code = "gamification_conflict_error"


class GamificationSeasonClosedError(GamificationValidationError):
    default_code = "gamification_season_closed"


class GamificationIdempotencyConflictError(GamificationConflictError):
    default_code = "gamification_idempotency_conflict"
