from __future__ import annotations

import pytest

from houston.analytics.analytics_capacity_eval import (
    ANALYTICS_CAPACITY_SCHEMA_VERSION,
    CapacityProfile,
    benchmark_analytics_capacity,
    resolve_capacity_profile,
    seed_analytics_capacity_dataset,
)
from houston.analytics.classifier import OpenAIPatternClassifierProvider
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.signals.models import Signal

pytestmark = pytest.mark.django_db(transaction=True)


def test_capacity_profile_dimensions_can_be_overridden_independently():
    profile = resolve_capacity_profile(
        "smoke",
        establishments=7,
        signals=800,
        patterns=90,
        warmups=0,
        timing_iterations=3,
    )

    assert profile.establishments == 7
    assert profile.signals == 800
    assert profile.patterns == 90
    assert profile.warmups == 0
    assert profile.timing_iterations == 3


def test_small_capacity_dataset_and_benchmark_do_not_call_openai(monkeypatch, settings):
    settings.DEBUG = True

    def unexpected_openai_call(*args, **kwargs):
        raise AssertionError("capacity benchmark must not call OpenAI")

    monkeypatch.setattr(
        OpenAIPatternClassifierProvider,
        "classify",
        unexpected_openai_call,
    )
    profile = CapacityProfile(
        name="test",
        establishments=2,
        signals=120,
        patterns=10,
        shortlist_cardinalities=(),
        warmups=0,
        timing_iterations=2,
    )

    dataset = seed_analytics_capacity_dataset(
        profile,
        seed=350,
        include_shortlist_cases=False,
    )
    report = benchmark_analytics_capacity(dataset, profile, explain=False)

    assert Signal.objects.filter(
        establishment__organization_id=dataset.organization_id
    ).count() == 120
    assert OperationalPattern.objects.filter(
        organization_id=dataset.organization_id
    ).count() == 10
    assert SignalPatternAssignment.objects.filter(
        signal__establishment__organization_id=dataset.organization_id
    ).count() == dataset.assignment_count
    assert report["schema_version"] == ANALYTICS_CAPACITY_SCHEMA_VERSION
    assert report["configuration"]["timing_isolated_from_diagnostics"] is True
    assert {row["name"] for row in report["read_scenarios"]} >= {
        "dashboard_7d",
        "dashboard_30d",
        "dashboard_90d",
        "patterns_30d_filtered",
        "pattern_detail_30d",
        "pattern_drilldown_30d_page1",
    }
