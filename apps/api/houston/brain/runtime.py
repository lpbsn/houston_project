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
from houston.brain.collection import REQUIRED_SEARCHES
from houston.brain.configuration import (
    billed_input_tokens,
    digest,
    estimate_tokens,
    follow_up_ceilings,
    frozen_extraction,
    frozen_knowledge,
    runtime_ceilings,
    useful_input_tokens,
)
from houston.brain.contract import (
    CORRECTION_KEY,
    ENGINE_RULES,
    MAX_SUBJECTS,
    SCHEMA_VERSION,
    SYNTHESIS_KEY,
    accepted_result,
    analysis_correction_majorant,
    apply_coverage,
    assess,
    correction_envelope,
    correction_input_majorant,
    intermediate_result,
    minimal_call_output,
    ordered_coverage,
    piece_ids_of,
    subject_keys_of,
    synthesis_envelope,
    synthesis_input_majorant,
)
from houston.brain.errors import BrainWorkError, CaptureTimeout, CaptureVolumeExceeded
from houston.brain.lots import PlannedLot, plan_lots, sections_from_payload
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainLot,
    BrainMessage,
    BrainSlot,
)
from houston.brain.openai_provider import OpenAIBrainProvider
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
        provider = _provider_from_configuration(
            analysis.configuration,
            timeout_seconds=ceilings["provider_timeout_seconds"],
            max_output_tokens=ceilings["per_call_output_tokens"],
        )
        if provider is None:
            _fail(analysis_id, token, "provider_not_allowed")
            return
    if not _capture_if_open(analysis_id, token):
        return
    analysis = _running(analysis_id, token)
    if analysis is None or not _guard(analysis, token):
        return
    knowledge = frozen_knowledge(analysis.configuration)
    context = _dossier_context(analysis_id)
    if context is None:
        _fail(analysis_id, token, "insufficient_coverage")
        return
    _dossier, items, runs = context
    if not _searches_executed(runs):
        _fail(analysis_id, token, "insufficient_coverage")
        return
    useful = useful_input_tokens(ceilings["per_call_input_tokens"])
    if useful < estimate_tokens(list(ENGINE_RULES)):
        _fail(analysis_id, token, "budget_exceeded")
        return
    searches = sorted({run.code for run in runs})
    try:
        planned = plan_lots(
            sections_from_payload(extraction.payload),
            per_call_input_tokens=ceilings["per_call_input_tokens"],
            total_input_tokens=ceilings["total_input_tokens"],
            max_calls=ceilings["max_calls"],
            knowledge=knowledge,
            searches=searches,
            items=items,
        )
    except BrainWorkError as exc:
        _fail(analysis_id, token, exc.code)
        return
    pieces = piece_ids_of(planned)
    if any(
        estimate_tokens(minimal_call_output(_reading_piece_ids(lot)))
        > ceilings["per_call_output_tokens"]
        for lot in planned
    ):
        _fail(analysis_id, token, "budget_exceeded")
        return
    synthesis_tokens = 0
    if len(planned) > 1:
        synthesis_tokens = synthesis_input_majorant(
            pieces,
            key_slots=MAX_SUBJECTS,
            knowledge=knowledge,
            per_call_output_tokens=ceilings["per_call_output_tokens"],
            lot_count=len(planned),
        )
        correction_tokens = correction_input_majorant(
            key_slots=MAX_SUBJECTS,
            knowledge=knowledge,
            per_call_output_tokens=ceilings["per_call_output_tokens"],
        )
        tail_calls = 2
    else:
        # The one analysis call can still require a correction. Reserve that envelope
        # with the same gate as the multi-lot correction, before any provider call.
        correction_tokens = analysis_correction_majorant(
            pieces,
            items,
            key_slots=MAX_SUBJECTS,
            knowledge=knowledge,
        )
        tail_calls = 1
    envelopes_fit = all(lot.reserved_input_tokens <= useful for lot in planned)
    tails_fit = synthesis_tokens <= useful and correction_tokens <= useful
    # Each call bills its user envelope plus the prompt and schema sent with it.
    components = [lot.reserved_input_tokens for lot in planned]
    components.append(correction_tokens)
    if len(planned) > 1:
        components.append(synthesis_tokens)
    reserved = sum(billed_input_tokens(tokens) for tokens in components)
    calls = len(planned) + tail_calls
    if (
        not envelopes_fit
        or not tails_fit
        or reserved > ceilings["total_input_tokens"]
        or calls > ceilings["max_calls"]
    ):
        _fail(analysis_id, token, "budget_exceeded")
        return
    if not _touch(analysis_id, token, reserved_input_tokens=reserved):
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
                if len(planned) > 1 and _stored_reading_rejected(
                    analysis_id, token, existing.output, lot, items
                ):
                    return
                continue
            _fail(analysis_id, token, "configuration_unusable")
            return
        if analysis.provider_calls_used >= ceilings["max_calls"]:
            _fail(analysis_id, token, "budget_exceeded")
            return
        result = _invoke_provider(
            provider,
            analysis_id=analysis_id,
            token=token,
            lot_key=lot.stable_key,
            payload=lot.payload,
            timeout_seconds=ceilings["provider_timeout_seconds"],
        )
        if result is None:
            return
        outcome = _accept_call(
            analysis_id=analysis_id,
            token=token,
            lot=lot,
            config_hash=config_hash,
            result=result,
            ceilings=ceilings,
            configuration=analysis.configuration,
            sent_tokens=lot.reserved_input_tokens,
            # One reading lot can fail and still be stored: settlement rechecks it
            # and may correct it. Several lots are stored only when the contract passes.
            reading_items=items if len(planned) > 1 else None,
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
    _settle(
        analysis_id,
        token,
        provider=provider,
        planned=planned,
        pieces=pieces,
        ceilings=ceilings,
        configuration=analysis.configuration,
        started=started,
        synthesis_tokens=synthesis_tokens,
        correction_tokens=correction_tokens,
    )


def _provider_from_configuration(
    configuration: object,
    *,
    timeout_seconds: int,
    max_output_tokens: int,
) -> BrainProvider | None:
    """Adapter for the frozen provider. A missing key or unknown name selects nothing.

    The API key is read from process settings at call time. It is not copied onto the
    analysis and it is not placed in the provider payload.
    """
    if not isinstance(configuration, dict):
        return None
    name = str(configuration.get("provider") or "").strip().lower()
    if name == "fake":
        return FakeBrainProvider()
    if name != "openai":
        return None
    from django.conf import settings

    api_key = str(settings.OPENAI_API_KEY or "").strip()
    model = str(configuration.get("model") or "").strip()
    if not api_key or not model:
        return None
    return OpenAIBrainProvider(
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
    )


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
    sent_tokens: int = 0,
    reading_items=None,
) -> str:
    acceptable = _output_acceptable(result, ceilings["per_call_output_tokens"])
    payload_tokens = max(lot.reserved_input_tokens, sent_tokens)
    charged = (
        result.input_tokens
        if result.input_tokens is not None
        else billed_input_tokens(payload_tokens)
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
            if reading_items is not None:
                stored_failure = _reading_refusal(existing.output, lot, reading_items)
                if stored_failure is not None:
                    _fail_locked(row, stored_failure)
                    return "stopped"
            return "reused"
        # A multi-lot reading output is judged before the lot row exists. A refusal
        # is charged here and leaves no validated lot for a later attempt to reuse.
        contract_failure = None
        if reading_items is not None and acceptable:
            contract_failure = _reading_refusal(result.output, lot, reading_items)
        row.provider_calls_used = calls
        row.consumed_input_tokens = consumed
        row.lease_expires_at = now + timedelta(seconds=ceilings["lease_seconds"])
        if not acceptable or over_budget or contract_failure is not None:
            if not acceptable:
                code = "provider_output_rejected"
            elif over_budget:
                code = "budget_exceeded"
            else:
                code = contract_failure or "response_invalid"
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


def _reading_refusal(output, lot, items) -> str | None:
    """Contract code for one reading output, or None when that output is acceptable."""
    assessment = assess(output, pieces=_reading_piece_ids(lot), items=items)
    if assessment.ok:
        return None
    return assessment.issues[0].code if assessment.issues else "response_invalid"


def _stored_reading_rejected(analysis_id, token, output, lot, items) -> bool:
    """A reused multi-lot reading output is not trusted without its contract."""
    code = _reading_refusal(output, lot, items)
    if code is None:
        return False
    _fail(analysis_id, token, code)
    return True


def _reading_piece_ids(lot) -> list[str]:
    raw = lot.payload.get("required_piece_ids") if isinstance(lot.payload, dict) else None
    if isinstance(raw, list):
        return [str(piece_id) for piece_id in raw if piece_id]
    return piece_ids_of([lot])


def _settle(
    analysis_id,
    token,
    *,
    provider: BrainProvider,
    planned,
    pieces,
    ceilings: dict[str, int],
    configuration: dict,
    started: float,
    synthesis_tokens: int,
    correction_tokens: int,
) -> None:
    analysis = _running(analysis_id, token)
    if analysis is None or not _guard(analysis, token):
        return
    if _attempt_expired(analysis, ceilings, started):
        _fail(analysis_id, token, "attempt_exceeded")
        return
    if str(configuration.get("schema_version") or "") != SCHEMA_VERSION:
        _fail(analysis_id, token, "configuration_unusable")
        return
    context = _dossier_context(analysis_id)
    if context is None:
        _fail(analysis_id, token, "insufficient_coverage")
        return
    _dossier, items, runs = context
    if not _searches_executed(runs):
        _fail(analysis_id, token, "insufficient_coverage")
        return
    if len(planned) == 1:
        stored = BrainLot.objects.filter(
            analysis_id=analysis_id,
            stable_key=planned[0].stable_key,
            status=BrainLot.Status.VALIDATED,
        ).first()
        if stored is None:
            _fail(analysis_id, token, "lots_incomplete")
            return
        candidate = stored.output
        assessment = assess(candidate, pieces=pieces, items=items)
        if assessment.ok and assessment.parsed is not None:
            _finish(analysis_id, token, assessment.parsed, items)
            return
        _correct(
            analysis_id,
            token,
            provider=provider,
            assessment=assessment,
            pieces=pieces,
            items=items,
            ceilings=ceilings,
            configuration=configuration,
            started=started,
            reserved_tokens=correction_tokens,
        )
        return
    prepared = _prepare_synthesis(
        analysis_id,
        token,
        planned=planned,
        pieces=pieces,
    )
    if prepared is None:
        return
    coverage, intermediates, required_keys = prepared
    if not _renew(analysis_id, token, ceilings["lease_seconds"]):
        _cancel_if_requested(analysis_id, token)
        return
    synthesis_payload = synthesis_envelope(
        pieces,
        intermediates=intermediates,
        required_subject_keys=required_keys,
        knowledge=frozen_knowledge(configuration),
    )
    candidate = _contract_call(
        analysis_id=analysis_id,
        token=token,
        provider=provider,
        lot_key=SYNTHESIS_KEY,
        payload=synthesis_payload,
        ceilings=ceilings,
        configuration=configuration,
        reserved_tokens=synthesis_tokens,
    )
    if candidate is None:
        return
    assessment = assess(
        apply_coverage(candidate, coverage),
        pieces=pieces,
        items=items,
        required_subject_keys=required_keys,
    )
    if assessment.ok and assessment.parsed is not None:
        _finish(analysis_id, token, assessment.parsed, items)
        return
    _correct(
        analysis_id,
        token,
        provider=provider,
        assessment=assessment,
        pieces=pieces,
        items=items,
        ceilings=ceilings,
        configuration=configuration,
        started=started,
        assembled_coverage=coverage,
        candidate=candidate,
        required_subject_keys=required_keys,
        reserved_tokens=correction_tokens,
    )


def _prepare_synthesis(analysis_id, token, *, planned, pieces):
    """Lot keys and assembled coverage. A gap here does not call the provider."""
    stored = {
        row.stable_key: row
        for row in BrainLot.objects.filter(
            analysis_id=analysis_id,
            status=BrainLot.Status.VALIDATED,
        )
    }
    keys: list[str] = []
    seen: set[str] = set()
    coverage: list[dict] = []
    intermediates = []
    for lot in planned:
        row = stored.get(lot.stable_key)
        if row is None:
            _fail(analysis_id, token, "lots_incomplete")
            return None
        piece_ids = _reading_piece_ids(lot)
        for key in subject_keys_of(row.output):
            if key in seen:
                _fail(analysis_id, token, "response_invalid")
                return None
            seen.add(key)
            keys.append(key)
        ordered = ordered_coverage(row.output, piece_ids)
        if ordered is None:
            _fail(analysis_id, token, "insufficient_coverage")
            return None
        coverage.extend(ordered)
        intermediate = intermediate_result(lot.stable_key, row.output, piece_ids)
        if intermediate is None:
            _fail(analysis_id, token, "insufficient_coverage")
            return None
        intermediates.append(intermediate)
    if len(seen) > MAX_SUBJECTS:
        _fail(analysis_id, token, "budget_exceeded")
        return None
    if {entry["piece_id"] for entry in coverage} != set(pieces):
        _fail(analysis_id, token, "insufficient_coverage")
        return None
    return coverage, intermediates, keys


def _correct(
    analysis_id,
    token,
    *,
    provider: BrainProvider,
    assessment,
    pieces,
    items,
    ceilings: dict[str, int],
    configuration: dict,
    started: float,
    assembled_coverage=None,
    candidate=None,
    required_subject_keys=None,
    reserved_tokens: int | None = None,
) -> None:
    analysis = _running(analysis_id, token)
    if analysis is None or not _guard(analysis, token):
        return
    if _attempt_expired(analysis, ceilings, started):
        _fail(analysis_id, token, "attempt_exceeded")
        return
    if not _renew(analysis_id, token, ceilings["lease_seconds"]):
        _cancel_if_requested(analysis_id, token)
        return
    required = (
        assessment.subject_keys if required_subject_keys is None else required_subject_keys
    )
    knowledge = frozen_knowledge(configuration)
    if assembled_coverage is None:
        correction_payload = correction_envelope(
            assessment.issues,
            pieces,
            items,
            required,
        )
        correction_payload["knowledge"] = knowledge
    else:
        correction_payload = correction_envelope(
            assessment.issues,
            pieces,
            items,
            required,
            candidate=candidate if isinstance(candidate, dict) else {},
            knowledge=knowledge,
            assemble_coverage=True,
        )
    corrected = _contract_call(
        analysis_id=analysis_id,
        token=token,
        provider=provider,
        lot_key=CORRECTION_KEY,
        payload=correction_payload,
        ceilings=ceilings,
        configuration=configuration,
        reserved_tokens=reserved_tokens,
    )
    if corrected is None:
        return
    if assembled_coverage is not None:
        corrected = apply_coverage(corrected, assembled_coverage)
    second = assess(
        corrected,
        pieces=pieces,
        items=items,
        required_subject_keys=required,
    )
    if not second.ok or second.parsed is None:
        code = second.issues[0].code if second.issues else "response_invalid"
        _fail(analysis_id, token, code)
        return
    _finish(analysis_id, token, second.parsed, items)


def _contract_call(
    *,
    analysis_id,
    token,
    provider: BrainProvider,
    lot_key: str,
    payload: dict,
    ceilings: dict[str, int],
    configuration: dict,
    reserved_tokens: int | None = None,
) -> dict | None:
    analysis = _running(analysis_id, token)
    if analysis is None:
        return None
    config_hash = digest(configuration)
    envelope_hash = digest(payload)
    existing = _validated_lot(analysis_id, lot_key)
    if existing is not None:
        if _same_lot(existing, envelope_hash, config_hash):
            return existing.output
        _fail(analysis_id, token, "configuration_unusable")
        return None
    actual = estimate_tokens(payload)
    reserved = actual if reserved_tokens is None else reserved_tokens
    useful = useful_input_tokens(ceilings["per_call_input_tokens"])
    if (
        actual > useful
        or (reserved_tokens is not None and actual > reserved_tokens)
        or not _within_call_budget(analysis, reserved, ceilings)
    ):
        _fail(analysis_id, token, "budget_exceeded")
        return None
    result = _invoke_provider(
        provider,
        analysis_id=analysis_id,
        token=token,
        lot_key=lot_key,
        payload=payload,
        timeout_seconds=ceilings["provider_timeout_seconds"],
    )
    if result is None:
        return None
    step = PlannedLot(
        stable_key=lot_key,
        payload=payload,
        input_hash=envelope_hash,
        reserved_input_tokens=reserved,
    )
    outcome = _accept_call(
        analysis_id=analysis_id,
        token=token,
        lot=step,
        config_hash=config_hash,
        result=result,
        ceilings=ceilings,
        configuration=configuration,
        sent_tokens=reserved,
    )
    if outcome == "reused":
        stored = _validated_lot(analysis_id, lot_key)
        if stored is not None and _same_lot(stored, envelope_hash, config_hash):
            return stored.output
        return None
    if outcome != "written":
        return None
    return result.output


def _invoke_provider(provider, *, analysis_id, token, lot_key, payload, timeout_seconds):
    """Call the adapter. A contract error is terminal and does not spend the transient retry."""
    try:
        return provider.complete(
            analysis_id=str(analysis_id),
            lot_key=lot_key,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
    except BrainProviderUnavailable:
        raise
    except BrainWorkError:
        _fail(analysis_id, token, "response_invalid")
        return None


def _validated_lot(analysis_id, stable_key):
    return BrainLot.objects.filter(
        analysis_id=analysis_id,
        stable_key=stable_key,
        status=BrainLot.Status.VALIDATED,
    ).first()


def _same_lot(existing, input_hash: str, configuration_hash: str) -> bool:
    return (
        existing.input_hash == input_hash
        and existing.configuration_hash == configuration_hash
    )


def _finish(analysis_id, token, parsed, items) -> None:
    analysis = _running(analysis_id, token)
    if analysis is None or not _guard(analysis, token):
        return
    try:
        extraction = frozen_extraction(analysis)
    except BrainWorkError as exc:
        _fail(analysis_id, token, exc.code)
        return
    _complete(
        analysis_id,
        token,
        result=accepted_result(parsed, items, extraction.payload),
    )


def _within_call_budget(analysis: BrainAnalysis, reserved: int, ceilings: dict[str, int]) -> bool:
    if reserved > useful_input_tokens(ceilings["per_call_input_tokens"]):
        return False
    if analysis.provider_calls_used + 1 > ceilings["max_calls"]:
        return False
    return (
        analysis.consumed_input_tokens + billed_input_tokens(reserved)
        <= ceilings["total_input_tokens"]
    )


def _searches_executed(runs) -> bool:
    """A code alone is not an execution. The run must keep the scope that was read."""
    by_code = {}
    for run in runs:
        if run.code in by_code:
            return False
        by_code[run.code] = run
    if set(by_code) != set(REQUIRED_SEARCHES):
        return False
    for run in by_code.values():
        criteria = run.criteria if isinstance(run.criteria, dict) else None
        establishment_id = str((criteria or {}).get("establishment_id") or "").strip()
        if criteria is None or not establishment_id:
            return False
        if run.examined_count is None or run.retained_count is None:
            return False
    return True


def _dossier_context(analysis_id):
    dossier = BrainDossier.objects.filter(analysis_id=analysis_id, closed_at__isnull=False).first()
    if dossier is None:
        return None
    items = list(dossier.items.order_by("stable_key", "id"))
    runs = list(dossier.search_runs.order_by("code", "id"))
    return dossier, items, runs


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
        provider=str(configuration.get("provider") or "fake"),
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
