from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """Operational uploads are never exposed via a public URL."""

    def url(self, name, *args, **kwargs):
        raise NotImplementedError("Private operational media has no public URL.")


def get_private_media_storage() -> PrivateMediaStorage:
    return PrivateMediaStorage(
        location=settings.HOUSTON_PRIVATE_MEDIA_ROOT,
        base_url=None,
    )
