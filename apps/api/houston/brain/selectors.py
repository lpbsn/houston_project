"""Bounded reads for Brain history, dossier evidence, suggestions, and Knowledge."""

from __future__ import annotations

import uuid
from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from houston.action_plans.models import ActionPlan
from houston.brain.contract import public_sources
from houston.brain.errors import BrainAccessDenied, BrainWorkError
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainDossierItem,
    BrainExtraction,
    BrainKnowledgeVersion,
    BrainMechanismCandidate,
    BrainMessage,
    BrainObjective,
    BrainObjectiveEvaluation,
    BrainReporting,
    BrainSearchRun,
    BrainSlot,
    BrainSuggestion,
)
from houston.establishments.permissions import resolve_establishment_admin_actor
from houston.platform.selectors import is_active_platform_operator

_PLATFORM_VERSION_LIMIT = 100
_RELATED_PLAN_LIMIT = 20
_PAGE_DEFAULT = 30
_PAGE_MAX = 50
_MESSAGE_PAGE = 50
_WARNING_LIMIT = 40
_NOT_FOUND = "Not found."

_FAILURE_MESSAGES = {
    "cancel_requested": "L'analyse a été annulée.",
    "author_rights_lost": "Le traitement s'est arrêté : l'accès de l'auteur n'est plus valide.",
    "configuration_unusable": (
        "La configuration figée n'est plus utilisable. Une nouvelle analyse peut être demandée."
    ),
    "capture_timeout": "La capture du dossier a dépassé le temps autorisé.",
    "capture_volume_exceeded": (
        "Une catégorie dépasse le plafond de collecte. "
        "Le résultat n'est pas présenté comme exhaustif."
    ),
    "budget_exceeded": "Le budget du traitement est dépassé. Aucun résultat partiel n'est publié.",
    "transport_lost": "Le traitement n'a pas pu être repris.",
    "transient_exhausted": "Le traitement a échoué après la reprise autorisée.",
    "empty_document": "Le document ne contient pas de contenu analysable.",
    "insufficient_coverage": "Une partie requise du document n'a pas été traitée.",
    "provider_unavailable": "Le service d'analyse est indisponible.",
    "unknown_reference": "Une référence hors dossier a été refusée.",
    "response_invalid": "La réponse d'analyse n'a pas pu être validée.",
}
_FAILURE_GENERIC = (
    "Le traitement n'a pas abouti. Aucun résultat partiel n'est présenté comme une conclusion."
)


def failure_message(code: str) -> str:
    if not code:
        return ""
    return _FAILURE_MESSAGES.get(code, _FAILURE_GENERIC)


def suggestion_for_admin(*, user, suggestion_id) -> BrainSuggestion:
    suggestion = (
        BrainSuggestion.objects.select_related("current_revision")
        .filter(pk=suggestion_id)
        .first()
    )
    if suggestion is None:
        raise BrainWorkError(
            code="suggestion_not_found",
            message="La suggestion est introuvable.",
        )
    if resolve_establishment_admin_actor(user, suggestion.establishment_id) is None:
        raise BrainAccessDenied()
    return suggestion


def objective_state(*, user, objective_id) -> dict:
    objective = (
        BrainObjective.objects.select_related("current_revision", "current_bilan")
        .filter(pk=objective_id)
        .first()
    )
    if objective is None or objective.current_revision_id is None:
        raise BrainWorkError(
            code="objective_not_found",
            message="L'objectif est introuvable.",
        )
    if resolve_establishment_admin_actor(user, objective.establishment_id) is None:
        raise BrainAccessDenied()
    revision = objective.current_revision
    bilan = objective.current_bilan
    return {
        "id": str(objective.id),
        "current_revision_id": str(revision.id),
        "indicator": revision.indicator,
        "unit": revision.unit,
        "scope": revision.scope,
        "reference": revision.reference,
        "target": revision.target,
        "due_on": revision.due_on.isoformat() if revision.due_on else None,
        "method": revision.method,
        "decision": revision.decision,
        "current_bilan": None
        if bilan is None
        else {
            "id": str(bilan.id),
            "analysis_id": str(bilan.analysis_id),
            "revision_id": str(bilan.revision_id),
            "measured_period_start": bilan.measured_period_start.isoformat(),
            "measured_period_end": bilan.measured_period_end.isoformat(),
            "outcome": bilan.outcome,
            "reason": bilan.reason,
        },
    }


def plans_opened_since_capture(
    *,
    establishment_id,
    analysis_id,
    pilot_business_unit_id,
    exclude_plan_id,
) -> list[uuid.UUID]:
    """Plans created after the capture, signaled at confirmation and left unchanged."""
    capture_at = (
        BrainDossier.objects.filter(analysis_id=analysis_id, closed_at__isnull=False)
        .values_list("capture_started_at", flat=True)
        .first()
    )
    if capture_at is None:
        return []
    rows = ActionPlan.objects.filter(
        establishment_id=establishment_id,
        pilot_business_unit_id=pilot_business_unit_id,
        created_at__gt=capture_at,
    ).exclude(pk=exclude_plan_id)
    ordered = rows.order_by("-created_at", "-id").values_list("id", flat=True)
    return list(ordered[:_RELATED_PLAN_LIMIT])


def platform_knowledge_versions(*, user) -> list[dict]:
    """Global formulations only. Client evidence is not a field of this read."""
    if not is_active_platform_operator(user):
        raise BrainAccessDenied()
    rows = BrainKnowledgeVersion.objects.order_by("-approved_at", "-created_at")[
        :_PLATFORM_VERSION_LIMIT
    ]
    return [
        {
            "id": str(row.id),
            "formulation": row.global_formulation,
            "conditions": row.conditions,
            "limits": row.limits,
            "uncertainty": row.uncertainty,
            "approved_at": row.approved_at.isoformat() if row.approved_at else None,
            "activated_at": row.activated_at.isoformat() if row.activated_at else None,
            "is_active": row.is_active,
        }
        for row in rows
    ]


def platform_mechanism(*, user, candidate_id) -> dict:
    """Global representation only. Dossier items and private evidence are not loaded."""
    if not is_active_platform_operator(user):
        raise BrainAccessDenied()
    candidate = (
        BrainMechanismCandidate.objects.filter(pk=candidate_id)
        .values("id", "status", "global_representation", "knowledge_version_id")
        .first()
    )
    if candidate is None:
        raise BrainWorkError(
            code="mechanism_not_found",
            message="Le mécanisme candidat est introuvable.",
        )
    version_id = candidate["knowledge_version_id"]
    is_active = False
    if version_id is not None:
        is_active = bool(
            BrainKnowledgeVersion.objects.filter(pk=version_id)
            .values_list("is_active", flat=True)
            .first()
        )
    representation = candidate["global_representation"]
    if not isinstance(representation, dict):
        representation = {}
    withheld = representation.get("withheld")
    return {
        "id": str(candidate["id"]),
        "status": candidate["status"],
        "knowledge_version_id": None if version_id is None else str(version_id),
        "is_active": is_active,
        "representation": {
            "formulation": str(representation.get("formulation") or ""),
            "conditions": str(representation.get("conditions") or ""),
            "limits": str(representation.get("limits") or ""),
            "uncertainty": str(representation.get("uncertainty") or ""),
            "withheld": withheld if isinstance(withheld, dict) else {},
        },
    }


def _admin(user, establishment_id) -> None:
    if resolve_establishment_admin_actor(user, establishment_id) is None:
        raise BrainAccessDenied()


def _person(user) -> dict:
    if user is None:
        return {"id": None, "name": ""}
    name = " ".join(part for part in (user.first_name, user.last_name) if part).strip()
    return {"id": str(user.id), "name": name or user.username}


def _page_limit(value) -> int:
    if value in (None, ""):
        return _PAGE_DEFAULT
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BrainWorkError(code="invalid_page", message="La page demandée est invalide.") from exc
    if parsed < 1 or parsed > _PAGE_MAX:
        raise BrainWorkError(code="invalid_page", message="La page demandée est invalide.")
    return parsed


def _cursor(value: str | None):
    if not value:
        return None
    created_raw, separator, id_raw = str(value).partition("|")
    if not separator:
        raise BrainWorkError(code="invalid_cursor", message="Le curseur est invalide.")
    try:
        created = datetime.fromisoformat(created_raw)
        item_id = uuid.UUID(id_raw)
    except ValueError as exc:
        raise BrainWorkError(code="invalid_cursor", message="Le curseur est invalide.") from exc
    if timezone.is_naive(created):
        raise BrainWorkError(code="invalid_cursor", message="Le curseur est invalide.")
    return created, item_id


def _apply_cursor(queryset, cursor):
    if cursor is None:
        return queryset
    created, item_id = cursor
    return queryset.filter(Q(created_at__lt=created) | Q(created_at=created, id__lt=item_id))


def _next_cursor(rows: list, limit: int):
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    last = page[-1]
    return page, f"{last.created_at.isoformat()}|{last.id}"


def _extraction_summary(reporting: BrainReporting) -> dict:
    extraction = (
        BrainExtraction.objects.filter(
            reporting_id=reporting.id,
            source_sha256=reporting.content_sha256,
        )
        .order_by("-created_at")
        .first()
    )
    payload = {}
    if extraction is not None and isinstance(extraction.payload, dict):
        payload = extraction.payload
    warnings = _notice_list(payload.get("warnings"))
    limits = _notice_list(payload.get("limits"))
    measures = payload.get("measures")
    qualitative = payload.get("qualitative")
    coverage = payload.get("coverage")
    if coverage not in {"complete", "partial"}:
        coverage = "partial" if limits else "complete" if extraction is not None else "unknown"
    return {
        "coverage": coverage,
        "warnings": warnings,
        "limits": limits,
        "measure_count": len(measures) if isinstance(measures, list) else 0,
        "qualitative_count": len(qualitative) if isinstance(qualitative, list) else 0,
    }


def _notice_list(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    notices = []
    for item in value[:_WARNING_LIMIT]:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "")
        message = str(item.get("message") or "")
        if code and message:
            notices.append({"code": code, "message": message})
    return notices


def _reporting_dict(reporting: BrainReporting) -> dict:
    return {
        "id": str(reporting.id),
        "original_filename": reporting.original_filename,
        "source_format": reporting.source_format,
        "byte_size": reporting.byte_size,
        "status": reporting.status,
        "rejection_code": reporting.rejection_code,
        "rejection_message": reporting.rejection_message,
        "period_start": reporting.period_start.isoformat() if reporting.period_start else None,
        "period_end": reporting.period_end.isoformat() if reporting.period_end else None,
        "period_confirmed": reporting.period_confirmed_at is not None,
        "author": _person(reporting.author),
        "created_at": reporting.created_at.isoformat(),
        "extraction": _extraction_summary(reporting),
    }


def _analysis_work(analysis: BrainAnalysis) -> dict:
    return {
        "kind": "analysis",
        "id": str(analysis.id),
        "analysis_id": str(analysis.id),
        "status": analysis.status,
        "reporting_id": str(analysis.reporting_id),
    }


def _message_work(message: BrainMessage) -> dict:
    return {
        "kind": "follow_up",
        "id": str(message.id),
        "analysis_id": str(message.analysis_id),
        "status": message.status,
        "reporting_id": str(message.analysis.reporting_id),
    }


def reporting_page(*, user, establishment_id, limit, cursor: str | None) -> dict:
    _admin(user, establishment_id)
    bounded = _page_limit(limit)
    rows = list(
        _apply_cursor(
            BrainReporting.objects.select_related("author")
            .filter(establishment_id=establishment_id)
            .exclude(status=BrainReporting.Status.DRAFT)
            .order_by("-created_at", "-id"),
            _cursor(cursor),
        )[: bounded + 1]
    )
    page, next_cursor = _next_cursor(rows, bounded)
    return {"results": [_reporting_dict(row) for row in page], "next_cursor": next_cursor}


def reporting_detail(*, user, establishment_id, reporting_id) -> dict:
    _admin(user, establishment_id)
    reporting = (
        BrainReporting.objects.select_related("author")
        .filter(pk=reporting_id, establishment_id=establishment_id)
        .exclude(status=BrainReporting.Status.DRAFT)
        .first()
    )
    if reporting is None:
        raise BrainAccessDenied()
    return _reporting_dict(reporting)


def active_brain_work(*, user, establishment_id) -> dict | None:
    _admin(user, establishment_id)
    slot = (
        BrainSlot.objects.select_related("analysis", "message", "message__analysis")
        .filter(
            establishment_id=establishment_id,
            status__in=(BrainSlot.Status.QUEUED, BrainSlot.Status.RUNNING),
        )
        .first()
    )
    if slot is None:
        return None
    if slot.kind == BrainSlot.Kind.FOLLOW_UP and slot.message_id is not None:
        return _message_work(slot.message)
    if slot.analysis_id is None:
        return None
    return _analysis_work(slot.analysis)


def analysis_page(*, user, establishment_id, limit, cursor: str | None) -> dict:
    _admin(user, establishment_id)
    bounded = _page_limit(limit)
    rows = list(
        _apply_cursor(
            BrainAnalysis.objects.select_related("author", "reporting")
            .filter(establishment_id=establishment_id)
            .order_by("-created_at", "-id"),
            _cursor(cursor),
        )[: bounded + 1]
    )
    page, next_cursor = _next_cursor(rows, bounded)
    return {"results": [_analysis_summary(row) for row in page], "next_cursor": next_cursor}


def _analysis_summary(analysis: BrainAnalysis) -> dict:
    reporting = analysis.reporting
    return {
        "id": str(analysis.id),
        "status": analysis.status,
        "failure_code": analysis.failure_code,
        "failure_message": failure_message(analysis.failure_code)
        if analysis.status in {BrainAnalysis.Status.FAILED, BrainAnalysis.Status.CANCELED}
        else "",
        "author": _person(analysis.author),
        "created_at": analysis.created_at.isoformat(),
        "reporting": {
            "id": str(reporting.id),
            "original_filename": reporting.original_filename,
            "period_start": reporting.period_start.isoformat() if reporting.period_start else None,
            "period_end": reporting.period_end.isoformat() if reporting.period_end else None,
        },
    }


def _message_dict(message: BrainMessage) -> dict:
    result = message.result if isinstance(message.result, dict) else None
    declaration = message.declaration if isinstance(message.declaration, dict) else None
    return {
        "id": str(message.id),
        "request_id": message.request_id,
        "sequence": message.sequence,
        "purpose": message.purpose,
        "body": message.body,
        "status": message.status,
        "failure_code": message.failure_code,
        "failure_message": failure_message(message.failure_code)
        if message.status in {BrainMessage.Status.FAILED, BrainMessage.Status.CANCELED}
        else "",
        "author": _person(message.author),
        "created_at": message.created_at.isoformat(),
        "declaration": declaration,
        "result": result,
    }


def analysis_detail(*, user, establishment_id, analysis_id) -> dict:
    _admin(user, establishment_id)
    analysis = (
        BrainAnalysis.objects.select_related("author", "reporting")
        .filter(pk=analysis_id, establishment_id=establishment_id)
        .first()
    )
    if analysis is None:
        raise BrainAccessDenied()
    dossier = BrainDossier.objects.filter(analysis_id=analysis.id).first()
    messages = list(
        BrainMessage.objects.select_related("author")
        .filter(analysis_id=analysis.id)
        .order_by("-sequence")[: _MESSAGE_PAGE + 1]
    )
    hidden = 0
    if len(messages) > _MESSAGE_PAGE:
        hidden = (
            BrainMessage.objects.filter(analysis_id=analysis.id).count() - _MESSAGE_PAGE
        )
        messages = messages[:_MESSAGE_PAGE]
    messages.reverse()
    suggestions = list(
        BrainSuggestion.objects.select_related("current_revision")
        .filter(analysis_id=analysis.id, establishment_id=establishment_id)
        .order_by("created_at", "id")[:20]
    )
    evaluations = list(
        BrainObjectiveEvaluation.objects.select_related("revision", "objective")
        .filter(analysis_id=analysis.id, establishment_id=establishment_id)
        .order_by("measured_period_end", "id")[:50]
    )
    mechanisms = list(
        BrainMechanismCandidate.objects.filter(
            analysis_id=analysis.id,
            establishment_id=establishment_id,
        ).order_by("created_at", "id")[:20]
    )
    searches = []
    if dossier is not None:
        searches = list(
            BrainSearchRun.objects.filter(dossier_id=dossier.id).order_by("code")
        )
    result = (
        analysis.result
        if analysis.status == BrainAnalysis.Status.COMPLETED and isinstance(analysis.result, dict)
        else None
    )
    summary = _analysis_summary(analysis)
    summary.update(
        {
            "claimed_at": analysis.claimed_at.isoformat() if analysis.claimed_at else None,
            "result": result,
            "dossier": None
            if dossier is None
            else {
                "period_start": dossier.period_start.isoformat(),
                "period_end": dossier.period_end.isoformat(),
                "timezone": dossier.timezone,
                "capture_started_at": dossier.capture_started_at.isoformat(),
                "closed_at": dossier.closed_at.isoformat() if dossier.closed_at else None,
            },
            "searches": [
                {
                    "code": run.code,
                    "examined_count": run.examined_count,
                    "retained_count": run.retained_count,
                    "criteria": run.criteria if isinstance(run.criteria, dict) else {},
                }
                for run in searches
            ],
            "messages": [_message_dict(message) for message in messages],
            "older_message_count": max(hidden, 0),
            "suggestions": [_suggestion_dict(row) for row in suggestions],
            "evaluations": [_evaluation_dict(row) for row in evaluations],
            "mechanisms": [_establishment_mechanism(row) for row in mechanisms],
        }
    )
    return summary


def dossier_source_page(*, user, establishment_id, analysis_id, limit, cursor: str | None) -> dict:
    _admin(user, establishment_id)
    dossier = (
        BrainDossier.objects.filter(
            analysis_id=analysis_id,
            establishment_id=establishment_id,
            closed_at__isnull=False,
        )
        .only("id")
        .first()
    )
    if dossier is None:
        raise BrainAccessDenied()
    bounded = _page_limit(limit)
    rows = list(
        _apply_cursor(
            BrainDossierItem.objects.filter(dossier_id=dossier.id).order_by("-created_at", "-id"),
            _cursor(cursor),
        )[: bounded + 1]
    )
    page, next_cursor = _next_cursor(rows, bounded)
    return {"results": public_sources(page), "next_cursor": next_cursor}


def dossier_item(*, user, establishment_id, item_id) -> dict:
    _admin(user, establishment_id)
    item = (
        BrainDossierItem.objects.select_related("dossier")
        .filter(pk=item_id, dossier__establishment_id=establishment_id)
        .first()
    )
    if item is None:
        raise BrainAccessDenied()
    payload = item.payload if isinstance(item.payload, dict) else {}
    return {
        "id": str(item.id),
        "analysis_id": str(item.dossier.analysis_id),
        "category": item.category,
        "role": item.role,
        "reason": item.reason,
        "stable_key": item.stable_key,
        "payload": payload,
    }


def message_for_admin(*, user, establishment_id, message_id) -> BrainMessage:
    _admin(user, establishment_id)
    message = (
        BrainMessage.objects.select_related("analysis")
        .filter(pk=message_id, analysis__establishment_id=establishment_id)
        .first()
    )
    if message is None:
        raise BrainAccessDenied()
    return message


def suggestion_payload(*, user, suggestion_id, establishment_id) -> dict:
    suggestion = suggestion_for_admin(user=user, suggestion_id=suggestion_id)
    if suggestion.establishment_id != establishment_id:
        raise BrainAccessDenied()
    return _suggestion_dict(suggestion)


def _suggestion_dict(suggestion: BrainSuggestion) -> dict:
    revision = suggestion.current_revision
    return {
        "id": str(suggestion.id),
        "status": suggestion.status,
        "action_plan_id": None
        if suggestion.action_plan_id is None
        else str(suggestion.action_plan_id),
        "current_revision_id": None if revision is None else str(revision.id),
        "title": "" if revision is None else revision.title,
        "description": "" if revision is None else revision.description,
        "tasks": [] if revision is None else list(revision.tasks or []),
        "pilot_business_unit_id": None
        if revision is None or revision.pilot_business_unit_id is None
        else str(revision.pilot_business_unit_id),
        "assignees": [] if revision is None else list(revision.assignees or []),
        "start_at": None
        if revision is None or revision.start_at is None
        else revision.start_at.isoformat(),
        "end_at": None
        if revision is None or revision.end_at is None
        else revision.end_at.isoformat(),
        "occurrence_date": None
        if revision is None or revision.occurrence_date is None
        else revision.occurrence_date.isoformat(),
        "all_day": False if revision is None else revision.all_day,
        "requires_validation": True if revision is None else revision.requires_validation,
    }


def _evaluation_dict(evaluation: BrainObjectiveEvaluation) -> dict:
    revision = evaluation.revision
    return {
        "id": str(evaluation.id),
        "objective_id": str(evaluation.objective_id),
        "revision_id": str(evaluation.revision_id),
        "indicator": revision.indicator,
        "outcome": evaluation.outcome,
        "reason": evaluation.reason,
        "measured_period_start": evaluation.measured_period_start.isoformat(),
        "measured_period_end": evaluation.measured_period_end.isoformat(),
        "source_item_ids": list(evaluation.source_item_ids or []),
        "is_current_bilan": evaluation.objective.current_bilan_id == evaluation.id,
    }


def _establishment_mechanism(candidate: BrainMechanismCandidate) -> dict:
    representation = (
        candidate.global_representation
        if isinstance(candidate.global_representation, dict)
        else {}
    )
    return {
        "id": str(candidate.id),
        "status": candidate.status,
        "formulation": candidate.formulation,
        "global_representation": {
            "formulation": str(representation.get("formulation") or ""),
            "conditions": str(representation.get("conditions") or ""),
            "limits": str(representation.get("limits") or ""),
            "uncertainty": str(representation.get("uncertainty") or ""),
        },
        "private_evidence_item_ids": [
            str(item_id) for item_id in (candidate.private_evidence or [])[:20]
        ],
        "knowledge_version_id": None
        if candidate.knowledge_version_id is None
        else str(candidate.knowledge_version_id),
    }


def objective_page(*, user, establishment_id, limit, cursor: str | None) -> dict:
    _admin(user, establishment_id)
    bounded = _page_limit(limit)
    rows = list(
        _apply_cursor(
            BrainObjective.objects.select_related("current_revision", "current_bilan")
            .filter(establishment_id=establishment_id, current_revision__isnull=False)
            .order_by("-created_at", "-id"),
            _cursor(cursor),
        )[: bounded + 1]
    )
    page, next_cursor = _next_cursor(rows, bounded)
    return {"results": [_living_objective(row) for row in page], "next_cursor": next_cursor}


def _living_objective(objective: BrainObjective) -> dict:
    revision = objective.current_revision
    bilan = objective.current_bilan
    return {
        "id": str(objective.id),
        "current_revision_id": str(revision.id),
        "indicator": revision.indicator,
        "unit": revision.unit,
        "scope": revision.scope,
        "reference": revision.reference,
        "target": revision.target,
        "due_on": revision.due_on.isoformat() if revision.due_on else None,
        "method": revision.method,
        "decision": revision.decision,
        "current_bilan": None
        if bilan is None
        else {
            "id": str(bilan.id),
            "analysis_id": str(bilan.analysis_id),
            "revision_id": str(bilan.revision_id),
            "measured_period_start": bilan.measured_period_start.isoformat(),
            "measured_period_end": bilan.measured_period_end.isoformat(),
            "outcome": bilan.outcome,
            "reason": bilan.reason,
        },
    }


def platform_mechanism_candidates(*, user) -> list[dict]:
    """Global formulations only. Private evidence and dossiers are not loaded."""
    if not is_active_platform_operator(user):
        raise BrainAccessDenied()
    rows = list(
        BrainMechanismCandidate.objects.order_by("-created_at", "-id").values(
            "id",
            "status",
            "global_representation",
            "knowledge_version_id",
        )[:_PLATFORM_VERSION_LIMIT]
    )
    version_ids = [row["knowledge_version_id"] for row in rows if row["knowledge_version_id"]]
    active = set(
        BrainKnowledgeVersion.objects.filter(pk__in=version_ids, is_active=True).values_list(
            "id",
            flat=True,
        )
    )
    listed = []
    for row in rows:
        representation = row["global_representation"]
        if not isinstance(representation, dict):
            representation = {}
        version_id = row["knowledge_version_id"]
        listed.append(
            {
                "id": str(row["id"]),
                "status": row["status"],
                "knowledge_version_id": None if version_id is None else str(version_id),
                "is_active": version_id in active,
                "representation": {
                    "formulation": str(representation.get("formulation") or ""),
                    "conditions": str(representation.get("conditions") or ""),
                    "limits": str(representation.get("limits") or ""),
                    "uncertainty": str(representation.get("uncertainty") or ""),
                    "withheld": representation.get("withheld")
                    if isinstance(representation.get("withheld"), dict)
                    else {},
                },
            }
        )
    return listed
