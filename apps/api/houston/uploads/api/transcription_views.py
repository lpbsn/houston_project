from __future__ import annotations

import tempfile
from pathlib import Path

from drf_spectacular.utils import OpenApiResponse, extend_schema
from houston.accounts.api.serializers import DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.ai.transcription import (
    TranscriptionInvalidAudioError,
    TranscriptionServiceError,
    TranscriptionTimeoutError,
    TranscriptionUnavailableError,
    transcribe_audio_file,
    validate_transcription_audio_upload,
)
from houston.establishments.permissions import HasActiveMembership
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.serializers import TranscriptionResponseSerializer
from houston.uploads.api.views import EstablishmentScopedObservationMixin
from houston.uploads.permissions import CanSubmitObservation
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView


class TranscriptionCreateView(EstablishmentScopedObservationMixin, APIView):
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
            200: TranscriptionResponseSerializer,
            400: OpenApiResponse(response=DetailResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            408: OpenApiResponse(response=DetailResponseSerializer),
            503: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Accepts multipart audio, transcribes via backend OpenAI, deletes the temp file "
            "in all cases, and returns editable text. Audio is never persisted."
        ),
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
                {"code": "missing_file", "detail": "An audio file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        declared_content_type = getattr(uploaded_file, "content_type", None)
        try:
            validate_transcription_audio_upload(
                uploaded_file=uploaded_file,
                declared_content_type=declared_content_type,
            )
        except TranscriptionInvalidAudioError as exc:
            return Response(
                {"code": exc.error_code, "detail": "Invalid audio upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suffix = _suffix_for_content_type(declared_content_type)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_path = Path(temp_file.name)

            result = transcribe_audio_file(
                establishment=membership.establishment,
                audio_path=temp_path,
                declared_content_type=declared_content_type,
            )
        except TranscriptionTimeoutError as exc:
            return Response(
                {"code": exc.error_code, "detail": "Transcription timed out."},
                status=status.HTTP_408_REQUEST_TIMEOUT,
            )
        except TranscriptionUnavailableError as exc:
            return Response(
                {"code": exc.error_code, "detail": "Transcription is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except TranscriptionServiceError as exc:
            return Response(
                {"code": exc.error_code, "detail": "Transcription failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

        serializer = TranscriptionResponseSerializer(
            {
                "text": result.text,
                "language": result.language,
                "correlation_id": result.correlation_id,
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


def _suffix_for_content_type(content_type: str | None) -> str:
    normalized = (content_type or "").split(";")[0].strip().lower()
    mapping = {
        "audio/webm": ".webm",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/m4a": ".m4a",
        "audio/x-m4a": ".m4a",
    }
    return mapping.get(normalized, ".bin")
