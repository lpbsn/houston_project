"""V6 truth-table runners — Lot 1 PERS-01/02/04; Lot 2 PRE-*/PERS-03/ERR-01."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.ai.observation_pipeline import (
    PRECONDITION_INVALID_ESTABLISHMENT,
    PRECONDITION_NO_ACTIVE_BUSINESS_UNIT,
    FakeObservationPipelineProvider,
    ObservationPipelineSkippedError,
    ObservationPipelineTimeoutError,
    establishment_can_run_observation_pipeline,
    evaluate_observation_pipeline_precondition,
)
from houston.establishments.models import BusinessUnit
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import Signal
from houston.signals.services import run_observation_pipeline
from houston.signals.signal_classification import routing_status_for_classification
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership, create_establishment
from houston.testing.pipeline_v6_acceptance import (
    get_truth_table_row,
    iter_truth_table_rows,
    list_truth_table_row_ids,
)

pytestmark = pytest.mark.django_db

LOT1_IMPLEMENTED_TRUTH_ROWS = frozenset({"PERS-01", "PERS-02", "PERS-04"})
LOT2_IMPLEMENTED_TRUTH_ROWS = frozenset(
    {
        "PRE-01",
        "PRE-02",
        "PRE-03",
        "PRE-04",
        "PERS-03",
        "ERR-01",
    }
)
IMPLEMENTED_TRUTH_ROWS = LOT1_IMPLEMENTED_TRUTH_ROWS | LOT2_IMPLEMENTED_TRUTH_ROWS

# Lot 2 owns precondition start; Signal unassigned creation is Lot 5.
LOT2_PARTIAL_EXPECTED_KEYS = {
    "PRE-03": frozenset({"allows_pipeline", "error_code"}),
    "PRE-04": frozenset({"allows_pipeline", "error_code"}),
}


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


def _run_pers_03(row: dict) -> dict:
    membership = build_membership()
    create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    observation = create_observation(membership=membership)

    class _TimeoutProvider(FakeObservationPipelineProvider):
        def propose(self, *, input_payload):
            raise ObservationPipelineTimeoutError("provider timeout")

    provider = _TimeoutProvider()
    for _ in range(3):
        with pytest.raises(ObservationPipelineTimeoutError):
            run_observation_pipeline(observation.id, provider=provider)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == row["input"]["technical_error"]
    signal_created = Signal.objects.filter(establishment=membership.establishment).exists()
    return {
        "routing_status": None,
        "signal_created": signal_created,
        "processing_failed": True,
        "error_code": processing.last_error_code,
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


def _precondition_result(*, establishment_id: uuid.UUID) -> dict:
    try:
        evaluate_observation_pipeline_precondition(establishment_id=establishment_id)
    except ObservationPipelineSkippedError as exc:
        return {
            "allows_pipeline": False,
            "error_code": exc.error_code,
            "creates_signal": False,
            "routing_status": None,
        }
    return {
        "allows_pipeline": True,
        "error_code": None,
        "creates_signal": True,
        "routing_status": "unassigned",
    }


def _run_pre_01(row: dict) -> dict:
    missing_id = uuid.uuid4()
    result = _precondition_result(establishment_id=missing_id)
    assert result["error_code"] == PRECONDITION_INVALID_ESTABLISHMENT
    assert establishment_can_run_observation_pipeline(establishment_id=missing_id) is False
    return result


def _run_pre_02(row: dict) -> dict:
    establishment = create_establishment()
    result = _precondition_result(establishment_id=establishment.id)
    assert result["error_code"] == PRECONDITION_NO_ACTIVE_BUSINESS_UNIT
    return result


def _run_pre_03(row: dict) -> dict:
    establishment = create_establishment()
    create_business_unit(establishment=establishment, key="hotel", label="Hôtel")
    result = _precondition_result(establishment_id=establishment.id)
    assert result["allows_pipeline"] is True
    return {
        "allows_pipeline": result["allows_pipeline"],
        "error_code": result["error_code"],
    }


def _run_pre_04(row: dict) -> dict:
    establishment = create_establishment()
    create_business_unit(establishment=establishment, key="spa", label="Spa")

    def _empty_snapshot_ready(*, establishment_id):
        return BusinessUnit.objects.none()

    # Active BU exists; snapshot-ready empty must not block Lot 2 precondition.
    with patch(
        "houston.establishments.taxonomy_snapshot.snapshot_ready_business_units",
        side_effect=_empty_snapshot_ready,
    ):
        from houston.establishments.taxonomy_snapshot import (
            establishment_has_active_business_units,
            establishment_has_any_active_business_unit,
        )

        assert establishment_has_any_active_business_unit(
            establishment_id=establishment.id,
        )
        # Snapshot-ready helper still consults the (patched) snapshot predicate.
        assert (
            establishment_has_active_business_units(establishment_id=establishment.id)
            is False
        )
        result = _precondition_result(establishment_id=establishment.id)
    assert result["allows_pipeline"] is True
    return {
        "allows_pipeline": result["allows_pipeline"],
        "error_code": result["error_code"],
    }


def _run_err_01(row: dict) -> dict:
    membership = build_membership()
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider(
        payload={"schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION, "candidates": []}
    )
    run_observation_pipeline(observation.id, provider=provider)
    processing = observation.processing
    processing.refresh_from_db()
    signal_created = Signal.objects.filter(establishment=membership.establishment).exists()
    return {
        "error_code": processing.last_error_code,
        "routing_status": None,
        "signal_created": signal_created,
    }


def _run_v6_truth_row(row: dict) -> dict:
    row_id = row["id"]
    runners = {
        "PERS-01": _run_pers_01,
        "PERS-02": _run_pers_02,
        "PERS-03": _run_pers_03,
        "PERS-04": _run_pers_04,
        "PRE-01": _run_pre_01,
        "PRE-02": _run_pre_02,
        "PRE-03": _run_pre_03,
        "PRE-04": _run_pre_04,
        "ERR-01": _run_err_01,
    }
    runner = runners.get(row_id)
    if runner is None:
        raise NotImplementedError(
            f"v6_pending: truth row {row_id} owned by {row['owning_lot']} "
            "is not wired to a V6 service yet"
        )
    return runner(row)


@pytest.mark.parametrize("row_id", list_truth_table_row_ids())
def test_v6_truth_table_row_matches_expected_v6(row_id: str):
    row = get_truth_table_row(row_id)
    if row_id not in IMPLEMENTED_TRUTH_ROWS:
        pytest.xfail(
            f"v6_pending: truth row {row_id} owned by {row['owning_lot']} "
            "is not wired to a V6 service yet"
        )
    actual = _run_v6_truth_row(row)
    expected = row["expected_v6"]
    partial_keys = LOT2_PARTIAL_EXPECTED_KEYS.get(row_id)
    if partial_keys is not None:
        assert {key: actual[key] for key in partial_keys} == {
            key: expected[key] for key in partial_keys
        }
        return
    assert actual == expected


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


def test_no_lot2_truth_row_remains_unimplemented_xfail():
    lot2_ids = {
        row["id"]
        for _, row in iter_truth_table_rows()
        if row.get("owning_lot") == "lot2"
    }
    assert lot2_ids
    assert lot2_ids <= LOT2_IMPLEMENTED_TRUTH_ROWS
