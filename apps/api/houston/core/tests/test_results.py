import pytest

from houston.core.results import ServiceResult


def test_success_result_with_value():
    result = ServiceResult.success(value="ok")

    assert result.ok is True
    assert result.failed is False
    assert result.value == "ok"
    assert result.error_code is None
    assert result.message is None


def test_success_result_without_value():
    result = ServiceResult.success()

    assert result.ok is True
    assert result.failed is False
    assert result.value is None


def test_failure_result():
    result = ServiceResult.failure(error_code="invalid_state", message="Invalid state.")

    assert result.ok is False
    assert result.failed is True
    assert result.value is None
    assert result.error_code == "invalid_state"
    assert result.message == "Invalid state."


def test_success_result_rejects_error_details():
    with pytest.raises(ValueError, match="Successful results cannot include error details."):
        ServiceResult(ok=True, error_code="invalid", message="Should not be here.")


def test_failure_result_rejects_value():
    with pytest.raises(ValueError, match="Failed results cannot include a value."):
        ServiceResult(ok=False, value="unexpected", error_code="invalid", message="Failed.")


def test_failure_result_requires_error_code():
    with pytest.raises(ValueError, match="Failed results require an error_code."):
        ServiceResult(ok=False, message="Failed.")


def test_failure_result_requires_message():
    with pytest.raises(ValueError, match="Failed results require a message."):
        ServiceResult(ok=False, error_code="invalid")
