from __future__ import annotations

import uuid

from django.http import FileResponse, Http404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from houston.observations.media_access import resolve_observation_media_preview
from houston.uploads.api.views import EstablishmentScopedObservationMixin
from houston.uploads.private_storage import get_private_media_storage
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


class ObservationMediaPreviewView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["observations"],
        parameters=[
            OpenApiParameter(
                name="token",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Binary media preview."),
            404: OpenApiResponse(description="Not found."),
        },
    )
    def get(self, request, establishment_id, media_id):
        token = request.query_params.get("token", "").strip()
        media = resolve_observation_media_preview(
            establishment_id=uuid.UUID(str(establishment_id)),
            media_id=uuid.UUID(str(media_id)),
            token=token,
        )
        if media is None:
            raise Http404

        storage = get_private_media_storage()
        storage_key = media.storage_key
        if not storage_key or not storage.exists(storage_key):
            raise Http404

        file_handle = storage.open(storage_key, "rb")
        response = FileResponse(file_handle, content_type=media.content_type)
        response["Cache-Control"] = "private, no-store"
        return response
