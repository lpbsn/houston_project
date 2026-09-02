from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.api.safety_serializers import (
    ContentReportCreateRequestSerializer,
    ContentReportResponseSerializer,
    MembershipBlockResponseSerializer,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import HasActiveMembership
from houston.establishments.safety_services import (
    ContentReportValidationError,
    block_membership,
    create_content_report,
    unblock_membership,
)
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin


def _resolve_membership(request, establishment_id):
    membership = resolve_observation_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return membership


class MembershipBlockView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["safety"],
        request=None,
        responses={
            201: MembershipBlockResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Blocks 1:1 DMs and mentions with another membership in this establishment.",
    )
    def post(self, request, establishment_id, membership_id):
        actor = _resolve_membership(request, self.establishment_id)
        if isinstance(actor, Response):
            return actor
        target = EstablishmentMembership.objects.filter(
            id=membership_id,
            establishment_id=self.establishment_id,
        ).first()
        if target is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            block = block_membership(actor_membership=actor, target_membership=target)
        except ContentReportValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            MembershipBlockResponseSerializer(
                {
                    "blocker_membership_id": block.blocker_membership_id,
                    "blocked_membership_id": block.blocked_membership_id,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["safety"],
        request=None,
        responses={
            204: OpenApiResponse(description="Block removed."),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Removes a block created by the current membership.",
    )
    def delete(self, request, establishment_id, membership_id):
        actor = _resolve_membership(request, self.establishment_id)
        if isinstance(actor, Response):
            return actor
        unblock_membership(actor_membership=actor, target_membership_id=membership_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContentReportCreateView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["safety"],
        request=ContentReportCreateRequestSerializer,
        responses={
            201: ContentReportResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Files an in-app content or user report. "
            "Operator is notified with identifiers only."
        ),
    )
    def post(self, request, establishment_id):
        actor = _resolve_membership(request, self.establishment_id)
        if isinstance(actor, Response):
            return actor
        serializer = ContentReportCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            report = create_content_report(
                actor_membership=actor,
                content_kind=serializer.validated_data["content_kind"],
                reason=serializer.validated_data["reason"],
                target_membership_id=serializer.validated_data.get("target_membership_id"),
                content_id=serializer.validated_data.get("content_id"),
            )
        except ContentReportValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            ContentReportResponseSerializer(
                {
                    "id": report.id,
                    "status": report.status,
                    "content_kind": report.content_kind,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )
