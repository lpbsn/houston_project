"""Atomic admission of one Brain analysis or follow-up.

The idempotency key absorbs a technical double send. The context fingerprint
returns the queued, running, or completed analysis of the same reporting,
period, mechanisms, and contributions. A follow-up does not take the
one-running analysis lock.
"""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction

from houston.brain.configuration import (
    admission_configuration,
    context_fingerprint,
    copied_mechanisms,
)
from houston.brain.errors import (
    BrainAccessDenied,
    BrainCapacityUnavailable,
    BrainWorkError,
)
from houston.brain.models import (
    BrainAnalysis,
    BrainCapacity,
    BrainDossier,
    BrainExtraction,
    BrainMessage,
    BrainReporting,
    BrainSlot,
)
from houston.establishments.permissions import resolve_establishment_admin_actor

logger = logging.getLogger(__name__)

_ACTIVE = (BrainSlot.Status.QUEUED, BrainSlot.Status.RUNNING)
_OPEN_ANALYSIS = (
    BrainAnalysis.Status.QUEUED,
    BrainAnalysis.Status.RUNNING,
    BrainAnalysis.Status.COMPLETED,
)
_KEY_MAX = 128
_PURPOSES = {choice.value for choice in BrainMessage.Purpose}
_DECLARATIONS = {
    BrainMessage.Purpose.CORRECTION,
    BrainMessage.Purpose.NEW_FACT,
    BrainMessage.Purpose.NEW_DOCUMENT,
}


def admit_brain_work(
    *,
    user,
    establishment_id,
    reporting_id=None,
    idempotency_key: str | None = None,
    analysis_id=None,
    request_id: str | None = None,
    body: str | None = None,
    purpose: str | None = None,
    cited_item_ids: list[str] | None = None,
    contributions: list | None = None,
) -> BrainAnalysis | BrainMessage:
    """Insert one queued analysis or follow-up, or return the work already admitted.

    The capacity lock is held only until this transaction commits. Nothing is published here.
    """
    actor = resolve_establishment_admin_actor(user, establishment_id)
    if actor is None:
        raise BrainAccessDenied()
    follow_up = request_id is not None
    if follow_up:
        request_id = _clean_key(request_id)
        cited = _clean_follow_up(body, purpose, cited_item_ids)
        text = body.strip()
    else:
        key = _clean_key(idempotency_key)
        joined = _contributions(contributions)
    try:
        with transaction.atomic():
            BrainCapacity.objects.select_for_update().get(pk=1)
            if follow_up:
                return _admit_follow_up(
                    actor=actor,
                    establishment_id=establishment_id,
                    analysis_id=analysis_id,
                    request_id=request_id,
                    body=text,
                    purpose=purpose,
                    cited_item_ids=cited,
                )
            existing = _analysis_for_key(establishment_id, key)
            if existing is not None:
                return existing
            fingerprint, mechanisms = _fingerprint_for(
                establishment_id=establishment_id,
                reporting_id=reporting_id,
                contributions=joined,
            )
            same_context = _analysis_for_fingerprint(establishment_id, fingerprint)
            if same_context is not None:
                return same_context
            _require_capacity()
            try:
                with transaction.atomic():
                    return _insert_analysis(
                        actor=actor,
                        establishment_id=establishment_id,
                        reporting_id=reporting_id,
                        idempotency_key=key,
                        contributions=joined,
                        fingerprint=fingerprint,
                        mechanisms=mechanisms,
                    )
            except IntegrityError:
                raced = _analysis_for_key(establishment_id, key) or _analysis_for_fingerprint(
                    establishment_id,
                    fingerprint,
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


def _analysis_for_fingerprint(establishment_id, fingerprint: str) -> BrainAnalysis | None:
    if not fingerprint:
        return None
    return (
        BrainAnalysis.objects.filter(
            establishment_id=establishment_id,
            context_fingerprint=fingerprint,
            status__in=_OPEN_ANALYSIS,
        )
        .order_by("created_at", "id")
        .first()
    )


def _active_follow_up(establishment_id) -> BrainMessage | None:
    slot = (
        BrainSlot.objects.select_related("message")
        .filter(
            establishment_id=establishment_id,
            status__in=_ACTIVE,
            kind=BrainSlot.Kind.FOLLOW_UP,
        )
        .first()
    )
    if slot is None or slot.message_id is None:
        return None
    return slot.message


def _clean_follow_up(body, purpose, cited_item_ids) -> list[str]:
    if purpose not in _PURPOSES:
        raise BrainWorkError(
            code="invalid_follow_up",
            message="Le follow-up n'a pas de demande reconnue.",
        )
    if not isinstance(body, str) or not body.strip():
        raise BrainWorkError(
            code="invalid_follow_up",
            message="Le message du follow-up est requis.",
        )
    if cited_item_ids is None:
        return []
    if not isinstance(cited_item_ids, list):
        raise BrainWorkError(
            code="invalid_follow_up",
            message="Les références du follow-up sont invalides.",
        )
    seen = []
    for item_id in cited_item_ids:
        if not isinstance(item_id, str) or not item_id.strip():
            raise BrainWorkError(
                code="invalid_follow_up",
                message="Les références du follow-up sont invalides.",
            )
        value = item_id.strip()
        if value not in seen:
            seen.append(value)
    return seen


def _admit_follow_up(
    *,
    actor,
    establishment_id,
    analysis_id,
    request_id: str,
    body: str,
    purpose: str,
    cited_item_ids: list[str],
) -> BrainAnalysis | BrainMessage:
    analysis = BrainAnalysis.objects.filter(
        id=analysis_id,
        establishment_id=establishment_id,
    ).first()
    if analysis is None:
        raise BrainWorkError(
            code="follow_up_unavailable",
            message="Aucun dossier figé n'est disponible pour un follow-up.",
        )
    existing = BrainMessage.objects.filter(analysis=analysis, request_id=request_id).first()
    if existing is not None:
        return existing
    active = _active_follow_up(establishment_id)
    if active is not None:
        return active
    closed = BrainDossier.objects.filter(
        analysis=analysis,
        closed_at__isnull=False,
    ).exists()
    if analysis.status != BrainAnalysis.Status.COMPLETED or not closed:
        raise BrainWorkError(
            code="follow_up_unavailable",
            message="Aucun dossier figé n'est disponible pour un follow-up.",
        )
    _require_capacity()
    try:
        with transaction.atomic():
            return _insert_follow_up(
                actor=actor,
                analysis=analysis,
                request_id=request_id,
                body=body,
                purpose=purpose,
                cited_item_ids=cited_item_ids,
            )
    except IntegrityError:
        raced = BrainMessage.objects.filter(
            analysis=analysis,
            request_id=request_id,
        ).first() or _active_follow_up(analysis.establishment_id)
        if raced is None:
            raise
        return raced


def _insert_follow_up(
    *,
    actor,
    analysis: BrainAnalysis,
    request_id: str,
    body: str,
    purpose: str,
    cited_item_ids: list[str],
) -> BrainMessage:
    last = (
        BrainMessage.objects.filter(analysis=analysis)
        .order_by("-sequence")
        .values_list("sequence", flat=True)
        .first()
    )
    declaration = None
    if purpose in _DECLARATIONS:
        declaration = {"kind": purpose, "text": body, "applied": False}
    token = uuid.uuid4()
    message = BrainMessage.objects.create(
        analysis=analysis,
        author=actor.user,
        request_id=request_id,
        sequence=(last or 0) + 1,
        purpose=purpose,
        body=body,
        cited_item_ids=cited_item_ids,
        declaration=declaration,
        status=BrainMessage.Status.QUEUED,
        attempt_token=token,
    )
    BrainSlot.objects.create(
        establishment_id=analysis.establishment_id,
        analysis=analysis,
        message=message,
        kind=BrainSlot.Kind.FOLLOW_UP,
        status=BrainSlot.Status.QUEUED,
        token=token,
    )
    from houston.brain.runtime import schedule_follow_up_publish

    schedule_follow_up_publish(message.id, token)
    logger.info(
        "brain_follow_up_admitted",
        extra={
            "event": "brain_follow_up_admitted",
            "message_id": str(message.id),
            "analysis_id": str(analysis.id),
            "establishment_id": str(analysis.establishment_id),
        },
    )
    return message


def _require_capacity() -> None:
    limit = int(settings.HOUSTON_BRAIN_MAX_QUEUED_AND_RUNNING)
    analyses = BrainAnalysis.objects.filter(
        status__in=(BrainAnalysis.Status.QUEUED, BrainAnalysis.Status.RUNNING)
    ).count()
    messages = BrainMessage.objects.filter(
        status__in=(BrainMessage.Status.QUEUED, BrainMessage.Status.RUNNING)
    ).count()
    if analyses + messages >= limit:
        raise BrainCapacityUnavailable()


def _contributions(value) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise BrainWorkError(
            code="invalid_contribution",
            message="L'apport joint n'est pas reconnu.",
        )
    rows = []
    seen = set()
    for item in value:
        if isinstance(item, str):
            kind, text = "apport", item.strip()
        elif isinstance(item, dict):
            kind = str(item.get("kind") or "apport").strip() or "apport"
            text = str(item.get("text") or "").strip()
        else:
            raise BrainWorkError(
                code="invalid_contribution",
                message="L'apport joint n'est pas reconnu.",
            )
        if not text or (kind, text) in seen:
            continue
        seen.add((kind, text))
        rows.append({"kind": kind, "text": text})
    rows.sort(key=lambda row: (row["kind"], row["text"]))
    return rows


def _fingerprint_for(*, establishment_id, reporting_id, contributions: list[dict]):
    reporting = _ready_reporting(establishment_id, reporting_id)
    mechanisms = copied_mechanisms()
    return (
        context_fingerprint(
            reporting=reporting,
            mechanisms=mechanisms,
            contributions=contributions,
        ),
        mechanisms,
    )


def _ready_reporting(establishment_id, reporting_id) -> BrainReporting:
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
    return reporting


def _insert_analysis(
    *,
    actor,
    establishment_id,
    reporting_id,
    idempotency_key: str,
    contributions: list[dict],
    fingerprint: str,
    mechanisms: list[dict],
) -> BrainAnalysis:
    reporting = _ready_reporting(establishment_id, reporting_id)
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
        context_fingerprint=fingerprint,
        configuration=admission_configuration(
            extraction,
            mechanisms=mechanisms,
            contributions=contributions,
        ),
    )
    running = BrainAnalysis.objects.filter(
        establishment_id=establishment_id,
        status=BrainAnalysis.Status.RUNNING,
    ).exists()
    if not running:
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
