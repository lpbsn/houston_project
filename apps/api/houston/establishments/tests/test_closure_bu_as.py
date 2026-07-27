"""Closure tests for BusinessUnit-as-identity (post-0026)."""

from __future__ import annotations

import pytest

from houston.core.exceptions import DomainConflictError
from houston.establishments.business_unit_domain_service import (
    update_business_unit_specific_name,
)
from houston.establishments.business_unit_identity import business_unit_public_key
from houston.establishments.onboarding_proposal_v3_migration import (
    PROPOSAL_SCHEMA_VERSION_V3,
)
from houston.establishments.services import (
    OnboardingProposalValidationError,
    validate_onboarding_proposal_payload,
)
from houston.testing.factories import create_establishment
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
