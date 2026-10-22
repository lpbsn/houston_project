"""Follow-ups on a closed dossier.

The message has its own status and budgets. A failure here does not change the
completed analysis. Citations are dossier item ids. A declaration is stored and
is not written back onto the dossier. A reanalysis is described and not admitted.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Literal

from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from houston.accounts.models import User
from houston.ai.models import AIUsageLog
from houston.brain.configuration import (
    call_input_tokens,
    digest,
    follow_up_ceilings,
    frozen_counter,
    frozen_knowledge,
    frozen_mechanisms,
)
from houston.brain.errors import BrainWorkError
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainDossierItem,
    BrainLot,
    BrainMessage,
    BrainSlot,
)
from houston.brain.provider import (
    BrainProvider,
    BrainProviderUnavailable,
    FakeBrainProvider,
    ProviderCallResult,
)
from houston.brain.runtime import (
    _input_gap_context,
    _output_acceptable,
    _token,
    claim_message,
    renew_message,
    requeue_message,
    touch_message,
    transition_message,
)
from houston.establishments.permissions import resolve_establishment_admin_actor

logger = logging.getLogger(__name__)

FOLLOW_UP_SCHEMA = "brain_follow_up_v1"
_DECLARATIONS = {
    BrainMessage.Purpose.CORRECTION,
    BrainMessage.Purpose.NEW_FACT,
    BrainMessage.Purpose.NEW_DOCUMENT,
}
_NEW_FILE = {
    BrainMessage.Purpose.CORRECTION,
    BrainMessage.Purpose.NEW_DOCUMENT,
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FollowUpCitation(_Strict):
    item_id: str = Field(min_length=1, max_length=64)


class FollowUpModelOutput(_Strict):
    """What the provider may return. It cannot publish a decision object."""

    schema_version: Literal["brain_follow_up_v1"]
    mode: Literal["explanation", "hypothesis"]
    answer: str = Field(min_length=1, max_length=4000)
    hypothesis_label: str | None = Field(default=None, max_length=200)
    citations: list[FollowUpCitation] = Field(default_factory=list, max_length=40)


def run_brain_follow_up(
    message_id,
    attempt_token,
    *,
    provider: BrainProvider | None = None,
) -> None:
    token = _token(attempt_token)
    if token is None or not claim_message(message_id, token):
        return
    started = time.monotonic()
    try:
        _execute(message_id, token, provider=provider, started=started)
    except BrainProviderUnavailable:
        if not requeue_message(message_id, token):
            transition_message(
                message_id,
                token,
                status=BrainMessage.Status.FAILED,
                failure_code="transient_exhausted",
            )
    except Exception:
        logger.exception(
            "brain_follow_up_attempt_interrupted",
            extra={
                "event": "brain_follow_up_attempt_interrupted",
                "message_id": str(message_id),
            },
        )
        raise


def write_follow_up_lot(
    *,
    message_id,
    attempt_token,
    stable_key: str,
    input_hash: str,
    configuration_hash: str,
    output: dict,
    reserved_input_tokens: int,
) -> bool:
    """Insert one validated lot for the current running message token. Never rewrite one."""
    token = _token(attempt_token)
    if token is None:
        return False
    with transaction.atomic():
        current = (
            BrainMessage.objects.select_for_update()
            .filter(
                id=message_id,
                attempt_token=token,
                status=BrainMessage.Status.RUNNING,
            )
            .first()
        )
        if current is None:
            return False
        existing = BrainLot.objects.filter(
            analysis_id=current.analysis_id,
            stable_key=stable_key,
        ).first()
        if existing is not None:
            return False
        BrainLot.objects.create(
            analysis_id=current.analysis_id,
            stable_key=stable_key,
            input_hash=input_hash,
            configuration_hash=configuration_hash,
            status=BrainLot.Status.VALIDATED,
            output=output,
            attempt_token=token,
            reserved_input_tokens=reserved_input_tokens,
        )
        return True


def configuration_proposal(analysis: BrainAnalysis) -> dict:
    return _proposal_result(
        analysis,
        reason="configuration_unusable",
        answer=(
            "La configuration figée de l'analyse est inutilisable. "
            "Une nouvelle analyse peut être demandée explicitement. Elle n'est pas lancée."
        ),
    )


def _execute(message_id, token, *, provider: BrainProvider | None, started: float) -> None:
    message = _running(message_id, token)
    if message is None or not _rights_hold(message, token):
        return
    analysis = message.analysis
    if analysis.status != BrainAnalysis.Status.COMPLETED or not _dossier_closed(analysis.id):
        _fail(message_id, token, "follow_up_unavailable")
        return
    try:
        ceilings = follow_up_ceilings(analysis.configuration)
    except BrainWorkError:
        _fail(
            message_id,
            token,
            "configuration_unusable",
            result=configuration_proposal(analysis),
        )
        return
    if _attempt_expired(message, ceilings, started):
        _fail(message_id, token, "attempt_exceeded")
        return
    if message.purpose in _DECLARATIONS:
        _complete_declaration(message, token)
        return
    if provider is None:
        if analysis.configuration.get("provider") != "fake":
            _fail(message_id, token, "provider_not_allowed")
            return
        provider = FakeBrainProvider()
    dossier_items = list(
        BrainDossierItem.objects.filter(
            dossier__analysis_id=analysis.id,
            dossier__closed_at__isnull=False,
        )
    )
    by_id = {str(item.id): item for item in dossier_items}
    required_ids = _required_ids(message, analysis)
    unknown = [item_id for item_id in required_ids if item_id not in by_id]
    if unknown:
        _complete(
            message_id,
            token,
            _proposal_result(
                analysis,
                reason="unknown_reference",
                answer=(
                    "Une référence demandée n'appartient pas au dossier figé. "
                    "Aucune source vivante n'est lue. Une nouvelle analyse est proposée "
                    "et n'est pas lancée."
                ),
                unknown_item_ids=unknown,
            ),
        )
        return
    try:
        payload = _context_payload(message, analysis, by_id, required_ids, ceilings)
    except BrainWorkError as exc:
        if exc.code == "configuration_unusable":
            _fail(
                message_id,
                token,
                exc.code,
                result=configuration_proposal(analysis),
            )
            return
        if exc.code != "budget_exceeded":
            _fail(message_id, token, exc.code)
            return
        _fail(
            message_id,
            token,
            "budget_exceeded",
            result=_proposal_result(
                analysis,
                reason="budget_exceeded",
                answer=(
                    "Le budget du follow-up ne peut pas contenir les preuves requises. "
                    "Elles n'ont pas été tronquées. Une nouvelle analyse est proposée "
                    "et n'est pas lancée."
                ),
            ),
        )
        return
    if not _rights_hold(_running(message_id, token), token):
        return
    if not renew_message(message_id, token, ceilings["lease_seconds"]):
        _cancel_if_requested(message_id, token)
        return
    config_hash = digest(analysis.configuration)
    input_hash = digest(payload)
    lot_key = follow_up_lot_key(message_id)
    existing = BrainLot.objects.filter(
        analysis_id=analysis.id,
        stable_key=lot_key,
        status=BrainLot.Status.VALIDATED,
    ).first()
    if existing is not None:
        same = existing.input_hash == input_hash and existing.configuration_hash == config_hash
        if not same:
            _fail(
                message_id,
                token,
                "configuration_unusable",
                result=configuration_proposal(analysis),
            )
            return
        output = existing.output
    else:
        provider_name, model_name = frozen_counter(analysis.configuration)
        reserved_exact = call_input_tokens(payload, provider=provider_name, model=model_name)
        if not touch_message(message_id, token, reserved_input_tokens=reserved_exact):
            return
        result = provider.complete(
            analysis_id=str(analysis.id),
            lot_key=lot_key,
            payload=payload,
            timeout_seconds=ceilings["provider_timeout_seconds"],
        )
        outcome = _accept_provider_call(
            message=message,
            token=token,
            lot_key=lot_key,
            input_hash=input_hash,
            config_hash=config_hash,
            payload=payload,
            result=result,
            ceilings=ceilings,
            configuration=analysis.configuration,
            dossier_ids=set(by_id),
        )
        if outcome != "written":
            return
        stored = BrainLot.objects.filter(
            analysis_id=analysis.id,
            stable_key=lot_key,
            status=BrainLot.Status.VALIDATED,
        ).first()
        if stored is None:
            return
        output = stored.output
    parsed = _validated_output(output, set(by_id))
    if parsed is None:
        _fail(message_id, token, "response_invalid")
        return
    if not _rights_hold(_running(message_id, token), token):
        return
    _complete(message_id, token, _answer_result(parsed, payload))


def follow_up_lot_key(message_id) -> str:
    return f"fu-{message_id}"


def _complete_declaration(message: BrainMessage, token) -> None:
    analysis = message.analysis
    declaration = message.declaration if isinstance(message.declaration, dict) else None
    if declaration is None or declaration.get("applied") is not False:
        _fail(message.id, token, "response_invalid")
        return
    reason = message.purpose
    if reason == BrainMessage.Purpose.CORRECTION:
        answer = (
            "La correction est conservée comme déclaration. Elle n'est pas appliquée au dossier. "
            "Une nouvelle analyse est proposée et n'est pas lancée."
        )
    elif reason == BrainMessage.Purpose.NEW_DOCUMENT:
        answer = (
            "Le document déclaré n'est pas ajouté au dossier. "
            "Une nouvelle analyse sur un reporting corrigé est proposée et n'est pas lancée."
        )
    else:
        answer = (
            "Le fait déclaré est conservé comme déclaration. Il n'entre pas dans le dossier. "
            "Une nouvelle analyse est proposée et n'est pas lancée."
        )
    _complete(
        message.id,
        token,
        _proposal_result(
            analysis,
            reason=reason,
            answer=answer,
            declaration=declaration,
        ),
    )


def _context_payload(message, analysis, by_id, required_ids, ceilings) -> dict:
    required_items = [_item_record(by_id[item_id]) for item_id in required_ids]
    prior = list(
        BrainMessage.objects.filter(
            analysis_id=analysis.id,
            status=BrainMessage.Status.COMPLETED,
            sequence__lt=message.sequence,
        ).order_by("sequence", "id")
    )
    declarations = []
    for earlier in prior:
        if not isinstance(earlier.declaration, dict):
            continue
        declarations.append(
            {
                "sequence": earlier.sequence,
                "kind": earlier.declaration.get("kind"),
                "text": earlier.declaration.get("text"),
                "applied": False,
            }
        )
    config = analysis.configuration if isinstance(analysis.configuration, dict) else {}
    knowledge = frozen_knowledge(config)
    mechanisms = frozen_mechanisms(config)
    budget = min(ceilings["per_call_input_tokens"], ceilings["follow_up_total_input_tokens"])
    provider_name, model_name = frozen_counter(analysis.configuration)

    def assemble(
        selected: list[dict],
        history_kept: list[dict],
        history_omitted: list[dict],
    ) -> dict:
        required = {
            "question": message.body,
            "purpose": message.purpose,
            "frozen_configuration": {
                "knowledge": knowledge,
                "mechanisms": selected,
                "mechanisms_omitted": len(mechanisms) - len(selected),
                "schema_version": config.get("schema_version"),
                "prompt_version": config.get("prompt_version"),
                "model": config.get("model"),
            },
            "analysis_result": analysis.result,
            "required_items": required_items,
            "declarations": declarations,
        }
        return _envelope(
            message,
            required,
            required_ids,
            history_kept,
            _summary(history_omitted),
        )

    kept_mechanisms = list(mechanisms)
    # Mechanisms that fit beside the required evidence stay. The omitted tail is counted.
    while True:
        bare = assemble(kept_mechanisms, [], [])
        if call_input_tokens(bare, provider=provider_name, model=model_name) <= budget:
            break
        if not kept_mechanisms:
            raise BrainWorkError(
                code="budget_exceeded",
                message="Le budget du follow-up ne peut pas contenir les preuves requises.",
            )
        kept_mechanisms.pop()
    views = [_message_view(earlier) for earlier in prior]
    kept = list(views)
    omitted: list[dict] = []
    # Newest turns stay in full while they fit. Older turns become one derived summary.
    while True:
        payload = assemble(kept_mechanisms, kept, omitted)
        if call_input_tokens(payload, provider=provider_name, model=model_name) <= budget:
            return payload
        if not kept:
            raise BrainWorkError(
                code="budget_exceeded",
                message="Le budget du follow-up ne peut pas contenir les preuves requises.",
            )
        omitted.append(kept.pop(0))
        omitted.sort(key=lambda view: view["sequence"])


def _envelope(message, required, required_ids, kept, summary) -> dict:
    return {
        "contract": FOLLOW_UP_SCHEMA,
        "purpose": message.purpose,
        "required_item_ids": list(required_ids),
        "question": required["question"],
        "frozen_configuration": required["frozen_configuration"],
        "analysis_result": required["analysis_result"],
        "required_items": required["required_items"],
        "declarations": required["declarations"],
        "history": {
            "summary": summary,
            "messages": kept,
        },
    }


def _summary(omitted: list[dict]) -> dict | None:
    if not omitted:
        return None
    return {
        "derived": True,
        "covers_sequences": [view["sequence"] for view in omitted],
        "message_count": len(omitted),
    }


def _message_view(message: BrainMessage) -> dict:
    result = message.result if isinstance(message.result, dict) else {}
    return {
        "sequence": message.sequence,
        "purpose": message.purpose,
        "body": message.body,
        "answer": result.get("answer") or "",
    }


def _item_record(item: BrainDossierItem) -> dict:
    return {
        "item_id": str(item.id),
        "category": item.category,
        "stable_key": item.stable_key,
        "role": item.role,
        "payload": item.payload,
        "reason": item.reason,
    }


def _required_ids(message: BrainMessage, analysis: BrainAnalysis) -> list[str]:
    explicit = message.cited_item_ids if isinstance(message.cited_item_ids, list) else []
    if explicit:
        return [str(item_id) for item_id in explicit]
    found = []
    seen = set()

    def walk(node) -> None:
        if isinstance(node, dict):
            item_id = node.get("item_id")
            if isinstance(item_id, str) and item_id not in seen:
                seen.add(item_id)
                found.append(item_id)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    if isinstance(analysis.result, dict):
        walk(analysis.result.get("subjects"))
    return found


def _accept_provider_call(
    *,
    message: BrainMessage,
    token,
    lot_key: str,
    input_hash: str,
    config_hash: str,
    payload: dict,
    result: ProviderCallResult,
    ceilings: dict[str, int],
    configuration: dict,
    dossier_ids: set[str],
) -> str:
    acceptable = _output_acceptable(result, ceilings["per_call_output_tokens"])
    provider_name, model_name = frozen_counter(configuration)
    reserved = call_input_tokens(payload, provider=provider_name, model=model_name)
    charged = result.input_tokens if result.input_tokens is not None else reserved
    gap = _input_gap_context(
        estimated=reserved,
        provider_tokens=result.input_tokens,
        per_call=ceilings["per_call_input_tokens"],
        lot_key=lot_key,
    )
    parsed = _validated_output(result.output, dossier_ids) if acceptable else None
    now = timezone.now()
    with transaction.atomic():
        row = (
            BrainMessage.objects.select_for_update()
            .filter(
                id=message.id,
                attempt_token=token,
                status=BrainMessage.Status.RUNNING,
            )
            .first()
        )
        if row is None or row.cancel_requested_at is not None:
            return "stopped"
        calls = row.provider_calls_used + 1
        consumed = row.consumed_input_tokens + max(0, charged)
        over_budget = (
            calls > ceilings["follow_up_max_calls"]
            or consumed > ceilings["follow_up_total_input_tokens"]
            or (
                result.input_tokens is not None
                and result.input_tokens > ceilings["per_call_input_tokens"]
            )
        )
        code = ""
        if not acceptable:
            code = "provider_output_rejected"
        elif over_budget:
            code = "budget_exceeded"
        elif parsed is None:
            unknown = _unknown_citation(result.output, dossier_ids)
            code = "unknown_reference" if unknown else "response_invalid"
        row.provider_calls_used = calls
        row.consumed_input_tokens = consumed
        row.lease_expires_at = now + timedelta(seconds=ceilings["lease_seconds"])
        if code:
            row.status = BrainMessage.Status.FAILED
            row.failure_code = code
            row.lease_expires_at = None
            update_fields = [
                "provider_calls_used",
                "consumed_input_tokens",
                "lease_expires_at",
                "status",
                "failure_code",
                "updated_at",
            ]
            if code == "budget_exceeded":
                row.result = _proposal_result(
                    message.analysis,
                    reason="budget_exceeded",
                    answer=(
                        "Le budget du follow-up est épuisé. "
                        "Une nouvelle analyse est proposée et n'est pas lancée."
                    ),
                )
                update_fields.append("result")
            row.save(update_fields=update_fields)
            BrainSlot.objects.filter(message_id=message.id).delete()
            _usage(
                message,
                configuration=configuration,
                result=result,
                error_code=code,
                status=AIUsageLog.Status.FAILED,
                error_context=gap,
            )
            return "failed"
        existing = BrainLot.objects.filter(
            analysis_id=message.analysis_id,
            stable_key=lot_key,
        ).first()
        if existing is not None and (
            existing.input_hash != input_hash or existing.configuration_hash != config_hash
        ):
            row.status = BrainMessage.Status.FAILED
            row.failure_code = "configuration_unusable"
            row.lease_expires_at = None
            row.result = configuration_proposal(message.analysis)
            row.save(
                update_fields=[
                    "provider_calls_used",
                    "consumed_input_tokens",
                    "lease_expires_at",
                    "status",
                    "failure_code",
                    "result",
                    "updated_at",
                ]
            )
            BrainSlot.objects.filter(message_id=message.id).delete()
            return "failed"
        if existing is None:
            BrainLot.objects.create(
                analysis_id=message.analysis_id,
                stable_key=lot_key,
                input_hash=input_hash,
                configuration_hash=config_hash,
                status=BrainLot.Status.VALIDATED,
                output=result.output,
                attempt_token=token,
                reserved_input_tokens=reserved,
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
            message,
            configuration=configuration,
            result=result,
            error_code="",
            status=AIUsageLog.Status.SUCCEEDED,
            error_context=gap,
        )
        return "written"


def _validated_output(output, dossier_ids: set[str]) -> FollowUpModelOutput | None:
    if not isinstance(output, dict):
        return None
    try:
        parsed = FollowUpModelOutput.model_validate(output)
    except ValidationError:
        return None
    if parsed.mode == "hypothesis":
        if not (parsed.hypothesis_label or "").strip():
            return None
    elif parsed.hypothesis_label:
        return None
    if any(citation.item_id not in dossier_ids for citation in parsed.citations):
        return None
    return parsed


def _unknown_citation(output, dossier_ids: set[str]) -> bool:
    if not isinstance(output, dict):
        return False
    citations = output.get("citations")
    if not isinstance(citations, list):
        return False
    for citation in citations:
        if isinstance(citation, dict) and citation.get("item_id") not in dossier_ids:
            return True
    return False


def _answer_result(parsed: FollowUpModelOutput, payload: dict) -> dict:
    history = payload.get("history") if isinstance(payload, dict) else {}
    summary = history.get("summary") if isinstance(history, dict) else None
    messages = history.get("messages") if isinstance(history, dict) else []
    summarized = []
    if isinstance(summary, dict):
        summarized = list(summary.get("covers_sequences") or [])
    return {
        "schema_version": FOLLOW_UP_SCHEMA,
        "mode": parsed.mode,
        "answer": parsed.answer,
        "hypothesis_label": parsed.hypothesis_label,
        "citations": [citation.model_dump() for citation in parsed.citations],
        "declaration": None,
        "reanalysis": None,
        "unknown_item_ids": [],
        "context": {
            "required_item_ids": list(payload.get("required_item_ids") or []),
            "full_message_sequences": [
                view["sequence"] for view in messages if isinstance(view, dict)
            ],
            "summarized_sequences": summarized,
            "derived_summary": bool(summary),
        },
    }


def _proposal_result(
    analysis: BrainAnalysis,
    *,
    reason: str,
    answer: str,
    declaration: dict | None = None,
    unknown_item_ids: list[str] | None = None,
) -> dict:
    reporting = analysis.reporting
    return {
        "schema_version": FOLLOW_UP_SCHEMA,
        "mode": "reanalysis_proposed",
        "answer": answer,
        "hypothesis_label": None,
        "citations": [],
        "declaration": declaration,
        "reanalysis": {
            "proposed": True,
            "launched": False,
            "reason": reason,
            "linked_analysis_id": str(analysis.id),
            "reporting_id": str(analysis.reporting_id),
            "period_start": reporting.period_start.isoformat() if reporting.period_start else None,
            "period_end": reporting.period_end.isoformat() if reporting.period_end else None,
            "requires_new_reporting": reason in _NEW_FILE,
        },
        "unknown_item_ids": list(unknown_item_ids or []),
        "context": None,
    }


def _running(message_id, token) -> BrainMessage | None:
    return (
        BrainMessage.objects.select_related("analysis", "analysis__reporting", "author")
        .filter(
            id=message_id,
            attempt_token=token,
            status=BrainMessage.Status.RUNNING,
        )
        .first()
    )


def _rights_hold(message: BrainMessage | None, token) -> bool:
    if message is None:
        return False
    if message.cancel_requested_at is not None:
        transition_message(
            message.id,
            token,
            status=BrainMessage.Status.CANCELED,
            failure_code="cancel_requested",
        )
        return False
    user = User.objects.filter(pk=message.author_id).first()
    if resolve_establishment_admin_actor(user, message.analysis.establishment_id) is None:
        transition_message(
            message.id,
            token,
            status=BrainMessage.Status.CANCELED,
            failure_code="author_rights_lost",
        )
        return False
    return True


def _dossier_closed(analysis_id) -> bool:
    return BrainDossier.objects.filter(analysis_id=analysis_id, closed_at__isnull=False).exists()


def _attempt_expired(message: BrainMessage, ceilings: dict[str, int], started: float) -> bool:
    if message.claimed_at is None:
        return False
    elapsed = timezone.now() - message.claimed_at
    if elapsed.total_seconds() >= ceilings["attempt_hard_seconds"]:
        return True
    return (time.monotonic() - started) >= ceilings["attempt_hard_seconds"]


def _complete(message_id, token, result: dict) -> bool:
    completed = transition_message(
        message_id,
        token,
        status=BrainMessage.Status.COMPLETED,
        only_if_not_canceled=True,
        result=result,
    )
    if completed:
        logger.info(
            "brain_follow_up_completed",
            extra={"event": "brain_follow_up_completed", "message_id": str(message_id)},
        )
        return True
    _cancel_if_requested(message_id, token)
    return False


def _fail(message_id, token, failure_code: str, result: dict | None = None) -> bool:
    failed = transition_message(
        message_id,
        token,
        status=BrainMessage.Status.FAILED,
        failure_code=failure_code,
        result=result,
    )
    if failed:
        logger.info(
            "brain_follow_up_failed",
            extra={
                "event": "brain_follow_up_failed",
                "message_id": str(message_id),
                "failure_code": failure_code,
            },
        )
    return failed


def _cancel_if_requested(message_id, token) -> None:
    row = BrainMessage.objects.filter(
        id=message_id,
        attempt_token=token,
        status=BrainMessage.Status.RUNNING,
    ).first()
    if row is not None and row.cancel_requested_at is not None:
        transition_message(
            message_id,
            token,
            status=BrainMessage.Status.CANCELED,
            failure_code=row.failure_code or "cancel_requested",
        )


def _usage(
    message,
    *,
    configuration,
    result,
    error_code: str,
    status: str,
    error_context: dict | None = None,
) -> None:
    input_tokens = result.input_tokens
    output_tokens = result.output_tokens
    total = None
    if input_tokens is not None or output_tokens is not None:
        total = (input_tokens or 0) + (output_tokens or 0)
    AIUsageLog.objects.create(
        ai_domain=AIUsageLog.Domain.BRAIN_FOLLOW_UP,
        provider=str(configuration.get("provider") or "fake"),
        model=str(configuration.get("model") or ""),
        prompt_version=str(configuration.get("prompt_version") or ""),
        schema_version=FOLLOW_UP_SCHEMA,
        status=status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total,
        error_code=error_code,
        error_context=error_context or {},
        correlation_id=message.id,
        establishment_id=message.analysis.establishment_id,
    )
