import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from houston.uploads.private_storage import PrivateMediaStorage, get_private_media_storage
from storages.backends.s3 import S3Storage


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
