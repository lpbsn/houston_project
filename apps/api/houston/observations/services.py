from __future__ import annotations

import uuid

from django.db import transaction
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.observations.constants import (
    MAX_OBSERVATION_PHOTOS,
    OBSERVATION_RAW_TEXT_MAX_LENGTH,
    OBSERVATION_RAW_TEXT_MIN_LENGTH,
)
from houston.observations.exceptions import (
    ObservationUploadNotFoundError,
    ObservationValidationError,
)
from houston.observations.models import Observation, ObservationMedia, ObservationProcessing
from houston.uploads.models import TemporaryUpload


def validate_observation_text(text: str) -> str:
    normalized = (text or "").strip()
    if len(normalized) < OBSERVATION_RAW_TEXT_MIN_LENGTH:
        raise ObservationValidationError("Text is too short.")
    if len(normalized) > OBSERVATION_RAW_TEXT_MAX_LENGTH:
        raise ObservationValidationError("Text is too long.")
    return normalized


@transaction.atomic
def submit_observation(
    *,
    membership: EstablishmentMembership,
    text: str,
    temporary_upload_ids: list[uuid.UUID],
) -> Observation:
    raw_text = validate_observation_text(text)

    if len(temporary_upload_ids) > MAX_OBSERVATION_PHOTOS:
        raise ObservationValidationError("Too many photos.")

    uploads = list(
        TemporaryUpload.objects.filter(
            id__in=temporary_upload_ids,
            establishment_id=membership.establishment_id,
            uploaded_by_id=membership.user_id,
            status=TemporaryUpload.Status.VALIDATED,
        ).order_by("created_at")
    )
    if len(uploads) != len(set(temporary_upload_ids)):
        raise ObservationUploadNotFoundError("One or more uploads were not found.")

    now = timezone.now()
    observation = Observation.objects.create(
        establishment=membership.establishment,
        submitted_by_membership=membership,
        raw_text=raw_text,
        submitted_at=now,
    )
    ObservationProcessing.objects.create(
        observation=observation,
        status=ObservationProcessing.Status.QUEUED,
        queued_at=now,
    )

    for position, upload in enumerate(uploads, start=1):
        ObservationMedia.objects.create(
            observation=observation,
            temporary_upload=upload,
            position=position,
            content_type=upload.content_type,
            size_bytes=upload.size_bytes,
            storage_key=upload.file.name,
        )
        upload.status = TemporaryUpload.Status.LINKED
        upload.linked_at = now
        upload.save(update_fields=["status", "linked_at", "updated_at"])

    return observation
