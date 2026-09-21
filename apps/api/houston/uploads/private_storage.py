from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage, Storage

PRIVATE_MEDIA_BACKEND_FILESYSTEM = "filesystem"
PRIVATE_MEDIA_BACKEND_S3 = "s3"
SUPPORTED_PRIVATE_MEDIA_BACKENDS = frozenset(
    {PRIVATE_MEDIA_BACKEND_FILESYSTEM, PRIVATE_MEDIA_BACKEND_S3}
)

logger = logging.getLogger(__name__)


def _is_missing_storage_object_error(exc: BaseException) -> bool:
    if isinstance(exc, FileNotFoundError):
        return True
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False
    error = response.get("Error") or {}
    code = str(error.get("Code") or "")
    return code in {"404", "NoSuchKey", "NotFound"}


def delete_private_media_object_idempotent(
    *,
    storage_key: str,
    storage: PrivateMediaStorage | None = None,
) -> None:
    if not storage_key:
        return
    storage = storage or get_private_media_storage()
    try:
        storage.delete(storage_key)
    except Exception as exc:
        if _is_missing_storage_object_error(exc):
            return
        logger.warning(
            "storage_file_delete_failed",
            extra={
                "event": "storage_file_delete_failed",
                "exception_class": type(exc).__name__,
            },
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


def _s3_object_key(*, inner: Storage, name: str) -> str:
    inner_type = type(inner)
    if hasattr(inner_type, "_clean_name") and hasattr(inner_type, "_normalize_name"):
        return inner._normalize_name(inner._clean_name(name))
    return name


def generate_private_media_presigned_get_url(
    *,
    name: str,
    storage: PrivateMediaStorage | None = None,
    expires_in: int | None = None,
) -> str:
    if storage is None:
        backend = getattr(
            settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", PRIVATE_MEDIA_BACKEND_FILESYSTEM
        )
        if (backend or "").strip().lower() != PRIVATE_MEDIA_BACKEND_S3:
            raise ImproperlyConfigured(
                "Presigned GET URLs require HOUSTON_PRIVATE_MEDIA_BACKEND=s3."
            )
        storage = get_private_media_storage()
    inner = storage._inner
    if not hasattr(inner, "bucket"):
        raise ImproperlyConfigured("Presigned GET URLs require an S3 private media backend.")
    ttl = int(
        expires_in
        if expires_in is not None
        else settings.HOUSTON_OBSERVATION_MEDIA_S3_PRESIGN_TTL_SECONDS
    )
    cache_control = f"private, max-age={ttl}, must-revalidate"
    client = inner.bucket.meta.client
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": inner.bucket_name,
            "Key": _s3_object_key(inner=inner, name=name),
            "ResponseCacheControl": cache_control,
        },
        ExpiresIn=ttl,
    )


def generate_private_media_presigned_put_url(
    *,
    name: str,
    content_type: str,
    storage: PrivateMediaStorage,
    expires_in: int,
) -> str:
    inner = storage._inner
    if not hasattr(inner, "bucket"):
        raise ImproperlyConfigured("Presigned PUT URLs require an S3 private media backend.")
    client = inner.bucket.meta.client
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": inner.bucket_name,
            "Key": _s3_object_key(inner=inner, name=name),
            "ContentType": content_type,
        },
        ExpiresIn=int(expires_in),
        HttpMethod="PUT",
    )


def _build_s3_storage(
    *,
    bucket: str,
    access_key: str,
    secret_key: str,
    endpoint_url: str,
    region: str,
    addressing_style: str,
) -> Storage:
    from storages.backends.s3 import S3Storage

    options: dict[str, object] = {
        "bucket_name": bucket,
        "access_key": access_key,
        "secret_key": secret_key,
        "endpoint_url": endpoint_url,
        "region_name": region,
        "default_acl": None,
        "querystring_auth": False,
        "file_overwrite": False,
    }
    if addressing_style:
        options["addressing_style"] = addressing_style
    return S3Storage(**options)


def _build_private_media_storage(
    *,
    backend: str,
    filesystem_root: str,
    bucket: str,
    access_key: str,
    secret_key: str,
    endpoint_url: str,
    region: str,
    addressing_style: str,
) -> PrivateMediaStorage:
    normalized = (backend or PRIVATE_MEDIA_BACKEND_FILESYSTEM).strip().lower()
    if normalized == PRIVATE_MEDIA_BACKEND_FILESYSTEM:
        return PrivateMediaStorage(
            FileSystemStorage(
                location=filesystem_root,
                base_url=None,
            )
        )
    if normalized == PRIVATE_MEDIA_BACKEND_S3:
        return PrivateMediaStorage(
            _build_s3_storage(
                bucket=bucket,
                access_key=access_key,
                secret_key=secret_key,
                endpoint_url=endpoint_url,
                region=region,
                addressing_style=addressing_style,
            )
        )
    raise ImproperlyConfigured(
        f"Unsupported private media backend={normalized!r}. Use 'filesystem' or 's3'."
    )


def get_private_media_storage() -> PrivateMediaStorage:
    backend = getattr(settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", PRIVATE_MEDIA_BACKEND_FILESYSTEM)
    return _build_private_media_storage(
        backend=backend,
        filesystem_root=settings.HOUSTON_PRIVATE_MEDIA_ROOT,
        bucket=settings.HOUSTON_S3_BUCKET,
        access_key=settings.HOUSTON_S3_ACCESS_KEY_ID,
        secret_key=settings.HOUSTON_S3_SECRET_ACCESS_KEY,
        endpoint_url=settings.HOUSTON_S3_ENDPOINT_URL,
        region=settings.HOUSTON_S3_REGION,
        addressing_style=(settings.HOUSTON_S3_ADDRESSING_STYLE or "").strip(),
    )


def get_chat_private_media_storage() -> PrivateMediaStorage:
    backend = getattr(settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", PRIVATE_MEDIA_BACKEND_FILESYSTEM)
    filesystem_root = getattr(
        settings,
        "HOUSTON_CHAT_PRIVATE_MEDIA_ROOT",
        "",
    ) or str(settings.BASE_DIR / "private_chat_media")
    return _build_private_media_storage(
        backend=backend,
        filesystem_root=filesystem_root,
        bucket=getattr(settings, "HOUSTON_CHAT_S3_BUCKET", ""),
        access_key=getattr(settings, "HOUSTON_CHAT_S3_ACCESS_KEY_ID", ""),
        secret_key=getattr(settings, "HOUSTON_CHAT_S3_SECRET_ACCESS_KEY", ""),
        endpoint_url=getattr(settings, "HOUSTON_CHAT_S3_ENDPOINT_URL", ""),
        region=getattr(settings, "HOUSTON_CHAT_S3_REGION", ""),
        addressing_style=(getattr(settings, "HOUSTON_CHAT_S3_ADDRESSING_STYLE", "") or "").strip(),
    )
