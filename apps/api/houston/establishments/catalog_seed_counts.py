"""Expected row counts for versioned catalog seed CSVs (single source of truth)."""

from __future__ import annotations

from houston.establishments.catalog_source_normalization import (
    load_normalized_activity_subject_rows,
    load_normalized_business_unit_rows,
)

EXPECTED_CATALOG_BUSINESS_UNIT_COUNT = len(load_normalized_business_unit_rows())
EXPECTED_CATALOG_ACTIVITY_SUBJECT_COUNT = len(load_normalized_activity_subject_rows())
