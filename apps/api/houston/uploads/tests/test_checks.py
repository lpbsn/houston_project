from pathlib import Path

from houston.uploads.checks import (
    check_observation_media_preview_windows,
    check_private_media_backend,
    check_private_media_root_configured,
    check_private_media_root_writable,
    check_private_media_s3_configured,
)


def test_private_media_root_writable_check_passes(settings, tmp_path):
    settings.DEBUG = False
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = str(tmp_path / "private_media")

    errors = check_private_media_root_writable(None)

    assert errors == []
    assert (tmp_path / "private_media").is_dir()


def test_private_media_root_writable_check_skipped_in_debug(settings, tmp_path, monkeypatch):
    settings.DEBUG = True
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = str(tmp_path / "private_media")

    def deny_write_text(self, *args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "write_text", deny_write_text)

    errors = check_private_media_root_writable(None)

    assert errors == []


def test_private_media_root_writable_check_fails_when_not_writable(settings, tmp_path, monkeypatch):
    settings.DEBUG = False
    media_root = tmp_path / "private_media"
    media_root.mkdir()
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = str(media_root)

    def deny_write_text(self, *args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "write_text", deny_write_text)

    errors = check_private_media_root_writable(None)

    assert len(errors) == 1
    assert errors[0].id == "uploads.E001"


def test_private_media_root_configured_check_fails_when_empty_in_production(settings):
    settings.DEBUG = False
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = ""

    errors = check_private_media_root_configured(None)

    assert len(errors) == 1
    assert errors[0].id == "uploads.E002"


def test_private_media_root_configured_check_skipped_in_debug(settings):
    settings.DEBUG = True
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = ""

    errors = check_private_media_root_configured(None)

    assert errors == []


def test_filesystem_checks_still_require_writable_root(settings, tmp_path):
    settings.DEBUG = False
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = str(tmp_path / "private_media")

    assert check_private_media_backend(None) == []
    assert check_private_media_root_configured(None) == []
    assert check_private_media_root_writable(None) == []
    assert check_private_media_s3_configured(None) == []


def test_s3_backend_skips_filesystem_root_checks(settings):
    settings.DEBUG = False
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "s3"
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = ""
    settings.HOUSTON_S3_ENDPOINT_URL = "https://s3.example.invalid"
    settings.HOUSTON_S3_BUCKET = "houston-private-media"
    settings.HOUSTON_S3_ACCESS_KEY_ID = "access-key"
    settings.HOUSTON_S3_SECRET_ACCESS_KEY = "secret-key"
    settings.HOUSTON_S3_REGION = "auto"

    assert check_private_media_root_configured(None) == []
    assert check_private_media_root_writable(None) == []
    assert check_private_media_s3_configured(None) == []


def test_s3_backend_fails_when_required_settings_missing(settings):
    settings.DEBUG = False
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "s3"
    settings.HOUSTON_S3_ENDPOINT_URL = ""
    settings.HOUSTON_S3_BUCKET = ""
    settings.HOUSTON_S3_ACCESS_KEY_ID = ""
    settings.HOUSTON_S3_SECRET_ACCESS_KEY = ""
    settings.HOUSTON_S3_REGION = ""

    errors = check_private_media_s3_configured(None)

    assert len(errors) == 1
    assert errors[0].id == "uploads.E004"


def test_unknown_backend_fails_in_production(settings):
    settings.DEBUG = False
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "minio"

    errors = check_private_media_backend(None)

    assert len(errors) == 1
    assert errors[0].id == "uploads.E003"


def test_unknown_backend_skipped_in_debug(settings):
    settings.DEBUG = True
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "minio"

    assert check_private_media_backend(None) == []


def test_preview_windows_accept_default_p_greater_than_c_and_w_at_least_c(settings):
    settings.HOUSTON_OBSERVATION_MEDIA_PREVIEW_CACHE_MAX_AGE_SECONDS = 60
    settings.HOUSTON_OBSERVATION_MEDIA_PREVIEW_URL_BUCKET_SECONDS = 60
    settings.HOUSTON_OBSERVATION_MEDIA_S3_PRESIGN_TTL_SECONDS = 120

    assert check_observation_media_preview_windows(None) == []


def test_preview_windows_reject_presign_ttl_not_greater_than_cache(settings):
    settings.HOUSTON_OBSERVATION_MEDIA_PREVIEW_CACHE_MAX_AGE_SECONDS = 60
    settings.HOUSTON_OBSERVATION_MEDIA_PREVIEW_URL_BUCKET_SECONDS = 60
    settings.HOUSTON_OBSERVATION_MEDIA_S3_PRESIGN_TTL_SECONDS = 60

    errors = check_observation_media_preview_windows(None)

    assert len(errors) == 1
    assert errors[0].id == "uploads.E005"


def test_preview_windows_reject_bucket_shorter_than_cache(settings):
    settings.HOUSTON_OBSERVATION_MEDIA_PREVIEW_CACHE_MAX_AGE_SECONDS = 60
    settings.HOUSTON_OBSERVATION_MEDIA_PREVIEW_URL_BUCKET_SECONDS = 30
    settings.HOUSTON_OBSERVATION_MEDIA_S3_PRESIGN_TTL_SECONDS = 120

    errors = check_observation_media_preview_windows(None)

    assert len(errors) == 1
    assert errors[0].id == "uploads.E006"
