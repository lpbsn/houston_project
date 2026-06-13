from __future__ import annotations

import logging

import pytest
from django.utils import timezone

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

pytestmark = [pytest.mark.django_db, pytest.mark.slow]


def _setup_bar_taxonomy(establishment):
    bar = create_business_unit(
        establishment=establishment,
        key="bar",
        label="Bar",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=bar,
        label="Stock",
    )
    return bar


def _legacy_signal(*, establishment, bar, subject, title="Rupture sirop mojito"):
    return Signal.objects.create(
        establishment=establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=subject,
        title=title,
        structured_summary="Sirop mojito manquant au bar.",
        issue_focus="",
        last_activity_at=timezone.now(),
    )


def _mojito_candidate(*, aggregate_into_signal_id=None):
    return PipelineCandidateOutput(
        title="Toujours plus de sirop mojito au bar",
        structured_summary="La rupture de sirop mojito au bar persiste.",
        issue_focus="sirop mojito",
        affected_business_unit_key="bar",
        responsible_business_unit_key="bar",
        activity_subject_key="stock",
        operational_unit_key=None,
        location_text="Bar",
        aggregate_into_signal_id=aggregate_into_signal_id,
    )


def test_legacy_empty_issue_focus_aggregates_v4_candidate():
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    legacy = _legacy_signal(
        establishment=membership.establishment,
        bar=bar,
        subject=subject,
    )
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[_mojito_candidate()],
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNAL_AGGREGATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    row = CandidateSignal.objects.get(observation=observation)
    assert row.outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
    assert row.result_signal_id == legacy.id


def test_legacy_aggregate_enriches_signal_issue_focus():
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    legacy = _legacy_signal(
        establishment=membership.establishment,
        bar=bar,
        subject=subject,
    )
    observation = create_observation(membership=membership)

    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[_mojito_candidate()],
        ),
    )

    legacy.refresh_from_db()
    assert legacy.issue_focus == "sirop mojito"


def test_legacy_empty_issue_focus_hint_mismatch_still_aggregates_via_fallback(caplog):
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    legacy = _legacy_signal(
        establishment=membership.establishment,
        bar=bar,
        subject=subject,
    )
    observation = create_observation(membership=membership)

    with caplog.at_level(logging.INFO, logger="houston.signals.services"):
        apply_pipeline_output(
            observation=observation,
            output=ObservationPipelineOutput(
                schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                candidates=[_mojito_candidate(aggregate_into_signal_id=str(legacy.id))],
            ),
        )

    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    row = CandidateSignal.objects.get(observation=observation)
    assert row.outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
    assert row.result_signal_id == legacy.id

    records = [
        r
        for r in caplog.records
        if getattr(r, "event", None) == "observation_pipeline_candidate_applied"
    ]
    assert len(records) == 1
    assert records[0].hint_rejected_reason == "hint_issue_focus_mismatch"
    assert records[0].aggregation_match_mode == "legacy_fallback"


def test_aggregation_match_mode_exact_on_same_focus(caplog):
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    existing = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=subject,
        title="Rupture sirop mojito",
        structured_summary="Sirop mojito manquant.",
        issue_focus="sirop mojito",
        last_activity_at=timezone.now(),
    )
    observation = create_observation(membership=membership)

    with caplog.at_level(logging.INFO, logger="houston.signals.services"):
        apply_pipeline_output(
            observation=observation,
            output=ObservationPipelineOutput(
                schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                candidates=[_mojito_candidate()],
            ),
        )

    records = [
        r
        for r in caplog.records
        if getattr(r, "event", None) == "observation_pipeline_candidate_applied"
    ]
    assert len(records) == 1
    assert records[0].aggregation_match_mode == "exact"
    row = CandidateSignal.objects.get(observation=observation)
    assert row.result_signal_id == existing.id


def test_different_issue_focus_does_not_aggregate():
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=subject,
        title="Rupture sirop mojito",
        structured_summary="Sirop mojito manquant.",
        issue_focus="sirop mojito",
        last_activity_at=timezone.now(),
    )
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Rupture de pain",
                    structured_summary="Plus de pain disponible.",
                    issue_focus="pain",
                    affected_business_unit_key="bar",
                    responsible_business_unit_key="bar",
                    activity_subject_key="stock",
                    operational_unit_key=None,
                    location_text=None,
                    aggregate_into_signal_id=None,
                )
            ],
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 2


def test_same_issue_focus_still_aggregates():
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    existing = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=subject,
        title="Rupture sirop mojito",
        structured_summary="Sirop mojito manquant.",
        issue_focus="sirop mojito",
        last_activity_at=timezone.now(),
    )
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[_mojito_candidate()],
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNAL_AGGREGATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    row = CandidateSignal.objects.get(observation=observation)
    assert row.result_signal_id == existing.id


def test_multiple_legacy_signals_same_taxonomy_creates_new():
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    _legacy_signal(
        establishment=membership.establishment,
        bar=bar,
        subject=subject,
        title="Legacy signal A",
    )
    _legacy_signal(
        establishment=membership.establishment,
        bar=bar,
        subject=subject,
        title="Legacy signal B",
    )
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[_mojito_candidate()],
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 3


def test_legacy_enriched_then_different_focus_creates_new():
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    legacy = _legacy_signal(
        establishment=membership.establishment,
        bar=bar,
        subject=subject,
        title="Rupture de pain",
    )
    first_observation = create_observation(membership=membership)
    apply_pipeline_output(
        observation=first_observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Rupture de pain",
                    structured_summary="Plus de pain disponible.",
                    issue_focus="pain",
                    affected_business_unit_key="bar",
                    responsible_business_unit_key="bar",
                    activity_subject_key="stock",
                    operational_unit_key=None,
                    location_text=None,
                    aggregate_into_signal_id=None,
                )
            ],
        ),
    )
    legacy.refresh_from_db()
    assert legacy.issue_focus == "pain"

    second_observation = create_observation(membership=membership)
    outcome = apply_pipeline_output(
        observation=second_observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Rupture de pain blanc",
                    structured_summary="Le pain blanc est en rupture.",
                    issue_focus="pain blanc",
                    affected_business_unit_key="bar",
                    responsible_business_unit_key="bar",
                    activity_subject_key="stock",
                    operational_unit_key=None,
                    location_text=None,
                    aggregate_into_signal_id=None,
                )
            ],
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 2


def test_candidate_signal_persists_issue_focus():
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    _legacy_signal(
        establishment=membership.establishment,
        bar=bar,
        subject=subject,
    )
    observation = create_observation(membership=membership)

    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[_mojito_candidate()],
        ),
    )

    row = CandidateSignal.objects.get(observation=observation)
    assert row.issue_focus == "sirop mojito"
    assert row.outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
