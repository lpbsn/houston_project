from __future__ import annotations

from django.utils import timezone

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.observations.models import Observation, ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import Signal
from houston.testing.taxonomy import (
    RESTAURANT_MODULE_KEY,
    RestaurantV3Taxonomy,
)

GOLDEN_OBSERVATION_TEXT = (
    "La lumière clignote à l'entrée de restaurant. Il n'y a plus de sirop mojito au bar."
)


def golden_two_candidate_pipeline_output(
    *,
    taxonomy: RestaurantV3Taxonomy,
) -> ObservationPipelineOutput:
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assert taxonomy.stock_subject is not None
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière clignote à l'entrée du restaurant",
                structured_summary=(
                    "Éclairage instable signalé à l'entrée du restaurant, "
                    "intervention maintenance requise."
                ),
                issue_focus="lumière entrée restaurant",
                affected_business_unit_key=RESTAURANT_MODULE_KEY,
                responsible_business_unit_key="maintenance",
                activity_subject_key=taxonomy.lighting_subject.normalized_name,
                operational_unit_key=None,
                location_text="Entrée restaurant",
                aggregate_into_signal_id=None,
            ),
            PipelineCandidateOutput(
                title="Rupture de sirop mojito au bar",
                structured_summary=(
                    "Plus de sirop mojito disponible au bar, réassort stock nécessaire."
                ),
                issue_focus="sirop mojito",
                affected_business_unit_key="bar",
                responsible_business_unit_key="bar",
                activity_subject_key=taxonomy.stock_subject.normalized_name,
                operational_unit_key=None,
                location_text="Bar",
                aggregate_into_signal_id=None,
            ),
        ],
    )


def classify_golden_restaurant_signals(
    *,
    establishment: Establishment,
    business_units,
) -> None:
    lighting = Signal.objects.filter(
        establishment=establishment,
        title__icontains="lumière",
    ).first()
    if lighting is not None:
        lighting.affected_business_unit = business_units.restaurant
        lighting.responsible_business_unit = business_units.maintenance
        lighting.save(
            update_fields=[
                "affected_business_unit",
                "responsible_business_unit",
                "updated_at",
            ]
        )

    syrup = Signal.objects.filter(
        establishment=establishment,
        title__icontains="mojito",
    ).first()
    if syrup is not None:
        syrup.affected_business_unit = business_units.bar
        syrup.responsible_business_unit = business_units.bar
        syrup.save(
            update_fields=[
                "affected_business_unit",
                "responsible_business_unit",
                "updated_at",
            ]
        )


def create_observation(*, membership: EstablishmentMembership, text: str = "A" * 20) -> Observation:
    now = timezone.now()
    observation = Observation.objects.create(
        establishment=membership.establishment,
        submitted_by_membership=membership,
        raw_text=text,
        submitted_at=now,
    )
    ObservationProcessing.objects.create(
        observation=observation,
        status=ObservationProcessing.Status.QUEUED,
        queued_at=now,
    )
    return observation


def signal_feed_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/signal-feed/"


def signal_detail_url(establishment_id, signal_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/signals/{signal_id}/"
