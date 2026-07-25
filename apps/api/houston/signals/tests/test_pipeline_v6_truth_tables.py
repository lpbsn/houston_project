"""V6 truth-table runners — Lot 1/2 + Lot 3 CTX-* + Lot 4 ERR-02/03."""

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
    _resolve_action_plan_business_unit_context,
    build_pipeline_input,
    establishment_can_run_observation_pipeline,
    evaluate_observation_pipeline_precondition,
)
from houston.ai.observation_pipeline_schema import ObservationPipelineOutput
from houston.establishments.business_unit_identity import normalize_generic_activity_subject_name
from houston.establishments.models import ActivitySubject, BusinessUnit, CatalogActivitySubject
from houston.establishments.taxonomy_snapshot import (
    build_active_business_units,
    build_routing_taxonomy,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_membership_with_business_unit_scope,
)
from houston.observations.models import ObservationProcessing
from houston.signals.catalog_capabilities import CATALOG_CAPABILITIES_VERSION
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import Signal
from houston.signals.services import run_observation_pipeline
from houston.signals.signal_classification import routing_status_for_classification
from houston.signals.tests.conftest import create_observation
from houston.signals.tests.pipeline_helpers import fake_provider_payload
from houston.testing.action_plan_pipeline import create_action_plan_task_observation
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
LOT3_IMPLEMENTED_TRUTH_ROWS = frozenset(
    {
        "CTX-01",
        "CTX-02",
        "CTX-03",
        "CTX-04",
        "CTX-05",
        "CTX-06",
        "CTX-07",
        "CTX-08",
    }
)
LOT4_IMPLEMENTED_TRUTH_ROWS = frozenset({"ERR-02", "ERR-03"})
IMPLEMENTED_TRUTH_ROWS = (
    LOT1_IMPLEMENTED_TRUTH_ROWS
    | LOT2_IMPLEMENTED_TRUTH_ROWS
    | LOT3_IMPLEMENTED_TRUTH_ROWS
    | LOT4_IMPLEMENTED_TRUTH_ROWS
)

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


def _run_err_02(row: dict) -> dict:
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider(
        exc=ObservationPipelineTimeoutError("provider timeout"),
    )
    with pytest.raises(ObservationPipelineTimeoutError):
        run_observation_pipeline(observation.id, provider=provider)
    processing = observation.processing
    processing.refresh_from_db()
    return {
        "error_code": processing.last_error_code,
        "routing_status": None,
        "signal_created": Signal.objects.filter(
            establishment=membership.establishment,
        ).exists(),
    }


def _run_err_03(row: dict) -> dict:
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    observation = create_observation(membership=membership)
    # Valid taxonomy keys but schema-invalid payload (missing V6 required fields).
    invalid_payload = {
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "candidates": [
            {
                "title": "Broken",
                "structured_summary": "Missing required V6 fields.",
                "issue_focus": "broken",
            }
        ],
    }
    # Ensure fake helper shape itself is parseable when complete (contract guard).
    assert ObservationPipelineOutput.model_validate(
        fake_provider_payload(
            affected_routing_key=hotel.routing_key,
            subject_routing_key=subject.routing_key,
        )
    )
    provider = FakeObservationPipelineProvider(payload=invalid_payload)
    run_observation_pipeline(observation.id, provider=provider)
    processing = observation.processing
    processing.refresh_from_db()
    return {
        "error_code": processing.last_error_code,
        "routing_status": None,
        "signal_created": Signal.objects.filter(
            establishment=membership.establishment,
        ).exists(),
    }


def _catalog_key_for_active(unit: dict, *, establishment) -> str | None:
    bu = BusinessUnit.objects.get(id=unit["id"], establishment=establishment)
    if bu.catalog_business_unit_id is None:
        return None
    return bu.catalog_business_unit.key


def _run_ctx_01(row: dict) -> dict:
    establishment = create_establishment()
    create_business_unit(establishment=establishment, key="spa", label="Spa")
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hôtel")
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Ménage",
    )
    active = build_active_business_units(establishment_id=establishment.id)
    routing = build_routing_taxonomy(establishment_id=establishment.id)
    active_keys = {
        _catalog_key_for_active(unit, establishment=establishment) for unit in active
    }
    routing_keys = {unit["catalog_key"] for unit in routing["business_units"]}
    return {
        "active_includes": sorted(k for k in active_keys if k in {"spa", "hotel"}),
        "routing_excludes": ["spa"] if "spa" not in routing_keys else [],
        "routing_includes": sorted(k for k in routing_keys if k in {"spa", "hotel"}),
    }


def _run_ctx_02(row: dict) -> dict:
    establishment = create_establishment()
    for key, label in (("spa", "Spa"), ("hotel", "Hôtel"), ("bar", "Bar")):
        create_business_unit(establishment=establishment, key=key, label=label)
    active = build_active_business_units(establishment_id=establishment.id)
    return {
        "active_count": len(active),
        "active_omitted": len(active) != 3,
    }


def _run_ctx_03(row: dict) -> dict:
    membership = build_membership()
    establishment = membership.establishment
    rooftop = create_business_unit(
        establishment=establishment, key="rooftop", label="Rooftop"
    )
    food_court = create_business_unit(
        establishment=establishment, key="food_court", label="Food Court"
    )
    create_activity_subject(
        establishment=establishment, business_unit=rooftop, label="Service"
    )
    create_activity_subject(
        establishment=establishment, business_unit=food_court, label="Service"
    )
    create_membership_with_business_unit_scope(
        membership=membership, business_unit=rooftop
    )
    create_membership_with_business_unit_scope(
        membership=membership, business_unit=food_court
    )
    observation = create_observation(membership=membership)
    payload = build_pipeline_input(observation=observation)
    keys = payload["submission_context"]["author_scope_business_unit_routing_keys"]
    return {
        "author_scope_count": len(keys),
        "author_scopes_sorted": keys == sorted(keys),
        "author_scopes_deduped": len(keys) == len(set(keys)),
    }


def _run_ctx_04(row: dict) -> dict:
    membership = build_membership()
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Task subject",
    )
    observation = create_action_plan_task_observation(
        membership=membership,
        task_business_unit=maintenance,
        pilot_business_unit=maintenance,
    )
    payload = build_pipeline_input(observation=observation)
    ctx = payload["action_plan_context"]
    return {
        "context_business_unit_source": ctx["context_business_unit_source"],
        "business_unit_routing_key_null": ctx["business_unit_routing_key"] is None,
    }


def _run_ctx_05(row: dict) -> dict:
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Pilot subject",
    )
    observation = create_action_plan_task_observation(
        membership=membership,
        task_business_unit=hotel,
        pilot_business_unit=maintenance,
    )
    payload = build_pipeline_input(observation=observation)
    ctx = payload["action_plan_context"]
    return {
        "context_business_unit_source": ctx["context_business_unit_source"],
        "business_unit_routing_key_null": ctx["business_unit_routing_key"] is None,
        "uses_pilot_name": ctx["business_unit_specific_name"] == maintenance.specific_name,
    }


def _run_ctx_06(row: dict) -> dict:
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    spa = create_business_unit(
        establishment=membership.establishment, key="spa", label="Spa"
    )
    observation = create_action_plan_task_observation(
        membership=membership,
        task_business_unit=hotel,
        pilot_business_unit=spa,
    )
    payload = build_pipeline_input(observation=observation)
    ctx = payload["action_plan_context"]
    return {
        "business_unit_routing_key_null": ctx["business_unit_routing_key"] is None,
        "business_unit_specific_name_null": ctx["business_unit_specific_name"] is None,
        "context_business_unit_source": ctx["context_business_unit_source"],
    }


def _run_ctx_07(row: dict) -> dict:
    routing_key, specific_name, source = _resolve_action_plan_business_unit_context(
        task_business_unit=None,
        pilot_business_unit=None,
        routable_keys=set(),
    )
    return {
        "business_unit_routing_key_null": routing_key is None,
        "business_unit_specific_name_null": specific_name is None,
        "context_business_unit_source": source,
    }


def _run_ctx_08(row: dict) -> dict:
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(
        establishment=establishment, key="hotel", label="Hôtel"
    )
    known_catalog = CatalogActivitySubject.objects.create(
        catalog_business_unit=hotel.catalog_business_unit,
        key="hotel__menage",
        label="Ménage",
        description="Propreté",
        active=True,
        sort_order=1,
    )
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=hotel,
        catalog_activity_subject=known_catalog,
        normalized_name=normalize_generic_activity_subject_name(known_catalog.label),
        label="",
        description="",
        routing_key=known_catalog.key,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )
    unknown_catalog = CatalogActivitySubject.objects.create(
        catalog_business_unit=hotel.catalog_business_unit,
        key="hotel__unknown_capability_subject",
        label="Inconnu capacités",
        description="",
        active=True,
        sort_order=2,
    )
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=hotel,
        catalog_activity_subject=unknown_catalog,
        normalized_name=normalize_generic_activity_subject_name(unknown_catalog.label),
        label="",
        description="",
        routing_key=unknown_catalog.key,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Machine à café",
    )
    taxonomy = build_routing_taxonomy(establishment_id=establishment.id)
    subjects = {
        item["routing_key"]: item
        for item in taxonomy["business_units"][0]["activity_subjects"]
    }
    free_subject = next(s for s in subjects.values() if s["source"] == "free")
    return {
        "capabilities_version_present": (
            taxonomy.get("capabilities_version") == CATALOG_CAPABILITIES_VERSION
        ),
        "known_capabilities_non_empty": bool(subjects[known_catalog.key]["capabilities"]),
        "unknown_capabilities_empty": subjects[unknown_catalog.key]["capabilities"] == [],
        "free_capabilities_empty": free_subject["capabilities"] == [],
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
        "ERR-02": _run_err_02,
        "ERR-03": _run_err_03,
        "CTX-01": _run_ctx_01,
        "CTX-02": _run_ctx_02,
        "CTX-03": _run_ctx_03,
        "CTX-04": _run_ctx_04,
        "CTX-05": _run_ctx_05,
        "CTX-06": _run_ctx_06,
        "CTX-07": _run_ctx_07,
        "CTX-08": _run_ctx_08,
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
            "context",
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


def test_no_lot3_truth_row_remains_unimplemented_xfail():
    lot3_ids = {
        row["id"]
        for _, row in iter_truth_table_rows()
        if row.get("owning_lot") == "lot3"
    }
    assert lot3_ids
    assert lot3_ids <= LOT3_IMPLEMENTED_TRUTH_ROWS


def test_no_lot4_truth_row_remains_unimplemented_xfail():
    lot4_ids = {
        row["id"]
        for _, row in iter_truth_table_rows()
        if row.get("owning_lot") == "lot4"
    }
    assert lot4_ids
    assert lot4_ids <= LOT4_IMPLEMENTED_TRUTH_ROWS
    assert lot4_ids == LOT4_IMPLEMENTED_TRUTH_ROWS
