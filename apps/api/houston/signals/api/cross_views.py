from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.management_scope import (
    resolve_management_memberships_for_scope,
    user_can_access_management_scope,
)
from houston.establishments.permissions import HasActiveMembership
from houston.signals.api.serializers import (
    SignalDetailSerializer,
    SignalFeedResponseSerializer,
    serialize_signal_detail,
    serialize_signal_feed_item,
)
from houston.signals.feed_cursor import (
    SignalFeedCursorError,
    apply_signal_feed_cursor,
    encode_signal_feed_cursor,
    parse_signal_feed_cursor,
)
from houston.signals.feed_filters import (
    SignalFeedFilterValidationError,
    build_applied_filters_payload,
    parse_cross_signal_feed_filters,
)
from houston.signals.permissions import can_use_needs_qualification_filter
from houston.signals.selectors import (
    cross_signal_feed_queryset,
    get_cross_signal_for_detail,
)

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 50


class CanAccessCrossScope(permissions.BasePermission):
    message = "You do not have permission to access the cross-establishment scope."

    def has_permission(self, request, view) -> bool:
        return user_can_access_management_scope(request.user)


def _parse_page_size(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return min(max(value, 1), MAX_PAGE_SIZE)


def _parse_optional_establishment_id(query_params):
    raw_value = query_params.get("establishment_id")
    if raw_value in (None, ""):
        return None, None
    try:
        return uuid.UUID(str(raw_value)), None
    except (TypeError, ValueError):
        return None, Response(
            {
                "code": "validation_error",
                "detail": "establishment_id must be a valid UUID.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


def _resolve_cross_memberships(request):
    establishment_id, error = _parse_optional_establishment_id(request.query_params)
    if error is not None:
        return None, error
    if not user_can_access_management_scope(request.user):
        return None, Response(
            {
                "code": "permission_denied",
                "detail": "You do not have permission to access the cross-establishment scope.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    memberships = resolve_management_memberships_for_scope(
        request.user,
        establishment_id=establishment_id,
    )
    if establishment_id is not None and not memberships:
        return None, Response(
            {
                "code": "permission_denied",
                "detail": "Establishment is outside the management scope.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    return memberships, None


class CrossSignalFeedView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessCrossScope,
    ]

    @extend_schema(
        tags=["signals"],
        operation_id="v1_cross_signal_feed_retrieve",
        parameters=[
            OpenApiParameter(name="establishment_id", required=False, type=str),
            OpenApiParameter(name="page_size", required=False, type=int),
            OpenApiParameter(name="cursor", required=False, type=str),
            OpenApiParameter(name="statuses", required=False, type=str),
            OpenApiParameter(name="business_unit_ids", required=False, type=str),
            OpenApiParameter(name="activity_subject_ids", required=False, type=str),
            OpenApiParameter(name="needs_qualification", required=False, type=bool),
        ],
        responses={
            200: SignalFeedResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request):
        memberships, error = _resolve_cross_memberships(request)
        if error is not None:
            return error

        page_size = _parse_page_size(request.query_params.get("page_size"))
        try:
            cursor = parse_signal_feed_cursor(request.query_params.get("cursor"))
        except SignalFeedCursorError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            feed_filters = parse_cross_signal_feed_filters(
                query_params=request.query_params,
                establishment_ids=tuple(
                    membership.establishment_id for membership in memberships
                ),
            )
        except SignalFeedFilterValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        actor = memberships[0]
        if feed_filters.needs_qualification and not can_use_needs_qualification_filter(
            actor
        ):
            return Response(
                {
                    "code": "permission_denied",
                    "detail": "needs_qualification is not available for this role.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = cross_signal_feed_queryset(
            memberships=memberships,
            filters=feed_filters if feed_filters.has_any() else None,
        )
        if cursor is not None:
            queryset = apply_signal_feed_cursor(queryset, cursor)
        page_candidates = list(queryset[: page_size + 1])
        has_more = len(page_candidates) > page_size
        items = page_candidates[:page_size]
        next_cursor = encode_signal_feed_cursor(items[-1]) if has_more and items else None

        payload = {
            "items": [
                serialize_signal_feed_item(
                    signal=signal,
                    membership=actor,
                    read_only=True,
                )
                for signal in items
            ],
            "next_cursor": next_cursor,
            "has_more": has_more,
            "applied_filters": build_applied_filters_payload(
                view_mode="general",
                filters=feed_filters,
            ),
        }
        return Response(SignalFeedResponseSerializer(payload).data)


class CrossSignalDetailView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessCrossScope,
    ]

    @extend_schema(
        tags=["signals"],
        operation_id="v1_cross_signal_retrieve",
        responses={
            200: SignalDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, signal_id):
        memberships, error = _resolve_cross_memberships(request)
        if error is not None:
            return error

        signal, membership = get_cross_signal_for_detail(
            memberships=memberships,
            signal_id=uuid.UUID(str(signal_id)),
        )
        if signal is None or membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = serialize_signal_detail(
            signal=signal,
            membership=membership,
            request=request,
            read_only=True,
        )
        return Response(SignalDetailSerializer(payload).data)
