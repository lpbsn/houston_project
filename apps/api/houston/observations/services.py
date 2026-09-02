from __future__ import annotations

import logging
import uuid

from django.db import transaction
from django.utils import timezone

from houston.core.observability import build_observation_enqueue_failure_log_context
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

logger = logging.getLogger(__name__)


def validate_observation_text(text: str) -> str:
    normalized = (text or "").strip()
    if len(normalized) < OBSERVATION_RAW_TEXT_MIN_LENGTH:
        raise ObservationValidationError("Text is too short.")
    if len(normalized) > OBSERVATION_RAW_TEXT_MAX_LENGTH:
        raise ObservationValidationError("Text is too long.")
    return normalized


def _validate_action_plan_observation_context(
    *,
    membership: EstablishmentMembership,
    action_plan_execution,
    action_plan_execution_task,
) -> None:
    if action_plan_execution is None or action_plan_execution_task is None:
        raise ObservationValidationError("Action plan context is required.")
    if action_plan_execution.establishment_id != membership.establishment_id:
        raise ObservationValidationError("Invalid action plan execution.")
    if action_plan_execution_task.action_plan_execution_id != action_plan_execution.id:
        raise ObservationValidationError("Invalid action plan task execution.")

    from houston.action_plans.permissions import can_execute_action_plan_task

    if not can_execute_action_plan_task(membership, action_plan_execution_task):
        raise ObservationValidationError("Not allowed to submit this action plan observation.")


@transaction.atomic
def submit_observation(
    *,
    membership: EstablishmentMembership,
    text: str,
    temporary_upload_ids: list[uuid.UUID],
    origin: str = Observation.Origin.DIRECT_REPORT,
    action_plan_execution=None,
    action_plan_execution_task=None,
) -> Observation:
    from houston.accounts.legal_services import require_current_ai_consent, require_current_terms

    require_current_terms(user=membership.user)
    require_current_ai_consent(user=membership.user)
    raw_text = validate_observation_text(text)

    has_action_plan_context = (
        action_plan_execution is not None or action_plan_execution_task is not None
    )

    if origin == Observation.Origin.ACTION_PLAN_TASK:
        _validate_action_plan_observation_context(
            membership=membership,
            action_plan_execution=action_plan_execution,
            action_plan_execution_task=action_plan_execution_task,
        )
    elif has_action_plan_context:
        raise ObservationValidationError(
            "Action plan context is only allowed for action_plan_task origin.",
        )

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
        origin=origin,
        action_plan_execution=action_plan_execution,
        action_plan_execution_task=action_plan_execution_task,
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

    observation_id = observation.id
    transaction.on_commit(
        lambda: _enqueue_observation_processing(observation_id),
    )

    return observation


def _enqueue_observation_processing(observation_id: uuid.UUID) -> None:
    from houston.signals.tasks import process_observation_task

    try:
        process_observation_task.delay(str(observation_id))
    except Exception as exc:
        logger.error(
            "observation_processing_enqueue_failed",
            extra=build_observation_enqueue_failure_log_context(
                observation_id=observation_id,
                event="observation_processing_enqueue_failed",
                exception_class=type(exc).__name__,
            ),
            exc_info=False,
        )
        raise
