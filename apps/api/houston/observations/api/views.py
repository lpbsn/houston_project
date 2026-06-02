from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from houston.accounts.api.serializers import DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.permissions import HasActiveMembership
from houston.observations.api.serializers import (
    ObservationSubmitRequestSerializer,
    ObservationSubmitResponseSerializer,
)
from houston.observations.exceptions import (
    ObservationUploadNotFoundError,
    ObservationValidationError,
)
from houston.observations.models import ObservationProcessing
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
            400: OpenApiResponse(response=DetailResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
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
