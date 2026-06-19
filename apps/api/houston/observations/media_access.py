from __future__ import annotations

import uuid

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse

from houston.observations.models import ObservationMedia
from houston.signals.constants import FEED_SIGNAL_STATUSES
from houston.signals.models import SignalSourceObservation

_PREVIEW_SIGNER_SALT = "houston.observation-media.preview"


def observation_media_preview_ttl_seconds() -> int:
    return int(getattr(settings, "HOUSTON_OBSERVATION_MEDIA_PREVIEW_TTL_SECONDS", 3600))


def sign_observation_media_preview(
    *,
    establishment_id: uuid.UUID,
    media_id: uuid.UUID,
) -> str:
    signer = TimestampSigner(salt=_PREVIEW_SIGNER_SALT)
    return signer.sign(f"{establishment_id}:{media_id}")


def unsign_observation_media_preview(*, token: str) -> tuple[uuid.UUID, uuid.UUID]:
    signer = TimestampSigner(salt=_PREVIEW_SIGNER_SALT)
    payload = signer.unsign(token, max_age=observation_media_preview_ttl_seconds())
    establishment_id_str, media_id_str = payload.split(":", 1)
    return uuid.UUID(establishment_id_str), uuid.UUID(media_id_str)


def build_observation_media_preview_url(
    *,
    request,
    establishment_id: uuid.UUID,
    media_id: uuid.UUID,
) -> str:
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
    return request.build_absolute_uri(f"{path}?token={token}")


def is_observation_media_preview_authorized(
    *,
    media: ObservationMedia,
    establishment_id: uuid.UUID,
) -> bool:
    if media.observation.establishment_id != establishment_id:
        return False
    return (
        SignalSourceObservation.objects.filter(
            observation_id=media.observation_id,
            link_type=SignalSourceObservation.LinkType.CREATED_FROM,
            signal__establishment_id=establishment_id,
            signal__status__in=FEED_SIGNAL_STATUSES,
        ).exists()
    )


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

    media = (
        ObservationMedia.objects.filter(id=media_id)
        .select_related("observation")
        .first()
    )
    if media is None:
        return None
    if not is_observation_media_preview_authorized(media=media, establishment_id=establishment_id):
        return None
    return media
