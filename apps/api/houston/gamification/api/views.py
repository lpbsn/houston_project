from __future__ import annotations

import uuid

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.permissions import HasActiveMembership
from houston.gamification.api.serializers import (
    GamificationOverviewSerializer,
    GamificationTransactionListSerializer,
)
from houston.gamification.selectors import (
    build_point_transactions_page,
    gamification_overview_payload,
    serialize_point_transaction,
)
from houston.gamification.transaction_cursor import TransactionCursorError
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 50


class EstablishmentScopedGamificationMixin(EstablishmentScopedObservationMixin):
    pass


def _resolve_membership(request, establishment_id: uuid.UUID):
    membership = resolve_observation_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return membership


def _parse_page_size(raw: str | None) -> int:
    if raw is None or raw == "":
        return DEFAULT_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.") from None
    if value < 1 or value > MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")
    return value


def _parse_season_id(raw: str | None) -> uuid.UUID | None:
    if raw is None or raw == "":
        return None
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise ValueError("Invalid season_id.") from exc


class GamificationOverviewView(EstablishmentScopedGamificationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["gamification"],
        responses={
            200: GamificationOverviewSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Returns the authenticated membership gamification summary and rules.",
    )
    def get(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        payload = gamification_overview_payload(
            membership=membership,
            establishment=membership.establishment,
        )
        return Response(GamificationOverviewSerializer(payload).data)


class GamificationTransactionListView(EstablishmentScopedGamificationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["gamification"],
        parameters=[
            OpenApiParameter(name="page_size", required=False, type=int),
            OpenApiParameter(name="cursor", required=False, type=str),
            OpenApiParameter(name="season_id", required=False, type=OpenApiTypes.UUID),
        ],
        responses={
            200: GamificationTransactionListSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Lists point transactions for the authenticated membership.",
    )
    def get(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        try:
            page_size = _parse_page_size(request.query_params.get("page_size"))
            season_id = _parse_season_id(request.query_params.get("season_id"))
        except ValueError as exc:
            return Response(
                {"code": "validation_error", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            page = build_point_transactions_page(
                membership=membership,
                establishment_id=self.establishment_id,
                season_id=season_id,
                cursor=request.query_params.get("cursor"),
                page_size=page_size,
            )
        except TransactionCursorError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {
            "items": [serialize_point_transaction(item) for item in page.items],
            "next_cursor": page.next_cursor,
            "has_more": page.has_more,
        }
        return Response(GamificationTransactionListSerializer(payload).data)
