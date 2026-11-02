from __future__ import annotations

from houston.core.exceptions import DomainNotFoundError


class CommentValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class CommentError(Exception):
    """Base comments domain error for discussion tools."""


class CommentNotFoundError(DomainNotFoundError, CommentError):
    default_code = "not_found"
    default_message = "Comment resource not found."


class CommentPermissionError(CommentError):
    default_code = "permission_denied"

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        *,
        code: str | None = None,
    ) -> None:
        self.message = message
        self.code = code or self.default_code
        super().__init__(message)
