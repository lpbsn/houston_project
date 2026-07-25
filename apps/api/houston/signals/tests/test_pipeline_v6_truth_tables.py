"""V6 truth-table runners — Lot 1 implements PERS-01/02/04 (models/helpers/constraints)."""

from __future__ import annotations

import pytest
from django.utils import timezone

from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.models import Signal
from houston.signals.signal_classification import routing_status_for_classification
from houston.testing.factories import create_establishment
from houston.testing.pipeline_v6_acceptance import (
    get_truth_table_row,
    iter_truth_table_rows,
    list_truth_table_row_ids,
)

pytestmark = pytest.mark.django_db

LOT1_IMPLEMENTED_TRUTH_ROWS = frozenset({"PERS-01", "PERS-02", "PERS-04"})


def _run_pers_01(row: dict) -> dict:
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key=row["input"]["affected_key"],
        label="Hôtel",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Ménage",
    )
    routing_status = routing_status_for_classification(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
    )
    Signal.objects.create(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="PERS-01",
        structured_summary="Coherent triplet.",
        issue_focus="menage",
        status=Signal.Status.OPEN,
        routing_status=routing_status,
        last_activity_at=timezone.now(),
    )
    return {
        "routing_status": routing_status,
        "signal_created": True,
        "subject_business_unit_matches_responsible": (
            subject.business_unit_id == hotel.id
        ),
    }


def _run_pers_02(row: dict) -> dict:
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key=row["input"]["affected_key"],
        label="Hôtel",
    )
    routing_status = routing_status_for_classification(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=None,
        activity_subject=None,
    )
    Signal.objects.create(
        establishment=establishment,
        affected_business_unit=hotel,
        title="PERS-02",
        structured_summary="Partial routing.",
        issue_focus="partial",
        status=Signal.Status.OPEN,
        routing_status=routing_status,
        last_activity_at=timezone.now(),
    )
    return {
        "routing_status": routing_status,
        "signal_created": True,
    }


def _run_pers_04(row: dict) -> dict:
    establishment = create_establishment()
    now = timezone.now()
    for index in range(row["input"]["signal_count"]):
        Signal.objects.create(
            establishment=establishment,
            title=f"PERS-04-{index}",
            structured_summary="Unassigned coexistence.",
            issue_focus="same-null-key",
            status=Signal.Status.OPEN,
            routing_status=Signal.RoutingStatus.UNASSIGNED,
            last_activity_at=now,
        )
    count = Signal.objects.filter(
        establishment=establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
    ).count()
    return {
        "signal_count": count,
        "routing_status": Signal.RoutingStatus.UNASSIGNED,
        "unique_constraint_applies": False,
    }


def _run_v6_truth_row(row: dict) -> dict:
    row_id = row["id"]
    if row_id == "PERS-01":
        return _run_pers_01(row)
    if row_id == "PERS-02":
        return _run_pers_02(row)
    if row_id == "PERS-04":
        return _run_pers_04(row)
    raise NotImplementedError(
        f"v6_pending: truth row {row_id} owned by {row['owning_lot']} "
        "is not wired to a V6 service yet"
    )


@pytest.mark.parametrize("row_id", list_truth_table_row_ids())
def test_v6_truth_table_row_matches_expected_v6(row_id: str):
    row = get_truth_table_row(row_id)
    if row_id not in LOT1_IMPLEMENTED_TRUTH_ROWS:
        pytest.xfail(
            f"v6_pending: truth row {row_id} owned by {row['owning_lot']} "
            "is not wired to a V6 service yet"
        )
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


def test_pers_03_owned_by_lot2():
    row = get_truth_table_row("PERS-03")
    assert row["owning_lot"] == "lot2"


def test_no_lot1_truth_row_remains_unimplemented_xfail():
    lot1_ids = {
        row["id"]
        for _, row in iter_truth_table_rows()
        if row.get("owning_lot") == "lot1"
    }
    assert lot1_ids
    assert lot1_ids <= LOT1_IMPLEMENTED_TRUTH_ROWS
