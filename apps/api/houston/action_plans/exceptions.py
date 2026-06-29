from __future__ import annotations


class ActionPlanServiceError(Exception):
    error_code = "action_plan_error"


class ActionPlanValidationError(ActionPlanServiceError):
    error_code = "validation_error"


class ActionPlanStateError(ActionPlanServiceError):
    error_code = "invalid_action_plan_state"


class ActionPlanPermissionError(ActionPlanServiceError):
    error_code = "permission_denied"
