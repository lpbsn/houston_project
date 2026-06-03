from pathlib import Path

from houston.uploads.checks import check_private_media_root_writable


def test_private_media_root_writable_check_passes(settings, tmp_path):
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = str(tmp_path / "private_media")

    errors = check_private_media_root_writable(None)

    assert errors == []
    assert (tmp_path / "private_media").is_dir()


def test_private_media_root_writable_check_fails_when_not_writable(settings, tmp_path, monkeypatch):
    media_root = tmp_path / "private_media"
    media_root.mkdir()
    settings.HOUSTON_PRIVATE_MEDIA_ROOT = str(media_root)

    def deny_write_text(self, *args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "write_text", deny_write_text)

    errors = check_private_media_root_writable(None)

    assert len(errors) == 1
    assert errors[0].id == "uploads.E001"
