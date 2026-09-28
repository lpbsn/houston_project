from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.action_plans.api.serializers import (
    ExecutionHistoryResponseSerializer,
    serialize_execution_history_page,
)
from houston.action_plans.constants import TERMINAL_EXECUTION_STATUSES
from houston.action_plans.execution_history import build_execution_history_page
from houston.action_plans.history_cursor import parse_execution_history_cursor
from houston.core.history_query import parse_history_query
from houston.core.opaque_cursor import OpaqueCursorError
from houston.establishments.management_scope import (
    resolve_management_memberships_for_scope,
    user_can_access_management_scope,
)
from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import HasActiveMembership
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin

_HISTORY_PARAMETERS = [
    OpenApiParameter(name="view_mode", required=True, type=str, enum=["personal", "general"]),
    OpenApiParameter(name="page_size", required=False, type=int),
    OpenApiParameter(
        name="cursor",
        required=False,
        type=str,
        description="Opaque continuation cursor. Continuation returns items only.",
    ),
    OpenApiParameter(
        name="period",
        required=False,
        type=str,
        enum=["7", "30", "90", "custom", "all"],
        description="Paris civil days. Defaults to 30, today included.",
    ),
    OpenApiParameter(
        name="from",
        required=False,
        type=str,
        description="Custom period start, YYYY-MM-DD.",
    ),
    OpenApiParameter(
        name="to",
        required=False,
        type=str,
        description="Custom period end, YYYY-MM-DD, inclusive.",
    ),
    OpenApiParameter(
        name="status",
        required=False,
        type=str,
        enum=["all", "done", "canceled"],
        description="Defaults to all terminal statuses.",
    ),
]


def _history_error(exc: Exception) -> Response:
    code = getattr(exc, "code", None) or "validation_error"
    detail = getattr(exc, "detail", None) or str(exc)
    return Response({"code": code, "detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _prepare_memberships(
    memberships: list[EstablishmentMembership],
) -> list[EstablishmentMembership]:
    if not memberships:
        return []
    by_id = {
        membership.id: membership
        for membership in EstablishmentMembership.objects.filter(
            pk__in=[membership.pk for membership in memberships],
        )
        .select_related("establishment")
        .prefetch_related(membership_scope_prefetch())
    }
    return [by_id[membership.id] for membership in memberships if membership.id in by_id]


class ExecutionHistoryView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
    ]

    @extend_schema(
        tags=["action-plans"],
        operation_id="v1_execution_history_retrieve",
        parameters=_HISTORY_PARAMETERS,
        responses={
            200: ExecutionHistoryResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
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
        return _execution_history_response(request, memberships=[membership], scope="establishment")


class CanAccessCrossScope(permissions.BasePermission):
    message = "You do not have permission to access the cross-establishment scope."

    def has_permission(self, request, view) -> bool:
        return user_can_access_management_scope(request.user)


class CrossExecutionHistoryView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessCrossScope,
    ]

    @extend_schema(
        tags=["action-plans"],
        operation_id="v1_cross_execution_history_retrieve",
        parameters=_HISTORY_PARAMETERS,
        responses={
            200: ExecutionHistoryResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request):
        memberships = resolve_management_memberships_for_scope(request.user)
        return _execution_history_response(request, memberships=memberships, scope="cross")


def _execution_history_response(request, *, memberships, scope: str) -> Response:
    try:
        query = parse_history_query(
            request.query_params,
            statuses=TERMINAL_EXECUTION_STATUSES,
            now=timezone.now(),
        )
        cursor = parse_execution_history_cursor(request.query_params.get("cursor"))
        page = build_execution_history_page(
            memberships=_prepare_memberships(memberships),
            view_mode=query.view_mode,
            scope=scope,
            status=query.status,
            period=query.period,
            period_from=query.period_from,
            period_to=query.period_to,
            window=query.window,
            page_size=query.page_size,
            cursor=cursor,
        )
    except (OpaqueCursorError, ValueError) as exc:
        return _history_error(exc)
    return Response(ExecutionHistoryResponseSerializer(serialize_execution_history_page(page)).data)
