from houston.core.exceptions import (
    DomainConflictError,
    DomainError,
    DomainNotFoundError,
    DomainValidationError,
)


def test_domain_error_uses_defaults():
    error = DomainError()

    assert error.code == "domain_error"
    assert error.message == "A domain error occurred."
    assert str(error) == "A domain error occurred."


def test_domain_error_accepts_custom_message_and_code():
    error = DomainError(message="Custom problem.", code="custom_code")

    assert error.code == "custom_code"
    assert error.message == "Custom problem."
    assert str(error) == "Custom problem."


def test_domain_error_subclasses_define_generic_codes():
    assert DomainValidationError().code == "validation_error"
    assert DomainConflictError().code == "conflict_error"
    assert DomainNotFoundError().code == "not_found_error"
