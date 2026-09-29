from __future__ import annotations

import uuid

from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.observations.constants import (
    MAX_OBSERVATION_PHOTOS,
    OBSERVATION_RAW_TEXT_MAX_LENGTH,
    OBSERVATION_RAW_TEXT_MIN_LENGTH,
)
from houston.observations.exceptions import (
    ObservationSubmissionConflictError,
    ObservationUploadNotFoundError,
    ObservationValidationError,
)
from houston.observations.models import Observation, ObservationMedia, ObservationProcessing
from houston.uploads.models import TemporaryUpload


def _upload_identity(upload_ids: list[uuid.UUID]) -> tuple[str, ...]:
    return tuple(sorted(str(upload_id) for upload_id in upload_ids))


def _stored_upload_identity(observation: Observation) -> tuple[str, ...]:
    upload_ids = observation.media_items.values_list("temporary_upload_id", flat=True)
    return tuple(sorted(str(upload_id) for upload_id in upload_ids))


def _same_observation_command(
    observation: Observation,
    *,
    raw_text: str,
    temporary_upload_ids: list[uuid.UUID],
    origin: str,
    action_plan_execution_id: uuid.UUID | None,
    action_plan_execution_task_id: uuid.UUID | None,
) -> bool:
    return (
        observation.raw_text == raw_text
        and observation.origin == origin
        and observation.action_plan_execution_id == action_plan_execution_id
        and observation.action_plan_execution_task_id == action_plan_execution_task_id
        and _stored_upload_identity(observation) == _upload_identity(temporary_upload_ids)
    )


def _require_same_command(
    observation: Observation,
    *,
    raw_text: str,
    temporary_upload_ids: list[uuid.UUID],
    origin: str,
    action_plan_execution_id: uuid.UUID | None,
    action_plan_execution_task_id: uuid.UUID | None,
) -> Observation:
    if _same_observation_command(
        observation,
        raw_text=raw_text,
        temporary_upload_ids=temporary_upload_ids,
        origin=origin,
        action_plan_execution_id=action_plan_execution_id,
        action_plan_execution_task_id=action_plan_execution_task_id,
    ):
        return observation
    raise ObservationSubmissionConflictError(
        "This submission id was already used for a different observation.",
    )


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
    client_submission_id: uuid.UUID,
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

    execution_id = getattr(action_plan_execution, "id", None)
    task_id = getattr(action_plan_execution_task, "id", None)
    existing = (
        Observation.objects.filter(
            establishment_id=membership.establishment_id,
            submitted_by_membership=membership,
            client_submission_id=client_submission_id,
        )
        .prefetch_related("media_items")
        .first()
    )
    if existing is not None:
        return _require_same_command(
            existing,
            raw_text=raw_text,
            temporary_upload_ids=temporary_upload_ids,
            origin=origin,
            action_plan_execution_id=execution_id,
            action_plan_execution_task_id=task_id,
        )

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
    try:
        with transaction.atomic():
            observation = Observation.objects.create(
                establishment=membership.establishment,
                submitted_by_membership=membership,
                raw_text=raw_text,
                origin=origin,
                action_plan_execution=action_plan_execution,
                action_plan_execution_task=action_plan_execution_task,
                client_submission_id=client_submission_id,
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
    except IntegrityError:
        raced = Observation.objects.filter(
            establishment_id=membership.establishment_id,
            submitted_by_membership=membership,
            client_submission_id=client_submission_id,
        ).first()
        if raced is None:
            raise
        return _require_same_command(
            raced,
            raw_text=raw_text,
            temporary_upload_ids=temporary_upload_ids,
            origin=origin,
            action_plan_execution_id=execution_id,
            action_plan_execution_task_id=task_id,
        )

    observation_id = observation.id
    transaction.on_commit(
        lambda: _enqueue_observation_processing(observation_id),
    )

    return observation


def _enqueue_observation_processing(observation_id: uuid.UUID) -> None:
    from houston.signals.services import enqueue_observation_processing

    enqueue_observation_processing(observation_id)
