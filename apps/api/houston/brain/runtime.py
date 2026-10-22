"""Claim, lease, and one engine pass for an analysis. Follow-ups keep their own row.

A stale attempt token matches no row. A continuation keeps the sealed dossier
and the committed trace. It does not recapture and it does not call the provider
again for a tool that already has an envelope.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from houston.accounts.models import User
from houston.ai.models import AIUsageLog
from houston.brain.configuration import follow_up_ceilings, frozen_counter, runtime_ceilings
from houston.brain.engine import PROVIDER_TIMEOUT_SECONDS, run_engine
from houston.brain.errors import (
    BrainWorkError,
    CaptureTimeout,
    CaptureVolumeExceeded,
)
from houston.brain.models import BrainAnalysis, BrainMessage, BrainSlot
from houston.brain.provider import (
    BrainProviderUnavailable,
    EngineFakeProvider,
    ProviderCallResult,
)
from houston.establishments.permissions import resolve_establishment_admin_actor

logger = logging.getLogger(__name__)

_RUNNING = BrainAnalysis.Status.RUNNING
_QUEUED = BrainAnalysis.Status.QUEUED
_CALL_MARGIN_SECONDS = 30
_TERMINAL = (
    BrainAnalysis.Status.COMPLETED,
    BrainAnalysis.Status.FAILED,
    BrainAnalysis.Status.CANCELED,
)


def publish_brain_analysis(analysis_id, attempt_token) -> bool:
    from django.conf import settings

    from houston.brain.tasks import run_brain_analysis_task
    from houston.core.celery_publish import publish_celery_task

    published = publish_celery_task(
        run_brain_analysis_task,
        args=(str(analysis_id), str(attempt_token)),
        queue=settings.HOUSTON_BRAIN_ANALYSIS_QUEUE,
    )
    if not published:
        logger.error(
            "brain_analysis_publish_failed",
            extra={
                "event": "brain_analysis_publish_failed",
                "analysis_id": str(analysis_id),
            },
        )
        return False
    BrainAnalysis.objects.filter(
        id=analysis_id,
        attempt_token=attempt_token,
        status=_QUEUED,
    ).update(published_at=timezone.now(), updated_at=timezone.now())
    return True


def schedule_analysis_publish(analysis_id, attempt_token) -> None:
    def _enqueue() -> None:
        publish_brain_analysis(analysis_id, attempt_token)

    transaction.on_commit(_enqueue)


def publish_brain_follow_up(message_id, attempt_token) -> bool:
    from django.conf import settings

    from houston.brain.tasks import run_brain_follow_up_task
    from houston.core.celery_publish import publish_celery_task

    published = publish_celery_task(
        run_brain_follow_up_task,
        args=(str(message_id), str(attempt_token)),
        queue=settings.HOUSTON_BRAIN_ANALYSIS_QUEUE,
    )
    if not published:
        logger.error(
            "brain_follow_up_publish_failed",
            extra={
                "event": "brain_follow_up_publish_failed",
                "message_id": str(message_id),
            },
        )
        return False
    BrainMessage.objects.filter(
        id=message_id,
        attempt_token=attempt_token,
        status=_QUEUED,
    ).update(published_at=timezone.now(), updated_at=timezone.now())
    return True


def schedule_follow_up_publish(message_id, attempt_token) -> None:
    def _enqueue() -> None:
        publish_brain_follow_up(message_id, attempt_token)

    transaction.on_commit(_enqueue)


def schedule_next_analysis(establishment_id) -> None:
    """Publish the oldest queued analysis once the establishment has no running one."""
    if BrainAnalysis.objects.filter(
        establishment_id=establishment_id,
        status=_RUNNING,
    ).exists():
        return
    nxt = (
        BrainAnalysis.objects.filter(
            establishment_id=establishment_id,
            status=_QUEUED,
            cancel_requested_at__isnull=True,
        )
        .order_by("created_at", "id")
        .first()
    )
    if nxt is None:
        return
    schedule_analysis_publish(nxt.id, nxt.attempt_token)


def claim_analysis(analysis_id, attempt_token) -> bool:
    token = _token(attempt_token)
    if token is None:
        return False
    current = BrainAnalysis.objects.filter(id=analysis_id, attempt_token=token).first()
    if current is None or current.status != _QUEUED:
        return False
    if current.cancel_requested_at is not None:
        _cancel_queued(analysis_id, token, "cancel_requested")
        return False
    try:
        ceilings = runtime_ceilings(current.configuration)
    except BrainWorkError:
        _fail_queued(analysis_id, token, "configuration_unusable")
        return False
    now = timezone.now()
    try:
        with transaction.atomic():
            if (
                BrainAnalysis.objects.filter(
                    establishment_id=current.establishment_id,
                    status=_RUNNING,
                )
                .exclude(id=analysis_id)
                .exists()
            ):
                return False
            updated = BrainAnalysis.objects.filter(
                id=analysis_id,
                status=_QUEUED,
                attempt_token=token,
                cancel_requested_at__isnull=True,
            ).update(
                status=_RUNNING,
                claimed_at=now,
                lease_expires_at=now + timedelta(seconds=ceilings["lease_seconds"]),
                attempt_count=F("attempt_count") + 1,
                transport_republish_count=0,
                transport_stall_since=None,
                updated_at=now,
            )
    except IntegrityError:
        return False
    return updated == 1


def claim_message(message_id, attempt_token) -> bool:
    """Same queued-token update as an analysis. The row is the follow-up, not the analysis."""
    token = _token(attempt_token)
    if token is None:
        return False
    current = BrainMessage.objects.filter(id=message_id, attempt_token=token).first()
    if current is None or current.status != _QUEUED:
        return False
    if current.cancel_requested_at is not None:
        transition_message(
            message_id,
            token,
            status=BrainMessage.Status.CANCELED,
            failure_code="cancel_requested",
            queued=True,
        )
        return False
    analysis = BrainAnalysis.objects.filter(id=current.analysis_id).first()
    try:
        ceilings = follow_up_ceilings(None if analysis is None else analysis.configuration)
    except BrainWorkError:
        result = None
        if analysis is not None:
            from houston.brain.followups import configuration_proposal

            result = configuration_proposal(analysis)
        transition_message(
            message_id,
            token,
            status=BrainMessage.Status.FAILED,
            failure_code="configuration_unusable",
            result=result,
            queued=True,
        )
        return False
    now = timezone.now()
    updated = BrainMessage.objects.filter(
        id=message_id,
        status=_QUEUED,
        attempt_token=token,
        cancel_requested_at__isnull=True,
    ).update(
        status=_RUNNING,
        claimed_at=now,
        lease_expires_at=now + timedelta(seconds=ceilings["lease_seconds"]),
        attempt_count=F("attempt_count") + 1,
        transport_republish_count=0,
        transport_stall_since=None,
        updated_at=now,
    )
    if not updated:
        return False
    BrainSlot.objects.filter(message_id=message_id, status=_QUEUED).update(
        status=BrainSlot.Status.RUNNING,
        token=token,
        updated_at=now,
    )
    return True


def renew_message(message_id, token, lease_seconds: int) -> bool:
    now = timezone.now()
    updated = BrainMessage.objects.filter(
        id=message_id,
        attempt_token=token,
        status=_RUNNING,
        cancel_requested_at__isnull=True,
    ).update(
        lease_expires_at=now + timedelta(seconds=lease_seconds),
        updated_at=now,
    )
    return updated == 1


def touch_message(message_id, token, **fields) -> bool:
    fields["updated_at"] = timezone.now()
    updated = BrainMessage.objects.filter(
        id=message_id,
        attempt_token=token,
        status=_RUNNING,
    ).update(**fields)
    return updated == 1


def transition_message(
    message_id,
    token,
    *,
    status: str,
    failure_code: str = "",
    only_if_not_canceled: bool = False,
    result: dict | None = None,
    queued: bool = False,
) -> bool:
    """Terminal write for the current message token. The analysis row is not updated."""
    expected = _QUEUED if queued else _RUNNING
    now = timezone.now()
    with transaction.atomic():
        row = (
            BrainMessage.objects.select_for_update()
            .filter(id=message_id, attempt_token=token, status=expected)
            .first()
        )
        if row is None:
            return False
        if only_if_not_canceled and row.cancel_requested_at is not None:
            return False
        row.status = status
        if failure_code:
            row.failure_code = failure_code
        row.lease_expires_at = None
        if status == BrainMessage.Status.CANCELED and row.cancel_requested_at is None:
            row.cancel_requested_at = now
        update_fields = [
            "status",
            "failure_code",
            "lease_expires_at",
            "cancel_requested_at",
            "updated_at",
        ]
        if result is not None:
            row.result = result
            update_fields.append("result")
        row.save(update_fields=update_fields)
        BrainSlot.objects.filter(message_id=message_id).delete()
        return True


def requeue_message(message_id, token) -> bool:
    """One execution retry. The previous token can no longer write the message or its lot."""
    new_token = uuid.uuid4()
    with transaction.atomic():
        row = (
            BrainMessage.objects.select_for_update()
            .filter(
                id=message_id,
                attempt_token=token,
                status=_RUNNING,
                transient_retries_used=0,
                cancel_requested_at__isnull=True,
            )
            .first()
        )
        if row is None:
            return False
        establishment_id = BrainAnalysis.objects.filter(id=row.analysis_id).values_list(
            "establishment_id",
            flat=True,
        ).first()
        _rotate_queued_attempt(row, new_token)
        slot = BrainSlot.objects.select_for_update().filter(message_id=row.id).first()
        if slot is None:
            BrainSlot.objects.create(
                establishment_id=establishment_id,
                analysis_id=row.analysis_id,
                message=row,
                kind=BrainSlot.Kind.FOLLOW_UP,
                status=_QUEUED,
                token=new_token,
            )
        else:
            slot.token = new_token
            slot.status = _QUEUED
            slot.kind = BrainSlot.Kind.FOLLOW_UP
            slot.save(update_fields=["token", "status", "kind", "updated_at"])
    publish_brain_follow_up(message_id, new_token)
    return True


def request_analysis_cancel(analysis_id) -> str:
    """Terminal cancel, or the status already stored. A completed analysis stays completed."""
    now = timezone.now()
    with transaction.atomic():
        row = BrainAnalysis.objects.select_for_update().filter(id=analysis_id).first()
        if row is None:
            return ""
        if row.status in _TERMINAL:
            return row.status
        if row.cancel_requested_at is None:
            row.cancel_requested_at = now
        row.status = BrainAnalysis.Status.CANCELED
        row.failure_code = row.failure_code or "cancel_requested"
        row.lease_expires_at = None
        row.save(
            update_fields=[
                "status",
                "failure_code",
                "cancel_requested_at",
                "lease_expires_at",
                "updated_at",
            ]
        )
        BrainSlot.objects.filter(analysis_id=analysis_id).delete()
        establishment_id = row.establishment_id
        schedule_next_analysis(establishment_id)
        return row.status


def request_follow_up_cancel(message_id) -> str:
    """Terminal cancel of one follow-up. The completed analysis stays completed."""
    now = timezone.now()
    terminal = (
        BrainMessage.Status.COMPLETED,
        BrainMessage.Status.FAILED,
        BrainMessage.Status.CANCELED,
    )
    with transaction.atomic():
        row = BrainMessage.objects.select_for_update().filter(id=message_id).first()
        if row is None:
            return ""
        if row.status in terminal:
            return row.status
        if row.cancel_requested_at is None:
            row.cancel_requested_at = now
        row.status = BrainMessage.Status.CANCELED
        row.failure_code = row.failure_code or "cancel_requested"
        row.lease_expires_at = None
        row.save(
            update_fields=[
                "status",
                "failure_code",
                "cancel_requested_at",
                "lease_expires_at",
                "updated_at",
            ]
        )
        BrainSlot.objects.filter(message_id=message_id).delete()
        return row.status


def run_brain_analysis(
    analysis_id,
    attempt_token,
    *,
    provider=None,
) -> None:
    token = _token(attempt_token)
    if token is None or not claim_analysis(analysis_id, token):
        return
    started = time.monotonic()
    try:
        _run_claimed(analysis_id, token, provider=provider, started=started)
    except BrainProviderUnavailable:
        _handoff_transient(analysis_id, token)
    except CaptureTimeout:
        _fail(analysis_id, token, "capture_timeout")
    except CaptureVolumeExceeded:
        _fail(analysis_id, token, "capture_volume_exceeded")
    except BrainWorkError as exc:
        _fail(analysis_id, token, exc.code)
    except Exception:
        logger.exception(
            "brain_analysis_attempt_interrupted",
            extra={"event": "brain_analysis_attempt_interrupted", "analysis_id": str(analysis_id)},
        )
        raise


def _run_claimed(analysis_id, token, *, provider, started: float) -> None:
    analysis = _running(analysis_id, token)
    if analysis is None or not _guard(analysis, token):
        return
    if provider is None:
        provider = _engine_provider(analysis.configuration)
        if provider is None:
            _fail(analysis_id, token, "provider_not_allowed")
            return
    logged = _LoggingProvider(provider, analysis_id, token)

    def before_turn() -> str:
        current = _running(analysis_id, token)
        if current is None or not _guard(current, token):
            return "stop"
        try:
            ceilings = runtime_ceilings(current.configuration)
        except BrainWorkError:
            return "impossible"
        if not _renew(analysis_id, token, ceilings["lease_seconds"]):
            return "stop"
        elapsed = time.monotonic() - started
        remaining = ceilings["attempt_soft_seconds"] - elapsed
        needed = PROVIDER_TIMEOUT_SECONDS + _CALL_MARGIN_SECONDS
        if remaining >= needed:
            return "continue"
        if elapsed < _CALL_MARGIN_SECONDS:
            return "impossible"
        return "handoff"

    outcome = run_engine(analysis_id, logged, before_turn=before_turn)
    if outcome.get("handoff") is True:
        _requeue_continuation(analysis_id, token)
        return
    if outcome.get("impossible") is True:
        _fail(analysis_id, token, "attempt_exceeded")
        return
    if outcome.get("stopped") is True or "qualification" not in outcome:
        return
    _complete(analysis_id, token, outcome)


def _engine_provider(configuration: object):
    """Adapter for the frozen provider. The API key is read here and is not stored."""
    if not isinstance(configuration, dict):
        return None
    name = str(configuration.get("provider") or "").strip().lower()
    if name in {"", "fake"}:
        return EngineFakeProvider()
    if name != "openai":
        return None
    from django.conf import settings

    from houston.brain.openai_provider import OpenAIBrainProvider

    api_key = str(settings.OPENAI_API_KEY or "").strip()
    model = str(configuration.get("model") or "").strip()
    if not api_key or not model:
        return None
    raw_ceilings = configuration.get("ceilings")
    ceilings = raw_ceilings if isinstance(raw_ceilings, dict) else {}
    try:
        max_output = int(ceilings.get("per_call_output_tokens") or 0)
    except (TypeError, ValueError):
        max_output = 0
    if max_output <= 0:
        return None
    return OpenAIBrainProvider(
        api_key=api_key,
        model=model,
        timeout_seconds=PROVIDER_TIMEOUT_SECONDS,
        max_output_tokens=max_output,
    )


class _LoggingProvider:
    def __init__(self, inner, analysis_id, token):
        self.inner = inner
        self.analysis_id = analysis_id
        self.token = token

    def complete(self, **kwargs):
        analysis = _running(self.analysis_id, self.token)
        try:
            turn = self.inner.complete(**kwargs)
        except Exception:
            if analysis is not None:
                _usage(analysis, error_code="provider_error", status=AIUsageLog.Status.FAILED)
            raise
        if analysis is not None:
            _usage(
                analysis,
                input_tokens=getattr(turn, "input_tokens", None),
                output_tokens=getattr(turn, "output_tokens", None),
                error_code="",
                status=AIUsageLog.Status.SUCCEEDED,
            )
            _touch(
                self.analysis_id,
                self.token,
                provider_calls_used=F("provider_calls_used") + 1,
            )
        return turn


def _input_gap_context(
    *,
    estimated: int,
    provider_tokens: int | None,
    per_call: int,
    lot_key: str,
) -> dict:
    """Provider overrun of the exact reservation or a product ceiling. No dossier text."""
    if provider_tokens is None:
        return {}
    if provider_tokens > estimated or provider_tokens > per_call:
        return {
            "estimated_input_tokens": estimated,
            "provider_input_tokens": provider_tokens,
            "per_call_input_tokens": per_call,
            "lot_key": lot_key,
        }
    return {}


def _output_acceptable(result: ProviderCallResult, per_call_output_tokens: int) -> bool:
    if result.truncated or not isinstance(result.output, dict):
        return False
    if result.output_tokens is None:
        return False
    return 0 <= result.output_tokens <= per_call_output_tokens


def _guard(analysis: BrainAnalysis | None, token) -> bool:
    if analysis is None:
        return False
    if analysis.cancel_requested_at is not None:
        _transition(
            analysis.id,
            token,
            status=BrainAnalysis.Status.CANCELED,
            failure_code="cancel_requested",
        )
        return False
    user = User.objects.filter(pk=analysis.author_id).first()
    if resolve_establishment_admin_actor(user, analysis.establishment_id) is None:
        _transition(
            analysis.id,
            token,
            status=BrainAnalysis.Status.CANCELED,
            failure_code="author_rights_lost",
        )
        return False
    return True


def _complete(analysis_id, token, result: dict | None = None) -> bool:
    try:
        completed = _transition(
            analysis_id,
            token,
            status=BrainAnalysis.Status.COMPLETED,
            only_if_not_canceled=True,
            result=result,
        )
    except BrainWorkError as exc:
        _fail(analysis_id, token, exc.code)
        return False
    if completed:
        logger.info(
            "brain_analysis_completed",
            extra={"event": "brain_analysis_completed", "analysis_id": str(analysis_id)},
        )
        return True
    _cancel_if_requested(analysis_id, token)
    return False


def _cancel_if_requested(analysis_id, token) -> None:
    row = BrainAnalysis.objects.filter(id=analysis_id, attempt_token=token, status=_RUNNING).first()
    if row is not None and row.cancel_requested_at is not None:
        _transition(
            analysis_id,
            token,
            status=BrainAnalysis.Status.CANCELED,
            failure_code=row.failure_code or "cancel_requested",
        )


def _fail(analysis_id, token, failure_code: str) -> bool:
    failed = _transition(
        analysis_id,
        token,
        status=BrainAnalysis.Status.FAILED,
        failure_code=failure_code,
    )
    if failed:
        logger.info(
            "brain_analysis_failed",
            extra={
                "event": "brain_analysis_failed",
                "analysis_id": str(analysis_id),
                "failure_code": failure_code,
            },
        )
    return failed


def _transition(
    analysis_id,
    token,
    *,
    status: str,
    failure_code: str = "",
    only_if_not_canceled: bool = False,
    result: dict | None = None,
) -> bool:
    now = timezone.now()
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(id=analysis_id, attempt_token=token, status=_RUNNING)
            .first()
        )
        if row is None:
            return False
        if only_if_not_canceled and row.cancel_requested_at is not None:
            return False
        if status == BrainAnalysis.Status.COMPLETED:
            from houston.brain.publication import persist_completed_analysis

            persist_completed_analysis(row, result)
        row.status = status
        if failure_code:
            row.failure_code = failure_code
        row.lease_expires_at = None
        if status == BrainAnalysis.Status.CANCELED and row.cancel_requested_at is None:
            row.cancel_requested_at = now
        update_fields = [
            "status",
            "failure_code",
            "lease_expires_at",
            "cancel_requested_at",
            "updated_at",
        ]
        if result is not None:
            row.result = result
            update_fields.append("result")
        row.save(update_fields=update_fields)
        BrainSlot.objects.filter(analysis_id=analysis_id).delete()
        if status in _TERMINAL:
            schedule_next_analysis(row.establishment_id)
        return True


def _fail_locked(row: BrainAnalysis, failure_code: str) -> None:
    row.status = BrainAnalysis.Status.FAILED
    row.failure_code = failure_code
    row.lease_expires_at = None
    row.save(update_fields=["status", "failure_code", "lease_expires_at", "updated_at"])
    BrainSlot.objects.filter(analysis_id=row.id).delete()
    schedule_next_analysis(row.establishment_id)


def _handoff_transient(analysis_id, token) -> None:
    new_token = uuid.uuid4()
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(id=analysis_id, attempt_token=token, status=_RUNNING)
            .first()
        )
        if row is None:
            return
        if row.transient_retries_used >= 1:
            _fail_locked(row, "transient_exhausted")
            return
        _rotate_queued_attempt(row, new_token)
    publish_brain_analysis(analysis_id, new_token)


def _requeue_continuation(analysis_id, token) -> bool:
    """Hand the same investigation to a fresh task. The trace and dossier stay."""
    new_token = uuid.uuid4()
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(
                id=analysis_id,
                attempt_token=token,
                status=_RUNNING,
                cancel_requested_at__isnull=True,
            )
            .first()
        )
        if row is None:
            return False
        row.attempt_token = new_token
        row.status = _QUEUED
        row.claimed_at = None
        row.lease_expires_at = None
        row.published_at = None
        row.transport_stall_since = None
        row.save(
            update_fields=[
                "attempt_token",
                "status",
                "claimed_at",
                "lease_expires_at",
                "published_at",
                "transport_stall_since",
                "updated_at",
            ]
        )
    publish_brain_analysis(analysis_id, new_token)
    return True


def _rotate_queued_attempt(row, new_token) -> None:
    """Requeue one locked running row under a new token. The caller keeps its own guards."""
    row.attempt_token = new_token
    row.status = _QUEUED
    row.claimed_at = None
    row.lease_expires_at = None
    row.published_at = None
    row.transport_stall_since = None
    row.transient_retries_used = 1
    row.save(
        update_fields=[
            "attempt_token",
            "status",
            "claimed_at",
            "lease_expires_at",
            "published_at",
            "transport_stall_since",
            "transient_retries_used",
            "updated_at",
        ]
    )


def _renew(analysis_id, token, lease_seconds: int) -> bool:
    now = timezone.now()
    updated = BrainAnalysis.objects.filter(
        id=analysis_id,
        attempt_token=token,
        status=_RUNNING,
        cancel_requested_at__isnull=True,
    ).update(
        lease_expires_at=now + timedelta(seconds=lease_seconds),
        updated_at=now,
    )
    return updated == 1


def _touch(analysis_id, token, **fields) -> bool:
    fields["updated_at"] = timezone.now()
    updated = BrainAnalysis.objects.filter(
        id=analysis_id,
        attempt_token=token,
        status=_RUNNING,
    ).update(**fields)
    return updated == 1


def _running(analysis_id, token) -> BrainAnalysis | None:
    return (
        BrainAnalysis.objects.select_related("author", "establishment", "reporting")
        .filter(id=analysis_id, attempt_token=token, status=_RUNNING)
        .first()
    )


def _usage(
    analysis: BrainAnalysis,
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    error_code: str,
    status: str,
) -> None:
    configuration = analysis.configuration if isinstance(analysis.configuration, dict) else {}
    provider, model = frozen_counter(configuration)
    total = None
    if input_tokens is not None or output_tokens is not None:
        total = (input_tokens or 0) + (output_tokens or 0)
    AIUsageLog.objects.create(
        ai_domain=AIUsageLog.Domain.BRAIN_ANALYSIS,
        provider=provider,
        model=model,
        prompt_version=str(configuration.get("prompt_version") or ""),
        schema_version=str(configuration.get("schema_version") or ""),
        status=status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total,
        error_code=error_code,
        error_context={},
        correlation_id=analysis.id,
        establishment_id=analysis.establishment_id,
    )


def _cancel_queued(analysis_id, token, failure_code: str) -> None:
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(id=analysis_id, attempt_token=token, status=_QUEUED)
            .first()
        )
        if row is None:
            return
        row.status = BrainAnalysis.Status.CANCELED
        row.failure_code = failure_code
        row.save(update_fields=["status", "failure_code", "updated_at"])
        BrainSlot.objects.filter(analysis_id=analysis_id).delete()
        schedule_next_analysis(row.establishment_id)


def _fail_queued(analysis_id, token, failure_code: str) -> None:
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(id=analysis_id, attempt_token=token, status=_QUEUED)
            .first()
        )
        if row is None:
            return
        row.status = BrainAnalysis.Status.FAILED
        row.failure_code = failure_code
        row.save(update_fields=["status", "failure_code", "updated_at"])
        BrainSlot.objects.filter(analysis_id=analysis_id).delete()
        schedule_next_analysis(row.establishment_id)


def _token(value) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
