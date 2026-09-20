from __future__ import annotations

import uuid

from django.utils import timezone

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.establishments.services import ensure_onboarding_draft_for_session
from houston.organizations.models import Organization
from houston.testing.factories import create_user
from houston.testing.taxonomy import create_activity_subject, create_business_unit


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
    ensure_onboarding_draft_for_session(session=session, actor=actor)
    return session


def create_ready_runtime(session, owner):
    establishment = session.establishment
    EstablishmentActivityDescription.objects.update_or_create(
        establishment=establishment,
        defaults={
            "description": "A" * 50,
            "source": EstablishmentActivityDescription.Source.MANUAL,
            "submitted_by": owner,
            "validated_at": timezone.now(),
        },
    )
    business_unit = create_business_unit(
        establishment=establishment,
        key="coworking",
        label="Coworking",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=business_unit,
        label="Propreté",
    )
    director = create_user(username=f"director_ready_{uuid.uuid4().hex[:8]}")
    EstablishmentMembership.objects.create(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.INVITED,
    )
    return business_unit
