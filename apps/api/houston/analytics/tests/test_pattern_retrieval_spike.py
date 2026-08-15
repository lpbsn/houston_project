from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from houston.analytics.pattern_retrieval_spike import (
    K_VALUES,
    PROJECTION_PHENOMENON_V1,
    FakeHashEmbeddingProvider,
    build_signal_projection_text,
    choose_smallest_satisfying_k,
    cosine_similarity,
    evaluate_analytics_pattern_retrieval_spike,
)
from houston.testing.analytics_pattern_corpus import get_analytics_pattern_scenario

pytestmark = pytest.mark.django_db


def test_build_signal_projection_text_is_phenomenon_minimal():
    scenario = get_analytics_pattern_scenario("hotel_facilities")
    signal = next(item for item in scenario["signals"] if item["ref"] == "hf_01")

    text = build_signal_projection_text(
        signal=signal,
        scenario=scenario,
        projection=PROJECTION_PHENOMENON_V1,
    )

    assert "Room climate not cooling" in text
    assert "climate unit not cooling" in text
    assert "Climate equipment" in text
    assert "Floor 5" not in text
    assert "Rooms" not in text
    assert "Maintenance" not in text


def test_cosine_similarity_and_k_selection():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    recommended = choose_smallest_satisfying_k(
        {
            1: {"rate": 0.5},
            3: {"rate": 0.9},
            5: {"rate": 0.99},
            8: {"rate": 1.0},
        }
    )
    assert recommended == 5
    assert choose_smallest_satisfying_k({k: {"rate": 0.5} for k in K_VALUES}) is None


def test_fake_hash_provider_is_deterministic():
    provider = FakeHashEmbeddingProvider()
    first = provider.embed_texts(["guest room climate"])
    second = provider.embed_texts(["guest room climate"])
    assert first == second
    assert len(first[0]) == provider.dimensions


def test_phase0_fake_provider_runs_and_emits_oracle_metric_shape():
    payload = evaluate_analytics_pattern_retrieval_spike(
        provider_name="fake",
        also_run_ablations=False,
    )

    assert payload["metric_name"] == "oracle_retrieval_recall"
    assert payload["schema_version"] == "analytics_pattern_retrieval_spike_v1"
    assert "phase0_status" in payload
    assert "recommended_k" in payload
    primary = payload["reports"][0]
    assert primary["projection"] == PROJECTION_PHENOMENON_V1
    for k in K_VALUES:
        assert str(k) in primary["recall"]
        assert "passed" in primary["recall"][str(k)]
        assert "total" in primary["recall"][str(k)]
    # Oracle creates are unscored; scored decisions must be > 0.
    assert primary["recall"]["8"]["total"] > 0
    # Sibling create pairs must leave at least one scored attach_oracle_sibling.
    assert any(
        decision["decision_kind"] == "attach_oracle_sibling"
        for decision in primary["decisions"]
    )
    assert any(
        decision["decision_kind"] == "oracle_create" and not decision["scored"]
        for decision in primary["decisions"]
    )


def test_management_command_fake_json():
    stdout = StringIO()
    call_command(
        "evaluate_analytics_pattern_retrieval_spike",
        "--provider",
        "fake",
        "--json",
        "--case-id",
        "hotel_facilities",
        stdout=stdout,
    )
    payload = json.loads(stdout.getvalue())
    assert payload["reports"][0]["by_scenario"]["hotel_facilities"]["8"]["total"] > 0


def test_management_command_openai_requires_opt_in(settings):
    settings.OPENAI_API_KEY = "sk-test"
    with pytest.raises(CommandError, match="opt-in"):
        call_command(
            "evaluate_analytics_pattern_retrieval_spike",
            "--provider",
            "openai",
        )
