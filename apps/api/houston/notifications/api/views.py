from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.permissions import HasActiveMembership
from houston.notifications.api.serializers import (
    MarkAllNotificationsReadResponseSerializer,
    NotificationItemSerializer,
    NotificationListResponseSerializer,
    NotificationPreferencesSerializer,
    NotificationPreferencesUpdateSerializer,
    PushDeviceResponseSerializer,
    PushDeviceUpsertSerializer,
    serialize_notification,
)
from houston.notifications.constants import (
    INVALID_PAGE_SIZE_ERROR_DETAIL,
    INVALID_STATUS_FILTER_ERROR_DETAIL,
)
from houston.notifications.exceptions import NotificationCursorError
from houston.notifications.models import Notification
from houston.notifications.navigation import build_comment_navigation_index
from houston.notifications.push.services import (
    get_push_device_for_user,
    revoke_push_device,
    upsert_push_device,
)
from houston.notifications.selectors import build_notifications_page, count_unread_notifications
from houston.notifications.services import (
    get_notification_preferences,
    mark_all_notifications_read,
    mark_notification_read,
    update_notification_preferences,
)
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 50

VALID_STATUS_FILTERS = frozenset(
    {
        Notification.Status.UNREAD,
        Notification.Status.READ,
        Notification.Status.ARCHIVED,
    }
)


def _parse_page_size(raw: str | None) -> int:
    if raw is None or raw == "":
        return DEFAULT_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(INVALID_PAGE_SIZE_ERROR_DETAIL)
    if value < 1 or value > MAX_PAGE_SIZE:
        raise ValueError(INVALID_PAGE_SIZE_ERROR_DETAIL)
    return value


def _parse_status_filter(raw: str | None) -> str | None:
    if raw is None or raw == "":
        return None
    if raw not in VALID_STATUS_FILTERS:
        raise ValueError(INVALID_STATUS_FILTER_ERROR_DETAIL)
    return raw


class NotificationsListView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["notifications"],
        parameters=[
            OpenApiParameter(
                name="status",
                required=False,
                type=str,
                enum=list(VALID_STATUS_FILTERS),
            ),
            OpenApiParameter(name="page_size", required=False, type=int),
            OpenApiParameter(name="cursor", required=False, type=str),
        ],
        responses={
            200: NotificationListResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Lists in-app notifications for the authenticated recipient.",
    )
    def get(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            status_filter = _parse_status_filter(request.query_params.get("status"))
            page_size = _parse_page_size(request.query_params.get("page_size"))
        except ValueError as exc:
            return Response(
                {"code": "validation_error", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            page = build_notifications_page(
                membership=membership,
                status=status_filter,
                cursor=request.query_params.get("cursor"),
                page_size=page_size,
            )
        except NotificationCursorError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment_navigation_by_subject_id = build_comment_navigation_index(
            establishment_id=membership.establishment_id,
            notifications=page.items,
        )
        payload = {
            "items": [
                serialize_notification(
                    item,
                    comment_navigation_by_subject_id=comment_navigation_by_subject_id,
                )
                for item in page.items
            ],
            "next_cursor": page.next_cursor,
            "has_more": page.has_more,
            "applied_filters": {"status": page.applied_status},
            "counts": {"unread": count_unread_notifications(membership=membership)},
        }
        return Response(NotificationListResponseSerializer(payload).data)


class NotificationMarkReadView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["notifications"],
        request=None,
        responses={
            200: NotificationItemSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, notification_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        notification = mark_notification_read(
            membership=membership,
            notification_id=uuid.UUID(str(notification_id)),
        )
        if notification is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(NotificationItemSerializer(serialize_notification(notification)).data)


class NotificationsMarkAllReadView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["notifications"],
        request=None,
        responses={
            200: MarkAllNotificationsReadResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        updated_count = mark_all_notifications_read(
            membership=membership,
            establishment_id=self.establishment_id,
        )
        return Response({"updated_count": updated_count})


class NotificationPreferencesView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["notifications"],
        responses={
            200: NotificationPreferencesSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Returns in-app notification preferences for the authenticated recipient.",
    )
    def get(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = get_notification_preferences(membership=membership)
        return Response(NotificationPreferencesSerializer(payload).data)

    @extend_schema(
        tags=["notifications"],
        request=NotificationPreferencesUpdateSerializer,
        responses={
            200: NotificationPreferencesSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Updates in-app notification preferences for the authenticated recipient.",
    )
    def patch(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = NotificationPreferencesUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"code": "validation_error", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = update_notification_preferences(
            membership=membership,
            notifications_enabled=serializer.validated_data.get("notifications_enabled"),
            push_enabled=serializer.validated_data.get("push_enabled"),
        )
        return Response(NotificationPreferencesSerializer(payload).data)


def _serialize_push_device(device) -> dict:
    return {
        "id": device.id,
        "platform": device.platform,
        "created_at": device.created_at,
        "last_seen_at": device.last_seen_at,
    }


class PushDeviceUpsertView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["push"],
        request=PushDeviceUpsertSerializer,
        responses={
            200: PushDeviceResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description="Creates or updates an FCM push device for the authenticated user.",
    )
    def post(self, request):
        serializer = PushDeviceUpsertSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"code": "validation_error", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device = upsert_push_device(
            user=request.user,
            token=serializer.validated_data["token"],
            platform=serializer.validated_data["platform"],
        )
        payload = _serialize_push_device(device)
        return Response(PushDeviceResponseSerializer(payload).data)


class PushDeviceRevokeView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["push"],
        request=None,
        responses={
            204: OpenApiResponse(description="Device revoked."),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Soft-revokes an FCM push device for the authenticated user.",
    )
    def delete(self, request, device_id):
        device = get_push_device_for_user(
            device_id=uuid.UUID(str(device_id)),
            user=request.user,
        )
        if device is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        revoke_push_device(device=device, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
