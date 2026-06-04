from __future__ import annotations


class ActionServiceError(Exception):
    error_code = "action_error"


class ActionValidationError(ActionServiceError):
    error_code = "validation_error"


class ActionStateError(ActionServiceError):
    error_code = "invalid_action_state"


class ActionPermissionError(ActionServiceError):
    error_code = "permission_denied"
