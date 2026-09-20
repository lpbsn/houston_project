from __future__ import annotations

import pytest

from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.testing.auth import TEST_PASSWORD  # noqa: F401
from houston.testing.onboarding import create_ready_runtime  # noqa: F401


@pytest.fixture
def imported_catalog():
    return sync_catalog_from_normalized_rows()


@pytest.fixture
def requires_empty_catalog(db):
    from houston.establishments.models import CatalogActivitySubject, CatalogBusinessUnit

    assert CatalogBusinessUnit.objects.count() == 0
    assert CatalogActivitySubject.objects.count() == 0
