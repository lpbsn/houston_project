from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import apply_pipeline_output, normalize_issue_focus
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership
from houston.testing.pipeline_golden_v4 import (
    get_pipeline_golden_v4_case,
    list_pipeline_golden_v4_case_ids,
    setup_active_signals_from_fixture,
    setup_taxonomy_from_fixture,
)

pytestmark = pytest.mark.django_db

OUTCOME_BY_NAME = {
    "signals_created": ObservationProcessing.Outcome.SIGNALS_CREATED,
    "signal_aggregated": ObservationProcessing.Outcome.SIGNAL_AGGREGATED,
    "mixed": ObservationProcessing.Outcome.SIGNALS_CREATED,
}

CANDIDATE_OUTCOME_BY_NAME = {
    "created_signal": CandidateSignal.Outcome.CREATED_SIGNAL,
    "aggregated_signal": CandidateSignal.Outcome.AGGREGATED_SIGNAL,
    "rejected": CandidateSignal.Outcome.REJECTED,
}


def _candidate_from_corpus(raw: dict) -> PipelineCandidateOutput:
    return PipelineCandidateOutput(**raw)


def _run_golden_case(case_id: str):
    case = get_pipeline_golden_v4_case(case_id)
    membership = build_membership()
    establishment = membership.establishment
    business_units, activity_subjects = setup_taxonomy_from_fixture(
        establishment=establishment,
        fixture=case["taxonomy_fixture"],
    )
    active_signals = setup_active_signals_from_fixture(
        establishment=establishment,
        setup=case.get("active_signals_setup", []),
        business_units=business_units,
        activity_subjects=activity_subjects,
    )
    observation = create_observation(
        membership=membership,
        text=case["observation_text"],
    )
    candidates = [_candidate_from_corpus(raw) for raw in case["expected_candidates"]]
    result = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=candidates,
        ),
    )
    return {
        "case": case,
        "result": result,
        "observation": observation,
        "establishment": establishment,
        "business_units": business_units,
        "activity_subjects": activity_subjects,
        "active_signals": active_signals,
    }


def _assert_apply_expectations(context: dict) -> None:
    case = context["case"]
    result = context["result"]
    observation = context["observation"]
    establishment = context["establishment"]
    business_units = context["business_units"]
    activity_subjects = context["activity_subjects"]
    active_signals = context["active_signals"]

    expected = case["expected_apply"]
    expected_outcome = OUTCOME_BY_NAME[case["expected_outcome"]]
    assert result.outcome == expected_outcome
    assert result.created_count == expected["created_count"]
    assert result.aggregated_count == expected["aggregated_count"]

    assert Signal.objects.filter(establishment=establishment).count() == expected["signal_count"]

    rejected_count = CandidateSignal.objects.filter(
        observation=observation,
        outcome=CandidateSignal.Outcome.REJECTED,
    ).count()
    assert rejected_count == expected.get("rejected_count", 0)

    latest_outcome_name = expected.get("latest_candidate_outcome")
    if latest_outcome_name is not None:
        latest_row = (
            CandidateSignal.objects.filter(observation=observation)
            .order_by("created_at")
            .last()
        )
        assert latest_row is not None
        assert latest_row.outcome == CANDIDATE_OUTCOME_BY_NAME[latest_outcome_name]

    aggregated_into_ref = expected.get("aggregated_into_ref")
    if aggregated_into_ref is not None:
        target_signal = active_signals[aggregated_into_ref]
        latest_row = (
            CandidateSignal.objects.filter(observation=observation)
            .order_by("created_at")
            .last()
        )
        assert latest_row is not None
        assert latest_row.result_signal_id == target_signal.id

    for signal_spec in expected.get("signals", []):
        affected = business_units[signal_spec["affected_business_unit_key"]]
        responsible = business_units[signal_spec["responsible_business_unit_key"]]
        subject = activity_subjects[signal_spec["activity_subject_key"]]
        matching = Signal.objects.filter(
            establishment=establishment,
            affected_business_unit=affected,
            responsible_business_unit=responsible,
            activity_subject=subject,
        )
        if "issue_focus" in signal_spec:
            matching = matching.filter(
                issue_focus=normalize_issue_focus(signal_spec["issue_focus"]),
            )
        assert matching.exists(), (
            f"Expected signal for issue_focus={signal_spec.get('issue_focus')!r} "
            f"with taxonomy {signal_spec['affected_business_unit_key']}/"
            f"{signal_spec['responsible_business_unit_key']}/"
            f"{signal_spec['activity_subject_key']}"
        )


@pytest.mark.parametrize("case_id", list_pipeline_golden_v4_case_ids())
def test_pipeline_v4_golden_corpus_case(case_id: str):
    _assert_apply_expectations(_run_golden_case(case_id))
