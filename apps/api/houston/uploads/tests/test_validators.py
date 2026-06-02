from __future__ import annotations

import io
import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from houston.accounts.models import User
from houston.establishments.models import Establishment
from houston.organizations.models import Organization
from houston.uploads.services import create_temporary_photo_upload
from houston.uploads.validators import (
    DetectedImageMetadata,
    FileTooLargeImageError,
    InvalidImageContentError,
    UnsupportedImageTypeError,
    _canonical_from_detected_format,
    validate_observation_photo_upload,
)
from PIL import Image

pytestmark = pytest.mark.django_db


def _jpeg_bytes(*, size: tuple[int, int] = (12, 12)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color="red").save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.read()


def _large_jpeg_bytes() -> bytes:
    width, height = 1536, 2048
    raw = os.urandom(width * height * 3)
    image = Image.frombytes("RGB", (width, height), raw)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    buffer.seek(0)
    data = buffer.read()
    assert len(data) > 1_000_000
    return data


def _png_file() -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="blue").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile("photo.png", buffer.read(), content_type="image/png")


def test_png_image_is_accepted():
    validated = validate_observation_photo_upload(
        uploaded_file=_png_file(),
        declared_content_type="image/png",
    )
    assert validated.stored_extension == "png"
    assert validated.content_type == "image/png"


def test_valid_jpeg_with_jpg_extension_is_accepted():
    uploaded = SimpleUploadedFile("IMG_0300.jpg", _jpeg_bytes(), content_type="image/jpeg")
    validated = validate_observation_photo_upload(
        uploaded_file=uploaded,
        declared_content_type="image/jpeg",
    )
    assert validated.stored_extension == "jpg"
    assert validated.content_type == "image/jpeg"


def test_valid_jpeg_with_jpeg_extension_is_accepted():
    uploaded = SimpleUploadedFile("IMG_0299.jpeg", _jpeg_bytes(), content_type="image/jpeg")
    validated = validate_observation_photo_upload(
        uploaded_file=uploaded,
        declared_content_type="image/jpeg",
    )
    assert validated.stored_extension == "jpg"
    assert validated.content_type == "image/jpeg"


def test_valid_jpeg_with_content_type_octet_stream_is_accepted_if_content_is_valid():
    uploaded = SimpleUploadedFile(
        "IMG_0299.jpeg",
        _jpeg_bytes(),
        content_type="application/octet-stream",
    )
    validated = validate_observation_photo_upload(
        uploaded_file=uploaded,
        declared_content_type="application/octet-stream",
    )
    assert validated.stored_extension == "jpg"
    assert validated.content_type == "image/jpeg"


def test_valid_jpeg_with_missing_content_type_is_accepted():
    uploaded = SimpleUploadedFile("IMG_0299.jpeg", _jpeg_bytes(), content_type="")
    validated = validate_observation_photo_upload(
        uploaded_file=uploaded,
        declared_content_type="",
    )
    assert validated.stored_extension == "jpg"
    assert validated.content_type == "image/jpeg"


def test_invalid_jpeg_content_is_rejected():
    uploaded = SimpleUploadedFile(
        "IMG_0299.jpeg",
        b"this is not a jpeg file",
        content_type="image/jpeg",
    )
    with pytest.raises(InvalidImageContentError) as exc_info:
        validate_observation_photo_upload(
            uploaded_file=uploaded,
            declared_content_type="image/jpeg",
        )
    assert exc_info.value.error_code == "invalid_image"


def test_file_pointer_is_reset_after_validation():
    source = _jpeg_bytes()
    uploaded = SimpleUploadedFile("IMG_0299.jpeg", source, content_type="image/jpeg")
    validate_observation_photo_upload(
        uploaded_file=uploaded,
        declared_content_type="image/jpeg",
    )
    uploaded.seek(0)
    reread = uploaded.read()
    assert len(reread) == len(source)
    assert reread[:2] == b"\xff\xd8"


def test_large_realistic_jpeg_around_one_mb_is_accepted():
    uploaded = SimpleUploadedFile(
        "IMG_0302.jpeg",
        _large_jpeg_bytes(),
        content_type="image/jpeg",
    )
    validated = validate_observation_photo_upload(
        uploaded_file=uploaded,
        declared_content_type="image/jpeg",
    )
    assert validated.content_type == "image/jpeg"


def test_mpo_format_is_normalized_as_jpeg():
    content_type, stored_extension = _canonical_from_detected_format("MPO")
    assert content_type == "image/jpeg"
    assert stored_extension == "jpg"


def test_mpo_detected_image_is_accepted_as_jpeg(monkeypatch):
    uploaded = SimpleUploadedFile(
        "IMG_0295.jpeg",
        _jpeg_bytes(),
        content_type="image/jpeg",
    )

    monkeypatch.setattr(
        "houston.uploads.validators._detect_image_metadata",
        lambda raw_bytes: DetectedImageMetadata(
            image_format="MPO",
            image_mode="RGB",
            image_size=(4032, 3024),
        ),
    )

    validated = validate_observation_photo_upload(
        uploaded_file=uploaded,
        declared_content_type="image/jpeg",
    )
    assert validated.content_type == "image/jpeg"
    assert validated.stored_extension == "jpg"


@override_settings(HOUSTON_OBSERVATION_PHOTO_MAX_BYTES=64)
def test_oversized_image_returns_file_too_large():
    uploaded = SimpleUploadedFile("large.jpeg", _jpeg_bytes(), content_type="image/jpeg")
    with pytest.raises(FileTooLargeImageError) as exc_info:
        validate_observation_photo_upload(
            uploaded_file=uploaded,
            declared_content_type="image/jpeg",
        )
    assert exc_info.value.error_code == "file_too_large"


def test_gif_image_is_rejected_as_unsupported_type():
    buffer = io.BytesIO()
    Image.new("P", (8, 8)).save(buffer, format="GIF")
    buffer.seek(0)
    uploaded = SimpleUploadedFile("photo.gif", buffer.read(), content_type="image/gif")

    with pytest.raises(UnsupportedImageTypeError) as exc_info:
        validate_observation_photo_upload(
            uploaded_file=uploaded,
            declared_content_type="image/gif",
        )
    assert exc_info.value.error_code == "unsupported_image_type"


def test_heic_image_is_accepted_when_encoder_available():
    pytest.importorskip("pillow_heif")
    import pillow_heif

    pillow_heif.register_heif_opener()
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="green").save(buffer, format="HEIF")
    buffer.seek(0)
    uploaded = SimpleUploadedFile("photo.heic", buffer.read(), content_type="image/heic")

    validated = validate_observation_photo_upload(
        uploaded_file=uploaded,
        declared_content_type="image/heic",
    )
    assert validated.stored_extension == "heic"
    assert validated.content_type == "image/heic"


def test_private_storage_has_no_public_url():
    from houston.uploads.private_storage import PrivateMediaStorage

    storage = PrivateMediaStorage(location="/tmp/houston-private-test")
    with pytest.raises(NotImplementedError):
        storage.url("establishments/example/photo.png")


def test_saved_upload_is_not_empty_after_validation():
    organization = Organization.objects.create(name="Upload Org", status=Organization.Status.ACTIVE)
    establishment = Establishment.objects.create(
        name="Upload Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    user = User.objects.create_user(
        username="upload_validator_user",
        email="upload_validator@example.com",
        password="secret-password-12",
        status=User.Status.ACTIVE,
    )
    uploaded = SimpleUploadedFile(
        "IMG_0299.jpeg",
        _jpeg_bytes(),
        content_type="application/octet-stream",
    )
    temporary_upload = create_temporary_photo_upload(
        establishment=establishment,
        uploaded_by=user,
        uploaded_file=uploaded,
        declared_content_type="application/octet-stream",
    )
    temporary_upload.file.open("rb")
    try:
        stored_bytes = temporary_upload.file.read()
    finally:
        temporary_upload.file.close()

    assert len(stored_bytes) > 0
    assert stored_bytes[:2] == b"\xff\xd8"
