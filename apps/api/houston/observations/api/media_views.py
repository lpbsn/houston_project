from __future__ import annotations

import uuid

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from houston.observations.media_access import (
    PREVIEW_VARIANT_FULL,
    PREVIEW_VARIANT_THUMBNAIL,
    observation_media_preview_cache_max_age_seconds,
    observation_media_preview_storage_key,
    parse_observation_media_preview_variant,
    resolve_observation_media_preview,
)
from houston.uploads.api.views import EstablishmentScopedObservationMixin
from houston.uploads.private_storage import (
    PRIVATE_MEDIA_BACKEND_S3,
    generate_private_media_presigned_get_url,
    get_private_media_storage,
)
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

_THUMBNAIL_CONTENT_TYPE = "image/jpeg"


def _is_s3_private_media_backend() -> bool:
    backend = getattr(settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", "")
    return (backend or "").strip().lower() == PRIVATE_MEDIA_BACKEND_S3


def _apply_preview_response_headers(response):
    max_age = observation_media_preview_cache_max_age_seconds()
    response["Cache-Control"] = f"private, max-age={max_age}, must-revalidate"
    response["Referrer-Policy"] = "no-referrer"
    return response


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
            OpenApiParameter(
                name="variant",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[PREVIEW_VARIANT_FULL, PREVIEW_VARIANT_THUMBNAIL],
                description="full (default) or thumbnail.",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Binary media preview."),
            302: OpenApiResponse(description="Redirect to a short-lived private storage GET."),
            404: OpenApiResponse(description="Not found."),
        },
    )
    def get(self, request, establishment_id, media_id):
        token = request.query_params.get("token", "").strip()
        variant = parse_observation_media_preview_variant(
            request.query_params.get("variant"),
        )
        if variant is None:
            raise Http404
        media = resolve_observation_media_preview(
            establishment_id=uuid.UUID(str(establishment_id)),
            media_id=uuid.UUID(str(media_id)),
            token=token,
        )
        if media is None:
            raise Http404

        storage = get_private_media_storage()
        storage_key = observation_media_preview_storage_key(media=media, variant=variant)
        if not storage_key or not storage.exists(storage_key):
            raise Http404

        if _is_s3_private_media_backend():
            location = generate_private_media_presigned_get_url(name=storage_key)
            return _apply_preview_response_headers(HttpResponseRedirect(location))

        content_type = (
            _THUMBNAIL_CONTENT_TYPE if variant == PREVIEW_VARIANT_THUMBNAIL else media.content_type
        )
        file_handle = storage.open(storage_key, "rb")
        return _apply_preview_response_headers(
            FileResponse(file_handle, content_type=content_type)
        )
