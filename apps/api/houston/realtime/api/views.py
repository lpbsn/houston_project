from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import AccessTokenAuthContext, BearerAccessTokenAuthentication
from houston.establishments.permissions import HasActiveMembership
from houston.realtime.access import resolve_operational_realtime_actor_membership
from houston.realtime.api.serializers import RealtimeWsTicketResponseSerializer
from houston.realtime.ws_ticket import issue_ws_ticket


class EstablishmentScopedRealtimeMixin:
    establishment_id: uuid.UUID | None = None

    def initial(self, request, *args, **kwargs):
        raw_id = self.kwargs.get("establishment_id")
        self.establishment_id = uuid.UUID(str(raw_id))
        super().initial(request, *args, **kwargs)


class CanAccessOperationalRealtime(permissions.BasePermission):
    message = "You do not have permission to access operational realtime for this establishment."

    def has_permission(self, request, view) -> bool:
        membership = resolve_operational_realtime_actor_membership(
            request,
            establishment_id=view.establishment_id,
        )
        return membership is not None


def _resolve_membership(request, establishment_id: uuid.UUID):
    membership = resolve_operational_realtime_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return membership


class RealtimeWsTicketView(EstablishmentScopedRealtimeMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessOperationalRealtime,
    ]

    @extend_schema(
        tags=["realtime"],
        request=None,
        responses={
            200: RealtimeWsTicketResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        auth_context = request.auth
        if not isinstance(auth_context, AccessTokenAuthContext):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        ticket, expires_in = issue_ws_ticket(
            membership=membership,
            session_id=auth_context.session.id,
        )
        serializer = RealtimeWsTicketResponseSerializer(
            {"ticket": ticket, "expires_in": expires_in},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
