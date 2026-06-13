from __future__ import annotations

import pytest

from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.testing.auth import TEST_PASSWORD  # noqa: F401
from houston.testing.onboarding import (  # noqa: F401
    MANUAL_V2_PROPOSAL_SCHEMA_VERSION,
    apply_validated_manual_v2_proposal,
    create_ready_runtime,
    create_validated_manual_v2_proposal,
    draft_manual_v2_payload_bu_only,
    valid_manual_v2_payload,
)


@pytest.fixture
def imported_catalog():
    return sync_catalog_from_normalized_rows()


@pytest.fixture
def requires_empty_catalog(db):
    from houston.establishments.models import CatalogActivitySubject, CatalogBusinessUnit

    assert CatalogBusinessUnit.objects.count() == 0
    assert CatalogActivitySubject.objects.count() == 0
