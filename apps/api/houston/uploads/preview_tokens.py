from __future__ import annotations

import time
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner, b62_encode


def upload_preview_token_ttl_seconds() -> int:
    return int(getattr(settings, "HOUSTON_UPLOAD_PREVIEW_TOKEN_TTL_SECONDS", 3600))


def upload_preview_token_bucket_seconds() -> int:
    return int(getattr(settings, "HOUSTON_UPLOAD_PREVIEW_TOKEN_BUCKET_SECONDS", 60))


class _BucketedTimestampSigner(TimestampSigner):
    def timestamp(self) -> str:
        window = max(1, upload_preview_token_bucket_seconds())
        bucketed = (int(time.time()) // window) * window
        return b62_encode(bucketed)


def sign_upload_preview_token(
    *,
    salt: str,
    establishment_id: uuid.UUID,
    attachment_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> str:
    signer = _BucketedTimestampSigner(salt=salt)
    return signer.sign(f"{establishment_id}:{attachment_id}:{membership_id}")


def unsign_upload_preview_token(
    *,
    salt: str,
    token: str,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID] | None:
    if not token:
        return None
    try:
        payload = TimestampSigner(salt=salt).unsign(
            token,
            max_age=upload_preview_token_ttl_seconds(),
        )
        establishment_raw, attachment_raw, membership_raw = payload.split(":", 2)
        return (
            uuid.UUID(establishment_raw),
            uuid.UUID(attachment_raw),
            uuid.UUID(membership_raw),
        )
    except (BadSignature, SignatureExpired, ValueError):
        return None


def with_preview_token(url: str, token: str | None) -> str:
    if not token:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode({'token': token})}"
