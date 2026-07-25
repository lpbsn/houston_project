"""Deterministic routing resolver for the observation pipeline (Lot 5).

Pure key matching against ``routing_taxonomy``; ORM materialization at the
frontier only. Reusable by the future qualification service (Lot 7).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from houston.ai.observation_pipeline_schema import PipelineCandidateOutput
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    OperationalUnit,
)
from houston.signals.signal_classification import routing_status_for_classification

# Stable audit ``source`` values produced by this module (JSON-serializable payloads).
AUDIT_SOURCES = frozenset(
    {
        "llm_validated",
        "invalid_key",
        "unresolved",
        "responsible_corrected",
        "subject_derived",
        "ambiguous_key",
        "materialization_miss",
    }
)


@dataclass(frozen=True)
class RoutingProposal:
    affected_business_unit_routing_key: str | None = None
    responsible_business_unit_routing_key: str | None = None
    activity_subject_routing_key: str | None = None
    operational_unit_key: str | None = None
    expected_action: str | None = None


@dataclass(frozen=True)
class RoutingTaxonomyIndex:
    business_unit_keys: frozenset[str]
    subject_to_business_units: dict[str, frozenset[str]]
    operational_unit_keys: frozenset[str]


@dataclass(frozen=True)
class KeyResolution:
    affected_business_unit_routing_key: str | None
    responsible_business_unit_routing_key: str | None
    activity_subject_routing_key: str | None
    operational_unit_key: str | None
    resolution_audit: dict[str, Any]


@dataclass(frozen=True)
class MaterializedRoutingFks:
    affected_business_unit: BusinessUnit | None
    responsible_business_unit: BusinessUnit | None
    activity_subject: ActivitySubject | None
    operational_unit: OperationalUnit | None


@dataclass(frozen=True)
class RoutingResolution:
    affected_business_unit: BusinessUnit | None
    responsible_business_unit: BusinessUnit | None
    activity_subject: ActivitySubject | None
    operational_unit: OperationalUnit | None
    routing_status: str
    resolution_audit: dict[str, Any]


def routing_proposal_from_pipeline_candidate(
    candidate: PipelineCandidateOutput,
) -> RoutingProposal:
    return RoutingProposal(
        affected_business_unit_routing_key=candidate.affected_business_unit_routing_key,
        responsible_business_unit_routing_key=candidate.responsible_business_unit_routing_key,
        activity_subject_routing_key=candidate.activity_subject_routing_key,
        operational_unit_key=candidate.operational_unit_key,
        expected_action=candidate.expected_action,
    )


def build_dimension_audit(
    *,
    source: str,
    proposed_key: str | None,
    resolved_key: str | None,
    **extra: Any,
) -> dict[str, Any]:
    if source not in AUDIT_SOURCES:
        raise ValueError(f"Unknown audit source: {source}")
    payload: dict[str, Any] = {
        "source": source,
        "proposed_key": proposed_key,
        "resolved_key": resolved_key,
    }
    payload.update(extra)
    return payload


def index_routing_taxonomy(routing_taxonomy: dict[str, Any]) -> RoutingTaxonomyIndex:
    business_unit_keys: set[str] = set()
    subject_to_bus: dict[str, set[str]] = {}
    for unit in routing_taxonomy.get("business_units") or []:
        bu_key = unit.get("routing_key")
        if not isinstance(bu_key, str) or not bu_key:
            continue
        business_unit_keys.add(bu_key)
        for subject in unit.get("activity_subjects") or []:
            subject_key = subject.get("routing_key")
            if isinstance(subject_key, str) and subject_key:
                subject_to_bus.setdefault(subject_key, set()).add(bu_key)
    operational_unit_keys: set[str] = set()
    for unit in routing_taxonomy.get("operational_units") or []:
        ou_key = unit.get("key")
        if isinstance(ou_key, str) and ou_key:
            operational_unit_keys.add(ou_key)
    return RoutingTaxonomyIndex(
        business_unit_keys=frozenset(business_unit_keys),
        subject_to_business_units={
            subject_key: frozenset(bu_keys)
            for subject_key, bu_keys in subject_to_bus.items()
        },
        operational_unit_keys=frozenset(operational_unit_keys),
    )


def resolve_affected_key(
    *,
    proposed_key: str | None,
    taxonomy_index: RoutingTaxonomyIndex,
) -> tuple[str | None, dict[str, Any]]:
    if proposed_key is None or proposed_key == "":
        return None, build_dimension_audit(
            source="unresolved",
            proposed_key=proposed_key,
            resolved_key=None,
        )
    if proposed_key in taxonomy_index.business_unit_keys:
        return proposed_key, build_dimension_audit(
            source="llm_validated",
            proposed_key=proposed_key,
            resolved_key=proposed_key,
        )
    return None, build_dimension_audit(
        source="invalid_key",
        proposed_key=proposed_key,
        resolved_key=None,
    )


def resolve_operational_unit_key(
    *,
    proposed_key: str | None,
    taxonomy_index: RoutingTaxonomyIndex,
) -> tuple[str | None, dict[str, Any]]:
    if proposed_key is None or proposed_key == "":
        return None, build_dimension_audit(
            source="unresolved",
            proposed_key=proposed_key,
            resolved_key=None,
        )
    if proposed_key in taxonomy_index.operational_unit_keys:
        return proposed_key, build_dimension_audit(
            source="llm_validated",
            proposed_key=proposed_key,
            resolved_key=proposed_key,
        )
    return None, build_dimension_audit(
        source="invalid_key",
        proposed_key=proposed_key,
        resolved_key=None,
    )


def apply_subject_responsible_invariant(
    *,
    proposed_responsible_key: str | None,
    proposed_subject_key: str | None,
    taxonomy_index: RoutingTaxonomyIndex,
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    """Resolve responsible+subject from explicit keys only; subject imposes responsible."""
    subject_key: str | None = None
    subject_audit: dict[str, Any]
    responsible_key: str | None = None
    responsible_audit: dict[str, Any]

    if proposed_subject_key is None or proposed_subject_key == "":
        subject_audit = build_dimension_audit(
            source="unresolved",
            proposed_key=proposed_subject_key,
            resolved_key=None,
        )
    else:
        candidate_bus = taxonomy_index.subject_to_business_units.get(proposed_subject_key)
        if candidate_bus is None:
            subject_audit = build_dimension_audit(
                source="invalid_key",
                proposed_key=proposed_subject_key,
                resolved_key=None,
            )
        elif len(candidate_bus) == 1:
            subject_key = proposed_subject_key
            subject_audit = build_dimension_audit(
                source="llm_validated",
                proposed_key=proposed_subject_key,
                resolved_key=subject_key,
            )
            derived_responsible = next(iter(candidate_bus))
            responsible_key = derived_responsible
            if (
                proposed_responsible_key
                and proposed_responsible_key != ""
                and proposed_responsible_key != derived_responsible
            ):
                responsible_audit = build_dimension_audit(
                    source="responsible_corrected",
                    proposed_key=proposed_responsible_key,
                    resolved_key=derived_responsible,
                )
            else:
                responsible_audit = build_dimension_audit(
                    source="subject_derived",
                    proposed_key=proposed_responsible_key,
                    resolved_key=derived_responsible,
                )
            return responsible_key, subject_key, responsible_audit, subject_audit
        else:
            # Ambiguous subject key shared by multiple business units.
            subject_audit = build_dimension_audit(
                source="ambiguous_key",
                proposed_key=proposed_subject_key,
                resolved_key=None,
                candidate_business_unit_keys=sorted(candidate_bus),
            )
            if proposed_responsible_key is None or proposed_responsible_key == "":
                responsible_audit = build_dimension_audit(
                    source="unresolved",
                    proposed_key=proposed_responsible_key,
                    resolved_key=None,
                )
                return None, None, responsible_audit, subject_audit
            if proposed_responsible_key in candidate_bus:
                subject_key = proposed_subject_key
                subject_audit = build_dimension_audit(
                    source="llm_validated",
                    proposed_key=proposed_subject_key,
                    resolved_key=subject_key,
                )
                responsible_audit = build_dimension_audit(
                    source="llm_validated",
                    proposed_key=proposed_responsible_key,
                    resolved_key=proposed_responsible_key,
                )
                return (
                    proposed_responsible_key,
                    subject_key,
                    responsible_audit,
                    subject_audit,
                )
            if proposed_responsible_key in taxonomy_index.business_unit_keys:
                responsible_audit = build_dimension_audit(
                    source="llm_validated",
                    proposed_key=proposed_responsible_key,
                    resolved_key=proposed_responsible_key,
                )
                return proposed_responsible_key, None, responsible_audit, subject_audit
            responsible_audit = build_dimension_audit(
                source="invalid_key",
                proposed_key=proposed_responsible_key,
                resolved_key=None,
            )
            return None, None, responsible_audit, subject_audit

    if proposed_responsible_key is None or proposed_responsible_key == "":
        responsible_audit = build_dimension_audit(
            source="unresolved",
            proposed_key=proposed_responsible_key,
            resolved_key=None,
        )
    elif proposed_responsible_key in taxonomy_index.business_unit_keys:
        responsible_key = proposed_responsible_key
        responsible_audit = build_dimension_audit(
            source="llm_validated",
            proposed_key=proposed_responsible_key,
            resolved_key=responsible_key,
        )
    else:
        responsible_audit = build_dimension_audit(
            source="invalid_key",
            proposed_key=proposed_responsible_key,
            resolved_key=None,
        )
    return responsible_key, None, responsible_audit, subject_audit


def resolve_responsible_subject(
    *,
    proposed_responsible_key: str | None,
    proposed_subject_key: str | None,
    taxonomy_index: RoutingTaxonomyIndex,
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    return apply_subject_responsible_invariant(
        proposed_responsible_key=proposed_responsible_key,
        proposed_subject_key=proposed_subject_key,
        taxonomy_index=taxonomy_index,
    )


def resolve_routing_keys(
    proposal: RoutingProposal,
    taxonomy_index: RoutingTaxonomyIndex,
) -> KeyResolution:
    affected_key, affected_audit = resolve_affected_key(
        proposed_key=proposal.affected_business_unit_routing_key,
        taxonomy_index=taxonomy_index,
    )
    (
        responsible_key,
        subject_key,
        responsible_audit,
        subject_audit,
    ) = resolve_responsible_subject(
        proposed_responsible_key=proposal.responsible_business_unit_routing_key,
        proposed_subject_key=proposal.activity_subject_routing_key,
        taxonomy_index=taxonomy_index,
    )
    operational_key, operational_audit = resolve_operational_unit_key(
        proposed_key=proposal.operational_unit_key,
        taxonomy_index=taxonomy_index,
    )
    return KeyResolution(
        affected_business_unit_routing_key=affected_key,
        responsible_business_unit_routing_key=responsible_key,
        activity_subject_routing_key=subject_key,
        operational_unit_key=operational_key,
        resolution_audit={
            "affected": affected_audit,
            "responsible": responsible_audit,
            "subject": subject_audit,
            "operational_unit": operational_audit,
        },
    )


def materialize_routing_fks(
    *,
    establishment_id: uuid.UUID,
    key_resolution: KeyResolution,
) -> MaterializedRoutingFks:
    affected: BusinessUnit | None = None
    if key_resolution.affected_business_unit_routing_key:
        affected = (
            BusinessUnit.objects.filter(
                establishment_id=establishment_id,
                routing_key=key_resolution.affected_business_unit_routing_key,
                active=True,
            )
            .select_related("catalog_business_unit")
            .first()
        )

    responsible: BusinessUnit | None = None
    if key_resolution.responsible_business_unit_routing_key:
        responsible = (
            BusinessUnit.objects.filter(
                establishment_id=establishment_id,
                routing_key=key_resolution.responsible_business_unit_routing_key,
                active=True,
            )
            .select_related("catalog_business_unit")
            .first()
        )

    subject: ActivitySubject | None = None
    if key_resolution.activity_subject_routing_key and responsible is not None:
        subject = (
            ActivitySubject.objects.filter(
                establishment_id=establishment_id,
                routing_key=key_resolution.activity_subject_routing_key,
                business_unit_id=responsible.id,
                active=True,
                business_unit__active=True,
            )
            .select_related("business_unit")
            .first()
        )
        if subject is not None and subject.business_unit_id != responsible.id:
            # Never persist incoherent subject/responsible.
            subject = None

    operational_unit: OperationalUnit | None = None
    if key_resolution.operational_unit_key:
        operational_unit = OperationalUnit.objects.filter(
            establishment_id=establishment_id,
            key=key_resolution.operational_unit_key,
            active=True,
        ).first()

    return MaterializedRoutingFks(
        affected_business_unit=affected,
        responsible_business_unit=responsible,
        activity_subject=subject,
        operational_unit=operational_unit,
    )


def resolve_candidate_routing(
    *,
    establishment_id: uuid.UUID,
    proposal: RoutingProposal,
    routing_taxonomy: dict[str, Any],
) -> RoutingResolution:
    """Orchestrator: index → pure key resolve → ORM materialize → routing_status.

    ``routing_taxonomy`` is required; it is never rebuilt silently when missing.
    """
    if routing_taxonomy is None:
        raise ValueError("routing_taxonomy is required")
    if not isinstance(routing_taxonomy, dict):
        raise TypeError("routing_taxonomy must be a dict")

    taxonomy_index = index_routing_taxonomy(routing_taxonomy)
    key_resolution = resolve_routing_keys(proposal, taxonomy_index)
    materialized = materialize_routing_fks(
        establishment_id=establishment_id,
        key_resolution=key_resolution,
    )

    establishment = Establishment.objects.filter(id=establishment_id).first()
    if establishment is None:
        raise ValueError(f"Unknown establishment_id: {establishment_id}")

    # If materialization dropped a key-validated dimension, reflect in audit.
    audit = dict(key_resolution.resolution_audit)
    if (
        key_resolution.affected_business_unit_routing_key
        and materialized.affected_business_unit is None
    ):
        audit["affected"] = build_dimension_audit(
            source="materialization_miss",
            proposed_key=proposal.affected_business_unit_routing_key,
            resolved_key=None,
        )
    if (
        key_resolution.activity_subject_routing_key
        and materialized.activity_subject is None
    ):
        audit["subject"] = build_dimension_audit(
            source="materialization_miss",
            proposed_key=proposal.activity_subject_routing_key,
            resolved_key=None,
        )
    if (
        key_resolution.responsible_business_unit_routing_key
        and materialized.responsible_business_unit is None
    ):
        audit["responsible"] = build_dimension_audit(
            source="materialization_miss",
            proposed_key=proposal.responsible_business_unit_routing_key,
            resolved_key=None,
        )
    if (
        key_resolution.operational_unit_key
        and materialized.operational_unit is None
    ):
        audit["operational_unit"] = build_dimension_audit(
            source="materialization_miss",
            proposed_key=proposal.operational_unit_key,
            resolved_key=None,
        )

    routing_status = routing_status_for_classification(
        establishment=establishment,
        affected_business_unit=materialized.affected_business_unit,
        responsible_business_unit=materialized.responsible_business_unit,
        activity_subject=materialized.activity_subject,
    )
    return RoutingResolution(
        affected_business_unit=materialized.affected_business_unit,
        responsible_business_unit=materialized.responsible_business_unit,
        activity_subject=materialized.activity_subject,
        operational_unit=materialized.operational_unit,
        routing_status=routing_status,
        resolution_audit=audit,
    )
