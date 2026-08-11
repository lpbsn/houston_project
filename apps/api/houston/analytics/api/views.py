from __future__ import annotations

import uuid
from dataclasses import asdict, is_dataclass
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.analytics.api.serializers import (
    AnalyticsDashboardResponseSerializer,
    AnalyticsPatternDetailResponseSerializer,
    AnalyticsPatternListResponseSerializer,
    AnalyticsPatternSignalsResponseSerializer,
)
from houston.analytics.comparisons import get_analytics_kpi_comparison
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.kpis import AnalyticsKPIResult
from houston.analytics.pattern_detail import get_analytics_pattern_detail
from houston.analytics.pattern_list import (
    DEFAULT_PATTERN_LIST_PAGE_SIZE,
    MAX_PATTERN_LIST_PAGE_SIZE,
    list_analytics_patterns,
)
from houston.analytics.pattern_signals import (
    DEFAULT_PATTERN_SIGNALS_PAGE_SIZE,
    MAX_PATTERN_SIGNALS_PAGE_SIZE,
    list_analytics_pattern_signals,
)
from houston.analytics.permissions import can_read_analytics
from houston.establishments.access import get_api_access_context
from houston.establishments.permissions import HasActiveMembership

ANALYTICS_READ_NOT_FOUND_CODES = frozenset({"analytics_pattern_not_found"})
ANALYTICS_READ_BAD_REQUEST_CODES = frozenset(
    {
        "analytics_period_invalid",
        "analytics_period_start_naive",
        "analytics_period_end_naive",
        "analytics_scope_invalid",
        "analytics_comparison_period_required",
        "analytics_recurrence_as_of_required",
        "analytics_recurrence_as_of_naive",
        "analytics_pattern_list_page_size_invalid",
        "analytics_pattern_list_cursor_invalid",
        "analytics_pattern_signals_page_size_invalid",
        "analytics_pattern_signals_cursor_invalid",
    }
)


class CanAccessAnalytics(permissions.BasePermission):
    message = "You do not have permission to access analytics."

    def has_permission(self, request, view) -> bool:
        access_context = get_api_access_context(request)
        return any(
            can_read_analytics(membership)
            for membership in access_context.active_memberships
        )


class AnalyticsAPIView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership, CanAccessAnalytics]


def _analytics_error_response(exc: AnalyticsValidationError) -> Response:
    if exc.code in ANALYTICS_READ_NOT_FOUND_CODES:
        return Response(
            {"code": exc.code, "detail": str(exc) or "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if exc.code in ANALYTICS_READ_BAD_REQUEST_CODES or exc.code:
        return Response(
            {"code": exc.code, "detail": str(exc) or "Validation failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {"code": "analytics_validation_error", "detail": str(exc) or "Validation failed."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _parse_required_aware_datetime(query_params, field_name: str):
    raw_value = query_params.get(field_name)
    if raw_value in (None, ""):
        raise AnalyticsValidationError(
            "period_start and period_end are required for analytics comparisons.",
            code="analytics_comparison_period_required",
        )
    try:
        value = parse_datetime(str(raw_value))
    except ValueError as exc:
        raise AnalyticsValidationError(
            f"{field_name} must be a valid datetime.",
            code="analytics_period_invalid",
        ) from exc
    if value is None:
        raise AnalyticsValidationError(
            f"{field_name} must be a valid datetime.",
            code="analytics_period_invalid",
        )
    if timezone.is_naive(value):
        raise AnalyticsValidationError(
            f"{field_name} must be timezone-aware.",
            code=f"analytics_{field_name}_naive",
        )
    return value


def _parse_period(query_params):
    return (
        _parse_required_aware_datetime(query_params, "period_start"),
        _parse_required_aware_datetime(query_params, "period_end"),
    )


def _parse_optional_uuid(query_params, field_name: str) -> uuid.UUID | None:
    raw_value = query_params.get(field_name)
    if raw_value in (None, ""):
        return None
    try:
        return uuid.UUID(str(raw_value))
    except (TypeError, ValueError) as exc:
        raise AnalyticsValidationError(
            f"{field_name} must be a valid UUID.",
            code="analytics_scope_invalid",
        ) from exc


def _scope_kwargs(query_params) -> dict[str, uuid.UUID | None]:
    return {
        "organization_id": _parse_optional_uuid(query_params, "organization_id"),
        "establishment_id": _parse_optional_uuid(query_params, "establishment_id"),
    }


def _dataclass_payload(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, tuple):
        return [_dataclass_payload(item) for item in value]
    if isinstance(value, list):
        return [_dataclass_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _dataclass_payload(item) for key, item in value.items()}
    return value


def _serialize_kpis(kpis: AnalyticsKPIResult) -> dict:
    return _dataclass_payload(kpis)


def _serialize_dashboard(result) -> dict:
    payload = _dataclass_payload(result)
    payload["current_kpis"] = _serialize_kpis(result.current_kpis)
    payload["previous_kpis"] = _serialize_kpis(result.previous_kpis)
    return payload


def _page_size_param(default: int, maximum: int) -> OpenApiParameter:
    return OpenApiParameter(
        name="page_size",
        required=False,
        type=int,
        description=f"Page size, default {default}, maximum {maximum}.",
    )


PERIOD_SCOPE_PARAMETERS = [
    OpenApiParameter(name="period_start", required=True, type=OpenApiTypes.DATETIME),
    OpenApiParameter(name="period_end", required=True, type=OpenApiTypes.DATETIME),
    OpenApiParameter(name="organization_id", required=False, type=OpenApiTypes.UUID),
    OpenApiParameter(name="establishment_id", required=False, type=OpenApiTypes.UUID),
]


class AnalyticsDashboardView(AnalyticsAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_dashboard_retrieve",
        parameters=PERIOD_SCOPE_PARAMETERS,
        responses={
            200: AnalyticsDashboardResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request):
        try:
            period_start, period_end = _parse_period(request.query_params)
            result = get_analytics_kpi_comparison(
                request.user,
                period_start=period_start,
                period_end=period_end,
                **_scope_kwargs(request.query_params),
            )
        except AnalyticsValidationError as exc:
            return _analytics_error_response(exc)
        return Response(AnalyticsDashboardResponseSerializer(_serialize_dashboard(result)).data)


class AnalyticsPatternListView(AnalyticsAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_patterns_list",
        parameters=[
            *PERIOD_SCOPE_PARAMETERS,
            _page_size_param(DEFAULT_PATTERN_LIST_PAGE_SIZE, MAX_PATTERN_LIST_PAGE_SIZE),
            OpenApiParameter(name="cursor", required=False, type=str),
        ],
        responses={
            200: AnalyticsPatternListResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request):
        try:
            period_start, period_end = _parse_period(request.query_params)
            result = list_analytics_patterns(
                request.user,
                period_start=period_start,
                period_end=period_end,
                page_size=request.query_params.get("page_size", DEFAULT_PATTERN_LIST_PAGE_SIZE),
                cursor=request.query_params.get("cursor"),
                **_scope_kwargs(request.query_params),
            )
        except AnalyticsValidationError as exc:
            return _analytics_error_response(exc)
        return Response(AnalyticsPatternListResponseSerializer(_dataclass_payload(result)).data)


class AnalyticsPatternDetailView(AnalyticsAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_pattern_retrieve",
        parameters=PERIOD_SCOPE_PARAMETERS,
        responses={
            200: AnalyticsPatternDetailResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, pattern_id):
        try:
            period_start, period_end = _parse_period(request.query_params)
            result = get_analytics_pattern_detail(
                request.user,
                pattern_id=pattern_id,
                period_start=period_start,
                period_end=period_end,
                **_scope_kwargs(request.query_params),
            )
        except AnalyticsValidationError as exc:
            return _analytics_error_response(exc)
        return Response(AnalyticsPatternDetailResponseSerializer(_dataclass_payload(result)).data)


class AnalyticsPatternSignalsView(AnalyticsAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_pattern_signals_list",
        parameters=[
            *PERIOD_SCOPE_PARAMETERS,
            _page_size_param(DEFAULT_PATTERN_SIGNALS_PAGE_SIZE, MAX_PATTERN_SIGNALS_PAGE_SIZE),
            OpenApiParameter(name="cursor", required=False, type=str),
        ],
        responses={
            200: AnalyticsPatternSignalsResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, pattern_id):
        try:
            period_start, period_end = _parse_period(request.query_params)
            result = list_analytics_pattern_signals(
                request.user,
                pattern_id=pattern_id,
                period_start=period_start,
                period_end=period_end,
                page_size=request.query_params.get(
                    "page_size",
                    DEFAULT_PATTERN_SIGNALS_PAGE_SIZE,
                ),
                cursor=request.query_params.get("cursor"),
                **_scope_kwargs(request.query_params),
            )
        except AnalyticsValidationError as exc:
            return _analytics_error_response(exc)
        return Response(AnalyticsPatternSignalsResponseSerializer(_dataclass_payload(result)).data)
