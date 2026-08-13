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
    AnalyticsOwnerGovernanceResponseSerializer,
    AnalyticsPatternDetailResponseSerializer,
    AnalyticsPatternFilterOptionsResponseSerializer,
    AnalyticsPatternIssueReportRequestSerializer,
    AnalyticsPatternIssueReportResponseSerializer,
    AnalyticsPatternListResponseSerializer,
    AnalyticsPatternMergeRequestSerializer,
    AnalyticsPatternMoveSignalsRequestSerializer,
    AnalyticsPatternRenameRequestSerializer,
    AnalyticsPatternSignalsResponseSerializer,
    AnalyticsPatternSplitToExistingRequestSerializer,
    AnalyticsPatternSplitToNewRequestSerializer,
)
from houston.analytics.comparisons import get_analytics_kpi_comparison
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.kpis import AnalyticsKPIResult
from houston.analytics.pattern_detail import get_analytics_pattern_detail
from houston.analytics.pattern_list import (
    DEFAULT_PATTERN_LIST_PAGE_SIZE,
    MAX_PATTERN_LIST_PAGE_SIZE,
    PATTERN_LIST_RECURRENCE_ALL,
    PATTERN_LIST_RECURRENCE_NON_RECURRENT,
    PATTERN_LIST_RECURRENCE_RECURRENT,
    PATTERN_LIST_SIGNAL_STATUSES,
    list_analytics_pattern_filter_options,
    list_analytics_patterns,
)
from houston.analytics.pattern_signals import (
    DEFAULT_PATTERN_SIGNALS_PAGE_SIZE,
    MAX_PATTERN_SIGNALS_PAGE_SIZE,
    list_analytics_pattern_signals,
)
from houston.analytics.permissions import can_read_analytics
from houston.analytics.services import (
    can_govern_any_operational_patterns,
    merge_operational_patterns_for_owner,
    move_signals_between_patterns_for_owner,
    rename_operational_pattern_for_owner,
    report_pattern_assignment_issue,
    split_operational_pattern_to_existing_for_owner,
    split_operational_pattern_to_new_for_owner,
)
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
        "analytics_pattern_list_filter_invalid",
        "analytics_pattern_signals_page_size_invalid",
        "analytics_pattern_signals_cursor_invalid",
    }
)
ANALYTICS_GOVERNANCE_NOT_FOUND_CODES = frozenset(
    {
        "analytics_pattern_not_found",
        "analytics_signal_not_found",
        "analytics_signal_wrong_organization",
        "analytics_signal_scope_forbidden",
    }
)
ANALYTICS_GOVERNANCE_CONFLICT_CODES = frozenset(
    {
        "analytics_assignment_missing",
        "analytics_assignment_wrong_pattern",
        "analytics_pattern_already_merged",
        "analytics_pattern_label_conflict",
        "analytics_pattern_merge_concurrent_change",
        "analytics_pattern_not_active",
        "analytics_pattern_retired",
        "analytics_pattern_same_source_target",
        "analytics_pattern_source_not_active",
        "analytics_pattern_target_not_active",
        "analytics_pattern_wrong_organization",
    }
)
ANALYTICS_GOVERNANCE_FORBIDDEN_CODES = frozenset({"analytics_owner_permission_required"})
ANALYTICS_PATTERN_ISSUE_FORBIDDEN_CODES = frozenset(
    {"analytics_pattern_issue_permission_denied"}
)
ANALYTICS_PATTERN_ISSUE_NOT_FOUND_CODES = frozenset(
    {"analytics_pattern_issue_target_not_found"}
)
ANALYTICS_PATTERN_ISSUE_CONFLICT_CODES = frozenset(
    {
        "analytics_pattern_assignment_missing",
        "analytics_pattern_assignment_mismatch",
    }
)
ANALYTICS_PATTERN_ISSUE_BAD_REQUEST_CODES = frozenset(
    {
        "analytics_pattern_issue_reason_invalid",
        "analytics_pattern_issue_comment_invalid",
        "analytics_pattern_issue_comment_too_long",
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


class CanGovernAnalyticsPatterns(permissions.BasePermission):
    message = "You do not have permission to govern analytics patterns."

    def has_permission(self, request, view) -> bool:
        return can_govern_any_operational_patterns(getattr(request, "user", None))


class AnalyticsAPIView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership, CanAccessAnalytics]


class AnalyticsOwnerGovernanceAPIView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanGovernAnalyticsPatterns,
    ]


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


def _analytics_governance_error_response(exc: AnalyticsValidationError) -> Response:
    if exc.code in ANALYTICS_GOVERNANCE_FORBIDDEN_CODES:
        return Response(
            {"code": exc.code, "detail": str(exc) or "Permission denied."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if exc.code in ANALYTICS_GOVERNANCE_NOT_FOUND_CODES:
        return Response(
            {"code": exc.code, "detail": str(exc) or "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if exc.code in ANALYTICS_GOVERNANCE_CONFLICT_CODES:
        return Response(
            {"code": exc.code, "detail": str(exc) or "Conflict."},
            status=status.HTTP_409_CONFLICT,
        )
    return Response(
        {
            "code": exc.code or "analytics_validation_error",
            "detail": str(exc) or "Validation failed.",
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _analytics_pattern_issue_error_response(exc: AnalyticsValidationError) -> Response:
    if exc.code in ANALYTICS_PATTERN_ISSUE_FORBIDDEN_CODES:
        return Response(
            {"code": exc.code, "detail": str(exc) or "Permission denied."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if exc.code in ANALYTICS_PATTERN_ISSUE_NOT_FOUND_CODES:
        return Response(
            {"code": exc.code, "detail": str(exc) or "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if exc.code in ANALYTICS_PATTERN_ISSUE_CONFLICT_CODES:
        return Response(
            {"code": exc.code, "detail": str(exc) or "Conflict."},
            status=status.HTTP_409_CONFLICT,
        )
    if exc.code in ANALYTICS_PATTERN_ISSUE_BAD_REQUEST_CODES:
        return Response(
            {"code": exc.code, "detail": str(exc) or "Validation failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {
            "code": exc.code or "analytics_validation_error",
            "detail": str(exc) or "Validation failed.",
        },
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


def _parse_optional_uuid_csv(query_params, field_name: str) -> tuple[uuid.UUID, ...] | None:
    raw_value = query_params.get(field_name)
    if raw_value in (None, ""):
        return None
    values = []
    try:
        for value in str(raw_value).split(","):
            if not value.strip():
                continue
            values.append(uuid.UUID(value.strip()))
    except ValueError as exc:
        raise AnalyticsValidationError(
            f"{field_name} must be a comma-separated list of UUIDs.",
            code="analytics_pattern_list_filter_invalid",
        ) from exc
    return tuple(sorted(set(values), key=str))


def _parse_optional_bool(query_params, field_name: str) -> bool:
    raw_value = query_params.get(field_name)
    if raw_value in (None, ""):
        return False
    normalized = str(raw_value).strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise AnalyticsValidationError(
        f"{field_name} must be a boolean.",
        code="analytics_pattern_list_filter_invalid",
    )


def _scope_kwargs(query_params) -> dict[str, uuid.UUID | None]:
    return {
        "organization_id": _parse_optional_uuid(query_params, "organization_id"),
        "establishment_id": _parse_optional_uuid(query_params, "establishment_id"),
    }


def _pattern_list_kwargs(query_params) -> dict[str, object]:
    establishment_id = _parse_optional_uuid(query_params, "establishment_id")
    establishment_ids = _parse_optional_uuid_csv(query_params, "establishment_ids")
    if establishment_id is not None and establishment_ids is not None:
        raise AnalyticsValidationError(
            "Use either establishment_id or establishment_ids, not both.",
            code="analytics_scope_invalid",
        )
    signal_statuses = _parse_csv_strings(query_params, "signal_statuses")
    invalid_statuses = sorted(
        status for status in signal_statuses if status not in PATTERN_LIST_SIGNAL_STATUSES
    )
    if invalid_statuses:
        raise AnalyticsValidationError(
            "signal_statuses contains an invalid analytics status.",
            code="analytics_pattern_list_filter_invalid",
        )
    recurrence = query_params.get("recurrence", PATTERN_LIST_RECURRENCE_ALL)
    if recurrence not in {
        PATTERN_LIST_RECURRENCE_ALL,
        PATTERN_LIST_RECURRENCE_RECURRENT,
        PATTERN_LIST_RECURRENCE_NON_RECURRENT,
    }:
        raise AnalyticsValidationError(
            "recurrence must be all, recurrent, or non_recurrent.",
            code="analytics_pattern_list_filter_invalid",
        )
    return {
        "organization_id": _parse_optional_uuid(query_params, "organization_id"),
        "establishment_id": establishment_id,
        "establishment_ids": establishment_ids,
        "q": query_params.get("q"),
        "recurrence": recurrence,
        "responsible_business_unit_ids": _parse_optional_uuid_csv(
            query_params,
            "responsible_business_unit_ids",
        ),
        "responsible_business_unit_unassigned": _parse_optional_bool(
            query_params,
            "responsible_business_unit_unassigned",
        ),
        "signal_statuses": signal_statuses,
    }


def _parse_csv_strings(query_params, field_name: str) -> tuple[str, ...]:
    raw_value = query_params.get(field_name)
    if raw_value in (None, ""):
        return ()
    return tuple(sorted({value.strip() for value in str(raw_value).split(",") if value.strip()}))


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


def _serialize_owner_governance(result) -> dict:
    return _dataclass_payload(result)


def _serialize_pattern_issue_report(report) -> dict:
    return {
        "report_id": report.id,
        "pattern_id": report.pattern_id,
        "signal_id": report.signal_id,
        "status": report.status,
        "report_type": report.report_type,
        "comment": report.comment,
        "created_at": report.created_at,
    }


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

PATTERN_LIST_FILTER_PARAMETERS = [
    OpenApiParameter(name="establishment_ids", required=False, type=str),
    OpenApiParameter(name="q", required=False, type=str),
    OpenApiParameter(
        name="recurrence",
        required=False,
        type=str,
        enum=[
            PATTERN_LIST_RECURRENCE_ALL,
            PATTERN_LIST_RECURRENCE_RECURRENT,
            PATTERN_LIST_RECURRENCE_NON_RECURRENT,
        ],
    ),
    OpenApiParameter(name="responsible_business_unit_ids", required=False, type=str),
    OpenApiParameter(
        name="responsible_business_unit_unassigned",
        required=False,
        type=bool,
    ),
    OpenApiParameter(name="signal_statuses", required=False, type=str),
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
            *PATTERN_LIST_FILTER_PARAMETERS,
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
                **_pattern_list_kwargs(request.query_params),
            )
        except AnalyticsValidationError as exc:
            return _analytics_error_response(exc)
        return Response(AnalyticsPatternListResponseSerializer(_dataclass_payload(result)).data)


class AnalyticsPatternFilterOptionsView(AnalyticsAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_pattern_filter_options_retrieve",
        parameters=[
            OpenApiParameter(name="organization_id", required=False, type=OpenApiTypes.UUID),
            OpenApiParameter(name="establishment_id", required=False, type=OpenApiTypes.UUID),
            OpenApiParameter(name="establishment_ids", required=False, type=str),
        ],
        responses={
            200: AnalyticsPatternFilterOptionsResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request):
        try:
            kwargs = _pattern_list_kwargs(request.query_params)
            result = list_analytics_pattern_filter_options(
                request.user,
                organization_id=kwargs["organization_id"],
                establishment_id=kwargs["establishment_id"],
                establishment_ids=kwargs["establishment_ids"],
            )
        except AnalyticsValidationError as exc:
            return _analytics_error_response(exc)
        return Response(
            AnalyticsPatternFilterOptionsResponseSerializer(_dataclass_payload(result)).data
        )


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


class AnalyticsPatternIssueReportView(AnalyticsAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_pattern_signal_issue_report_create",
        request=AnalyticsPatternIssueReportRequestSerializer,
        responses={
            201: AnalyticsPatternIssueReportResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, pattern_id, signal_id):
        serializer = AnalyticsPatternIssueReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            report = report_pattern_assignment_issue(
                request.user,
                pattern_id=pattern_id,
                signal_id=signal_id,
                reason=serializer.validated_data.get("reason", "wrong_pattern"),
                comment=serializer.validated_data.get("comment", ""),
            )
        except AnalyticsValidationError as exc:
            return _analytics_pattern_issue_error_response(exc)
        return Response(
            AnalyticsPatternIssueReportResponseSerializer(
                _serialize_pattern_issue_report(report)
            ).data,
            status=status.HTTP_201_CREATED,
        )


class AnalyticsPatternRenameView(AnalyticsOwnerGovernanceAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_pattern_rename",
        request=AnalyticsPatternRenameRequestSerializer,
        responses={
            200: AnalyticsOwnerGovernanceResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, pattern_id):
        serializer = AnalyticsPatternRenameRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = rename_operational_pattern_for_owner(
                request.user,
                pattern_id=pattern_id,
                label=serializer.validated_data["label"],
            )
        except AnalyticsValidationError as exc:
            return _analytics_governance_error_response(exc)
        return Response(
            AnalyticsOwnerGovernanceResponseSerializer(
                _serialize_owner_governance(result)
            ).data
        )


class AnalyticsPatternMergeView(AnalyticsOwnerGovernanceAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_pattern_merge",
        request=AnalyticsPatternMergeRequestSerializer,
        responses={
            200: AnalyticsOwnerGovernanceResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, pattern_id):
        serializer = AnalyticsPatternMergeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = merge_operational_patterns_for_owner(
                request.user,
                source_pattern_id=pattern_id,
                target_pattern_id=serializer.validated_data["target_pattern_id"],
            )
        except AnalyticsValidationError as exc:
            return _analytics_governance_error_response(exc)
        return Response(
            AnalyticsOwnerGovernanceResponseSerializer(
                _serialize_owner_governance(result)
            ).data
        )


class AnalyticsPatternMoveSignalsView(AnalyticsOwnerGovernanceAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_pattern_move_signals",
        request=AnalyticsPatternMoveSignalsRequestSerializer,
        responses={
            200: AnalyticsOwnerGovernanceResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, pattern_id):
        serializer = AnalyticsPatternMoveSignalsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = move_signals_between_patterns_for_owner(
                request.user,
                source_pattern_id=pattern_id,
                target_pattern_id=serializer.validated_data["target_pattern_id"],
                signal_ids=serializer.validated_data["signal_ids"],
            )
        except AnalyticsValidationError as exc:
            return _analytics_governance_error_response(exc)
        return Response(
            AnalyticsOwnerGovernanceResponseSerializer(
                _serialize_owner_governance(result)
            ).data
        )


class AnalyticsPatternSplitToExistingView(AnalyticsOwnerGovernanceAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_pattern_split_to_existing",
        request=AnalyticsPatternSplitToExistingRequestSerializer,
        responses={
            200: AnalyticsOwnerGovernanceResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, pattern_id):
        serializer = AnalyticsPatternSplitToExistingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = split_operational_pattern_to_existing_for_owner(
                request.user,
                source_pattern_id=pattern_id,
                target_pattern_id=serializer.validated_data["target_pattern_id"],
                signal_ids=serializer.validated_data["signal_ids"],
            )
        except AnalyticsValidationError as exc:
            return _analytics_governance_error_response(exc)
        return Response(
            AnalyticsOwnerGovernanceResponseSerializer(
                _serialize_owner_governance(result)
            ).data
        )


class AnalyticsPatternSplitToNewView(AnalyticsOwnerGovernanceAPIView):
    @extend_schema(
        tags=["analytics"],
        operation_id="v1_analytics_pattern_split_to_new",
        request=AnalyticsPatternSplitToNewRequestSerializer,
        responses={
            200: AnalyticsOwnerGovernanceResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, pattern_id):
        serializer = AnalyticsPatternSplitToNewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = split_operational_pattern_to_new_for_owner(
                request.user,
                source_pattern_id=pattern_id,
                label=serializer.validated_data["label"],
                signal_ids=serializer.validated_data["signal_ids"],
            )
        except AnalyticsValidationError as exc:
            return _analytics_governance_error_response(exc)
        return Response(
            AnalyticsOwnerGovernanceResponseSerializer(
                _serialize_owner_governance(result)
            ).data
        )
