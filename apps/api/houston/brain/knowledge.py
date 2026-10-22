"""Mechanism review and platform Knowledge. Approval does not activate a version."""

from __future__ import annotations

import re

from django.db import transaction
from django.utils import timezone

from houston.brain.errors import BrainAccessDenied, BrainWorkError
from houston.brain.models import (
    BrainDossierItem,
    BrainKnowledgeVersion,
    BrainMechanismCandidate,
)
from houston.establishments.models import Establishment
from houston.establishments.permissions import resolve_establishment_admin_actor
from houston.platform.selectors import is_active_platform_operator

_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_EXCERPT = 40


def publish_mechanism_candidates(analysis, proposals) -> None:
    """Store candidates. The global representation is screened here, with the dossier."""
    if not isinstance(proposals, list):
        return
    establishment_name = (
        Establishment.objects.filter(pk=analysis.establishment_id)
        .values_list("name", flat=True)
        .first()
        or ""
    )
    excerpts = dossier_excerpts(analysis.id)
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        key = str(proposal.get("key") or "").strip()
        formulation = str(proposal.get("formulation") or "").strip()
        if not key or not formulation:
            continue
        if BrainMechanismCandidate.objects.filter(analysis_id=analysis.id, stable_key=key).exists():
            continue
        conditions = str(proposal.get("conditions") or "")
        limits = str(proposal.get("limits") or "")
        uncertainty = str(proposal.get("uncertainty") or "")
        representation = _screened_representation(
            formulation=str(proposal.get("global_formulation") or ""),
            conditions=conditions,
            limits=limits,
            uncertainty=uncertainty,
            establishment_name=establishment_name,
            excerpts=excerpts,
        )
        evidence = _evidence(proposal.get("evidence_item_ids"), analysis.id)
        BrainMechanismCandidate.objects.create(
            analysis=analysis,
            establishment_id=analysis.establishment_id,
            stable_key=key,
            formulation=formulation,
            global_formulation=representation["formulation"],
            conditions=conditions,
            limits=limits,
            uncertainty=uncertainty,
            origin="analysis",
            private_evidence=evidence,
            global_representation=representation,
        )


def revise_global_representation(
    *,
    user,
    candidate_id,
    formulation: str,
    conditions: str = "",
    limits: str = "",
    uncertainty: str = "",
) -> dict:
    """Establishment-side preparation. The dossier check happens only here."""
    with transaction.atomic():
        candidate = (
            BrainMechanismCandidate.objects.select_for_update(of=("self",))
            .select_related("establishment")
            .filter(pk=candidate_id)
            .first()
        )
        if candidate is None:
            raise BrainWorkError(
                code="mechanism_not_found",
                message="Le mécanisme candidat est introuvable.",
            )
        if resolve_establishment_admin_actor(user, candidate.establishment_id) is None:
            raise BrainAccessDenied()
        if candidate.status != BrainMechanismCandidate.Status.CANDIDATE:
            raise BrainWorkError(
                code="mechanism_not_revisable",
                message="La représentation globale n'est plus modifiable.",
            )
        representation = _require_clean_representation(
            formulation=formulation,
            conditions=conditions,
            limits=limits,
            uncertainty=uncertainty,
            establishment_name=candidate.establishment.name,
            excerpts=dossier_excerpts(candidate.analysis_id),
        )
        candidate.global_representation = representation
        candidate.global_formulation = representation["formulation"]
        candidate.save(
            update_fields=["global_representation", "global_formulation", "updated_at"]
        )
        return representation


def decide_mechanism(*, user, candidate_id, decision: str) -> None:
    """Approve or reject the stored global representation. Approval does not read the dossier."""
    _require_operator(user)
    if decision not in {"approve", "reject"}:
        raise BrainWorkError(
            code="mechanism_decision_invalid",
            message="La revue du mécanisme n'est pas reconnue.",
        )
    with transaction.atomic():
        candidate = (
            BrainMechanismCandidate.objects.select_for_update(of=("self",))
            .only(
                "id",
                "status",
                "global_representation",
                "knowledge_version_id",
                "reviewed_by_id",
                "updated_at",
            )
            .filter(pk=candidate_id)
            .first()
        )
        if candidate is None:
            raise BrainWorkError(
                code="mechanism_not_found",
                message="Le mécanisme candidat est introuvable.",
            )
        if candidate.status == BrainMechanismCandidate.Status.APPROVED:
            return
        if candidate.status == BrainMechanismCandidate.Status.REJECTED:
            raise BrainWorkError(
                code="mechanism_already_rejected",
                message="Ce mécanisme a déjà été rejeté.",
            )
        if decision == "reject":
            candidate.status = BrainMechanismCandidate.Status.REJECTED
            candidate.reviewed_by = user
            candidate.save(update_fields=["status", "reviewed_by", "updated_at"])
            return
        representation = _representation(candidate.global_representation)
        if not representation["formulation"]:
            raise BrainWorkError(
                code="mechanism_formulation_required",
                message="L'approbation exige une formulation globale déjà préparée.",
            )
        version = BrainKnowledgeVersion.objects.create(
            identifier=candidate.stable_key[:80],
            global_formulation=representation["formulation"],
            conditions=representation["conditions"],
            limits=representation["limits"],
            uncertainty=representation["uncertainty"],
            approved_at=timezone.now(),
            is_active=False,
        )
        candidate.status = BrainMechanismCandidate.Status.APPROVED
        candidate.knowledge_version = version
        candidate.reviewed_by = user
        candidate.save(
            update_fields=["status", "knowledge_version", "reviewed_by", "updated_at"]
        )


def activate_knowledge_version(*, user, version_id) -> BrainKnowledgeVersion:
    """Explicit activation. It does not rewrite analyses that already copied a version."""
    _require_operator(user)
    with transaction.atomic():
        version = (
            BrainKnowledgeVersion.objects.select_for_update().filter(pk=version_id).first()
        )
        if version is None:
            raise BrainWorkError(
                code="knowledge_not_found",
                message="La version de Knowledge est introuvable.",
            )
        if version.approved_at is None:
            raise BrainWorkError(
                code="knowledge_not_approved",
                message="Une version non approuvée ne s'active pas.",
            )
        BrainKnowledgeVersion.objects.filter(
            is_active=True,
            identifier=version.identifier,
        ).exclude(pk=version.id).update(
            is_active=False,
            updated_at=timezone.now(),
        )
        version.is_active = True
        version.activated_at = timezone.now()
        version.save(update_fields=["is_active", "activated_at", "updated_at"])
        return version


def _screened_representation(
    *,
    formulation: str,
    conditions: str,
    limits: str,
    uncertainty: str,
    establishment_name: str,
    excerpts: list[str],
) -> dict:
    """Keep only text that passes the refusal gate. Failing text is not stored here."""
    withheld = {}
    kept = {}
    for field, value in (
        ("formulation", formulation),
        ("conditions", conditions),
        ("limits", limits),
        ("uncertainty", uncertainty),
    ):
        text = str(value or "").strip()
        if not text:
            kept[field] = ""
            continue
        issue = identifying_formulation(
            text,
            establishment_name=establishment_name,
            excerpts=excerpts,
        )
        if issue:
            kept[field] = ""
            withheld[field] = issue
            continue
        kept[field] = text
    kept["withheld"] = withheld
    return kept


def _require_clean_representation(
    *,
    formulation: str,
    conditions: str,
    limits: str,
    uncertainty: str,
    establishment_name: str,
    excerpts: list[str],
) -> dict:
    representation = _screened_representation(
        formulation=formulation,
        conditions=conditions,
        limits=limits,
        uncertainty=uncertainty,
        establishment_name=establishment_name,
        excerpts=excerpts,
    )
    if representation["withheld"]:
        field = next(iter(representation["withheld"]))
        issue = representation["withheld"][field]
        raise BrainWorkError(
            code=f"mechanism_{field}_{issue}",
            message=(
                "La représentation globale contient encore une donnée client. "
                "Retirer des identifiants ne suffit pas. "
                "Ce contrôle n'est pas une anonymisation."
            ),
        )
    return representation


def _representation(value) -> dict:
    raw = value if isinstance(value, dict) else {}
    return {
        "formulation": str(raw.get("formulation") or "").strip(),
        "conditions": str(raw.get("conditions") or "").strip(),
        "limits": str(raw.get("limits") or "").strip(),
        "uncertainty": str(raw.get("uncertainty") or "").strip(),
        "withheld": raw.get("withheld") if isinstance(raw.get("withheld"), dict) else {},
    }


def identifying_formulation(
    text: str,
    *,
    establishment_name: str,
    excerpts: list[str],
) -> str | None:
    """Refusal gate before exposure. Passing it is not an anonymisation."""
    if _UUID.search(text):
        return "identifier"
    folded = " ".join(text.casefold().split())
    name = " ".join(establishment_name.casefold().split())
    if len(name) >= 3 and name in folded:
        return "establishment_name"
    for excerpt in excerpts:
        compact = " ".join(excerpt.casefold().split())
        if len(compact) < _EXCERPT:
            continue
        if compact in folded:
            return "dossier_excerpt"
        checks = 0
        for start in range(0, len(compact) - _EXCERPT + 1, 20):
            if compact[start : start + _EXCERPT] in folded:
                return "dossier_excerpt"
            checks += 1
            if checks >= 12:
                break
    return None


def dossier_excerpts(analysis_id) -> list[str]:
    found: list[str] = []
    payloads = BrainDossierItem.objects.filter(dossier__analysis_id=analysis_id).values_list(
        "payload",
        flat=True,
    )
    for payload in payloads.iterator():
        _collect_strings(payload, found)
        if len(found) >= 100:
            break
    return found[:100]


def _collect_strings(value, found: list[str]) -> None:
    if len(found) >= 100:
        return
    if isinstance(value, str):
        text = value.strip()
        if len(text) >= _EXCERPT:
            found.append(text)
        return
    if isinstance(value, dict):
        for child in value.values():
            _collect_strings(child, found)
    elif isinstance(value, list):
        for child in value:
            _collect_strings(child, found)


def _evidence(value, analysis_id) -> list[str]:
    if not isinstance(value, list):
        return []
    rows = BrainDossierItem.objects.filter(dossier__analysis_id=analysis_id).values_list(
        "id",
        flat=True,
    )
    allowed = {str(item_id) for item_id in rows}
    kept = []
    for item_id in value[:20]:
        text = str(item_id)
        if text in allowed and text not in kept:
            kept.append(text)
    return kept


def _require_operator(user) -> None:
    if not is_active_platform_operator(user):
        raise BrainAccessDenied()
