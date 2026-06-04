from __future__ import annotations


class SignalServiceError(Exception):
    error_code = "signal_error"


class SignalValidationError(SignalServiceError):
    error_code = "signal_validation_error"


class SignalStateError(SignalServiceError):
    error_code = "invalid_signal_state"


class SignalPermissionError(SignalServiceError):
    error_code = "permission_denied"


class SignalBusinessConflictError(SignalServiceError):
    error_code = "business_conflict"
