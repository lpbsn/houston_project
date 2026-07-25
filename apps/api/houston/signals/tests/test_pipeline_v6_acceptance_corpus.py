"""Lot 0 — corpus validation (green) and temporary V5 runtime baseline guards."""

from __future__ import annotations

import copy
import uuid

import pytest

from houston.ai.observation_pipeline import (
    PRECONDITION_INVALID_ESTABLISHMENT,
    PRECONDITION_NO_ACTIVE_BUSINESS_UNIT,
    ObservationPipelineSkippedError,
    call_observation_pipeline,
    establishment_can_run_observation_pipeline,
    evaluate_observation_pipeline_precondition,
)
from houston.establishments.models import Establishment
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership
from houston.testing.pipeline_golden_v4 import (
    get_pipeline_golden_v4_case,
    remap_expected_candidates_to_routing_keys,
    setup_active_signals_from_fixture,
    setup_taxonomy_from_fixture,
)
from houston.testing.pipeline_v6_acceptance import (
    REQUIRED_CASE_IDS,
    assert_pipeline_v6_acceptance_artefacts_valid,
    get_pipeline_v6_acceptance_case,
    iter_truth_table_rows,
    list_executable_v5_baseline_case_ids,
    list_pipeline_v6_acceptance_case_ids,
    load_pipeline_v6_acceptance_corpus,
    load_pipeline_v6_truth_tables,
    validate_all_pipeline_v6_acceptance_artefacts,
    validate_pipeline_v6_lot_acceptance,
    validate_pipeline_v6_orphan_coverage,
)
from houston.testing.pipeline_v6_metrics import LOT_ACCEPTANCE, LOT_IDS, METRIC_IDS
from houston.testing.taxonomy import create_activity_subject, create_business_unit

pytestmark = pytest.mark.django_db


def test_pipeline_v6_acceptance_artefacts_are_valid():
    errors = validate_all_pipeline_v6_acceptance_artefacts()
    assert errors == [], "\n".join(errors)
    assert_pipeline_v6_acceptance_artefacts_valid()


def test_pipeline_v6_acceptance_corpus_has_required_case_ids():
    case_ids = list_pipeline_v6_acceptance_case_ids()
    assert case_ids == list(REQUIRED_CASE_IDS)
    assert len(case_ids) == 21


def test_pipeline_v6_lot_acceptance_covers_lot0_to_lot10():
    assert tuple(sorted(LOT_ACCEPTANCE)) == tuple(sorted(LOT_IDS))
    for lot_id in LOT_IDS:
        entry = LOT_ACCEPTANCE[lot_id]
        assert entry["criteria"], f"{lot_id} must list acceptance criteria"
    lot0_criteria = set(LOT_ACCEPTANCE["lot0"]["criteria"])
    for required in {
        "corpus_valid",
        "unique_ids",
        "observed_v5_recorded",
        "metrics_a_j_referenced",
        "truth_tables_valid",
        "v6_tests_explicitly_pending",
    }:
        assert required in lot0_criteria


def test_pipeline_v6_metrics_a_to_j_defined():
    assert METRIC_IDS == tuple("ABCDEFGHIJ")


def test_pipeline_v6_truth_tables_loadable():
    tables = load_pipeline_v6_truth_tables()
    assert set(tables["sections"]) == {
        "precondition",
        "resolver",
        "persistence",
        "aggregation",
        "errors",
        "context",
    }


def test_every_corpus_case_has_observed_v5_and_expected_v6():
    for case in load_pipeline_v6_acceptance_corpus()["cases"]:
        assert "observed_v5" in case
        assert "expected_v6" in case
        assert isinstance(case["observed_v5"]["executable"], bool)


def test_lot_acceptance_rejects_case_missing_lot_in_lots():
    corpus = copy.deepcopy(load_pipeline_v6_acceptance_corpus())
    case_id = LOT_ACCEPTANCE["lot9"]["case_ids"][0]
    case = next(c for c in corpus["cases"] if c["id"] == case_id)
    case["lots"] = [lot for lot in case["lots"] if lot != "lot9"]
    errors = validate_pipeline_v6_lot_acceptance(corpus=corpus)
    assert any(
        f"LOT_ACCEPTANCE[lot9] case {case_id} missing lot9 in lots" in err for err in errors
    ), errors


def test_orphan_coverage_rejects_lot_only_present_in_lot_acceptance():
    corpus = copy.deepcopy(load_pipeline_v6_acceptance_corpus())
    tables = copy.deepcopy(load_pipeline_v6_truth_tables())
    for case in corpus["cases"]:
        case["lots"] = [lot for lot in case.get("lots", []) if lot != "lot9"]
    assert "lot9" in LOT_ACCEPTANCE
    assert all(row.get("owning_lot") != "lot9" for _, row in iter_truth_table_rows(tables))
    errors = validate_pipeline_v6_orphan_coverage(corpus=corpus, truth_tables=tables)
    assert any("lot lot9 has no coverage reference" in err for err in errors), errors


def test_lot_acceptance_rejects_truth_row_owning_lot_mismatch():
    tables = copy.deepcopy(load_pipeline_v6_truth_tables())
    lot_id = "lot1"
    row_id = LOT_ACCEPTANCE[lot_id]["truth_row_ids"][0]
    for _, row in iter_truth_table_rows(tables):
        if row["id"] == row_id:
            row["owning_lot"] = "lot2"
            break
    else:
        raise AssertionError(f"truth row {row_id} not found")
    errors = validate_pipeline_v6_lot_acceptance(truth_tables=tables)
    assert any(
        f"LOT_ACCEPTANCE[{lot_id}] truth row {row_id} owning_lot 'lot2' != {lot_id}" in err
        for err in errors
    ), errors


# ---------------------------------------------------------------------------
# Temporary V5 runtime baseline guards (name prefix for -k selection/exclusion)
# Select:  -k v5_baseline_runtime
# Exclude: -k "not v5_baseline_runtime"
# ---------------------------------------------------------------------------


def test_v5_baseline_runtime_executable_case_ids_are_documented():
    executable_ids = list_executable_v5_baseline_case_ids()
    assert executable_ids
    for case_id in executable_ids:
        case = get_pipeline_v6_acceptance_case(case_id)
        assert case["observed_v5"]["executable"] is True


def test_v6_runtime_lot2_s15_01_invalid_establishment_skips():
    case = get_pipeline_v6_acceptance_case("S15-01")
    missing_id = uuid.uuid4()
    with pytest.raises(ObservationPipelineSkippedError) as missing_exc:
        evaluate_observation_pipeline_precondition(establishment_id=missing_id)
    assert missing_exc.value.error_code == case["expected_v6"]["error_code"]
    assert missing_exc.value.error_code == PRECONDITION_INVALID_ESTABLISHMENT
    assert case["expected_v6"]["pipeline_started"] is False

    membership = build_membership()
    create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    establishment = membership.establishment
    establishment.status = Establishment.Status.DEACTIVATED
    establishment.save(update_fields=["status", "updated_at"])
    observation = create_observation(membership=membership, text=case["observation_text"])
    assert (
        establishment_can_run_observation_pipeline(
            establishment_id=observation.establishment_id,
        )
        is False
    )
    with pytest.raises(ObservationPipelineSkippedError) as exc_info:
        call_observation_pipeline(observation=observation)
    assert exc_info.value.error_code == case["expected_v6"]["error_code"]


def test_v6_runtime_lot2_s15_02_no_active_business_unit_skips():
    case = get_pipeline_v6_acceptance_case("S15-02")
    membership = build_membership()
    observation = create_observation(membership=membership, text=case["observation_text"])
    assert (
        establishment_can_run_observation_pipeline(
            establishment_id=observation.establishment_id,
        )
        is False
    )
    with pytest.raises(ObservationPipelineSkippedError) as exc_info:
        call_observation_pipeline(observation=observation)
    assert exc_info.value.error_code == case["expected_v6"]["error_code"]
    assert exc_info.value.error_code == PRECONDITION_NO_ACTIVE_BUSINESS_UNIT
    assert case["expected_v6"]["pipeline_started"] is False


def test_v6_runtime_lot2_s15_04_active_bu_without_subjects_allows_pipeline():
    case = get_pipeline_v6_acceptance_case("S15-04")
    membership = build_membership()
    create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    assert (
        establishment_can_run_observation_pipeline(
            establishment_id=membership.establishment_id,
        )
        is True
    )
    assert case["expected_v6"]["pipeline_started"] is True
    assert case["expected_v6"]["error_code"] is None


def test_v5_baseline_runtime_s15_05_golden_g05_apply():
    _assert_v5_baseline_runtime_golden_apply("S15-05")


def test_v5_baseline_runtime_s15_11_golden_g01_segmentation():
    _assert_v5_baseline_runtime_golden_apply("S15-11")


def test_v5_baseline_runtime_s15_12_empty_candidates_no_signal():
    _assert_v5_baseline_runtime_empty_candidates("S15-12")


def test_v5_baseline_runtime_s15_14_empty_candidates_no_signal():
    _assert_v5_baseline_runtime_empty_candidates("S15-14")


def test_v5_baseline_runtime_s15_19_incoherent_subject_responsible_drops_candidate():
    case = get_pipeline_v6_acceptance_case("S15-19")
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hôtel")
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type="transversal",
    )
    menage = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Ménage",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Équipements d'exploitation",
    )
    observation = create_observation(membership=membership, text=case["observation_text"])
    result = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Problème ménage",
                    structured_summary="Hall à nettoyer.",
                    issue_focus="menage hall",
                    operational_unit_key=None,
                    location_text="hall",
                    aggregate_into_signal_id=None,
                    affected_business_unit_routing_key=hotel.routing_key,
                    responsible_business_unit_routing_key=maintenance.routing_key,
                    activity_subject_routing_key=menage.routing_key,
                )
            ],
        ),
    )
    assert result.outcome == ObservationProcessing.Outcome.NO_SIGNAL_CREATED
    assert case["observed_v5"]["outcome"] == "no_signal_created"
    assert (
        CandidateSignal.objects.filter(
            observation=observation,
            outcome=CandidateSignal.Outcome.REJECTED,
        ).count()
        == 1
    )
    assert Signal.objects.filter(establishment=establishment).count() == 0


def test_v6_runtime_lot2_s15_d1_active_non_snapshot_ready_allows_pipeline():
    case = get_pipeline_v6_acceptance_case("S15-D1")
    membership = build_membership()
    create_business_unit(
        establishment=membership.establishment,
        key="spa",
        label="Spa",
    )
    create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    assert (
        establishment_can_run_observation_pipeline(
            establishment_id=membership.establishment_id,
        )
        is True
    )
    assert case["expected_v6"]["pipeline_started"] is True
    assert case["expected_v6"]["error_code"] is None


def _assert_v5_baseline_runtime_golden_apply(case_id: str) -> None:
    case = get_pipeline_v6_acceptance_case(case_id)
    assert case["observed_v5"]["executable"] is True
    golden_ids = case["legacy_golden_ids"]
    assert golden_ids, f"{case_id} must declare legacy_golden_ids for golden apply baseline"
    golden_id = golden_ids[0]
    golden = get_pipeline_golden_v4_case(golden_id)
    membership = build_membership()
    establishment = membership.establishment
    business_units, activity_subjects = setup_taxonomy_from_fixture(
        establishment=establishment,
        fixture=golden["taxonomy_fixture"],
    )
    setup_active_signals_from_fixture(
        establishment=establishment,
        setup=golden.get("active_signals_setup", []),
        business_units=business_units,
        activity_subjects=activity_subjects,
    )
    observation = create_observation(
        membership=membership,
        text=golden["observation_text"],
    )
    remapped = remap_expected_candidates_to_routing_keys(
        expected_candidates=golden["expected_candidates"],
        business_units=business_units,
        activity_subjects=activity_subjects,
    )
    result = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[PipelineCandidateOutput(**raw) for raw in remapped],
        ),
    )
    assert result.outcome.value == golden["expected_outcome"]
    assert case["observed_v5"]["outcome"] == golden["expected_outcome"]
    assert case["observed_v5"]["pipeline_started"] is True
    expected_apply = golden["expected_apply"]
    assert result.created_count == expected_apply["created_count"]
    assert result.aggregated_count == expected_apply["aggregated_count"]
    assert (
        Signal.objects.filter(establishment=establishment).count()
        == expected_apply["signal_count"]
    )


def _assert_v5_baseline_runtime_empty_candidates(case_id: str) -> None:
    case = get_pipeline_v6_acceptance_case(case_id)
    membership = build_membership()
    create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    observation = create_observation(membership=membership, text=case["observation_text"])
    result = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[],
        ),
    )
    assert result.outcome == ObservationProcessing.Outcome.NO_SIGNAL_CREATED
    assert case["observed_v5"]["outcome"] == "no_signal_created"
    assert case["observed_v5"]["pipeline_started"] is True
