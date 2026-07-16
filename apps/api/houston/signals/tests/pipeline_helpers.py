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


def mojito_candidate(*, bar, subject, aggregate_into_signal_id=None):
    return PipelineCandidateOutput(
        title="Toujours plus de sirop mojito au bar",
        structured_summary="La rupture de sirop mojito au bar persiste.",
        issue_focus="sirop mojito",
        affected_business_unit_routing_key=bar.routing_key,
        responsible_business_unit_routing_key=bar.routing_key,
        activity_subject_routing_key=subject.routing_key,
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
    affected_routing_key: str,
    responsible_routing_key: str | None = None,
    subject_routing_key: str,
):
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Clim en panne",
                structured_summary="La climatisation ne fonctionne plus.",
                issue_focus="climatisation",
                affected_business_unit_routing_key=affected_routing_key,
                responsible_business_unit_routing_key=(
                    responsible_routing_key or affected_routing_key
                ),
                activity_subject_routing_key=subject_routing_key,
                operational_unit_key=None,
                location_text=None,
                aggregate_into_signal_id=None,
            )
        ],
    )


def fake_provider_payload(
    *,
    affected_routing_key: str,
    responsible_routing_key: str | None = None,
    subject_routing_key: str,
    issue_focus: str = "climatisation",
):
    return {
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "candidates": [
            {
                "title": "Clim en panne",
                "structured_summary": "La climatisation ne fonctionne plus.",
                "issue_focus": issue_focus,
                "affected_business_unit_routing_key": affected_routing_key,
                "responsible_business_unit_routing_key": (
                    responsible_routing_key or affected_routing_key
                ),
                "activity_subject_routing_key": subject_routing_key,
                "operational_unit_key": None,
                "location_text": None,
                "aggregate_into_signal_id": None,
            }
        ],
    }
