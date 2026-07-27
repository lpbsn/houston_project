"""Deterministic lexical anchoring for responsible-without-subject proposals.

A responsible BU without activity_subject is kept only when validated_text
contains a full-token sequence match of an explicit taxonomy label (specific_name
or distinct catalog generic_label). Proves mention, not business responsibility.
"""

from __future__ import annotations

from houston.establishments.models import BusinessUnit, Establishment
from houston.establishments.taxonomy_normalization import slugify_label
from houston.observations.models import Observation
from houston.signals.routing_resolver import (
    RoutingResolution,
    build_dimension_audit,
)
from houston.signals.signal_classification import routing_status_for_classification


def anchor_tokens(text: str) -> list[str]:
    slug = slugify_label(text or "")
    return [token for token in slug.split("_") if token]


def sequence_in(*, haystack: list[str], needle: list[str]) -> bool:
    if not needle:
        return False
    needle_len = len(needle)
    limit = len(haystack) - needle_len + 1
    for index in range(0, limit):
        if haystack[index : index + needle_len] == needle:
            return True
    return False


def business_unit_anchor_phrases(business_unit: BusinessUnit) -> list[str]:
    phrases: list[str] = []
    specific = (business_unit.specific_name or "").strip()
    if specific:
        phrases.append(specific)
    catalog = business_unit.catalog_business_unit
    generic = ""
    if catalog is not None:
        generic = (catalog.label or "").strip()
    if generic and anchor_tokens(generic) != anchor_tokens(specific):
        phrases.append(generic)
    return phrases


def is_responsible_textually_anchored(
    *,
    validated_text: str,
    responsible_bu: BusinessUnit,
) -> bool:
    text_tokens = anchor_tokens(validated_text)
    for phrase in business_unit_anchor_phrases(responsible_bu):
        if sequence_in(haystack=text_tokens, needle=anchor_tokens(phrase)):
            return True
    return False


def sanitize_unanchored_responsible_without_subject(
    *,
    observation: Observation,
    resolution: RoutingResolution,
) -> RoutingResolution:
    """Keep or reject responsible-without-subject based on lexical anchors in text."""
    if resolution.responsible_business_unit is None:
        return resolution
    if resolution.activity_subject is not None:
        return resolution

    responsible = resolution.responsible_business_unit
    proposed_key = (resolution.resolution_audit.get("responsible") or {}).get(
        "proposed_key"
    )
    audit = dict(resolution.resolution_audit)

    if is_responsible_textually_anchored(
        validated_text=observation.raw_text,
        responsible_bu=responsible,
    ):
        audit["responsible"] = build_dimension_audit(
            source="responsible_text_anchored",
            proposed_key=proposed_key,
            resolved_key=responsible.routing_key,
        )
        return RoutingResolution(
            affected_business_unit=resolution.affected_business_unit,
            responsible_business_unit=resolution.responsible_business_unit,
            activity_subject=resolution.activity_subject,
            operational_unit=resolution.operational_unit,
            routing_status=resolution.routing_status,
            resolution_audit=audit,
        )

    audit["responsible"] = build_dimension_audit(
        source="responsible_unanchored_rejected",
        proposed_key=proposed_key,
        resolved_key=None,
    )
    establishment = Establishment.objects.filter(id=observation.establishment_id).first()
    if establishment is None:
        raise ValueError(f"Unknown establishment_id: {observation.establishment_id}")
    routing_status = routing_status_for_classification(
        establishment=establishment,
        affected_business_unit=resolution.affected_business_unit,
        responsible_business_unit=None,
        activity_subject=None,
    )
    return RoutingResolution(
        affected_business_unit=resolution.affected_business_unit,
        responsible_business_unit=None,
        activity_subject=None,
        operational_unit=resolution.operational_unit,
        routing_status=routing_status,
        resolution_audit=audit,
    )
