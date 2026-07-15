from __future__ import annotations

from django.utils import timezone

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import Signal


def setup_bar_taxonomy(establishment):
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


def legacy_signal(*, establishment, bar, subject, title="Rupture sirop mojito"):
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


def mojito_candidate(*, aggregate_into_signal_id=None):
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


def setup_hotel_taxonomy(establishment):
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    return hotel


def output_with_candidate(
    *,
    affected_key: str = "hotel",
    responsible_key: str = "hotel",
    subject_key: str = "maintenance",
):
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Clim en panne",
                structured_summary="La climatisation ne fonctionne plus.",
                issue_focus="climatisation",
                affected_business_unit_key=affected_key,
                responsible_business_unit_key=responsible_key,
                activity_subject_key=subject_key,
                operational_unit_key=None,
                location_text=None,
                aggregate_into_signal_id=None,
            )
        ],
    )


def fake_provider_payload(*, issue_focus: str = "climatisation"):
    return {
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "candidates": [
            {
                "title": "Clim en panne",
                "structured_summary": "La climatisation ne fonctionne plus.",
                "issue_focus": issue_focus,
                "affected_business_unit_key": "hotel",
                "responsible_business_unit_key": "hotel",
                "activity_subject_key": "maintenance",
                "operational_unit_key": None,
                "location_text": None,
                "aggregate_into_signal_id": None,
            }
        ],
    }
