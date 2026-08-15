from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from houston.analytics.pattern_architecture_d_spike import (
    SemanticRetrievalShortlist,
    choose_d_shortlist_k,
    evaluate_architecture_d_k_selection,
    evaluate_architecture_d_spike,
)
from houston.analytics.pattern_retrieval_spike import (
    FakeHashEmbeddingProvider,
    PROJECTION_PHENOMENON_V1,
)

pytestmark = pytest.mark.django_db


def test_choose_d_shortlist_k_prefers_smallest_satisfying():
    assert (
        choose_d_shortlist_k(
            {
                3: {"rate": 1.0, "passed": 49, "total": 49},
                5: {"rate": 1.0, "passed": 49, "total": 49},
            }
        )
        == 3
    )
    assert (
        choose_d_shortlist_k(
            {
                3: {"rate": 0.9, "passed": 44, "total": 49},
                5: {"rate": 1.0, "passed": 49, "total": 49},
            }
        )
        == 5
    )
    assert choose_d_shortlist_k({3: {"rate": 0.5}, 5: {"rate": 0.7}}) is None


def test_semantic_shortlist_uses_phenomenon_projection_not_canonical_label_alone():
    provider = FakeHashEmbeddingProvider()
    shortlist = SemanticRetrievalShortlist(
        embedding_provider=provider,
        k=3,
        projection=PROJECTION_PHENOMENON_V1,
    )
    from django.utils import timezone

    from houston.testing.factories import build_membership
    from houston.signals.models import Signal
    from houston.testing.taxonomy import create_activity_subject, create_business_unit

    membership = build_membership()
    bu = create_business_unit(
        establishment=membership.establishment, key="rooms", label="Rooms"
    )
    activity = create_activity_subject(
        establishment=membership.establishment,
        business_unit=bu,
        label="Climate",
    )
    now = timezone.now()
    signal = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=bu,
        responsible_business_unit=bu,
        activity_subject=activity,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title="Room climate not cooling",
        structured_summary="The guest room climate unit no longer cools the room.",
        issue_focus="climate unit not cooling",
        last_activity_at=now,
    )
    result = shortlist(
        signal=signal,
        canonical_label="Totally Different Canonical Label XYZ",
    )
    assert result == []
    assert len(shortlist.calls) == 1
    call = shortlist.calls[0]
    assert "Room climate not cooling" in call.projection_text
    assert "climate unit not cooling" in call.projection_text
    assert "Climate" in call.projection_text
    assert "Totally Different Canonical Label XYZ" not in call.projection_text


def test_architecture_d_fake_k_selection_and_one_scenario_run():
    k_report = evaluate_architecture_d_k_selection(embedding_provider_name="fake")
    assert k_report["status"] in {"pass", "fail"}
    # Fake hash embeddings are weak; allow explicit K for plumbing test.
    payload = evaluate_architecture_d_spike(
        scenario_ids=["safety_public_areas"],
        runs=1,
        k=3,
        embedding_provider_name="fake",
        classifier_provider_name="fake",
        skip_k_selection=True,
    )
    assert payload["architecture"] == "D"
    assert payload["frozen_k"] == 3
    assert payload["shortlist_strategy"] == "semantic_retrieval_phenomenon_v1"
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["metrics"]["technical_success_rate"]["total"] == 6


def test_management_command_fake_json():
    stdout = StringIO()
    call_command(
        "evaluate_analytics_pattern_architecture_d_spike",
        "--embedding-provider",
        "fake",
        "--classifier-provider",
        "fake",
        "--runs",
        "1",
        "--k",
        "3",
        "--case-id",
        "safety_public_areas",
        "--json",
        stdout=stdout,
    )
    payload = json.loads(stdout.getvalue())
    assert payload["frozen_k"] == 3
    assert payload["runs"][0]["metrics"]["technical_success_rate"]["total"] == 6


def test_management_command_openai_requires_opt_in(settings):
    settings.OPENAI_API_KEY = "sk-test"
    with pytest.raises(CommandError, match="opt-in"):
        call_command(
            "evaluate_analytics_pattern_architecture_d_spike",
            "--phase",
            "k-selection",
            "--embedding-provider",
            "openai",
        )
