from __future__ import annotations

import time
import uuid

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner, b62_encode
from django.urls import reverse

from houston.observations.models import ObservationMedia
from houston.signals.constants import FEED_SIGNAL_STATUSES
from houston.signals.models import SignalSourceObservation
from houston.uploads.photo_keys import observation_photo_thumbnail_storage_key

_PREVIEW_SIGNER_SALT = "houston.observation-media.preview"
PREVIEW_VARIANT_FULL = "full"
PREVIEW_VARIANT_THUMBNAIL = "thumbnail"
PREVIEW_VARIANTS = frozenset({PREVIEW_VARIANT_FULL, PREVIEW_VARIANT_THUMBNAIL})


def observation_media_preview_ttl_seconds() -> int:
    return int(getattr(settings, "HOUSTON_OBSERVATION_MEDIA_PREVIEW_TTL_SECONDS", 3600))


def observation_media_preview_url_bucket_seconds() -> int:
    return int(getattr(settings, "HOUSTON_OBSERVATION_MEDIA_PREVIEW_URL_BUCKET_SECONDS", 60))


def observation_media_preview_cache_max_age_seconds() -> int:
    return int(getattr(settings, "HOUSTON_OBSERVATION_MEDIA_PREVIEW_CACHE_MAX_AGE_SECONDS", 60))


class _BucketedTimestampSigner(TimestampSigner):
    def timestamp(self) -> str:
        window = max(1, observation_media_preview_url_bucket_seconds())
        bucketed = (int(time.time()) // window) * window
        return b62_encode(bucketed)


def sign_observation_media_preview(
    *,
    establishment_id: uuid.UUID,
    media_id: uuid.UUID,
) -> str:
    signer = _BucketedTimestampSigner(salt=_PREVIEW_SIGNER_SALT)
    return signer.sign(f"{establishment_id}:{media_id}")


def unsign_observation_media_preview(*, token: str) -> tuple[uuid.UUID, uuid.UUID]:
    signer = TimestampSigner(salt=_PREVIEW_SIGNER_SALT)
    payload = signer.unsign(token, max_age=observation_media_preview_ttl_seconds())
    establishment_id_str, media_id_str = payload.split(":", 1)
    return uuid.UUID(establishment_id_str), uuid.UUID(media_id_str)


def parse_observation_media_preview_variant(value: str | None) -> str | None:
    raw = (value or "").strip() or PREVIEW_VARIANT_FULL
    if raw not in PREVIEW_VARIANTS:
        return None
    return raw


def build_observation_media_preview_url(
    *,
    request,
    establishment_id: uuid.UUID,
    media_id: uuid.UUID,
    token: str | None = None,
    variant: str = PREVIEW_VARIANT_FULL,
) -> str:
    if token is None:
        token = sign_observation_media_preview(
            establishment_id=establishment_id,
            media_id=media_id,
        )
    path = reverse(
        "observation-media-preview",
        kwargs={
            "establishment_id": establishment_id,
            "media_id": media_id,
        },
    )
    query = f"token={token}"
    if variant != PREVIEW_VARIANT_FULL:
        query = f"{query}&variant={variant}"
    return request.build_absolute_uri(f"{path}?{query}")


def observation_media_preview_storage_key(*, media: ObservationMedia, variant: str) -> str:
    storage_key = media.storage_key
    if variant == PREVIEW_VARIANT_THUMBNAIL:
        return observation_photo_thumbnail_storage_key(storage_key)
    return storage_key


def is_observation_media_preview_authorized(
    *,
    media: ObservationMedia,
    establishment_id: uuid.UUID,
) -> bool:
    if media.observation.establishment_id != establishment_id:
        return False
    return SignalSourceObservation.objects.filter(
        observation_id=media.observation_id,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        signal__establishment_id=establishment_id,
        signal__status__in=FEED_SIGNAL_STATUSES,
    ).exists()


def resolve_observation_media_preview(
    *,
    establishment_id: uuid.UUID,
    media_id: uuid.UUID,
    token: str,
) -> ObservationMedia | None:
    if not token:
        return None
    try:
        token_establishment_id, token_media_id = unsign_observation_media_preview(token=token)
    except (BadSignature, SignatureExpired, ValueError):
        return None
    if token_establishment_id != establishment_id or token_media_id != media_id:
        return None

    media = ObservationMedia.objects.filter(id=media_id).select_related("observation").first()
    if media is None:
        return None
    if not is_observation_media_preview_authorized(media=media, establishment_id=establishment_id):
        return None
    return media
