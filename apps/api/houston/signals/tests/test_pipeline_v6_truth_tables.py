"""Lot 0 — V6 truth-table skeletons (xfail until owning_lot implements behavior)."""

from __future__ import annotations

import pytest

from houston.testing.pipeline_v6_acceptance import (
    get_truth_table_row,
    iter_truth_table_rows,
    list_truth_table_row_ids,
)


def _run_v6_truth_row(row: dict) -> dict:
    """Future hook: owning_lot branches this to the real deterministic service.

    Lot 0 intentionally leaves this unimplemented so tests stay xfail (strict).
    """
    raise NotImplementedError(
        f"v6_pending: truth row {row['id']} owned by {row['owning_lot']} "
        "is not wired to a V6 service yet"
    )


@pytest.mark.xfail(strict=True, reason="v6_pending")
@pytest.mark.parametrize("row_id", list_truth_table_row_ids())
def test_v6_truth_table_row_matches_expected_v6(row_id: str):
    row = get_truth_table_row(row_id)
    actual = _run_v6_truth_row(row)
    assert actual == row["expected_v6"]


def test_v6_truth_table_rows_have_owning_lot():
    rows = iter_truth_table_rows()
    assert rows
    for section_name, row in rows:
        assert row["owning_lot"].startswith("lot")
        assert "expected_v6" in row
        assert "observed_v5" in row
        assert section_name in {
            "precondition",
            "resolver",
            "persistence",
            "aggregation",
            "errors",
        }
