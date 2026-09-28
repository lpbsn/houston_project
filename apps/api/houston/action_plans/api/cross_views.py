from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.action_plans.api.feed_params import (
    parse_execution_feed_category,
    parse_feed_page_size,
)
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
from houston.action_plans.execution_feed import (
    build_cross_action_plan_execution_feed_page,
    build_cross_action_plan_execution_feed_pins_page,
)
from houston.action_plans.feed_cursor import (
    ActionPlanExecutionFeedCursorError,
    parse_action_plan_execution_feed_cursor,
    parse_action_plan_execution_feed_pin_cursor,
)
from houston.action_plans.feed_serializers import (
    ActionPlanExecutionCalendarResponseSerializer,
    ActionPlanExecutionFeedPinsResponseSerializer,
    ActionPlanExecutionFeedResponseSerializer,
    ActionPlanExecutionUpcomingResponseSerializer,
    serialize_action_plan_execution_feed_item,
)
from houston.action_plans.lifecycle_promotion import ensure_execution_lifecycle_for_read
from houston.action_plans.selectors import (
    action_plan_execution_overdue,
    get_action_plan_execution_for_detail,
    get_cross_action_plan_execution_for_detail,
)
from houston.action_plans.upcoming_feed import (
    build_cross_action_plan_execution_upcoming_page,
    encode_upcoming_cursor,
    parse_upcoming_cursor,
)
from houston.establishments.permissions import HasActiveMembership
from houston.signals.api.cross_views import CanAccessCrossScope, _resolve_cross_memberships

CROSS_EXECUTION_PIN_PREVIEW_SIZE = 3
CROSS_EXECUTION_DEFAULT_VIEW_MODE: ExecutionFeedViewMode = "general"


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
            OpenApiParameter(
                name="category",
                required=False,
                type=str,
                enum=["all", "pending_validation", "overdue", "in_progress"],
                description="Defaults to all.",
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

        page_size = parse_feed_page_size(request.query_params.get("page_size"))
        category, category_error = parse_execution_feed_category(
            request.query_params.get("category"),
        )
        if category_error is not None:
            return category_error
        try:
            cursor = parse_action_plan_execution_feed_cursor(
                request.query_params.get("cursor"),
            )
        except ActionPlanExecutionFeedCursorError as exc:
            return Response(
                {"code": exc.code, "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            page = build_cross_action_plan_execution_feed_page(
                memberships=memberships,
                view_mode=view_mode,
                category=category,  # type: ignore[arg-type]
                page_size=page_size,
                cursor=cursor,
            )
        except ActionPlanExecutionFeedCursorError as exc:
            return Response(
                {"code": exc.code, "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
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
                            now=page.as_of,
                        ),
                        read_only=True,
                    ),
                }
                for execution in page.items
            ],
            "next_cursor": page.next_cursor,
            "has_more": page.has_more,
        }
        if page.pins is not None:
            payload["pins"] = [
                {
                    "item_type": "action_plan_execution",
                    "action_plan_execution": serialize_action_plan_execution_feed_item(
                        execution=execution,
                        membership=actor,
                        is_overdue=action_plan_execution_overdue(
                            execution=execution,
                            now=page.as_of,
                        ),
                        read_only=True,
                    ),
                }
                for execution in page.pins
            ]
        if page.scheduled_count is not None:
            payload["scheduled"] = {
                "count": page.scheduled_count,
                "next": (
                    {
                        "id": page.scheduled_next.id,
                        "start_at": page.scheduled_next.start_at,
                        "title": page.scheduled_next.title,
                    }
                    if page.scheduled_next is not None
                    else None
                ),
            }
        if page.section_counts is not None:
            payload["section_counts"] = page.section_counts
        return Response(ActionPlanExecutionFeedResponseSerializer(payload).data)


class CrossActionPlanExecutionFeedPinsView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessCrossScope,
    ]

    @extend_schema(
        tags=["action-plans"],
        operation_id="v1_cross_action_plan_execution_feed_pins_retrieve",
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
                name="category",
                required=False,
                type=str,
                enum=["all", "pending_validation", "overdue", "in_progress"],
                description="Defaults to all.",
            ),
            OpenApiParameter(name="page_size", required=False, type=int),
            OpenApiParameter(name="cursor", required=False, type=str),
        ],
        responses={
            200: ActionPlanExecutionFeedPinsResponseSerializer,
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
        category, category_error = parse_execution_feed_category(
            request.query_params.get("category"),
        )
        if category_error is not None:
            return category_error
        raw_page_size = request.query_params.get("page_size")
        page_size = (
            CROSS_EXECUTION_PIN_PREVIEW_SIZE
            if raw_page_size is None or raw_page_size == ""
            else parse_feed_page_size(raw_page_size)
        )
        try:
            cursor = parse_action_plan_execution_feed_pin_cursor(
                request.query_params.get("cursor"),
            )
            page = build_cross_action_plan_execution_feed_pins_page(
                memberships=memberships,
                view_mode=view_mode,
                category=category,  # type: ignore[arg-type]
                page_size=page_size,
                cursor=cursor,
            )
        except ActionPlanExecutionFeedCursorError as exc:
            return Response(
                {"code": exc.code, "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
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
                            now=page.as_of,
                        ),
                        read_only=True,
                    ),
                }
                for execution in page.items
            ],
            "next_cursor": page.next_cursor,
            "has_more": page.has_more,
        }
        return Response(ActionPlanExecutionFeedPinsResponseSerializer(payload).data)


class CrossActionPlanExecutionUpcomingView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessCrossScope,
    ]

    @extend_schema(
        tags=["action-plans"],
        operation_id="v1_cross_action_plan_execution_upcoming_retrieve",
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
            OpenApiParameter(
                name="cursor",
                required=False,
                type=str,
                description="Opaque pagination cursor from a previous response next_cursor.",
            ),
        ],
        responses={
            200: ActionPlanExecutionUpcomingResponseSerializer,
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

        page_size = parse_feed_page_size(request.query_params.get("page_size"))
        try:
            cursor_start_at, cursor_id = parse_upcoming_cursor(
                request.query_params.get("cursor"),
            )
        except ValueError as exc:
            return Response(
                {"code": "validation_error", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        executions, has_more, next_start_at, next_id = (
            build_cross_action_plan_execution_upcoming_page(
                memberships=memberships,
                view_mode=view_mode,
                page_size=page_size,
                cursor_start_at=cursor_start_at,
                cursor_id=cursor_id,
            )
        )
        actor = memberships[0]
        serialized_items = [
            {
                "item_type": "action_plan_execution",
                "action_plan_execution": serialize_action_plan_execution_feed_item(
                    execution=execution,
                    membership=actor,
                    is_overdue=False,
                    read_only=True,
                ),
            }
            for execution in executions
        ]
        next_cursor = None
        if has_more and next_start_at is not None and next_id is not None:
            next_cursor = encode_upcoming_cursor(
                start_at=next_start_at,
                execution_id=next_id,
            )
        payload = {
            "items": serialized_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
        return Response(ActionPlanExecutionUpcomingResponseSerializer(payload).data)


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
