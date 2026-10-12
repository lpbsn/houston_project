"""Bounded reads for suggestions, objectives, and platform Knowledge."""

from __future__ import annotations

import uuid

from houston.action_plans.models import ActionPlan
from houston.brain.errors import BrainAccessDenied, BrainWorkError
from houston.brain.models import (
    BrainDossier,
    BrainKnowledgeVersion,
    BrainMechanismCandidate,
    BrainObjective,
    BrainSuggestion,
)
from houston.establishments.permissions import resolve_establishment_admin_actor
from houston.platform.selectors import is_active_platform_operator

_PLATFORM_VERSION_LIMIT = 100
_RELATED_PLAN_LIMIT = 20


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
