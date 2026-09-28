from __future__ import annotations


class SignalServiceError(Exception):
    error_code = "signal_error"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code if code is not None else self.error_code


class SignalValidationError(SignalServiceError):
    error_code = "signal_validation_error"


class SignalStateError(SignalServiceError):
    error_code = "invalid_signal_state"


class SignalPermissionError(SignalServiceError):
    error_code = "permission_denied"


class SignalBusinessConflictError(SignalServiceError):
    error_code = "business_conflict"


class SignalPinLimitError(SignalServiceError):
    error_code = "signal_pin_limit"

    def __init__(
        self,
        message: str = "Signal pin limit reached.",
        *,
        replacement_candidates: list[dict] | None = None,
    ) -> None:
        super().__init__(message)
        self.replacement_candidates = replacement_candidates or []


class SignalPipelineCandidateError(SignalServiceError):
    error_code = "invalid_issue_focus"
