"""One analysis attempt: claim, capture, lots, and a conditional finish.

A stale attempt token matches no row. It does not change a validated lot or a terminal analysis.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from houston.accounts.models import User
from houston.ai.models import AIUsageLog
from houston.brain.capture import capture_dossier
from houston.brain.configuration import (
    digest,
    frozen_extraction,
    runtime_ceilings,
)
from houston.brain.errors import BrainWorkError, CaptureTimeout, CaptureVolumeExceeded
from houston.brain.lots import plan_lots, sections_from_payload
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainLot,
    BrainSlot,
)
from houston.brain.provider import (
    BrainProvider,
    BrainProviderUnavailable,
    FakeBrainProvider,
    ProviderCallResult,
)
from houston.establishments.permissions import resolve_establishment_admin_actor

logger = logging.getLogger(__name__)

_RUNNING = BrainAnalysis.Status.RUNNING
_QUEUED = BrainAnalysis.Status.QUEUED
_TERMINAL = (
    BrainAnalysis.Status.COMPLETED,
    BrainAnalysis.Status.FAILED,
    BrainAnalysis.Status.CANCELED,
)


def publish_brain_analysis(analysis_id, attempt_token) -> bool:
    from houston.brain.tasks import run_brain_analysis_task
    from houston.core.celery_publish import publish_celery_task

    published = publish_celery_task(
        run_brain_analysis_task,
        args=(str(analysis_id), str(attempt_token)),
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
    if not updated:
        return False
    BrainSlot.objects.filter(analysis_id=analysis_id, status=_QUEUED).update(
        status=BrainSlot.Status.RUNNING,
        token=token,
        updated_at=now,
    )
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
        return row.status


def write_validated_lot(
    *,
    analysis_id,
    attempt_token,
    stable_key: str,
    input_hash: str,
    configuration_hash: str,
    output: dict,
    reserved_input_tokens: int,
) -> bool:
    """Insert a validated lot only for the current running token. Never rewrite one."""
    token = _token(attempt_token)
    if token is None:
        return False
    with transaction.atomic():
        current = (
            BrainAnalysis.objects.select_for_update()
            .filter(id=analysis_id, attempt_token=token, status=_RUNNING)
            .first()
        )
        if current is None:
            return False
        existing = BrainLot.objects.filter(analysis_id=analysis_id, stable_key=stable_key).first()
        if existing is not None:
            return False
        BrainLot.objects.create(
            analysis_id=analysis_id,
            stable_key=stable_key,
            input_hash=input_hash,
            configuration_hash=configuration_hash,
            status=BrainLot.Status.VALIDATED,
            output=output,
            attempt_token=token,
            reserved_input_tokens=reserved_input_tokens,
        )
        return True


def run_brain_analysis(
    analysis_id,
    attempt_token,
    *,
    provider: BrainProvider | None = None,
) -> None:
    token = _token(attempt_token)
    if token is None or not claim_analysis(analysis_id, token):
        return
    started = time.monotonic()
    try:
        _execute(analysis_id, token, provider=provider, started=started)
    except BrainProviderUnavailable:
        _handoff_transient(analysis_id, token)
    except Exception:
        logger.exception(
            "brain_analysis_attempt_interrupted",
            extra={"event": "brain_analysis_attempt_interrupted", "analysis_id": str(analysis_id)},
        )
        raise


def _execute(analysis_id, token, *, provider: BrainProvider | None, started: float) -> None:
    analysis = _running(analysis_id, token)
    if analysis is None:
        return
    if not _guard(analysis, token):
        return
    try:
        ceilings = runtime_ceilings(analysis.configuration)
        extraction = frozen_extraction(analysis)
    except BrainWorkError as exc:
        _fail(analysis_id, token, exc.code)
        return
    if provider is None:
        if analysis.configuration.get("provider") != "fake":
            _fail(analysis_id, token, "provider_not_allowed")
            return
        provider = FakeBrainProvider()
    if not _capture_if_open(analysis_id, token):
        return
    analysis = _running(analysis_id, token)
    if analysis is None or not _guard(analysis, token):
        return
    try:
        planned = plan_lots(
            sections_from_payload(extraction.payload),
            per_call_input_tokens=ceilings["per_call_input_tokens"],
            total_input_tokens=ceilings["total_input_tokens"],
            max_calls=ceilings["max_calls"],
        )
    except BrainWorkError as exc:
        _fail(analysis_id, token, exc.code)
        return
    if not _touch(
        analysis_id,
        token,
        reserved_input_tokens=sum(lot.reserved_input_tokens for lot in planned),
    ):
        return
    config_hash = digest(analysis.configuration)
    for lot in planned:
        analysis = _running(analysis_id, token)
        if analysis is None or not _guard(analysis, token):
            return
        if _attempt_expired(analysis, ceilings, started):
            _fail(analysis_id, token, "attempt_exceeded")
            return
        if not _renew(analysis_id, token, ceilings["lease_seconds"]):
            _cancel_if_requested(analysis_id, token)
            return
        existing = BrainLot.objects.filter(
            analysis_id=analysis.id,
            stable_key=lot.stable_key,
            status=BrainLot.Status.VALIDATED,
        ).first()
        if existing is not None:
            same_input = existing.input_hash == lot.input_hash
            same_configuration = existing.configuration_hash == config_hash
            if same_input and same_configuration:
                continue
            _fail(analysis_id, token, "configuration_unusable")
            return
        if analysis.provider_calls_used >= ceilings["max_calls"]:
            _fail(analysis_id, token, "budget_exceeded")
            return
        result = provider.complete(
            analysis_id=str(analysis_id),
            lot_key=lot.stable_key,
            payload=lot.payload,
            timeout_seconds=ceilings["provider_timeout_seconds"],
        )
        outcome = _accept_call(
            analysis_id=analysis_id,
            token=token,
            lot=lot,
            config_hash=config_hash,
            result=result,
            ceilings=ceilings,
            configuration=analysis.configuration,
        )
        if outcome not in {"written", "reused"}:
            return
    validated_keys = set(
        BrainLot.objects.filter(
            analysis_id=analysis_id,
            status=BrainLot.Status.VALIDATED,
        ).values_list("stable_key", flat=True)
    )
    if any(lot.stable_key not in validated_keys for lot in planned):
        _fail(analysis_id, token, "lots_incomplete")
        return
    if not _guard(_running(analysis_id, token), token):
        return
    _complete(analysis_id, token)


def _capture_if_open(analysis_id, token) -> bool:
    if BrainDossier.objects.filter(analysis_id=analysis_id, closed_at__isnull=False).exists():
        return True
    try:
        capture_dossier(analysis_id)
    except CaptureTimeout:
        _fail(analysis_id, token, "capture_timeout")
        return False
    except CaptureVolumeExceeded:
        _fail(analysis_id, token, "capture_volume_exceeded")
        return False
    except BrainWorkError as exc:
        _fail(analysis_id, token, exc.code)
        return False
    return BrainDossier.objects.filter(analysis_id=analysis_id, closed_at__isnull=False).exists()


def _accept_call(
    *,
    analysis_id,
    token,
    lot,
    config_hash: str,
    result: ProviderCallResult,
    ceilings: dict[str, int],
    configuration: dict,
) -> str:
    acceptable = _output_acceptable(result, ceilings["per_call_output_tokens"])
    charged = (
        result.input_tokens if result.input_tokens is not None else lot.reserved_input_tokens
    )
    now = timezone.now()
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(id=analysis_id, attempt_token=token, status=_RUNNING)
            .first()
        )
        if row is None or row.cancel_requested_at is not None:
            return "stopped"
        existing = BrainLot.objects.filter(
            analysis_id=analysis_id,
            stable_key=lot.stable_key,
            status=BrainLot.Status.VALIDATED,
        ).first()
        calls = row.provider_calls_used + 1
        consumed = row.consumed_input_tokens + max(0, charged)
        over_budget = (
            calls > ceilings["max_calls"]
            or consumed > ceilings["total_input_tokens"]
            or (
                result.input_tokens is not None
                and result.input_tokens > ceilings["per_call_input_tokens"]
            )
        )
        if existing is not None:
            same = (
                existing.input_hash == lot.input_hash
                and existing.configuration_hash == config_hash
            )
            if not same:
                _fail_locked(row, "configuration_unusable")
                return "stopped"
            return "reused"
        row.provider_calls_used = calls
        row.consumed_input_tokens = consumed
        row.lease_expires_at = now + timedelta(seconds=ceilings["lease_seconds"])
        if not acceptable or over_budget:
            code = "provider_output_rejected" if not acceptable else "budget_exceeded"
            row.status = BrainAnalysis.Status.FAILED
            row.failure_code = code
            row.lease_expires_at = None
            row.save(
                update_fields=[
                    "provider_calls_used",
                    "consumed_input_tokens",
                    "lease_expires_at",
                    "status",
                    "failure_code",
                    "updated_at",
                ]
            )
            BrainSlot.objects.filter(analysis_id=analysis_id).delete()
            _usage(
                row,
                configuration=configuration,
                result=result,
                error_code=code,
                status=AIUsageLog.Status.FAILED,
            )
            return "failed"
        BrainLot.objects.create(
            analysis_id=analysis_id,
            stable_key=lot.stable_key,
            input_hash=lot.input_hash,
            configuration_hash=config_hash,
            status=BrainLot.Status.VALIDATED,
            output=result.output,
            attempt_token=token,
            reserved_input_tokens=lot.reserved_input_tokens,
        )
        row.save(
            update_fields=[
                "provider_calls_used",
                "consumed_input_tokens",
                "lease_expires_at",
                "updated_at",
            ]
        )
        _usage(
            row,
            configuration=configuration,
            result=result,
            error_code="",
            status=AIUsageLog.Status.SUCCEEDED,
        )
        return "written"


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


def _complete(analysis_id, token) -> bool:
    completed = _transition(
        analysis_id,
        token,
        status=BrainAnalysis.Status.COMPLETED,
        only_if_not_canceled=True,
    )
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
        row.status = status
        if failure_code:
            row.failure_code = failure_code
        row.lease_expires_at = None
        if status == BrainAnalysis.Status.CANCELED and row.cancel_requested_at is None:
            row.cancel_requested_at = now
        row.save(
            update_fields=[
                "status",
                "failure_code",
                "lease_expires_at",
                "cancel_requested_at",
                "updated_at",
            ]
        )
        BrainSlot.objects.filter(analysis_id=analysis_id).delete()
        return True


def _fail_locked(row: BrainAnalysis, failure_code: str) -> None:
    row.status = BrainAnalysis.Status.FAILED
    row.failure_code = failure_code
    row.lease_expires_at = None
    row.save(update_fields=["status", "failure_code", "lease_expires_at", "updated_at"])
    BrainSlot.objects.filter(analysis_id=row.id).delete()


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
        _retarget_slot(row, new_token)
    publish_brain_analysis(analysis_id, new_token)


def _retarget_slot(row: BrainAnalysis, new_token) -> None:
    slot = BrainSlot.objects.select_for_update().filter(analysis_id=row.id).first()
    if slot is None:
        BrainSlot.objects.create(
            establishment_id=row.establishment_id,
            analysis=row,
            kind=BrainSlot.Kind.ANALYSIS,
            status=_QUEUED,
            token=new_token,
        )
        return
    slot.token = new_token
    slot.status = _QUEUED
    slot.save(update_fields=["token", "status", "updated_at"])


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


def _attempt_expired(analysis: BrainAnalysis, ceilings: dict[str, int], started: float) -> bool:
    if analysis.claimed_at is None:
        return False
    elapsed = timezone.now() - analysis.claimed_at
    if elapsed.total_seconds() >= ceilings["attempt_hard_seconds"]:
        return True
    return (time.monotonic() - started) >= ceilings["attempt_hard_seconds"]


def _usage(
    analysis: BrainAnalysis,
    *,
    configuration: dict,
    result: ProviderCallResult,
    error_code: str,
    status: str,
) -> None:
    input_tokens = result.input_tokens
    output_tokens = result.output_tokens
    total = None
    if input_tokens is not None or output_tokens is not None:
        total = (input_tokens or 0) + (output_tokens or 0)
    AIUsageLog.objects.create(
        ai_domain=AIUsageLog.Domain.BRAIN_ANALYSIS,
        provider="fake",
        model=str(configuration.get("model") or ""),
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
        updated = BrainAnalysis.objects.filter(
            id=analysis_id,
            attempt_token=token,
            status=_QUEUED,
        ).update(
            status=BrainAnalysis.Status.CANCELED,
            failure_code=failure_code,
            updated_at=timezone.now(),
        )
        if updated:
            BrainSlot.objects.filter(analysis_id=analysis_id).delete()


def _fail_queued(analysis_id, token, failure_code: str) -> None:
    with transaction.atomic():
        updated = BrainAnalysis.objects.filter(
            id=analysis_id,
            attempt_token=token,
            status=_QUEUED,
        ).update(
            status=BrainAnalysis.Status.FAILED,
            failure_code=failure_code,
            updated_at=timezone.now(),
        )
        if updated:
            BrainSlot.objects.filter(analysis_id=analysis_id).delete()


def _token(value) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
