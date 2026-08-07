from __future__ import annotations

from houston.core.exceptions import DomainValidationError


class AnalyticsValidationError(DomainValidationError):
    default_code = "analytics_validation_error"
