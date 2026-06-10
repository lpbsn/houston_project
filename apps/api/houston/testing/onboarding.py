from __future__ import annotations

import uuid

from houston.accounts.models import User
from houston.establishments.models import (
    ActivitySubject,
    Establishment,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.establishments.services import (
    apply_onboarding_proposal,
    create_manual_onboarding_proposal,
    submit_manual_onboarding_proposal,
)
from houston.organizations.models import Organization
from houston.testing.factories import create_user
from houston.testing.taxonomy import create_business_unit

MANUAL_V2_PROPOSAL_SCHEMA_VERSION = "onboarding_proposal_v3"


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


def create_onboarding_session(
    *,
    actor: User,
    role: str = EstablishmentMembership.Role.OWNER,
    membership_status: str = EstablishmentMembership.Status.ACTIVE,
    organization_status: str = Organization.Status.ACTIVE,
    establishment_status: str = Establishment.Status.DRAFT,
    session_status: str = OnboardingSession.Status.STARTED,
) -> OnboardingSession:
    organization = Organization.objects.create(
        name=f"Demo Group {uuid.uuid4().hex[:6]}",
        status=organization_status,
    )
    establishment = Establishment.objects.create(
        name=f"Demo Site {uuid.uuid4().hex[:6]}",
        organization=organization,
        status=establishment_status,
    )
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        started_by=actor,
        status=session_status,
    )
    EstablishmentMembership.objects.create(
        user=actor,
        establishment=establishment,
        role=role,
        status=membership_status,
    )
    return session


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
    director = create_user(username=f"director_ready_{uuid.uuid4().hex[:8]}")
    EstablishmentMembership.objects.create(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.INVITED,
    )
    return business_unit
