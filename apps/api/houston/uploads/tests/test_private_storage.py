from unittest.mock import MagicMock

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from houston.uploads.private_storage import (
    PrivateMediaStorage,
    generate_private_media_presigned_get_url,
    get_private_media_storage,
)
from storages.backends.s3 import S3Storage
from storages.utils import clean_name


def test_private_storage_has_no_public_url():
    storage = PrivateMediaStorage(location="/tmp/houston-private-test")
    with pytest.raises(NotImplementedError):
        storage.url("establishments/example/photo.png")


def test_factory_uses_filesystem_backend_by_default(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = str(tmp_path / "private_media")

    storage = get_private_media_storage()

    assert isinstance(storage, PrivateMediaStorage)
    assert isinstance(storage._inner, FileSystemStorage)
    assert storage._inner.location == str(tmp_path / "private_media")


def test_factory_builds_s3_storage_from_houston_settings(settings):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "s3"
    settings.HOUSTON_S3_ENDPOINT_URL = "https://s3.example.invalid"
    settings.HOUSTON_S3_BUCKET = "houston-private-media"
    settings.HOUSTON_S3_ACCESS_KEY_ID = "access-key"
    settings.HOUSTON_S3_SECRET_ACCESS_KEY = "secret-key"
    settings.HOUSTON_S3_REGION = "auto"
    settings.HOUSTON_S3_ADDRESSING_STYLE = "path"

    storage = get_private_media_storage()

    assert isinstance(storage, PrivateMediaStorage)
    assert isinstance(storage._inner, S3Storage)
    assert storage._inner.bucket_name == "houston-private-media"
    assert storage._inner.endpoint_url == "https://s3.example.invalid"
    assert storage._inner.region_name == "auto"
    assert storage._inner.addressing_style == "path"
    assert not hasattr(storage, "location")


def test_factory_rejects_unknown_backend(settings):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "minio"

    with pytest.raises(ImproperlyConfigured, match="minio"):
        get_private_media_storage()


def test_presign_get_uses_ttl_p_and_private_response_cache_control(settings, monkeypatch):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "s3"
    settings.HOUSTON_S3_ENDPOINT_URL = "https://s3.example.invalid"
    settings.HOUSTON_S3_BUCKET = "houston-private-media"
    settings.HOUSTON_S3_ACCESS_KEY_ID = "access-key"
    settings.HOUSTON_S3_SECRET_ACCESS_KEY = "secret-key"
    settings.HOUSTON_S3_REGION = "auto"
    settings.HOUSTON_S3_ADDRESSING_STYLE = "path"
    settings.HOUSTON_OBSERVATION_MEDIA_S3_PRESIGN_TTL_SECONDS = 120

    storage = get_private_media_storage()
    inner = storage._inner
    assert isinstance(inner, S3Storage)

    monkeypatch.setattr(
        "houston.uploads.private_storage.get_private_media_storage",
        lambda: storage,
    )
    generate_presigned_url = MagicMock(return_value="https://bucket.example/object")
    monkeypatch.setattr(inner.bucket.meta.client, "generate_presigned_url", generate_presigned_url)

    name = "establishments/example/photo.jpg"
    url = generate_private_media_presigned_get_url(name=name)

    assert url == "https://bucket.example/object"
    # django-storages write path: clean_name() + _normalize_name (no inner._clean_name).
    expected_key = inner._normalize_name(clean_name(name))
    generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={
            "Bucket": inner.bucket_name,
            "Key": expected_key,
            "ResponseCacheControl": "private, max-age=120, must-revalidate",
        },
        ExpiresIn=120,
    )
    params = generate_presigned_url.call_args.kwargs["Params"]
    assert "public" not in params["ResponseCacheControl"]
    assert "max-age=121" not in params["ResponseCacheControl"]


def test_presign_get_rejected_on_filesystem_backend(settings):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"

    with pytest.raises(ImproperlyConfigured, match="s3"):
        generate_private_media_presigned_get_url(name="establishments/example/photo.jpg")
