"""Atomic admission of one Brain analysis. Access, then the existing work, then capacity."""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction

from houston.brain.configuration import admission_configuration
from houston.brain.errors import (
    BrainAccessDenied,
    BrainCapacityUnavailable,
    BrainWorkError,
)
from houston.brain.models import (
    BrainAnalysis,
    BrainCapacity,
    BrainExtraction,
    BrainReporting,
    BrainSlot,
)
from houston.establishments.permissions import resolve_establishment_admin_actor

logger = logging.getLogger(__name__)

_ACTIVE = (BrainSlot.Status.QUEUED, BrainSlot.Status.RUNNING)
_KEY_MAX = 128


def admit_brain_work(
    *,
    user,
    establishment_id,
    reporting_id,
    idempotency_key: str,
) -> BrainAnalysis:
    """Insert one queued analysis and its slot, or return the work already admitted.

    The capacity lock is held only until this transaction commits. Nothing is published here.
    """
    actor = resolve_establishment_admin_actor(user, establishment_id)
    if actor is None:
        raise BrainAccessDenied()
    key = _clean_key(idempotency_key)
    try:
        with transaction.atomic():
            BrainCapacity.objects.select_for_update().get(pk=1)
            existing = _analysis_for_key(establishment_id, key)
            if existing is not None:
                return existing
            active = _active_analysis(establishment_id)
            if active is not None:
                return active
            _require_capacity()
            try:
                with transaction.atomic():
                    return _insert_analysis(
                        actor=actor,
                        establishment_id=establishment_id,
                        reporting_id=reporting_id,
                        idempotency_key=key,
                    )
            except IntegrityError:
                raced = _analysis_for_key(establishment_id, key) or _active_analysis(
                    establishment_id
                )
                if raced is None:
                    raise
                return raced
    except BrainCapacity.DoesNotExist as exc:
        raise BrainWorkError(
            code="brain_capacity_missing",
            message="La capacité Brain n'est pas initialisée.",
        ) from exc


def _clean_key(idempotency_key: str) -> str:
    if not isinstance(idempotency_key, str):
        raise BrainWorkError(
            code="invalid_idempotency_key",
            message="La clé d'idempotence est requise.",
        )
    key = idempotency_key.strip()
    if not key or len(key) > _KEY_MAX:
        raise BrainWorkError(
            code="invalid_idempotency_key",
            message="La clé d'idempotence est requise.",
        )
    return key


def _analysis_for_key(establishment_id, idempotency_key: str) -> BrainAnalysis | None:
    return BrainAnalysis.objects.filter(
        establishment_id=establishment_id,
        idempotency_key=idempotency_key,
    ).first()


def _active_analysis(establishment_id) -> BrainAnalysis | None:
    slot = (
        BrainSlot.objects.select_related("analysis")
        .filter(establishment_id=establishment_id, status__in=_ACTIVE)
        .first()
    )
    if slot is None:
        return None
    return slot.analysis


def _require_capacity() -> None:
    limit = int(settings.HOUSTON_BRAIN_MAX_QUEUED_AND_RUNNING)
    active = BrainSlot.objects.filter(status__in=_ACTIVE).count()
    if active >= limit:
        raise BrainCapacityUnavailable()


def _insert_analysis(
    *, actor, establishment_id, reporting_id, idempotency_key: str
) -> BrainAnalysis:
    reporting = BrainReporting.objects.filter(
        id=reporting_id,
        establishment_id=establishment_id,
    ).first()
    if (
        reporting is None
        or reporting.status != BrainReporting.Status.READY
        or reporting.period_start is None
        or reporting.period_end is None
        or reporting.period_confirmed_at is None
    ):
        raise BrainWorkError(
            code="reporting_not_ready",
            message="Le reporting n'est pas prêt pour une analyse.",
        )
    extraction = (
        BrainExtraction.objects.filter(
            reporting_id=reporting.id,
            source_sha256=reporting.content_sha256,
        )
        .order_by("-created_at")
        .first()
    )
    if extraction is None:
        raise BrainWorkError(
            code="reporting_not_ready",
            message="Le reporting n'est pas prêt pour une analyse.",
        )
    token = uuid.uuid4()
    analysis = BrainAnalysis.objects.create(
        establishment_id=establishment_id,
        reporting=reporting,
        author=actor.user,
        idempotency_key=idempotency_key,
        status=BrainAnalysis.Status.QUEUED,
        attempt_token=token,
        configuration=admission_configuration(extraction),
    )
    BrainSlot.objects.create(
        establishment_id=establishment_id,
        analysis=analysis,
        kind=BrainSlot.Kind.ANALYSIS,
        status=BrainSlot.Status.QUEUED,
        token=token,
    )
    from houston.brain.runtime import schedule_analysis_publish

    schedule_analysis_publish(analysis.id, token)
    logger.info(
        "brain_analysis_admitted",
        extra={
            "event": "brain_analysis_admitted",
            "analysis_id": str(analysis.id),
            "establishment_id": str(establishment_id),
            "reporting_id": str(reporting.id),
        },
    )
    return analysis
