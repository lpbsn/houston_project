from __future__ import annotations

import logging
from typing import Any

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from houston.core.observability import build_api_request_log_context

logger = logging.getLogger(__name__)

_VALIDATION_DETAIL = "Request validation failed."
_INTERNAL_ERROR_DETAIL = "An unexpected error occurred."


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    response = drf_exception_handler(exc, context)

    if response is None:
        request = context.get("request")
        request_path = getattr(request, "path", "") if request is not None else ""
        request_method = getattr(request, "method", "") if request is not None else ""
        logger.error(
            "api_unhandled_exception",
            extra=build_api_request_log_context(
                request_path=request_path,
                request_method=request_method,
                exception_class=type(exc).__name__,
            ),
            exc_info=True,
        )
        return Response(
            {
                "code": "internal_error",
                "detail": _INTERNAL_ERROR_DETAIL,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.ValidationError):
        return Response(
            {
                "code": "validation_error",
                "detail": _VALIDATION_DETAIL,
                "errors": _normalize_validation_errors(exc.detail),
            },
            status=response.status_code,
            headers=response.headers,
        )

    detail = _extract_detail(response.data)
    code = _resolve_error_code(exc)

    response.data = {
        "code": code,
        "detail": detail,
    }
    return response


def _resolve_error_code(exc: Exception) -> str:
    if isinstance(exc, exceptions.NotAuthenticated):
        return "not_authenticated"
    if isinstance(exc, exceptions.PermissionDenied):
        return "permission_denied"
    if isinstance(exc, exceptions.NotFound):
        return "not_found"
    if isinstance(exc, exceptions.Throttled):
        return "throttled"
    if isinstance(exc, exceptions.APIException):
        default_code = getattr(exc, "default_code", None)
        if isinstance(default_code, str) and default_code:
            return default_code
    return "api_error"


def _extract_detail(data: Any) -> str:
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list) and detail and isinstance(detail[0], str):
            return detail[0]
    elif isinstance(data, list) and data and isinstance(data[0], str):
        return data[0]
    elif isinstance(data, str):
        return data
    return _INTERNAL_ERROR_DETAIL


def _normalize_validation_errors(detail: Any) -> Any:
    if isinstance(detail, list):
        normalized: list[Any] = []
        for item in detail:
            if isinstance(item, (dict, list)):
                normalized.append(_normalize_validation_errors(item))
            else:
                normalized.append(str(item))
        return normalized
    if isinstance(detail, dict):
        return {key: _normalize_validation_errors(value) for key, value in detail.items()}
    return [str(detail)]
