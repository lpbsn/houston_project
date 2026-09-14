from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage, Storage

PRIVATE_MEDIA_BACKEND_FILESYSTEM = "filesystem"
PRIVATE_MEDIA_BACKEND_S3 = "s3"
SUPPORTED_PRIVATE_MEDIA_BACKENDS = frozenset(
    {PRIVATE_MEDIA_BACKEND_FILESYSTEM, PRIVATE_MEDIA_BACKEND_S3}
)


class PrivateMediaStorage(Storage):
    """Wraps an inner Django Storage and never exposes a public URL."""

    def __init__(
        self,
        inner: Storage | None = None,
        *,
        location: str | None = None,
        base_url: str | None = None,
    ):
        super().__init__()
        if inner is not None:
            self._inner = inner
            return
        self._inner = FileSystemStorage(
            location=location or settings.HOUSTON_PRIVATE_MEDIA_ROOT,
            base_url=None,
        )

    def url(self, name, *args, **kwargs):
        raise NotImplementedError("Private operational media has no public URL.")

    def save(self, name, content, max_length=None):
        return self._inner.save(name, content, max_length=max_length)

    def _save(self, name, content):
        return self._inner._save(name, content)

    def open(self, name, mode="rb"):
        return self._inner.open(name, mode)

    def exists(self, name):
        return self._inner.exists(name)

    def delete(self, name):
        return self._inner.delete(name)

    def size(self, name):
        return self._inner.size(name)

    def generate_filename(self, filename):
        return self._inner.generate_filename(filename)

    def get_available_name(self, name, max_length=None):
        return self._inner.get_available_name(name, max_length=max_length)

    def get_valid_name(self, name):
        return self._inner.get_valid_name(name)


def _build_s3_storage() -> Storage:
    from storages.backends.s3 import S3Storage

    options: dict[str, object] = {
        "bucket_name": settings.HOUSTON_S3_BUCKET,
        "access_key": settings.HOUSTON_S3_ACCESS_KEY_ID,
        "secret_key": settings.HOUSTON_S3_SECRET_ACCESS_KEY,
        "endpoint_url": settings.HOUSTON_S3_ENDPOINT_URL,
        "region_name": settings.HOUSTON_S3_REGION,
        "default_acl": None,
        "querystring_auth": False,
        "file_overwrite": False,
    }
    addressing_style = (settings.HOUSTON_S3_ADDRESSING_STYLE or "").strip()
    if addressing_style:
        options["addressing_style"] = addressing_style
    return S3Storage(**options)


def get_private_media_storage() -> PrivateMediaStorage:
    backend = getattr(settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", PRIVATE_MEDIA_BACKEND_FILESYSTEM)
    backend = (backend or PRIVATE_MEDIA_BACKEND_FILESYSTEM).strip().lower()
    if backend == PRIVATE_MEDIA_BACKEND_FILESYSTEM:
        return PrivateMediaStorage(
            FileSystemStorage(
                location=settings.HOUSTON_PRIVATE_MEDIA_ROOT,
                base_url=None,
            )
        )
    if backend == PRIVATE_MEDIA_BACKEND_S3:
        return PrivateMediaStorage(_build_s3_storage())
    raise ImproperlyConfigured(
        f"Unsupported HOUSTON_PRIVATE_MEDIA_BACKEND={backend!r}. "
        "Use 'filesystem' or 's3'."
    )
