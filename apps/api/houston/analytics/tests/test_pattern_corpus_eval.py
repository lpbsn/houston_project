from __future__ import annotations

import json
import re
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from houston.analytics.classifier import (
    FakePatternClassifierProvider,
    PatternClassifierTimeoutError,
)
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.pattern_corpus_eval import (
    CorpusScenarioResult,
    _run_classification_to_terminal_state,
    analytics_pattern_corpus_eval_report_to_dict,
    evaluate_analytics_pattern_corpus,
    selected_scenarios_have_no_orphan_pairs,
)
from houston.analytics.services import create_operational_pattern
from houston.analytics.tests.test_classification_services import create_signal_for_membership
from houston.signals.models import Signal
from houston.testing.analytics_pattern_corpus import (
    CORPUS_SCHEMA_VERSION,
    get_analytics_pattern_scenario,
    list_analytics_pattern_scenario_ids,
    validate_analytics_pattern_corpus,
)
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db

UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def test_analytics_pattern_corpus_is_valid_and_has_seed_size():
    errors = validate_analytics_pattern_corpus()

    assert errors == []
    scenario_ids = list_analytics_pattern_scenario_ids()
    assert scenario_ids == [
        "hotel_facilities",
        "restaurant_stock",
        "housekeeping_rooms",
        "safety_public_areas",
        "frontdesk_guest_flow",
        "gym_operations",
        "concert_event",
        "shopping_mall",
        "coworking_living_space",
        "retail_store_holdout",
        "cinema_museum_holdout",
    ]
    signal_count = sum(
        len(get_analytics_pattern_scenario(scenario_id)["signals"])
        for scenario_id in scenario_ids
    )
    assert 60 <= signal_count <= 80


def test_analytics_pattern_corpus_validation_rejects_forbidden_data():
    corpus = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "scenarios": [
            {
                "id": "bad",
                "business_units": [{"key": "ops", "label": "Ops"}],
                "activity_subjects": [
                    {"key": "topic", "business_unit_key": "ops", "label": "Topic"}
                ],
                "signals": [
                    {
                        "ref": "s1",
                        "title": "Title",
                        "structured_summary": "Summary",
                        "issue_focus": "focus",
                        "activity_subject_key": "topic",
                        "affected_business_unit_key": "ops",
                        "responsible_business_unit_key": "ops",
                        "expected_new_pattern_label": "Pattern",
                        "raw_text": "forbidden",
                    }
                ],
                "initial_patterns": [],
                "fake_responses": {
                    "s1": {
                        "canonical_label": "Pattern",
                    }
                },
                "must_link": [],
                "must_not_link": [],
            }
        ],
    }

    errors = validate_analytics_pattern_corpus(corpus)

    assert any("forbidden key 'raw_text'" in error for error in errors)


def test_analytics_pattern_corpus_validation_rejects_invalid_pairs():
    corpus = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "scenarios": [
            {
                "id": "bad_pairs",
                "business_units": [{"key": "ops", "label": "Ops"}],
                "activity_subjects": [
                    {"key": "topic", "business_unit_key": "ops", "label": "Topic"}
                ],
                "signals": [
                    {
                        "ref": "s1",
                        "title": "Title 1",
                        "structured_summary": "Summary 1",
                        "issue_focus": "focus 1",
                        "activity_subject_key": "topic",
                        "affected_business_unit_key": "ops",
                        "responsible_business_unit_key": "ops",
                        "expected_new_pattern_label": "Pattern",
                    },
                    {
                        "ref": "s2",
                        "title": "Title 2",
                        "structured_summary": "Summary 2",
                        "issue_focus": "focus 2",
                        "activity_subject_key": "topic",
                        "affected_business_unit_key": "ops",
                        "responsible_business_unit_key": "ops",
                        "expected_new_pattern_label": "Other Pattern",
                    },
                ],
                "initial_patterns": [],
                "fake_responses": {
                    "s1": {
                        "canonical_label": "Pattern",
                    },
                    "s2": {
                        "canonical_label": "Other Pattern",
                    },
                },
                "must_link": [["s1", "s1"], ["s1", "s2"]],
                "must_not_link": [["s2", "s1"], ["s2", "missing"]],
            }
        ],
    }

    errors = validate_analytics_pattern_corpus(corpus)

    assert any("cannot self-reference" in error for error in errors)
    assert any("cannot be both must_link and must_not_link" in error for error in errors)
    assert any("references unknown signal" in error for error in errors)


def test_eval_fake_provider_uses_pattern_key_mapping_and_rolls_back():
    before_signals = Signal.objects.count()
    before_patterns = OperationalPattern.objects.count()

    report = evaluate_analytics_pattern_corpus(
        scenario_ids=["hotel_facilities"],
        provider_name="fake",
    )
    payload = analytics_pattern_corpus_eval_report_to_dict(report)

    assert Signal.objects.count() == before_signals
    assert OperationalPattern.objects.count() == before_patterns
    first = payload["scenarios"][0]["signals"][0]
    assert first["ref"] == "hf_01"
    assert first["assigned_pattern_key"] == "hvac_outage"
    assert payload["metrics"]["technical_success_rate"]["status"] == "pass"


def test_eval_report_json_contains_no_temporary_db_ids():
    report = evaluate_analytics_pattern_corpus(
        scenario_ids=["hotel_facilities"],
        provider_name="fake",
    )
    payload = analytics_pattern_corpus_eval_report_to_dict(report)

    serialized = json.dumps(payload, sort_keys=True)

    assert not UUID_RE.search(serialized)
    assert "pattern_id" not in serialized
    assert "organization_id" not in serialized
    assert "establishment_id" not in serialized


def test_eval_payloads_are_limited_to_allowed_structured_fields():
    report = evaluate_analytics_pattern_corpus(
        scenario_ids=["hotel_facilities"],
        provider_name="fake",
    )
    payload = analytics_pattern_corpus_eval_report_to_dict(report)
    serialized = json.dumps(payload, sort_keys=True)

    assert "raw_text" not in serialized
    assert "location_text" not in serialized
    assert "expected_action" not in serialized
    assert "routing_status" not in serialized


def test_eval_idempotence_only_scores_successful_first_pass():
    report = evaluate_analytics_pattern_corpus(
        scenario_ids=["hotel_facilities"],
        provider_name="fake",
    )
    scenario = report.scenario_results[0]

    assert scenario.idempotence == {
        "eligible_signal_count": 7,
        "passed_signal_count": 7,
        "status": "pass",
    }


def test_eval_compares_duplicate_guard_against_isolated_baseline():
    report = evaluate_analytics_pattern_corpus(
        scenario_ids=["hotel_facilities"],
        provider_name="fake",
    )
    scenario = report.scenario_results[0]
    comparison = scenario.duplicate_guard_comparison

    assert comparison["baseline"]["new_pattern_count"] == 2
    assert comparison["guard"]["new_pattern_count"] == 1
    assert comparison["guard"]["duplicate_guard_reuse_count"] == 1
    assert comparison["delta"]["false_merge_failing_count"] == 0
    hf_07 = next(result for result in scenario.signal_results if result.ref == "hf_07")
    assert hf_07.assigned_pattern_key == "water_leak"
    assert hf_07.duplicate_guard_decision == "reused"
    assert hf_07.duplicate_guard_reason_code == "same_phenomenon"


def test_eval_report_exposes_duplicate_guard_reason_code_distribution():
    report = evaluate_analytics_pattern_corpus(
        scenario_ids=["hotel_facilities"],
        provider_name="fake",
    )

    payload = analytics_pattern_corpus_eval_report_to_dict(report)
    hf_01 = next(
        signal
        for signal in payload["scenarios"][0]["signals"]
        if signal["ref"] == "hf_01"
    )
    hf_07 = next(
        signal
        for signal in payload["scenarios"][0]["signals"]
        if signal["ref"] == "hf_07"
    )

    assert hf_01["duplicate_guard_reason"] == "exact_semantic_alias"
    assert hf_01["duplicate_guard_reason_code"] is None
    assert hf_07["duplicate_guard_decision"] == "reused"
    assert hf_07["duplicate_guard_reason_code"] == "same_phenomenon"
    assert payload["scenarios"][0]["metrics"][
        "duplicate_guard_reason_code_distribution"
    ] == {"same_phenomenon": 1}
    assert payload["metrics"]["duplicate_guard_reason_code_distribution"] == {
        "same_phenomenon": 1
    }


def test_eval_case_id_selects_complete_scenario_without_orphan_pairs():
    report = evaluate_analytics_pattern_corpus(
        scenario_ids=["restaurant_stock"],
        provider_name="fake",
    )

    assert [scenario.scenario_id for scenario in report.scenario_results] == [
        "restaurant_stock"
    ]
    assert report.scenario_results[0].signal_order == (
        "rs_01",
        "rs_02",
        "rs_03",
        "rs_04",
        "rs_05",
        "rs_06",
    )
    assert selected_scenarios_have_no_orphan_pairs(["restaurant_stock"]) is True


def test_eval_metrics_support_not_applicable_denominators():
    corpus = get_analytics_pattern_scenario("hotel_facilities").copy()
    corpus["must_link"] = []
    corpus["must_not_link"] = []

    errors = validate_analytics_pattern_corpus(
        {
            "schema_version": CORPUS_SCHEMA_VERSION,
            "scenarios": [corpus],
        }
    )

    assert errors == []


def test_retry_runner_finalizes_retryable_errors_without_processing_assignment():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    provider = FakePatternClassifierProvider(
        exc=PatternClassifierTimeoutError("timeout"),
    )

    assignment = _run_classification_to_terminal_state(
        signal=signal,
        provider=provider,
        max_retries=0,
        retry_delay_seconds=0,
    )

    assert assignment is not None
    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED
    )
    assert assignment.last_error_code == "retry_exhausted"
    assert not SignalPatternAssignment.objects.filter(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
    ).exists()


def test_command_json_output_is_stable_and_non_mutating():
    before_signals = Signal.objects.count()
    before_patterns = OperationalPattern.objects.count()
    buffer = StringIO()

    call_command(
        "evaluate_analytics_pattern_corpus",
        case_id="hotel_facilities",
        provider="fake",
        json=True,
        stdout=buffer,
    )
    payload = json.loads(buffer.getvalue())

    assert Signal.objects.count() == before_signals
    assert OperationalPattern.objects.count() == before_patterns
    assert payload["scenarios"][0]["scenario_id"] == "hotel_facilities"
    assert not UUID_RE.search(json.dumps(payload, sort_keys=True))


def test_command_full_fake_corpus_passes_thresholds():
    buffer = StringIO()

    call_command(
        "evaluate_analytics_pattern_corpus",
        provider="fake",
        json=True,
        fail_on_threshold=True,
        stdout=buffer,
    )
    payload = json.loads(buffer.getvalue())

    assert payload["thresholds_passed"] is True
    assert payload["evaluation_status"] == "pass"
    assert payload["metrics"]["technical_success_rate"]["status"] == "pass"


def test_command_archive_writes_only_when_requested(tmp_path):
    buffer = StringIO()

    call_command(
        "evaluate_analytics_pattern_corpus",
        case_id="hotel_facilities",
        provider="fake",
        json=True,
        archive=True,
        archive_dir=str(tmp_path),
        stdout=buffer,
    )

    assert len(list(tmp_path.glob("analytics-pattern-eval-*.json"))) == 1


def test_command_fail_on_threshold_ignores_not_applicable(monkeypatch):
    from houston.analytics.pattern_corpus_eval import AnalyticsPatternCorpusEvalReport

    report = AnalyticsPatternCorpusEvalReport(
        provider="fake",
        provider_model="fake",
        classifier_version="analytics_pattern_v1:fake:fake",
        prompt_version="analytics_pattern_v1",
        schema_version="analytics_pattern_v1",
        timeout_seconds=None,
        max_retries=3,
        retry_delay_seconds=30,
        scenario_results=(
            CorpusScenarioResult(
                scenario_id="empty_metric_scenario",
                signal_order=(),
                signal_results=(),
            ),
        ),
        metrics={
            "false_merge_rate": {
                "passed": 0,
                "total": 0,
                "rate": None,
                "status": "not_applicable",
            },
            "acceptable_grouping_rate": {
                "passed": 0,
                "total": 0,
                "rate": None,
                "status": "not_applicable",
            },
            "technical_success_rate": {
                "passed": 0,
                "total": 0,
                "rate": None,
                "status": "not_applicable",
            },
        },
    )
    monkeypatch.setattr(
        "houston.analytics.management.commands.evaluate_analytics_pattern_corpus.evaluate_analytics_pattern_corpus",
        lambda **kwargs: report,
    )

    call_command(
        "evaluate_analytics_pattern_corpus",
        provider="fake",
        fail_on_threshold=True,
        stdout=StringIO(),
    )


def test_command_fail_on_threshold_raises_for_report_errors(monkeypatch):
    from houston.analytics.pattern_corpus_eval import AnalyticsPatternCorpusEvalReport

    report = AnalyticsPatternCorpusEvalReport(
        provider="fake",
        provider_model="fake",
        classifier_version="analytics_pattern_v1:fake:fake",
        prompt_version="analytics_pattern_v1",
        schema_version="analytics_pattern_v1",
        timeout_seconds=None,
        max_retries=3,
        retry_delay_seconds=30,
        scenario_results=(
            CorpusScenarioResult(
                scenario_id="failed_scenario",
                signal_order=(),
                signal_results=(),
            ),
        ),
        metrics={
            "false_merge_rate": {
                "passed": 0,
                "total": 0,
                "rate": None,
                "status": "not_applicable",
            },
            "acceptable_grouping_rate": {
                "passed": 0,
                "total": 0,
                "rate": None,
                "status": "not_applicable",
            },
            "technical_success_rate": {
                "passed": 0,
                "total": 0,
                "rate": None,
                "status": "not_applicable",
            },
        },
        errors=("scenario: ProgrammingError",),
    )
    monkeypatch.setattr(
        "houston.analytics.management.commands.evaluate_analytics_pattern_corpus.evaluate_analytics_pattern_corpus",
        lambda **kwargs: report,
    )
    buffer = StringIO()

    with pytest.raises(CommandError, match="eval failed"):
        call_command(
            "evaluate_analytics_pattern_corpus",
            provider="fake",
            json=True,
            fail_on_threshold=True,
            stdout=buffer,
        )
    payload = json.loads(buffer.getvalue())

    assert payload["thresholds_passed"] is True
    assert payload["evaluation_status"] == "fail"


def test_command_fail_on_threshold_raises_when_no_scenario_succeeded(monkeypatch):
    from houston.analytics.pattern_corpus_eval import AnalyticsPatternCorpusEvalReport

    report = AnalyticsPatternCorpusEvalReport(
        provider="fake",
        provider_model="fake",
        classifier_version="analytics_pattern_v1:fake:fake",
        prompt_version="analytics_pattern_v1",
        schema_version="analytics_pattern_v1",
        timeout_seconds=None,
        max_retries=3,
        retry_delay_seconds=30,
        scenario_results=(),
        metrics={
            "false_merge_rate": {
                "passed": 0,
                "total": 0,
                "rate": None,
                "status": "not_applicable",
            },
            "acceptable_grouping_rate": {
                "passed": 0,
                "total": 0,
                "rate": None,
                "status": "not_applicable",
            },
            "technical_success_rate": {
                "passed": 0,
                "total": 0,
                "rate": None,
                "status": "not_applicable",
            },
        },
    )
    monkeypatch.setattr(
        "houston.analytics.management.commands.evaluate_analytics_pattern_corpus.evaluate_analytics_pattern_corpus",
        lambda **kwargs: report,
    )
    buffer = StringIO()

    with pytest.raises(CommandError, match="eval failed"):
        call_command(
            "evaluate_analytics_pattern_corpus",
            provider="fake",
            json=True,
            fail_on_threshold=True,
            stdout=buffer,
        )
    payload = json.loads(buffer.getvalue())

    assert payload["thresholds_passed"] is True
    assert payload["evaluation_status"] == "fail"


def test_command_fail_on_threshold_raises_for_applicable_failure(monkeypatch):
    from houston.analytics.pattern_corpus_eval import AnalyticsPatternCorpusEvalReport

    report = AnalyticsPatternCorpusEvalReport(
        provider="fake",
        provider_model="fake",
        classifier_version="analytics_pattern_v1:fake:fake",
        prompt_version="analytics_pattern_v1",
        schema_version="analytics_pattern_v1",
        timeout_seconds=None,
        max_retries=3,
        retry_delay_seconds=30,
        scenario_results=(),
        metrics={
            "false_merge_rate": {
                "passed": 0,
                "total": 1,
                "rate": 0.0,
                "status": "pass",
            },
            "acceptable_grouping_rate": {
                "passed": 0,
                "total": 1,
                "rate": 0.0,
                "status": "fail",
            },
            "technical_success_rate": {
                "passed": 1,
                "total": 1,
                "rate": 1.0,
                "status": "pass",
            },
        },
    )
    monkeypatch.setattr(
        "houston.analytics.management.commands.evaluate_analytics_pattern_corpus.evaluate_analytics_pattern_corpus",
        lambda **kwargs: report,
    )

    with pytest.raises(CommandError, match="eval failed"):
        call_command(
            "evaluate_analytics_pattern_corpus",
            provider="fake",
            fail_on_threshold=True,
            stdout=StringIO(),
        )


def test_command_rejects_configured_provider_without_opt_in(monkeypatch):
    monkeypatch.delenv("HOUSTON_RUN_ANALYTICS_PATTERN_EVAL", raising=False)

    with pytest.raises(CommandError, match="opt-in"):
        call_command(
            "evaluate_analytics_pattern_corpus",
            provider="configured",
            stdout=StringIO(),
        )


def test_command_rejects_unknown_case_id():
    with pytest.raises(CommandError, match="Unknown Analytics pattern scenario"):
        call_command(
            "evaluate_analytics_pattern_corpus",
            case_id="missing",
            stdout=StringIO(),
        )


def test_expected_pattern_key_metrics_detect_unnecessary_new_pattern():
    membership = build_membership()
    pattern = create_operational_pattern(
        organization=membership.establishment.organization,
        label="Existing Pattern",
    )
    signal = create_signal_for_membership(membership)
    provider = FakePatternClassifierProvider(
        payload={
            "canonical_label": "Unexpected Fresh Pattern",
        }
    )

    assignment = _run_classification_to_terminal_state(
        signal=signal,
        provider=provider,
        max_retries=0,
        retry_delay_seconds=0,
    )

    assert pattern.label == "Existing Pattern"
    assert assignment is not None
    assert assignment.pattern is not None
    assert assignment.pattern.label == "Unexpected Fresh Pattern"
    assert assignment.assigned_at is not None
    assert assignment.assigned_at <= timezone.now()
