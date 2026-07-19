from __future__ import annotations

import uuid


class ActionPlanServiceError(Exception):
    error_code = "action_plan_error"


class ActionPlanValidationError(ActionPlanServiceError):
    error_code = "validation_error"


class ActionPlanStateError(ActionPlanServiceError):
    error_code = "invalid_action_plan_state"


class ActionPlanPermissionError(ActionPlanServiceError):
    error_code = "permission_denied"


class ActionPlanConflictError(ActionPlanServiceError):
    error_code = "conflict"

    def __init__(
        self,
        message: str = "",
        *,
        active_execution_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(message)
        self.active_execution_id = active_execution_id


class ActionPlanStaleExecutionError(ActionPlanConflictError):
    error_code = "stale_execution"

    def __init__(self, message: str = "This execution was modified by another user.") -> None:
        super().__init__(message)


class MixedSubmissionActorConflict(ActionPlanPermissionError):
    error_code = "mixed_submission_actor_conflict"


class MixedSubmissionPayloadConflict(ActionPlanConflictError):
    error_code = "mixed_submission_conflict"


class MixedSubmissionStepError(ActionPlanValidationError):
    error_code = "validation_error"

    def __init__(
        self,
        message: str = "",
        *,
        failed_step: str,
    ) -> None:
        super().__init__(message)
        self.failed_step = failed_step
