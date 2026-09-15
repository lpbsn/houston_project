from __future__ import annotations

import logging
from unittest.mock import MagicMock

from houston.uploads.private_storage import (
    PrivateMediaStorage,
    delete_private_media_object_idempotent,
)


def test_delete_missing_key_succeeds_on_filesystem(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_BACKEND = "filesystem"
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = str(tmp_path / "private_media")

    delete_private_media_object_idempotent(storage_key="missing/orphan.png")


def test_delete_does_not_fall_back_to_storage_location(monkeypatch, tmp_path):
    media_root = tmp_path / "should-not-be-used"
    media_root.mkdir()
    sentinel_key = "orphan.png"
    sentinel = media_root / sentinel_key
    sentinel.write_bytes(b"keep")
    deleted: list[str] = []

    class Inner:
        location = str(media_root)

        def delete(self, name):
            deleted.append(name)

    monkeypatch.setattr(
        "houston.uploads.private_storage.get_private_media_storage",
        lambda: PrivateMediaStorage(inner=Inner()),
    )

    delete_private_media_object_idempotent(storage_key=sentinel_key)

    assert deleted == [sentinel_key]
    assert sentinel.is_file()
    assert not hasattr(PrivateMediaStorage(inner=Inner()), "location")


def test_delete_missing_object_error_is_success(monkeypatch):
    inner = MagicMock()
    inner.delete.side_effect = FileNotFoundError("missing")
    monkeypatch.setattr(
        "houston.uploads.private_storage.get_private_media_storage",
        lambda: PrivateMediaStorage(inner=inner),
    )

    delete_private_media_object_idempotent(storage_key="gone.png")

    inner.delete.assert_called_once_with("gone.png")


def test_delete_unexpected_error_logs_key_and_exception_class(monkeypatch, caplog):
    inner = MagicMock()
    inner.delete.side_effect = RuntimeError("storage unavailable")
    monkeypatch.setattr(
        "houston.uploads.private_storage.get_private_media_storage",
        lambda: PrivateMediaStorage(inner=inner),
    )

    with caplog.at_level(logging.WARNING, logger="houston.uploads.private_storage"):
        delete_private_media_object_idempotent(storage_key="establishments/example/photo.png")

    records = [
        record for record in caplog.records if record.getMessage() == "storage_file_delete_failed"
    ]
    assert len(records) == 1
    assert records[0].storage_key == "establishments/example/photo.png"
    assert records[0].exception_class == "RuntimeError"
