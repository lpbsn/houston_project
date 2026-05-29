from __future__ import annotations

import pytest

from houston.establishments.proposal_catalog import (
    apply_proposal_item_addition,
    apply_proposal_item_removal,
    merge_expanded_proposal,
)
from houston.establishments.tests.conftest import (
    HOTEL_HEBERGEMENT_DOMAIN_KEY,
    HOTEL_HEBERGEMENT_MAINTENANCE_SUBJECT_KEY,
    HOTEL_MODULE_KEY,
    valid_v2_payload,
)

pytestmark = pytest.mark.django_db


def test_merge_expanded_proposal_includes_hotel_catalog_sections():
    base = {
        "schema_version": "onboarding_proposal_v2",
        "operational_units": [],
    }

    merged = merge_expanded_proposal(base_payload=base, module_keys=[HOTEL_MODULE_KEY])

    assert merged["schema_version"] == "onboarding_proposal_v2"
    assert merged["operational_units"] == []
    assert len(merged["operational_modules"]) == 1
    assert merged["operational_modules"][0]["key"] == HOTEL_MODULE_KEY
    assert len(merged["operational_domains"]) == 6
    assert len(merged["operational_subjects"]) == 29


def test_remove_domain_drops_orphan_subjects():
    payload = valid_v2_payload()

    updated = apply_proposal_item_removal(
        payload=payload,
        section="operational_domains",
        key=HOTEL_HEBERGEMENT_DOMAIN_KEY,
    )

    domain_keys = {item["key"] for item in updated["operational_domains"]}
    subject_keys = {item["key"] for item in updated["operational_subjects"]}

    assert HOTEL_HEBERGEMENT_DOMAIN_KEY not in domain_keys
    assert HOTEL_HEBERGEMENT_MAINTENANCE_SUBJECT_KEY not in subject_keys
    assert all(
        not item["key"].startswith(f"{HOTEL_HEBERGEMENT_DOMAIN_KEY}__")
        for item in updated["operational_subjects"]
    )


def test_remove_module_drops_all_children():
    payload = valid_v2_payload()

    updated = apply_proposal_item_removal(
        payload=payload,
        section="operational_modules",
        key=HOTEL_MODULE_KEY,
    )

    assert updated["operational_modules"] == []
    assert updated["operational_domains"] == []
    assert updated["operational_subjects"] == []


def test_add_subject_restores_parent_domain_and_module():
    payload = valid_v2_payload()
    stripped = apply_proposal_item_removal(
        payload=payload,
        section="operational_subjects",
        key=HOTEL_HEBERGEMENT_MAINTENANCE_SUBJECT_KEY,
    )
    assert HOTEL_HEBERGEMENT_MAINTENANCE_SUBJECT_KEY not in {
        item["key"] for item in stripped["operational_subjects"]
    }

    restored = apply_proposal_item_addition(
        payload=stripped,
        section="operational_subjects",
        key=HOTEL_HEBERGEMENT_MAINTENANCE_SUBJECT_KEY,
    )

    module_keys = {item["key"] for item in restored["operational_modules"]}
    domain_keys = {item["key"] for item in restored["operational_domains"]}
    subject_keys = {item["key"] for item in restored["operational_subjects"]}

    assert HOTEL_MODULE_KEY in module_keys
    assert HOTEL_HEBERGEMENT_DOMAIN_KEY in domain_keys
    assert HOTEL_HEBERGEMENT_MAINTENANCE_SUBJECT_KEY in subject_keys
