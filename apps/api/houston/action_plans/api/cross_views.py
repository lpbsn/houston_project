from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.action_plans.api.serializers import (
    ActionPlanExecutionDetailSerializer,
    serialize_execution_detail,
)
from houston.action_plans.calendar_feed import (
    ActionPlanExecutionCalendarWindowError,
    build_cross_action_plan_execution_calendar,
    parse_calendar_window_dates,
)
from houston.action_plans.constants import ExecutionFeedViewMode
from houston.action_plans.execution_feed import build_cross_action_plan_execution_feed_page
from houston.action_plans.feed_cursor import (
    ActionPlanExecutionFeedCursorError,
    parse_action_plan_execution_feed_cursor,
)
from houston.action_plans.feed_serializers import (
    ActionPlanExecutionCalendarResponseSerializer,
    ActionPlanExecutionFeedResponseSerializer,
    serialize_action_plan_execution_feed_item,
)
from houston.action_plans.lifecycle_promotion import ensure_execution_lifecycle_for_read
from houston.action_plans.selectors import (
    action_plan_execution_overdue,
    get_action_plan_execution_for_detail,
    get_cross_action_plan_execution_for_detail,
)
from houston.establishments.permissions import HasActiveMembership
from houston.signals.api.cross_views import CanAccessCrossScope, _resolve_cross_memberships

DEFAULT_FEED_PAGE_SIZE = 25
MAX_FEED_PAGE_SIZE = 50
CROSS_EXECUTION_DEFAULT_VIEW_MODE: ExecutionFeedViewMode = "general"


def _parse_feed_page_size(raw: str | None) -> int:
    if raw is None or raw == "":
        return DEFAULT_FEED_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_FEED_PAGE_SIZE
    return min(max(value, 1), MAX_FEED_PAGE_SIZE)


def _parse_cross_execution_view_mode(raw: str | None):
    if raw is None or raw.strip() == "":
        return CROSS_EXECUTION_DEFAULT_VIEW_MODE, None
    view_mode = raw.strip().lower()
    if view_mode not in {"personal", "general"}:
        return None, Response(
            {
                "code": "validation_error",
                "detail": "view_mode must be personal or general.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return view_mode, None


def _serialize_cross_calendar_bucket(executions, *, membership_by_execution_id, as_of):
    return [
        {
            "item_type": "action_plan_execution",
            "action_plan_execution": serialize_action_plan_execution_feed_item(
                execution=execution,
                membership=membership_by_execution_id[execution.id],
                is_overdue=action_plan_execution_overdue(
                    execution=execution,
                    now=as_of,
                ),
                read_only=True,
            ),
        }
        for execution in executions
    ]


class CrossActionPlanExecutionFeedView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessCrossScope,
    ]

    @extend_schema(
        tags=["action-plans"],
        operation_id="v1_cross_action_plan_execution_feed_retrieve",
        parameters=[
            OpenApiParameter(name="establishment_id", required=False, type=str),
            OpenApiParameter(
                name="view_mode",
                required=False,
                type=str,
                enum=["personal", "general"],
                description="Defaults to general.",
            ),
            OpenApiParameter(name="page_size", required=False, type=int),
            OpenApiParameter(name="cursor", required=False, type=str),
        ],
        responses={
            200: ActionPlanExecutionFeedResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request):
        memberships, error = _resolve_cross_memberships(request)
        if error is not None:
            return error

        view_mode, view_mode_error = _parse_cross_execution_view_mode(
            request.query_params.get("view_mode"),
        )
        if view_mode_error is not None:
            return view_mode_error

        page_size = _parse_feed_page_size(request.query_params.get("page_size"))
        try:
            cursor = parse_action_plan_execution_feed_cursor(
                request.query_params.get("cursor"),
            )
        except ActionPlanExecutionFeedCursorError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        (
            executions,
            has_more,
            next_cursor,
            as_of,
            scheduled_executions,
            scheduled_count,
        ) = build_cross_action_plan_execution_feed_page(
            memberships=memberships,
            view_mode=view_mode,
            page_size=page_size,
            cursor=cursor,
        )
        actor = memberships[0]
        payload = {
            "items": [
                {
                    "item_type": "action_plan_execution",
                    "action_plan_execution": serialize_action_plan_execution_feed_item(
                        execution=execution,
                        membership=actor,
                        is_overdue=action_plan_execution_overdue(
                            execution=execution,
                            now=as_of,
                        ),
                        read_only=True,
                    ),
                }
                for execution in executions
            ],
            "scheduled_items": [
                {
                    "item_type": "action_plan_execution",
                    "action_plan_execution": serialize_action_plan_execution_feed_item(
                        execution=execution,
                        membership=actor,
                        is_overdue=False,
                        read_only=True,
                    ),
                }
                for execution in scheduled_executions
            ],
            "scheduled_count": scheduled_count,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
        return Response(ActionPlanExecutionFeedResponseSerializer(payload).data)


class CrossActionPlanExecutionCalendarView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessCrossScope,
    ]

    @extend_schema(
        tags=["action-plans"],
        operation_id="v1_cross_action_plan_execution_calendar_retrieve",
        parameters=[
            OpenApiParameter(name="establishment_id", required=False, type=str),
            OpenApiParameter(
                name="view_mode",
                required=False,
                type=str,
                enum=["personal", "general"],
                description="Defaults to general.",
            ),
            OpenApiParameter(
                name="from",
                required=True,
                type=str,
                description="Inclusive civil start date (YYYY-MM-DD).",
            ),
            OpenApiParameter(
                name="to",
                required=True,
                type=str,
                description="Inclusive civil end date (YYYY-MM-DD).",
            ),
        ],
        responses={
            200: ActionPlanExecutionCalendarResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request):
        memberships, error = _resolve_cross_memberships(request)
        if error is not None:
            return error

        view_mode, view_mode_error = _parse_cross_execution_view_mode(
            request.query_params.get("view_mode"),
        )
        if view_mode_error is not None:
            return view_mode_error

        try:
            from_date, to_date = parse_calendar_window_dates(
                from_raw=request.query_params.get("from"),
                to_raw=request.query_params.get("to"),
            )
        except ActionPlanExecutionCalendarWindowError as exc:
            return Response(
                {"code": "validation_error", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        calendar = build_cross_action_plan_execution_calendar(
            memberships=memberships,
            view_mode=view_mode,
            from_date=from_date,
            to_date=to_date,
        )
        membership_by_execution_id = calendar["membership_by_execution_id"]
        as_of = calendar["as_of"]
        payload = {
            "timezone": calendar["timezone"],
            "items": _serialize_cross_calendar_bucket(
                calendar["items"],
                membership_by_execution_id=membership_by_execution_id,
                as_of=as_of,
            ),
            "unplanned": _serialize_cross_calendar_bucket(
                calendar["unplanned"],
                membership_by_execution_id=membership_by_execution_id,
                as_of=as_of,
            ),
        }
        return Response(ActionPlanExecutionCalendarResponseSerializer(payload).data)


class CrossActionPlanExecutionDetailView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessCrossScope,
    ]

    @extend_schema(
        tags=["action-plans"],
        operation_id="v1_cross_action_plan_execution_retrieve",
        responses={
            200: ActionPlanExecutionDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, execution_id):
        memberships, error = _resolve_cross_memberships(request)
        if error is not None:
            return error

        execution_uuid = uuid.UUID(str(execution_id))
        execution, membership = get_cross_action_plan_execution_for_detail(
            memberships=memberships,
            execution_id=execution_uuid,
        )
        if execution is None or membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ensure_execution_lifecycle_for_read(
            establishment_id=membership.establishment_id,
            execution_id=execution_uuid,
        )
        execution = get_action_plan_execution_for_detail(
            membership=membership,
            execution_id=execution_uuid,
        )
        if execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = serialize_execution_detail(
            execution,
            membership=membership,
            read_only=True,
        )
        return Response(ActionPlanExecutionDetailSerializer(payload).data)
