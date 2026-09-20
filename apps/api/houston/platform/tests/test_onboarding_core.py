from __future__ import annotations

import uuid

import pytest

from houston.accounts.models import User
from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    Establishment,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.establishments.services import (
    OnboardingReadinessError,
    complete_onboarding_session_core,
    invite_organizational_owner_core,
    start_onboarding_session,
    upsert_onboarding_draft_core,
)
from houston.organizations.models import Organization
from houston.testing.factories import create_user
from houston.testing.platform import grant_operator

pytestmark = pytest.mark.django_db


def _operator() -> User:
    return create_user(username=f"plat_op_{uuid.uuid4().hex[:8]}")


def _valid_payload(*, establishment_name: str) -> dict:
    bu_key = str(uuid.uuid4())
    subject_key = str(uuid.uuid4())
    return {
        "current_step": "team",
        "establishment": {
            "name": establishment_name,
            "description": "D" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        },
        "business_units": [
            {
                "client_key": bu_key,
                "catalog_key": "coworking",
                "specific_name": "Coworking Nord",
                "instance_description": "",
            }
        ],
        "activity_subjects": [
            {
                "client_key": subject_key,
                "business_unit_client_key": bu_key,
                "catalog_key": "coworking__proprete",
                "label": "",
                "description": "",
            }
        ],
        "team": {
            "director": {
                "email": f"director_{uuid.uuid4().hex[:8]}@example.com",
                "first_name": "Dir",
                "last_name": "Ector",
            },
            "members": [],
        },
    }


def test_complete_core_does_not_require_operator_membership():
    sync_catalog_from_normalized_rows()
    operator = _operator()
    grant_operator(operator)
    organization = Organization.objects.create(name=f"Core Org {uuid.uuid4().hex[:6]}")
    establishment = Establishment.objects.create(
        name=f"Core Site {uuid.uuid4().hex[:6]}",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    session = start_onboarding_session(
        organization=organization,
        establishment=establishment,
        started_by=operator,
    )
    assert EstablishmentMembership.objects.filter(user=operator).count() == 0

    upsert_onboarding_draft_core(
        session=session,
        actor=operator,
        payload=_valid_payload(establishment_name=establishment.name),
    )
    invitation = invite_organizational_owner_core(
        establishment=establishment,
        email=f"owner_{uuid.uuid4().hex[:8]}@example.com",
        first_name="Own",
        last_name="Er",
    )

    with pytest.raises(OnboardingReadinessError) as exc:
        complete_onboarding_session_core(session=session, actor=operator)
    assert "missing_active_owner_or_director" in {
        blocker["code"] for blocker in exc.value.readiness["blockers"]
    }

    owner_membership = invitation.membership
    owner_membership.status = EstablishmentMembership.Status.ACTIVE
    owner_membership.save(update_fields=["status", "updated_at"])
    owner = owner_membership.user
    owner.status = User.Status.ACTIVE
    owner.save(update_fields=["status", "updated_at"])

    result = complete_onboarding_session_core(session=session, actor=operator)
    assert result["activated"] is True
    assert EstablishmentMembership.objects.filter(user=operator).count() == 0
    organization.refresh_from_db()
    assert organization.has_been_operational is True
    session = OnboardingSession.objects.get(pk=session.pk)
    assert session.status == OnboardingSession.Status.ACTIVATED
