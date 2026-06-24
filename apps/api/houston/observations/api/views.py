from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from houston.accounts.api.serializers import (
    ApiErrorResponseSerializer,
    DetailResponseSerializer,
)
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.permissions import HasActiveMembership
from houston.observations.api.serializers import (
    ObservationProcessingStatusResponseSerializer,
    ObservationSubmitRequestSerializer,
    ObservationSubmitResponseSerializer,
)
from houston.observations.exceptions import (
    ObservationUploadNotFoundError,
    ObservationValidationError,
)
from houston.observations.models import ObservationProcessing
from houston.observations.selectors import get_observation_processing_status
from houston.observations.services import submit_observation
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin
from houston.uploads.permissions import CanSubmitObservation
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class ObservationSubmitView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanSubmitObservation,
    ]

    @extend_schema(
        tags=["observations"],
        request=ObservationSubmitRequestSerializer,
        responses={
            201: ObservationSubmitResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Submits a validated Observation with optional linked temporary photo uploads. "
            "Raw text is persisted internally and is not returned."
        ),
    )
    def post(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ObservationSubmitRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            observation = submit_observation(
                membership=membership,
                text=serializer.validated_data["text"],
                temporary_upload_ids=serializer.validated_data.get(
                    "temporary_upload_ids",
                    [],
                ),
            )
        except ObservationValidationError as exc:
            return Response(
                {"code": exc.error_code, "detail": "Invalid observation submission."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ObservationUploadNotFoundError as exc:
            return Response(
                {"code": exc.error_code, "detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        media_count = observation.media_items.count()
        response_serializer = ObservationSubmitResponseSerializer(
            {
                "id": observation.id,
                "submitted_at": observation.submitted_at,
                "media_count": media_count,
                "processing_status": ObservationProcessing.Status.QUEUED,
            }
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ObservationProcessingStatusView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanSubmitObservation,
    ]

    @extend_schema(
        tags=["observations"],
        responses={
            200: ObservationProcessingStatusResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Returns AI pipeline processing status for a submitted Observation. "
            "Visible to the submitter and establishment admins (owner/director) only. "
            "Does not expose raw observation text or AI prompts."
        ),
    )
    def get(self, request, establishment_id, observation_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        projection = get_observation_processing_status(
            membership=membership,
            observation_id=observation_id,
        )
        if projection is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        response_serializer = ObservationProcessingStatusResponseSerializer(
            {
                "observation_id": projection.observation_id,
                "status": projection.status,
                "outcome": projection.outcome,
                "signal_ids": projection.signal_ids,
                "signals": [
                    {
                        "id": summary.id,
                        "title": summary.title,
                        "affected_business_unit_key": summary.affected_business_unit_key,
                        "affected_business_unit_label": summary.affected_business_unit_label,
                        "responsible_business_unit_key": summary.responsible_business_unit_key,
                        "responsible_business_unit_label": summary.responsible_business_unit_label,
                        "activity_subject_key": summary.activity_subject_key,
                        "activity_subject_label": summary.activity_subject_label,
                        "location_text": summary.location_text,
                    }
                    for summary in projection.signals
                ],
                "last_error_code": projection.last_error_code,
                "ux_status": projection.ux_status,
                "created_at": projection.created_at,
                "updated_at": projection.updated_at,
                "processed_at": projection.processed_at,
            }
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)
