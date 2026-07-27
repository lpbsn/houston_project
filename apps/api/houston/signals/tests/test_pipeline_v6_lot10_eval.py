"""Lot 10 — V6 corpus eval (fake fixtures ≠ expected_v6) and fixture independence guards."""

from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from houston.signals.pipeline_v6_corpus_eval import (
    _assert_fixture_independent_of_expected_v6,
    evaluate_v6_case_fake,
    evaluate_v6_corpus_cases,
    get_fake_provider_fixture,
    list_v6_eval_case_ids,
    load_pipeline_v6_fake_provider_fixtures,
)
from houston.testing.pipeline_v6_metrics import LOT_ACCEPTANCE, METRIC_IDS

pytestmark = pytest.mark.django_db


def test_lot10_fake_fixtures_cover_lot10_case_ids():
    fixtures = load_pipeline_v6_fake_provider_fixtures()["fixtures"]
    for case_id in LOT_ACCEPTANCE["lot10"]["case_ids"]:
        assert case_id in fixtures, f"missing fake fixture for {case_id}"


def test_fake_fixtures_are_independent_of_expected_v6():
    for case_id in LOT_ACCEPTANCE["lot10"]["case_ids"]:
        fixture = get_fake_provider_fixture(case_id)
        _assert_fixture_independent_of_expected_v6(case_id, fixture)


@pytest.mark.parametrize("case_id", list(LOT_ACCEPTANCE["lot10"]["case_ids"]))
def test_lot10_v6_runtime_case_against_expected_v6(case_id: str):
    result = evaluate_v6_case_fake(case_id)
    assert result.passed, f"{case_id} failed: {result.diffs}"


def test_evaluate_v6_corpus_cases_lot10_all_pass():
    report = evaluate_v6_corpus_cases(
        case_ids=list_v6_eval_case_ids(lot="lot10"),
        provider_name="fake",
        archive=True,
    )
    assert report.errors == ()
    assert all(result.passed for result in report.case_results)
    assert report.archive_path
    for metric_id in METRIC_IDS:
        summary = report.metrics_summary[metric_id]
        if summary["status"] == "unscored":
            continue
        assert summary["status"] == "pass", metric_id


def test_evaluate_observation_pipeline_v6_command_json_fail_on_diff():
    out = StringIO()
    call_command(
        "evaluate_observation_pipeline_v6",
        "--case-id",
        "S15-12",
        "--json",
        "--fail-on-diff",
        "--no-archive",
        stdout=out,
    )
    payload = json.loads(out.getvalue())
    assert payload["all_passed"] is True
    assert payload["case_results"][0]["case_id"] == "S15-12"


def test_evaluate_observation_pipeline_v6_command_rejects_unknown_case():
    with pytest.raises(CommandError, match="Unknown S15 case"):
        call_command(
            "evaluate_observation_pipeline_v6",
            "--case-id",
            "S15-NOPE",
            "--no-archive",
        )


def test_evaluate_v6_corpus_cases_rejects_empty_case_ids():
    with pytest.raises(ValueError, match="No V6 eval cases selected"):
        evaluate_v6_corpus_cases(case_ids=[], provider_name="fake", archive=False)


def test_list_v6_eval_case_ids_rejects_unknown_lot():
    with pytest.raises(ValueError, match="Unknown V6 eval lot"):
        list_v6_eval_case_ids(lot="lot99")


def test_list_v6_eval_case_ids_rejects_known_lot_with_no_cases():
    with pytest.raises(ValueError, match="contains no executable corpus cases"):
        list_v6_eval_case_ids(lot="lot6")


def test_evaluate_observation_pipeline_v6_command_rejects_unknown_lot():
    with pytest.raises(CommandError, match="Unknown V6 eval lot"):
        call_command(
            "evaluate_observation_pipeline_v6",
            "--lot",
            "lot99",
            "--no-archive",
        )


def test_evaluate_v6_corpus_cases_none_defaults_to_lot10():
    report = evaluate_v6_corpus_cases(
        case_ids=None,
        provider_name="fake",
        archive=False,
    )
    expected = list_v6_eval_case_ids(lot="lot10")
    assert [r.case_id for r in report.case_results] == expected
    assert report.errors == ()
    assert all(result.passed for result in report.case_results)
