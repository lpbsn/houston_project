from __future__ import annotations

import uuid


class ChecklistError(Exception):
    """Base checklist domain error."""


class ChecklistValidationError(ChecklistError):
    """Invalid checklist input or state."""


class ChecklistPermissionError(ChecklistError):
    """Checklist permission denied."""


class ChecklistConflictError(ChecklistError):
    """Checklist business conflict."""

    def __init__(
        self,
        message: str = "",
        *,
        active_execution_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(message)
        self.active_execution_id = active_execution_id
