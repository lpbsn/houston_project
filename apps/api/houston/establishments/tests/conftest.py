from __future__ import annotations

from houston.establishments.catalog import load_arborescence_rows
from houston.establishments.proposal_catalog import merge_expanded_proposal
from houston.establishments.services import (
    create_manual_onboarding_proposal,
    validate_onboarding_proposal_section,
)

TEST_PASSWORD = "SecurePass123!"

HOTEL_MODULE_KEY = "hotel"
HOTEL_HEBERGEMENT_DOMAIN_KEY = "hotel__hebergement"
HOTEL_HEBERGEMENT_MAINTENANCE_SUBJECT_KEY = "hotel__hebergement__maintenance_equipements"

READINESS_DOMAIN_KEYS = (
    HOTEL_HEBERGEMENT_DOMAIN_KEY,
    "hotel__reception_hall",
    "hotel__parties_communes",
)


def first_catalog_subject_for_domain(domain_key: str) -> tuple[str, str]:
    for row in load_arborescence_rows():
        if row.domain_key == domain_key:
            return row.subject_key, row.subject_label
    raise KeyError(domain_key)


def valid_v2_payload(**overrides) -> dict:
    base = {
        "schema_version": "onboarding_proposal_v2",
        "operational_modules": [],
        "operational_domains": [],
        "operational_subjects": [],
        "operational_units": [
            {
                "key": "lobby",
                "label": "Lobby",
                "related_modules": [HOTEL_MODULE_KEY],
                "reason": "Front-of-house area.",
                "confidence_score": None,
            }
        ],
        "runtime_vocabulary": [
            {
                "term": "VRV",
                "meaning": "HVAC equipment",
                "mapped_domain_key": HOTEL_HEBERGEMENT_DOMAIN_KEY,
                "mapped_unit_key": "lobby",
                "reason": "Local technical term.",
            }
        ],
        "runtime_tags": [
            {
                "key": "hvac",
                "label": "HVAC",
                "related_domain_keys": [HOTEL_HEBERGEMENT_DOMAIN_KEY],
                "reason": "Helps classify HVAC issues.",
            }
        ],
        "routing_hints": [
            {
                "pattern": "VRV",
                "suggested_domain_keys": [HOTEL_HEBERGEMENT_DOMAIN_KEY],
                "suggested_unit_key": "lobby",
                "reason": "Route HVAC mentions to hebergement maintenance.",
                "confidence_score": None,
            }
        ],
    }
    payload = merge_expanded_proposal(base_payload=base, module_keys=[HOTEL_MODULE_KEY])
    payload.update(overrides)
    return payload


def valid_ai_modules_payload() -> dict:
    return {
        "schema_version": "onboarding_proposal_v2",
        "operational_modules": [
            {
                "key": HOTEL_MODULE_KEY,
                "label": "Hôtel",
                "reason": "The establishment includes hotel operations.",
                "confidence_score": 0.91,
            }
        ],
    }


def create_validated_proposal(session, owner, payload=None):
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=payload or valid_v2_payload(),
    )
    for section in [
        "operational_modules",
        "operational_domains",
        "operational_subjects",
        "operational_units",
        "runtime_vocabulary",
        "runtime_tags",
        "routing_hints",
    ]:
        proposal = validate_onboarding_proposal_section(
            proposal=proposal,
            actor=owner,
            section=section,
            decision="accepted",
        )
    return proposal
