from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.aggregation_eval import (
    compute_issue_focus_eval_metrics,
    count_active_taxonomy_peers_with_different_focus,
    find_active_taxonomy_duplicate_groups,
)
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import apply_pipeline_output, normalize_issue_focus
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership
from houston.testing.taxonomy import create_v3_signal

pytestmark = pytest.mark.django_db


def test_find_active_taxonomy_duplicate_groups_detects_distinct_issue_focus():
    membership = build_membership()
    establishment = membership.establishment
    bar = create_business_unit(establishment=establishment, key="bar", label="Bar")
    stock = create_activity_subject(
        establishment=establishment,
        business_unit=bar,
        label="Stock",
    )
    create_v3_signal(
        establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=stock,
        title="Rupture pain",
        structured_summary="Plus de pain.",
        issue_focus="pain",
    )
    create_v3_signal(
        establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=stock,
        title="Rupture mojito",
        structured_summary="Plus de sirop mojito.",
        issue_focus="sirop mojito",
    )

    groups = find_active_taxonomy_duplicate_groups(establishment_id=establishment.id)

    assert len(groups) == 1
    assert groups[0].signal_count == 2
    assert groups[0].distinct_issue_focus_count == 2
    assert set(groups[0].issue_focuses) == {"pain", "sirop mojito"}


def test_count_active_taxonomy_peers_with_different_focus_excludes_same_focus():
    membership = build_membership()
    establishment = membership.establishment
    bar = create_business_unit(establishment=establishment, key="bar", label="Bar")
    stock = create_activity_subject(
        establishment=establishment,
        business_unit=bar,
        label="Stock",
    )
    create_v3_signal(
        establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=stock,
        title="Rupture pain",
        structured_summary="Plus de pain.",
        issue_focus="pain",
    )

    peer_count = count_active_taxonomy_peers_with_different_focus(
        establishment_id=establishment.id,
        affected_business_unit_id=bar.id,
        responsible_business_unit_id=bar.id,
        activity_subject_id=stock.id,
        operational_unit_id=None,
        issue_focus=normalize_issue_focus("pain blanc"),
    )

    assert peer_count == 1


def test_compute_issue_focus_eval_metrics_counts_hint_issue_focus_mismatch():
    membership = build_membership()
    establishment = membership.establishment
    bar = create_business_unit(establishment=establishment, key="bar", label="Bar")
    stock = create_activity_subject(
        establishment=establishment,
        business_unit=bar,
        label="Stock",
    )
    mojito_signal = create_v3_signal(
        establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=stock,
        title="Rupture mojito",
        structured_summary="Plus de sirop mojito.",
        issue_focus="sirop mojito",
    )
    observation = create_observation(membership=membership)

    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Rupture pain",
                    structured_summary="Plus de pain.",
                    issue_focus="pain",
                    affected_business_unit_key="bar",
                    responsible_business_unit_key="bar",
                    activity_subject_key="stock",
                    operational_unit_key=None,
                    location_text="Bar",
                    aggregate_into_signal_id=str(mojito_signal.id),
                )
            ],
        ),
    )

    metrics = compute_issue_focus_eval_metrics(establishment_id=establishment.id)

    assert metrics.hint_provided_candidate_count == 1
    assert metrics.hint_rejected_created_count == 1
    assert metrics.hint_issue_focus_mismatch_count == 1
    assert Signal.objects.filter(establishment=establishment).count() == 2
    assert CandidateSignal.objects.filter(
        outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
    ).exists()
