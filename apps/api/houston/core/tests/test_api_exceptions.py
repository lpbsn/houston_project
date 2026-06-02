from __future__ import annotations

from django.test import RequestFactory
from rest_framework import exceptions, status

from houston.core.api.exceptions import api_exception_handler


def _context():
    request = RequestFactory().get("/api/v1/health/")
    return {"request": request, "view": None}


def test_validation_error_returns_code_detail_and_errors():
    exc = exceptions.ValidationError(
        {
            "email": ["Enter a valid email address."],
            "non_field_errors": ["Invalid payload."],
        }
    )

    response = api_exception_handler(exc, _context())

    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"
    assert response.data["detail"] == "Request validation failed."
    assert response.data["errors"] == {
        "email": ["Enter a valid email address."],
        "non_field_errors": ["Invalid payload."],
    }


def test_not_authenticated_returns_standard_contract():
    exc = exceptions.NotAuthenticated("Authentication credentials were not provided.")

    response = api_exception_handler(exc, _context())

    assert response is not None
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data == {
        "code": "not_authenticated",
        "detail": "Authentication credentials were not provided.",
    }


def test_permission_denied_returns_standard_contract():
    exc = exceptions.PermissionDenied("You do not have permission to perform this action.")

    response = api_exception_handler(exc, _context())

    assert response is not None
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        "code": "permission_denied",
        "detail": "You do not have permission to perform this action.",
    }


def test_not_found_returns_standard_contract():
    exc = exceptions.NotFound()

    response = api_exception_handler(exc, _context())

    assert response is not None
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == {
        "code": "not_found",
        "detail": "Not found.",
    }


def test_throttled_returns_standard_contract():
    exc = exceptions.Throttled(wait=60)

    response = api_exception_handler(exc, _context())

    assert response is not None
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data["code"] == "throttled"
    assert isinstance(response.data["detail"], str)
    assert response.data["detail"]


def test_unexpected_error_returns_safe_internal_error():
    exc = RuntimeError("unexpected failure")

    response = api_exception_handler(exc, _context())

    assert response is not None
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == {
        "code": "internal_error",
        "detail": "An unexpected error occurred.",
    }
