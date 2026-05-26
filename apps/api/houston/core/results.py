from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ServiceResult(Generic[T]):
    ok: bool
    value: T | None = None
    error_code: str | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        if self.ok:
            if self.error_code is not None or self.message is not None:
                raise ValueError("Successful results cannot include error details.")
            return

        if self.value is not None:
            raise ValueError("Failed results cannot include a value.")
        if self.error_code is None:
            raise ValueError("Failed results require an error_code.")
        if self.message is None:
            raise ValueError("Failed results require a message.")

    @classmethod
    def success(cls, value: T | None = None) -> ServiceResult[T]:
        return cls(ok=True, value=value)

    @classmethod
    def failure(cls, *, error_code: str, message: str) -> ServiceResult[T]:
        return cls(ok=False, error_code=error_code, message=message)

    @property
    def failed(self) -> bool:
        return not self.ok
