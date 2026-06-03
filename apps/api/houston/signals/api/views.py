from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.permissions import HasActiveMembership
from houston.signals.api.serializers import (
    SignalDetailSerializer,
    SignalFeedResponseSerializer,
    SignalUrgencyRequestSerializer,
    serialize_signal_detail,
    serialize_signal_feed_item,
)
from houston.signals.exceptions import SignalStateError, SignalValidationError
from houston.signals.feed_filters import (
    SignalFeedFilterValidationError,
    build_applied_filters_payload,
    parse_signal_feed_filters,
)
from houston.signals.permissions import (
    can_cancel_signal,
    can_pin_signal,
    can_resolve_signal,
    can_set_signal_urgency,
    can_view_signal_feed,
)
from houston.signals.selectors import get_signal_for_detail, signal_feed_queryset
from houston.signals.services import (
    cancel_signal,
    pin_signal,
    resolve_signal,
    set_signal_urgency,
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
                name="statuses",
                required=False,
                type=str,
                description="Comma-separated feed statuses: open, in_progress, resolved (max 3).",
            ),
            OpenApiParameter(
                name="module_keys",
                required=False,
                type=str,
                description="Comma-separated operational module keys (max 20).",
            ),
            OpenApiParameter(
                name="domain_keys",
                required=False,
                type=str,
                description="Comma-separated operational domain keys (max 50).",
            ),
            OpenApiParameter(
                name="subject_keys",
                required=False,
                type=str,
                description="Comma-separated operational subject keys (max 100).",
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
            feed_filters = parse_signal_feed_filters(
                query_params=request.query_params,
                establishment_id=self.establishment_id,
            )
        except SignalFeedFilterValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = signal_feed_queryset(
            membership=membership,
            view_mode=view_mode,  # type: ignore[arg-type]
            filters=feed_filters if feed_filters.has_any() else None,
        )
        items = list(queryset[:page_size])

        payload = {
            "items": [
                serialize_signal_feed_item(signal=signal, membership=membership) for signal in items
            ],
            "next_cursor": None,
            "has_more": queryset.count() > page_size,
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

        payload = serialize_signal_detail(signal=signal, membership=membership)
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


class SignalUrgencyView(EstablishmentScopedSignalMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewSignalFeed,
    ]

    @extend_schema(
        tags=["signals"],
        request=SignalUrgencyRequestSerializer,
        responses={
            200: SignalDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def patch(self, request, establishment_id, signal_id):
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

        if not can_set_signal_urgency(membership, signal):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        body = SignalUrgencyRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        try:
            signal = set_signal_urgency(
                signal=signal,
                urgency=body.validated_data["urgency"],
            )
        except (SignalStateError, SignalValidationError) as exc:
            return Response(
                {"code": exc.error_code, "detail": "Invalid signal state."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = serialize_signal_detail(signal=signal, membership=membership)
        return Response(SignalDetailSerializer(payload).data)


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
    else:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        if action == "cancel":
            signal = cancel_signal(signal=signal)
        else:
            signal = resolve_signal(signal=signal)
    except SignalStateError as exc:
        return Response(
            {"code": exc.error_code, "detail": "Invalid signal state."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = serialize_signal_detail(signal=signal, membership=membership)
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

    payload = serialize_signal_detail(signal=signal, membership=membership)
    return Response(SignalDetailSerializer(payload).data)


def _parse_page_size(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return min(max(value, 1), MAX_PAGE_SIZE)
