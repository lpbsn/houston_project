from __future__ import annotations

from houston.core.exceptions import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)


class ChatError(Exception):
    """Base chat domain error."""


class ChatNotFoundError(DomainNotFoundError, ChatError):
    default_code = "not_found"
    default_message = "Chat resource not found."


class ChatValidationError(DomainValidationError, ChatError):
    default_code = "validation_error"


class ChatPermissionError(ChatError):
    default_code = "permission_denied"

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        self.message = message
        self.code = self.default_code
        super().__init__(message)


class ChatConflictError(DomainConflictError, ChatError):
    default_code = "conflict_error"
