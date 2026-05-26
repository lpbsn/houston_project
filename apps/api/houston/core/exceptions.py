from __future__ import annotations


class DomainError(Exception):
    default_code = "domain_error"
    default_message = "A domain error occurred."

    def __init__(self, message: str | None = None, code: str | None = None) -> None:
        self.message = self.default_message if message is None else message
        self.code = self.default_code if code is None else code
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class DomainValidationError(DomainError):
    default_code = "validation_error"


class DomainConflictError(DomainError):
    default_code = "conflict_error"


class DomainNotFoundError(DomainError):
    default_code = "not_found_error"
