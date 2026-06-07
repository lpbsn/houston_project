from __future__ import annotations

import uuid

from houston.accounts.models import User
from houston.establishments.models import (
    ActivitySubject,
    EstablishmentMembership,
)
from houston.establishments.services import (
    apply_onboarding_proposal,
    create_manual_onboarding_proposal,
    submit_manual_onboarding_proposal,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
)

MANUAL_V2_PROPOSAL_SCHEMA_VERSION = "onboarding_proposal_v3"

TEST_PASSWORD = "SecurePass123!"


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


def draft_manual_v2_payload_bu_only(**overrides) -> dict:
    business_unit_client_key = str(uuid.uuid4())
    base = {
        "schema_version": MANUAL_V2_PROPOSAL_SCHEMA_VERSION,
        "business_units": [
            {
                "client_key": business_unit_client_key,
                "label": "Coworking",
                "description": "",
                "catalog_key": "coworking",
            }
        ],
        "activity_subjects": [],
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
