"""Apply-side: informational candidates create Signals (not filtered by signal_kind)."""

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
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def test_apply_informational_candidate_creates_signal():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    organisation = create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Organisation",
    )
    observation = create_observation(
        membership=membership,
        text="Les plannings sont disponibles, venez les demander",
    )

    result = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Plannings disponibles",
                    structured_summary="Les plannings sont disponibles auprès de l'équipe.",
                    issue_focus="planning disponible",
                    canonical_object="planning",
                    signal_kind="informational",
                    expected_action="inform",
                    information_type="schedule_update",
                    affected_business_unit_routing_key=hotel.routing_key,
                    responsible_business_unit_routing_key=hotel.routing_key,
                    activity_subject_routing_key=organisation.routing_key,
                    operational_unit_key=None,
                    location_text=None,
                )
            ],
        ),
    )

    assert result.outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert result.created_count == 1
    signal = Signal.objects.get(establishment=membership.establishment)
    assert signal.expected_action == "inform"
    assert signal.issue_focus == "planning disponible"
    candidate = CandidateSignal.objects.get(observation=observation)
    assert candidate.signal_kind == "informational"
    assert candidate.information_type == "schedule_update"
    assert candidate.canonical_object == "planning"
    assert candidate.outcome == CandidateSignal.Outcome.CREATED_SIGNAL
