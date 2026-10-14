"""Short-lived original preview. Every GET rechecks the current actor."""

from __future__ import annotations

import time
import uuid

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner, b62_encode
from django.urls import reverse

from houston.accounts.models import User
from houston.brain.models import BrainReporting
from houston.establishments.permissions import resolve_establishment_admin_actor

_SALT = "houston.brain.reporting-preview"


def brain_preview_ttl_seconds() -> int:
    return int(settings.HOUSTON_BRAIN_PREVIEW_TTL_SECONDS)


def brain_preview_url_bucket_seconds() -> int:
    return int(settings.HOUSTON_BRAIN_PREVIEW_URL_BUCKET_SECONDS)


class _BucketedTimestampSigner(TimestampSigner):
    def timestamp(self) -> str:
        window = max(1, brain_preview_url_bucket_seconds())
        bucketed = (int(time.time()) // window) * window
        return b62_encode(bucketed)


def sign_brain_reporting_preview(
    *,
    establishment_id: uuid.UUID,
    reporting_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str:
    signer = _BucketedTimestampSigner(salt=_SALT)
    return signer.sign(f"{establishment_id}:{reporting_id}:{user_id}")


def unsign_brain_reporting_preview(*, token: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    signer = TimestampSigner(salt=_SALT)
    payload = signer.unsign(token, max_age=brain_preview_ttl_seconds())
    establishment_raw, reporting_raw, user_raw = payload.split(":", 2)
    return uuid.UUID(establishment_raw), uuid.UUID(reporting_raw), uuid.UUID(user_raw)


def build_brain_reporting_preview_url(
    *,
    request,
    establishment_id: uuid.UUID,
    reporting_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str:
    token = sign_brain_reporting_preview(
        establishment_id=establishment_id,
        reporting_id=reporting_id,
        user_id=user_id,
    )
    path = reverse(
        "brain-reporting-preview",
        kwargs={
            "establishment_id": establishment_id,
            "reporting_id": reporting_id,
        },
    )
    return request.build_absolute_uri(f"{path}?token={token}")


def resolve_brain_reporting_preview(
    *,
    establishment_id: uuid.UUID,
    reporting_id: uuid.UUID,
    token: str,
) -> BrainReporting | None:
    """A valid signature is not access. The named user must still be an admin."""
    if not token:
        return None
    try:
        token_establishment, token_reporting, token_user = unsign_brain_reporting_preview(
            token=token
        )
    except (BadSignature, SignatureExpired, ValueError):
        return None
    if token_establishment != establishment_id or token_reporting != reporting_id:
        return None
    user = User.objects.filter(pk=token_user).first()
    if resolve_establishment_admin_actor(user, establishment_id) is None:
        return None
    reporting = BrainReporting.objects.filter(
        pk=reporting_id,
        establishment_id=establishment_id,
    ).first()
    if reporting is None or reporting.status == BrainReporting.Status.DRAFT:
        return None
    if not reporting.storage_key:
        return None
    return reporting
