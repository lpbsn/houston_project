from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from houston.analytics.pattern_resolver_spike import (
    FakeResolverProvider,
    parse_resolver_decision,
    evaluate_analytics_pattern_resolver_spike,
)

pytestmark = pytest.mark.django_db


def test_parse_resolver_decision_accepts_local_refs_only():
    reuse = parse_resolver_decision(
        {
            "result_type": "reuse_candidate",
            "candidate_ref": "c1",
            "canonical_label": None,
        },
        allowed_refs={"c1"},
    )
    assert reuse.result_type == "reuse_candidate"
    assert reuse.candidate_ref == "c1"

    create = parse_resolver_decision(
        {
            "result_type": "create_pattern",
            "candidate_ref": None,
            "canonical_label": "Guest amenity refill gap",
        },
        allowed_refs={"c1"},
    )
    assert create.canonical_label == "Guest amenity refill gap"

    with pytest.raises(Exception, match="outside shortlist"):
        parse_resolver_decision(
            {
                "result_type": "reuse_candidate",
                "candidate_ref": "c9",
                "canonical_label": None,
            },
            allowed_refs={"c1"},
        )


def test_phase1_fake_providers_run_single_scenario():
    payload = evaluate_analytics_pattern_resolver_spike(
        scenario_ids=["hotel_facilities"],
        runs=1,
        k=1,
        embedding_provider_name="fake",
        resolver_provider_name="fake",
    )
    assert payload["frozen_from_phase0"]["k"] == 1
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["metrics"]["technical_success_rate"]["total"] == 7
    assert "architecture_gate" in payload
    assert "product_gate" in payload


def test_management_command_fake_json():
    stdout = StringIO()
    call_command(
        "evaluate_analytics_pattern_resolver_spike",
        "--embedding-provider",
        "fake",
        "--resolver-provider",
        "fake",
        "--runs",
        "1",
        "--k",
        "1",
        "--case-id",
        "safety_public_areas",
        "--json",
        stdout=stdout,
    )
    payload = json.loads(stdout.getvalue())
    assert payload["runs"][0]["metrics"]["technical_success_rate"]["total"] == 6


def test_management_command_openai_requires_opt_in(settings):
    settings.OPENAI_API_KEY = "sk-test"
    with pytest.raises(CommandError, match="opt-in"):
        call_command(
            "evaluate_analytics_pattern_resolver_spike",
            "--embedding-provider",
            "openai",
            "--resolver-provider",
            "openai",
            "--runs",
            "1",
        )
