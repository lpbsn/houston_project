from __future__ import annotations

import uuid


class ActionPlanServiceError(Exception):
    error_code = "action_plan_error"


class ActionPlanValidationError(ActionPlanServiceError):
    error_code = "validation_error"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code if code is not None else self.error_code


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


class ActionPlanValidatedExecutionConflictError(ActionPlanConflictError):
    error_code = "business_conflict"


class PlanningSubmissionPayloadConflict(ActionPlanConflictError):
    error_code = "planning_submission_conflict"


class PlanningSubmissionItemError(ActionPlanValidationError):
    error_code = "validation_error"

    def __init__(
        self,
        message: str = "",
        *,
        item_id: uuid.UUID | None = None,
        item_index: int | None = None,
    ) -> None:
        super().__init__(message)
        self.item_id = item_id
        self.item_index = item_index


class ActionPlanExecutionObservationIntegrityError(ActionPlanConflictError):
    """Scheduled execution unexpectedly linked to an Observation (PROTECT)."""

    error_code = "execution_observation_integrity"

    def __init__(
        self,
        message: str = (
            "Cannot hard-delete scheduled execution while an Observation still "
            "references it or one of its tasks."
        ),
        *,
        execution_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(message)
        self.execution_id = execution_id
