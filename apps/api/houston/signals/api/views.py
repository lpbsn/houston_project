from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.api.serializers import BusinessUnitTreeResponseSerializer
from houston.establishments.permissions import HasActiveMembership
from houston.establishments.selectors import get_establishment_business_unit_tree
from houston.signals.api.serializers import (
    SignalDetailSerializer,
    SignalFeedResponseSerializer,
    SignalQualifyRoutingRequestSerializer,
    SignalQualifyRoutingResponseSerializer,
    serialize_signal_detail,
    serialize_signal_feed_item,
)
from houston.signals.exceptions import (
    SignalAlreadyMergedError,
    SignalBusinessConflictError,
    SignalPermissionError,
    SignalStateError,
    SignalValidationError,
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
    parse_signal_feed_filters,
)
from houston.signals.permissions import (
    can_access_qualify_routing_endpoint,
    can_cancel_signal,
    can_mark_signal_interesting,
    can_pin_signal,
    can_resolve_signal,
    can_use_needs_qualification_filter,
    can_view_signal_feed,
    is_triage_role,
)
from houston.signals.selectors import (
    get_signal_for_detail,
    get_signal_for_qualify_routing,
    signal_feed_queryset,
)
from houston.signals.services import (
    cancel_signal,
    mark_signal_interesting,
    pin_signal,
    qualify_signal_routing,
    resolve_signal,
    unpin_signal,
)
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 50


class EstablishmentScopedSignalMixin(EstablishmentScopedObservationMixin):
    pass


class CanViewSignalFeed(permissions.BasePermission):
    message = "You do not have permission to view the signal feed."

    def has_permission(self, request, view) -> bool:
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=view.establishment_id,
        )
        return can_view_signal_feed(membership)


class SignalFeedView(EstablishmentScopedSignalMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        parameters=[
            OpenApiParameter(
                name="view_mode",
                required=True,
                type=str,
                enum=["personal", "general"],
            ),
            OpenApiParameter(name="page_size", required=False, type=int),
            OpenApiParameter(
                name="cursor",
                required=False,
                type=str,
                description="Opaque pagination cursor from a previous response next_cursor.",
            ),
            OpenApiParameter(
                name="statuses",
                required=False,
                type=str,
                description=(
                    "Comma-separated feed statuses: open, in_progress, interesting, "
                    "resolved, canceled (max 5)."
                ),
            ),
            OpenApiParameter(
                name="business_unit_ids",
                required=False,
                type=str,
                description=(
                    "Comma-separated BusinessUnit UUIDs (max 20). "
                    "Matches affected_business_unit OR responsible_business_unit."
                ),
            ),
            OpenApiParameter(
                name="activity_subject_ids",
                required=False,
                type=str,
                description="Comma-separated ActivitySubject UUIDs (max 50).",
            ),
            OpenApiParameter(
                name="needs_qualification",
                required=False,
                type=bool,
                description=(
                    "When true, restrict to signals with no responsible business unit "
                    "(affected and activity_subject ignored) among active lifecycle "
                    "statuses. Owner/Director/Manager only; Staff receives 403."
                ),
            ),
        ],
        responses={
            200: SignalFeedResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        view_mode = request.query_params.get("view_mode", "").strip().lower()
        if view_mode not in {"personal", "general"}:
            return Response(
                {
                    "code": "validation_error",
                    "detail": "view_mode must be personal or general.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        page_size = _parse_page_size(request.query_params.get("page_size"))

        try:
            cursor = parse_signal_feed_cursor(request.query_params.get("cursor"))
        except SignalFeedCursorError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            feed_filters = parse_signal_feed_filters(
                query_params=request.query_params,
                establishment_id=self.establishment_id,
            )
        except SignalFeedFilterValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if feed_filters.needs_qualification and not can_use_needs_qualification_filter(
            membership
        ):
            return Response(
                {
                    "code": "permission_denied",
                    "detail": "needs_qualification is not available for this role.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = signal_feed_queryset(
            membership=membership,
            view_mode=view_mode,  # type: ignore[arg-type]
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
                serialize_signal_feed_item(signal=signal, membership=membership) for signal in items
            ],
            "next_cursor": next_cursor,
            "has_more": has_more,
            "applied_filters": build_applied_filters_payload(
                view_mode=view_mode,
                filters=feed_filters,
            ),
        }
        serializer = SignalFeedResponseSerializer(payload)
        return Response(serializer.data)


class SignalDetailView(EstablishmentScopedSignalMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        responses={
            200: SignalDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, signal_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        signal = get_signal_for_detail(
            membership=membership,
            signal_id=uuid.UUID(str(signal_id)),
        )
        if signal is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = serialize_signal_detail(signal=signal, membership=membership, request=request)
        return Response(SignalDetailSerializer(payload).data)


class SignalPinView(EstablishmentScopedSignalMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        request=None,
        responses={
            200: SignalDetailSerializer,
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, signal_id):
        return _signal_command_response(
            request=request,
            establishment_id=self.establishment_id,
            signal_id=signal_id,
            action="pin",
        )


class SignalUnpinView(EstablishmentScopedSignalMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        request=None,
        responses={
            200: SignalDetailSerializer,
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, signal_id):
        return _signal_command_response(
            request=request,
            establishment_id=self.establishment_id,
            signal_id=signal_id,
            action="unpin",
        )


class SignalCancelView(EstablishmentScopedSignalMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        request=None,
        responses={
            200: SignalDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, signal_id):
        return _signal_lifecycle_command_response(
            request=request,
            establishment_id=self.establishment_id,
            signal_id=signal_id,
            action="cancel",
        )


class SignalResolveView(EstablishmentScopedSignalMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        request=None,
        responses={
            200: SignalDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, signal_id):
        return _signal_lifecycle_command_response(
            request=request,
            establishment_id=self.establishment_id,
            signal_id=signal_id,
            action="resolve",
        )


class SignalMarkInterestingView(EstablishmentScopedSignalMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        request=None,
        responses={
            200: SignalDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, signal_id):
        return _signal_lifecycle_command_response(
            request=request,
            establishment_id=self.establishment_id,
            signal_id=signal_id,
            action="mark_interesting",
        )


class SignalQualifyRoutingOptionsView(EstablishmentScopedSignalMixin, APIView):
    """Establishment-wide active BU/AS tree for qualify pickers (triage roles)."""

    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        responses={
            200: BusinessUnitTreeResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Returns the establishment-wide active BusinessUnit / ActivitySubject tree "
            "for signal routing qualification pickers. Owner/Director/Manager only; "
            "not filtered by membership scope. Staff receives 403."
        ),
    )
    def get(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None or not is_triage_role(membership):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        tree = get_establishment_business_unit_tree(
            establishment_id=self.establishment_id,
            active_only=True,
        )
        if tree is None:
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(BusinessUnitTreeResponseSerializer(tree).data)


class SignalQualifyRoutingView(EstablishmentScopedSignalMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        request=SignalQualifyRoutingRequestSerializer,
        responses={
            200: SignalQualifyRoutingResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, signal_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        signal = get_signal_for_qualify_routing(
            membership=membership,
            signal_id=uuid.UUID(str(signal_id)),
        )
        if signal is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not can_access_qualify_routing_endpoint(membership, signal):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        request_serializer = SignalQualifyRoutingRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        patch = dict(request_serializer.validated_data)

        try:
            result = qualify_signal_routing(
                signal=signal,
                membership=membership,
                patch=patch,
            )
        except SignalPermissionError:
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )
        except SignalAlreadyMergedError as exc:
            return Response(
                {"code": exc.error_code, "detail": "Signal already merged."},
                status=status.HTTP_409_CONFLICT,
            )
        except SignalStateError as exc:
            return Response(
                {"code": exc.error_code, "detail": "Invalid signal state."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SignalValidationError as exc:
            return Response(
                {"code": exc.code, "detail": str(exc) or "Invalid qualification payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        detail_signal = get_signal_for_detail(
            membership=membership,
            signal_id=result.surviving_signal_id,
        )
        if detail_signal is None:
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = serialize_signal_detail(
            signal=detail_signal,
            membership=membership,
            request=request,
        )
        payload["qualification_outcome"] = result.qualification_outcome
        payload["surviving_signal_id"] = result.surviving_signal_id
        payload["merged_signal_id"] = result.merged_signal_id
        return Response(SignalQualifyRoutingResponseSerializer(payload).data)


def _signal_lifecycle_command_response(
    *,
    request,
    establishment_id: uuid.UUID,
    signal_id: str,
    action: str,
) -> Response:
    membership = resolve_observation_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    signal = get_signal_for_detail(
        membership=membership,
        signal_id=uuid.UUID(str(signal_id)),
    )
    if signal is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if action == "cancel":
        if not can_cancel_signal(membership, signal):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )
    elif action == "resolve":
        if not can_resolve_signal(membership, signal):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )
    elif action == "mark_interesting":
        if not can_mark_signal_interesting(membership, signal):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )
    else:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        if action == "cancel":
            signal = cancel_signal(signal=signal, actor_membership=membership)
        elif action == "resolve":
            signal = resolve_signal(signal=signal, actor_membership=membership)
        else:
            signal = mark_signal_interesting(signal=signal)
    except SignalBusinessConflictError as exc:
        return Response(
            {
                "code": exc.error_code, 
                "detail": "Cannot resolve signal with active linked action plans."
            },
            status=status.HTTP_409_CONFLICT,
        )
    except SignalStateError as exc:
        return Response(
            {"code": exc.error_code, "detail": "Invalid signal state."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = serialize_signal_detail(signal=signal, membership=membership, request=request)
    return Response(SignalDetailSerializer(payload).data)


def _signal_command_response(
    *,
    request,
    establishment_id: uuid.UUID,
    signal_id: str,
    action: str,
) -> Response:
    membership = resolve_observation_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    signal = get_signal_for_detail(
        membership=membership,
        signal_id=uuid.UUID(str(signal_id)),
    )
    if signal is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if not can_pin_signal(membership, signal):
        return Response(
            {"code": "permission_denied", "detail": "Permission denied."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        if action == "pin":
            signal = pin_signal(signal=signal, membership=membership)
        else:
            signal = unpin_signal(signal=signal)
    except SignalStateError as exc:
        return Response(
            {"code": exc.error_code, "detail": "Invalid signal state."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = serialize_signal_detail(signal=signal, membership=membership, request=request)
    return Response(SignalDetailSerializer(payload).data)


def _parse_page_size(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return min(max(value, 1), MAX_PAGE_SIZE)
