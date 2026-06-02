from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiResponse, extend_schema
from houston.accounts.api.serializers import DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.permissions import HasActiveMembership
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.serializers import (
    TemporaryUploadResponseSerializer,
)
from houston.uploads.exceptions import UploadNotDeletableError, UploadNotFoundError
from houston.uploads.permissions import CanSubmitObservation
from houston.uploads.services import create_temporary_photo_upload, delete_temporary_upload
from houston.uploads.validators import ImageValidationError
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView


class EstablishmentScopedObservationMixin:
    establishment_id: uuid.UUID | None = None

    def initial(self, request, *args, **kwargs):
        raw_id = self.kwargs.get("establishment_id")
        self.establishment_id = uuid.UUID(str(raw_id))
        super().initial(request, *args, **kwargs)


class TemporaryUploadListCreateView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanSubmitObservation,
    ]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["uploads"],
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "format": "binary"},
                },
                "required": ["file"],
            }
        },
        responses={
            201: TemporaryUploadResponseSerializer,
            400: OpenApiResponse(response=DetailResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Creates a temporary private photo upload for an Observation.",
    )
    def post(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"code": "missing_file", "detail": "A file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            upload = create_temporary_photo_upload(
                establishment=membership.establishment,
                uploaded_by=request.user,
                uploaded_file=uploaded_file,
                declared_content_type=getattr(uploaded_file, "content_type", None),
            )
        except ImageValidationError as exc:
            detail = "Invalid image upload."
            if exc.error_code == "file_too_large":
                detail = "Image file exceeds maximum size."
            elif exc.error_code == "unsupported_image_type":
                detail = "Unsupported image type."
            return Response(
                {"code": exc.error_code, "detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TemporaryUploadResponseSerializer(
            {
                "id": upload.id,
                "status": upload.status,
                "expires_at": upload.expires_at,
            }
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TemporaryUploadDeleteView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanSubmitObservation,
    ]

    @extend_schema(
        tags=["uploads"],
        responses={
            204: OpenApiResponse(description="Deleted."),
            400: OpenApiResponse(response=DetailResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Deletes an unlinked temporary photo upload owned by the current user.",
    )
    def delete(self, request, establishment_id, upload_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            delete_temporary_upload(
                establishment_id=self.establishment_id,
                upload_id=uuid.UUID(str(upload_id)),
                actor=request.user,
            )
        except UploadNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except UploadNotDeletableError as exc:
            return Response(
                {"code": exc.error_code, "detail": "Upload cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
