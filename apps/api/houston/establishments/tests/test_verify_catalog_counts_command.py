from __future__ import annotations

import pytest
from django.core.management import call_command

from houston.establishments.catalog_seed_counts import (
    EXPECTED_CATALOG_ACTIVITY_SUBJECT_COUNT,
    EXPECTED_CATALOG_BUSINESS_UNIT_COUNT,
)

pytestmark = pytest.mark.django_db


def test_verify_catalog_counts_succeeds_after_import(imported_catalog, capsys):
    call_command("verify_catalog_counts")
    output = capsys.readouterr().out
    assert "catalog-check OK" in output
    assert str(EXPECTED_CATALOG_BUSINESS_UNIT_COUNT) in output
    assert str(EXPECTED_CATALOG_ACTIVITY_SUBJECT_COUNT) in output


def test_verify_catalog_counts_fails_when_catalog_empty():
    from houston.establishments.models import CatalogActivitySubject, CatalogBusinessUnit

    CatalogActivitySubject.objects.all().delete()
    CatalogBusinessUnit.objects.all().delete()

    with pytest.raises(SystemExit) as exc_info:
        call_command("verify_catalog_counts")
    assert exc_info.value.code == 1
