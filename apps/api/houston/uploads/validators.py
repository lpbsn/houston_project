from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from django.conf import settings
from PIL import Image

try:
    import pillow_heif
except ImportError:  # pragma: no cover
    pillow_heif = None

logger = logging.getLogger(__name__)


class ImageValidationError(Exception):
    error_code = "invalid_image"


class FileTooLargeImageError(ImageValidationError):
    error_code = "file_too_large"


class UnsupportedImageTypeError(ImageValidationError):
    error_code = "unsupported_image_type"


class InvalidImageContentError(ImageValidationError):
    error_code = "invalid_image"


@dataclass(frozen=True)
class ValidatedImage:
    content_type: str
    stored_extension: str
    size_bytes: int


# Canonical mapping from detected Pillow format to stored MIME + extension.
_PIL_FORMAT_TO_CANONICAL: dict[str, tuple[str, str]] = {
    "JPEG": ("image/jpeg", "jpg"),
    "JPG": ("image/jpeg", "jpg"),
    "MPO": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
    "HEIF": ("image/heic", "heic"),
    "HEIC": ("image/heic", "heic"),
}

def _ensure_heif_opener_registered() -> None:
    if pillow_heif is not None:
        pillow_heif.register_heif_opener()


def _read_upload_bytes(uploaded_file) -> bytes:
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    return raw_bytes


@dataclass(frozen=True)
class DetectedImageMetadata:
    image_format: str
    image_mode: str
    image_size: tuple[int, int]


def _detect_image_metadata(raw_bytes: bytes) -> DetectedImageMetadata:
    try:
        with Image.open(io.BytesIO(raw_bytes)) as image:
            image.verify()
    except Exception as exc:
        raise InvalidImageContentError("Invalid image content.") from exc

    try:
        with Image.open(io.BytesIO(raw_bytes)) as image:
            image.load()
            detected_format = (image.format or "").upper()
            detected_mode = image.mode
            detected_size = image.size
    except Exception as exc:
        raise InvalidImageContentError("Invalid image content.") from exc

    if not detected_format:
        raise InvalidImageContentError("Invalid image content.")
    return DetectedImageMetadata(
        image_format=detected_format,
        image_mode=detected_mode,
        image_size=detected_size,
    )


def _canonical_from_detected_format(detected_format: str) -> tuple[str, str]:
    canonical = _PIL_FORMAT_TO_CANONICAL.get(detected_format)
    if canonical is None:
        raise UnsupportedImageTypeError("Unsupported image type.")
    return canonical


def validate_observation_photo_upload(
    *,
    uploaded_file,
    declared_content_type: str | None,
) -> ValidatedImage:
    _ensure_heif_opener_registered()

    size_bytes = int(getattr(uploaded_file, "size", 0) or 0)
    if size_bytes <= 0:
        raise InvalidImageContentError("Empty file.")
    if size_bytes > settings.HOUSTON_OBSERVATION_PHOTO_MAX_BYTES:
        raise FileTooLargeImageError("File exceeds maximum size.")

    raw_bytes = _read_upload_bytes(uploaded_file)
    detected = _detect_image_metadata(raw_bytes)
    normalized_declared = (declared_content_type or "").split(";")[0].strip().lower()
    try:
        content_type, stored_extension = _canonical_from_detected_format(detected.image_format)
    except UnsupportedImageTypeError:
        # Safe diagnostic metadata only; no file bytes/content logged.
        logger.warning(
            "Unsupported temporary upload image type: "
            "uploaded_filename=%s declared_content_type=%s size_bytes=%s "
            "pillow_image_format=%s pillow_image_mode=%s pillow_image_size=%s "
            "heif_plugin_loaded=%s error_raised_at=%s",
            getattr(uploaded_file, "name", ""),
            normalized_declared,
            size_bytes,
            detected.image_format,
            detected.image_mode,
            detected.image_size,
            pillow_heif is not None,
            "_canonical_from_detected_format",
        )
        raise

    uploaded_file.seek(0)
    return ValidatedImage(
        content_type=content_type,
        stored_extension=stored_extension,
        size_bytes=size_bytes,
    )
