from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from houston.ai.models import AIUsageLog
from houston.establishments.models import Establishment

logger = logging.getLogger(__name__)

TRANSCRIPTION_SCHEMA_VERSION = "ai_transcription_v1"


class TranscriptionServiceError(Exception):
    error_code = "transcription_error"


class TranscriptionUnavailableError(TranscriptionServiceError):
    error_code = "transcription_unavailable"


class TranscriptionTimeoutError(TranscriptionServiceError):
    error_code = "transcription_timeout"


class TranscriptionInvalidAudioError(TranscriptionServiceError):
    error_code = "invalid_audio"


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    correlation_id: uuid.UUID
    provider: str
    model: str
    latency_ms: int


_ALLOWED_AUDIO_CONTENT_TYPES = frozenset(
    {
        "audio/webm",
        "audio/mp4",
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/m4a",
        "audio/x-m4a",
    }
)


def validate_transcription_audio_upload(
    *,
    uploaded_file,
    declared_content_type: str | None,
) -> None:
    size_bytes = int(getattr(uploaded_file, "size", 0) or 0)
    if size_bytes <= 0:
        raise TranscriptionInvalidAudioError("Empty audio file.")
    if size_bytes > settings.HOUSTON_TRANSCRIPTION_AUDIO_MAX_BYTES:
        raise TranscriptionInvalidAudioError("Audio file exceeds maximum size.")

    normalized_type = (declared_content_type or "").split(";")[0].strip().lower()
    if normalized_type and normalized_type not in _ALLOWED_AUDIO_CONTENT_TYPES:
        raise TranscriptionInvalidAudioError("Unsupported audio type.")


def transcribe_audio_file(
    *,
    establishment: Establishment,
    audio_path: Path,
    declared_content_type: str | None,
) -> TranscriptionResult:
    correlation_id = uuid.uuid4()
    provider_name = settings.HOUSTON_AI_TRANSCRIPTION_PROVIDER
    model_name = settings.HOUSTON_AI_TRANSCRIPTION_MODEL
    started_at = time.monotonic()

    if not settings.OPENAI_API_KEY:
        _write_transcription_usage_log(
            establishment=establishment,
            provider=provider_name,
            model=model_name,
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(started_at),
            error_code=TranscriptionUnavailableError.error_code,
            correlation_id=correlation_id,
        )
        raise TranscriptionUnavailableError("Transcription is not configured.")

    try:
        text, language = _call_openai_transcription(
            audio_path=audio_path,
            declared_content_type=declared_content_type,
        )
        if not text.strip():
            raise TranscriptionServiceError("Empty transcription result.")

        if len(text) > 1000:
            text = text[:1000]

        latency_ms = _elapsed_ms(started_at)
        _write_transcription_usage_log(
            establishment=establishment,
            provider=provider_name,
            model=model_name,
            status=AIUsageLog.Status.SUCCEEDED,
            latency_ms=latency_ms,
            error_code="",
            correlation_id=correlation_id,
        )
        return TranscriptionResult(
            text=text,
            language=language or "",
            correlation_id=correlation_id,
            provider=provider_name,
            model=model_name,
            latency_ms=latency_ms,
        )
    except TranscriptionServiceError as exc:
        _write_transcription_usage_log(
            establishment=establishment,
            provider=provider_name,
            model=model_name,
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(started_at),
            error_code=getattr(exc, "error_code", TranscriptionServiceError.error_code),
            correlation_id=correlation_id,
        )
        raise
    except Exception as exc:
        error_code = TranscriptionServiceError.error_code
        if "timeout" in exc.__class__.__name__.lower():
            error_code = TranscriptionTimeoutError.error_code
        _write_transcription_usage_log(
            establishment=establishment,
            provider=provider_name,
            model=model_name,
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(started_at),
            error_code=error_code,
            correlation_id=correlation_id,
        )
        logger.warning(
            "Transcription failed.",
            extra={
                "correlation_id": str(correlation_id),
                "establishment_id": str(establishment.id),
                "error_code": error_code,
            },
        )
        raise TranscriptionServiceError("Transcription failed.") from exc


def _call_openai_transcription(
    *,
    audio_path: Path,
    declared_content_type: str | None,
) -> tuple[str, str]:
    try:
        from openai import APITimeoutError, OpenAI
    except ImportError as exc:  # pragma: no cover
        raise TranscriptionUnavailableError("OpenAI SDK is not installed.") from exc

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.HOUSTON_AI_TRANSCRIPTION_TIMEOUT_SECONDS,
        max_retries=0,
    )
    mime_type = (declared_content_type or "audio/webm").split(";")[0].strip().lower()

    try:
        with audio_path.open("rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=settings.HOUSTON_AI_TRANSCRIPTION_MODEL,
                file=(audio_path.name, audio_file, mime_type),
            )
    except APITimeoutError as exc:
        raise TranscriptionTimeoutError("Transcription timed out.") from exc

    text = getattr(response, "text", "") or ""
    language = getattr(response, "language", "") or ""
    return text, language


def _write_transcription_usage_log(
    *,
    establishment: Establishment,
    provider: str,
    model: str,
    status: str,
    latency_ms: int,
    error_code: str,
    correlation_id: uuid.UUID,
) -> None:
    try:
        AIUsageLog.objects.create(
            ai_domain=AIUsageLog.Domain.TRANSCRIPTION,
            provider=provider,
            model=model,
            prompt_version=settings.HOUSTON_AI_TRANSCRIPTION_PROMPT_VERSION,
            schema_version=TRANSCRIPTION_SCHEMA_VERSION,
            status=status,
            latency_ms=latency_ms,
            error_code=error_code,
            correlation_id=correlation_id,
            establishment=establishment,
        )
    except Exception:
        logger.warning(
            "Failed to write transcription usage log.",
            extra={
                "ai_domain": AIUsageLog.Domain.TRANSCRIPTION,
                "provider": provider,
                "model": model,
                "status": status,
                "correlation_id": str(correlation_id),
                "establishment_id": str(establishment.id),
            },
        )


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)
