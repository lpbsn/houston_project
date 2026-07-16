"""Closure tests for BusinessUnit-as-identity (post-0026)."""

from __future__ import annotations

import uuid

import pytest

from houston.core.exceptions import DomainConflictError
from houston.establishments.business_unit_domain_service import (
    update_business_unit_specific_name,
)
from houston.establishments.business_unit_identity import business_unit_public_key
from houston.establishments.models import OnboardingProposal
from houston.establishments.onboarding_proposal_v3_migration import (
    PROPOSAL_SCHEMA_VERSION_V3,
    process_non_terminal_v3_proposals,
)
from houston.establishments.services import (
    OnboardingProposalValidationError,
    validate_onboarding_proposal_payload,
)
from houston.testing.factories import create_establishment, create_user
from houston.testing.onboarding import create_onboarding_session
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


def test_validate_rejects_onboarding_proposal_v3_payload():
    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        validate_onboarding_proposal_payload(
            {
                "schema_version": PROPOSAL_SCHEMA_VERSION_V3,
                "business_units": [],
                "activity_subjects": [],
            }
        )

    assert any(
        error.get("code") == "unsupported_schema_version" for error in exc_info.value.errors
    )


def test_process_non_terminal_v3_proposals_converts_convertible_rows(imported_catalog):
    owner = create_user(username=f"closure_v3_convert_{uuid.uuid4().hex[:8]}")
    session = create_onboarding_session(actor=owner)
    proposal = OnboardingProposal.objects.create(
        onboarding_session=session,
        establishment=session.establishment,
        created_by=owner,
        status=OnboardingProposal.Status.DRAFT,
        payload={
            "schema_version": PROPOSAL_SCHEMA_VERSION_V3,
            "business_units": [
                {
                    "client_key": "bu-coworking",
                    "catalog_key": "coworking",
                    "label": "Coworking",
                    "description": "Open space",
                }
            ],
            "activity_subjects": [
                {
                    "client_key": "subject-proprete",
                    "business_unit_client_key": "bu-coworking",
                    "catalog_key": "coworking__proprete",
                    "label": "Propreté",
                    "description": "Catalog desc ignored",
                },
                {
                    "client_key": "subject-free",
                    "business_unit_client_key": "bu-coworking",
                    "label": "Salle libre",
                    "description": "Espace dédié",
                },
            ],
        },
    )

    counts = process_non_terminal_v3_proposals(dry_run=False)

    proposal.refresh_from_db()
    assert counts["converted"] == 1
    assert proposal.payload["schema_version"] == "onboarding_proposal_v4"
    assert proposal.payload["business_units"][0]["specific_name"] == "Coworking"
    assert proposal.status == OnboardingProposal.Status.DRAFT

    catalog_subject = proposal.payload["activity_subjects"][0]
    assert catalog_subject["catalog_key"] == "coworking__proprete"
    assert "label" not in catalog_subject
    assert "description" not in catalog_subject

    free_subject = proposal.payload["activity_subjects"][1]
    assert free_subject["catalog_key"] is None
    assert free_subject["label"] == "Salle libre"
    assert free_subject["description"] == "Espace dédié"

    validate_onboarding_proposal_payload(proposal.payload)


def test_process_non_terminal_v3_proposals_rejects_unconvertible_rows():
    owner = create_user(username=f"closure_v3_reject_{uuid.uuid4().hex[:8]}")
    session = create_onboarding_session(actor=owner)
    proposal = OnboardingProposal.objects.create(
        onboarding_session=session,
        establishment=session.establishment,
        created_by=owner,
        status=OnboardingProposal.Status.DRAFT,
        payload={
            "schema_version": PROPOSAL_SCHEMA_VERSION_V3,
            "business_units": [
                {
                    "client_key": "bu-free",
                    "label": "Free pole",
                    "description": "",
                }
            ],
            "activity_subjects": [],
        },
    )

    counts = process_non_terminal_v3_proposals(dry_run=False)

    proposal.refresh_from_db()
    assert counts["rejected"] == 1
    assert proposal.status == OnboardingProposal.Status.REJECTED
    assert proposal.last_error_code == "unsupported_schema_version_v3"


def test_specific_name_accepts_255_char_boundary(imported_catalog):
    establishment = create_establishment()
    long_name = "A" * 255
    business_unit = create_business_unit(
        establishment=establishment,
        key="hotel",
        label=long_name,
    )
    assert len(business_unit.specific_name) == 255


def test_rename_updates_normalized_specific_name_and_public_key(imported_catalog):
    establishment = create_establishment()
    business_unit = create_business_unit(
        establishment=establishment,
        key="restaurant",
        label="Food Court",
    )
    original_public_key = business_unit_public_key(business_unit=business_unit)

    renamed = update_business_unit_specific_name(
        establishment_id=establishment.id,
        business_unit_id=business_unit.id,
        specific_name="Rooftop",
    )

    assert renamed.specific_name == "Rooftop"
    assert renamed.normalized_specific_name == "rooftop"
    assert business_unit_public_key(business_unit=renamed) == "rooftop"
    assert business_unit_public_key(business_unit=renamed) != original_public_key


def test_rename_rejects_duplicate_normalized_specific_name(imported_catalog):
    establishment = create_establishment()
    first = create_business_unit(
        establishment=establishment,
        key="restaurant",
        label="Food Court",
    )
    second = create_business_unit(
        establishment=establishment,
        key="restaurant",
        label="Rooftop",
    )

    with pytest.raises(DomainConflictError) as exc_info:
        update_business_unit_specific_name(
            establishment_id=establishment.id,
            business_unit_id=second.id,
            specific_name=first.specific_name,
        )

    assert exc_info.value.code == "duplicate_specific_name"
