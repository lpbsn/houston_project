from __future__ import annotations

import uuid

import pytest

from houston.accounts.models import User
from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    Establishment,
    EstablishmentMembership,
    OnboardingDraft,
    OnboardingSession,
)
from houston.establishments.onboarding_draft import (
    DRAFT_VALIDATION_MODE_FINAL,
    DRAFT_VALIDATION_MODE_SOFT,
    OnboardingDraftValidationError,
    validate_onboarding_draft_payload,
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


def _events_payload(*, establishment_name: str) -> dict:
    event_key = str(uuid.uuid4())
    seminar_key = str(uuid.uuid4())
    subject_event = str(uuid.uuid4())
    subject_seminar = str(uuid.uuid4())
    return {
        "current_step": "team",
        "establishment": {
            "name": establishment_name,
            "description": "D" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        },
        "business_units": [
            {
                "client_key": event_key,
                "catalog_key": "evenements_privatisations",
                "specific_name": "Event",
                "instance_description": "",
            },
            {
                "client_key": seminar_key,
                "catalog_key": "evenements_privatisations",
                "specific_name": "Séminaire",
                "instance_description": "",
            },
        ],
        "activity_subjects": [
            {
                "client_key": subject_event,
                "business_unit_client_key": event_key,
                "catalog_key": "evenements_privatisations__facturation",
                "label": "",
                "description": "",
            },
            {
                "client_key": subject_seminar,
                "business_unit_client_key": seminar_key,
                "catalog_key": "evenements_privatisations__facturation",
                "label": "",
                "description": "",
            },
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


def test_final_draft_allows_two_transversal_instances_and_rejects_duplicate_names():
    sync_catalog_from_normalized_rows()
    payload = _events_payload(establishment_name="Site Events")
    normalized, errors, _warnings = validate_onboarding_draft_payload(
        payload,
        mode=DRAFT_VALIDATION_MODE_FINAL,
    )
    assert errors == []
    assert [item["specific_name"] for item in normalized["business_units"]] == [
        "Event",
        "Séminaire",
    ]

    payload["business_units"][1]["specific_name"] = "Event"
    with pytest.raises(OnboardingDraftValidationError) as exc_info:
        validate_onboarding_draft_payload(payload, mode=DRAFT_VALIDATION_MODE_FINAL)
    assert any(error["code"] == "duplicate_specific_name" for error in exc_info.value.errors)


def test_blank_member_row_is_kept_and_email_only_member_stays_invalid():
    sync_catalog_from_normalized_rows()
    payload = _valid_payload(establishment_name="Site Team")
    bu_key = payload["business_units"][0]["client_key"]
    payload["team"]["members"] = [
        {
            "email": "",
            "first_name": "",
            "last_name": "",
            "role": "manager",
            "business_unit_client_keys": [],
        },
        {
            "email": "sam@example.com",
            "first_name": "",
            "last_name": "",
            "role": "staff",
            "business_unit_client_keys": [],
        },
    ]

    normalized, errors, warnings = validate_onboarding_draft_payload(
        payload,
        mode=DRAFT_VALIDATION_MODE_SOFT,
    )
    assert normalized["team"]["members"][0]["role"] == "manager"
    assert normalized["team"]["members"][0]["email"] == ""
    assert len(normalized["team"]["members"]) == 2
    error_codes = [error["code"] for error in errors]
    warning_codes = [warning["code"] for warning in warnings]
    assert "missing_email" not in error_codes
    assert "missing_first_name" not in error_codes
    assert "missing_first_name" in warning_codes
    assert warning_codes.count("missing_member_business_units") == 1

    payload["team"]["members"] = [payload["team"]["members"][0]]
    normalized, errors, warnings = validate_onboarding_draft_payload(
        payload,
        mode=DRAFT_VALIDATION_MODE_FINAL,
    )
    assert errors == []
    assert warnings == []
    assert len(normalized["team"]["members"]) == 1

    payload["team"]["members"] = [
        {
            "email": "sam@example.com",
            "first_name": "Sam",
            "last_name": "Staff",
            "role": "staff",
            "business_unit_client_keys": [bu_key],
        },
        {
            "email": "only@example.com",
            "first_name": "",
            "last_name": "",
            "role": "staff",
            "business_unit_client_keys": [],
        },
    ]
    normalized, errors, warnings = validate_onboarding_draft_payload(
        payload,
        mode=DRAFT_VALIDATION_MODE_FINAL,
    )
    assert errors == []
    assert any(warning["code"] == "missing_first_name" for warning in warnings)


def test_complete_does_not_invite_blank_member_rows():
    sync_catalog_from_normalized_rows()
    operator = _operator()
    grant_operator(operator)
    organization = Organization.objects.create(name=f"Blank Org {uuid.uuid4().hex[:6]}")
    establishment = Establishment.objects.create(
        name=f"Blank Site {uuid.uuid4().hex[:6]}",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    session = start_onboarding_session(
        organization=organization,
        establishment=establishment,
        started_by=operator,
    )
    payload = _valid_payload(establishment_name=establishment.name)
    member_email = f"member_{uuid.uuid4().hex[:8]}@example.com"
    bu_key = payload["business_units"][0]["client_key"]
    payload["team"]["members"] = [
        {
            "email": "",
            "first_name": "",
            "last_name": "",
            "role": "manager",
            "business_unit_client_keys": [],
        },
        {
            "email": member_email,
            "first_name": "Sam",
            "last_name": "Staff",
            "role": "staff",
            "business_unit_client_keys": [bu_key],
        },
    ]
    upsert_onboarding_draft_core(session=session, actor=operator, payload=payload)
    stored = OnboardingDraft.objects.get(onboarding_session_id=session.id)
    assert len(stored.payload["team"]["members"]) == 2

    invitation = invite_organizational_owner_core(
        establishment=establishment,
        email=f"owner_{uuid.uuid4().hex[:8]}@example.com",
        first_name="Own",
        last_name="Er",
    )
    owner_membership = invitation.membership
    owner_membership.status = EstablishmentMembership.Status.ACTIVE
    owner_membership.save(update_fields=["status", "updated_at"])
    owner = owner_membership.user
    owner.status = User.Status.ACTIVE
    owner.save(update_fields=["status", "updated_at"])

    result = complete_onboarding_session_core(session=session, actor=operator)
    assert result["activated"] is True
    emails = set(
        EstablishmentMembership.objects.filter(establishment=establishment).values_list(
            "user__email", flat=True
        )
    )
    assert member_email in emails
    assert "" not in emails
    assert EstablishmentMembership.objects.filter(establishment=establishment).count() == 3
