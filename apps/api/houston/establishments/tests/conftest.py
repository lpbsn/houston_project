from __future__ import annotations

import uuid

from houston.accounts.models import User
from houston.establishments.models import (
    ActivitySubject,
    EstablishmentMembership,
    OnboardingCatalogSubject,
)
from houston.establishments.proposal_catalog import merge_expanded_proposal
from houston.establishments.services import (
    apply_onboarding_proposal,
    create_manual_onboarding_proposal,
    submit_manual_onboarding_proposal,
    validate_onboarding_proposal_section,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
)

MANUAL_V2_PROPOSAL_SCHEMA_VERSION = "onboarding_proposal_v3"

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
    subject = (
        OnboardingCatalogSubject.objects.filter(
            active=True,
            catalog_domain__key=domain_key,
            catalog_domain__active=True,
        )
        .order_by("sort_order", "key")
        .first()
    )
    if subject is None:
        raise KeyError(domain_key)
    return subject.key, subject.label


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


def valid_manual_v2_payload(**overrides) -> dict:
    business_unit_client_key = str(uuid.uuid4())
    activity_subject_client_key = str(uuid.uuid4())
    base = {
        "schema_version": MANUAL_V2_PROPOSAL_SCHEMA_VERSION,
        "business_units": [
            {
                "client_key": business_unit_client_key,
                "label": "Coworking",
                "description": "",
                "unit_type": "dedicated",
                "catalog_key": "coworking",
            }
        ],
        "activity_subjects": [
            {
                "client_key": activity_subject_client_key,
                "label": "Propreté",
                "description": "",
                "business_unit_client_key": business_unit_client_key,
                "catalog_key": "coworking__proprete",
            }
        ],
    }
    base.update(overrides)
    return base


def create_validated_manual_v2_proposal(session, owner, payload=None):
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=payload or valid_manual_v2_payload(),
    )
    return submit_manual_onboarding_proposal(proposal=proposal, actor=owner)


def apply_validated_manual_v2_proposal(session, owner, payload=None):
    proposal = create_validated_manual_v2_proposal(
        session=session,
        owner=owner,
        payload=payload,
    )
    return apply_onboarding_proposal(proposal=proposal, actor=owner)


def create_ready_runtime(session, owner):
    """Minimum BU/AS + invited director runtime for activation readiness."""
    establishment = session.establishment
    business_unit = create_business_unit(
        establishment=establishment,
        key="coworking",
        label="Coworking",
    )
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name="proprete",
        label="Propreté",
        active=True,
    )
    director = User.objects.create_user(
        username=f"director_ready_{uuid.uuid4().hex[:8]}",
        email=f"director_ready_{uuid.uuid4().hex[:8]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.INVITED,
    )
    return business_unit


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
