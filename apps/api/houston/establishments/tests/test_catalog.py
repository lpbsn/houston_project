from __future__ import annotations

import pytest

from houston.establishments.catalog import (
    catalog_domain_rows,
    catalog_module_rows,
    catalog_subject_rows,
    expand_module_keys,
    load_arborescence_rows,
)

pytestmark = pytest.mark.django_db


def test_load_arborescence_rows_counts():
    rows = load_arborescence_rows()
    module_keys = {row.module_key for row in rows}
    domain_keys = {row.domain_key for row in rows}

    assert len(module_keys) == 6
    assert len(domain_keys) == 31
    assert len(rows) == 154


def test_catalog_helper_row_counts_match_arborescence():
    assert len(catalog_module_rows()) == 6
    assert len(catalog_domain_rows()) == 31
    assert len(catalog_subject_rows()) == 154


def test_expand_module_keys_for_hotel():
    expanded = expand_module_keys(["hotel"])

    assert len(expanded["operational_domains"]) == 6
    assert len(expanded["operational_subjects"]) == 29
    assert all(item["module_key"] == "hotel" for item in expanded["operational_domains"])
    assert all(item["module_key"] == "hotel" for item in expanded["operational_subjects"])
    assert all(
        item["domain_key"].startswith("hotel__") for item in expanded["operational_subjects"]
    )
