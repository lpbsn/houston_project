from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.pipeline_corpus_eval import (
    compare_pipeline_output_to_expected,
    evaluate_corpus_cases,
    format_corpus_eval_report,
)
from houston.testing.pipeline_golden_v4 import get_pipeline_golden_v4_case

pytestmark = pytest.mark.django_db


def test_compare_pipeline_output_flags_routing_and_issue_focus_mismatch():
    case = get_pipeline_golden_v4_case("G03")
    expected = case["expected_candidates"][0]
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Wrong routing candidate",
                structured_summary="Candidate with wrong taxonomy routing.",
                issue_focus=expected["issue_focus"],
                affected_business_unit_key="maintenance",
                responsible_business_unit_key="maintenance",
                activity_subject_key="plomberie_eau",
                operational_unit_key=None,
                location_text="couloir",
                aggregate_into_signal_id=None,
            )
        ],
    )

    result = compare_pipeline_output_to_expected(
        case_id="G03",
        description=case["description"],
        expected_candidates=case["expected_candidates"],
        output=output,
    )

    assert result.passed is False
    assert any("missing candidate signature" in diff for diff in result.diffs)
    assert any("extra candidate signature" in diff for diff in result.diffs)


def test_compare_pipeline_output_accepts_matching_signatures():
    case = get_pipeline_golden_v4_case("G01")
    candidates = [
        PipelineCandidateOutput(**raw) for raw in case["expected_candidates"]
    ]
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=candidates,
    )

    result = compare_pipeline_output_to_expected(
        case_id="G01",
        description=case["description"],
        expected_candidates=case["expected_candidates"],
        output=output,
    )

    assert result.passed is True
    assert result.diffs == ()


def test_evaluate_corpus_cases_fake_provider_passes_g01():
    report = evaluate_corpus_cases(case_ids=["G01"], provider_name="fake")

    assert len(report.case_results) == 1
    assert report.case_results[0].passed is True
    assert report.errors == ()


def test_format_corpus_eval_report_includes_pass_status():
    report = evaluate_corpus_cases(case_ids=["G01"], provider_name="fake")
    human = format_corpus_eval_report(report)
    assert "G01 PASS" in human
    assert "1/1 passed" in human


def test_evaluate_observation_pipeline_command_fake_provider_json():
    buffer = StringIO()
    call_command(
        "evaluate_observation_pipeline",
        case_id="G01",
        provider="fake",
        json=True,
        stdout=buffer,
    )
    payload = json.loads(buffer.getvalue())

    assert payload["provider"] == "fake"
    assert payload["case_count"] == 1
    assert payload["passed_count"] == 1
    assert payload["cases"][0]["case_id"] == "G01"


def test_evaluate_observation_pipeline_command_rejects_openai_without_opt_in():
    with pytest.raises(CommandError, match="HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST"):
        call_command(
            "evaluate_observation_pipeline",
            case_id="G01",
            provider="openai",
        )


def test_evaluate_observation_pipeline_command_fail_on_diff(monkeypatch):
    from houston.signals.pipeline_corpus_eval import CaseEvalResult, CorpusEvalReport

    monkeypatch.setattr(
        "houston.signals.management.commands.evaluate_observation_pipeline.evaluate_corpus_cases",
        lambda **kwargs: CorpusEvalReport(
            provider="fake",
            case_results=(
                CaseEvalResult(
                    case_id="G03",
                    description="forced failure",
                    passed=False,
                    diffs=("forced diff",),
                ),
            ),
        ),
    )

    with pytest.raises(CommandError, match="failures or errors"):
        call_command(
            "evaluate_observation_pipeline",
            case_id="G03",
            provider="fake",
            fail_on_diff=True,
        )
