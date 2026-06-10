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


@pytest.fixture(scope="session")
def imported_catalog(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return sync_catalog_from_normalized_rows()
