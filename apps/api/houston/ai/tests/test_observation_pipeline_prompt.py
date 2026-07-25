from __future__ import annotations

import json

import pytest

from houston.ai.observation_pipeline import (
    _OBSERVATION_PIPELINE_SYSTEM_PROMPT,
    _system_prompt,
    build_pipeline_input,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    MAX_CANDIDATES_PER_OBSERVATION,
)
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership


def test_prompt_version_is_v6_1_schema_remains_v6():
    assert AI_OBSERVATION_PIPELINE_PROMPT_VERSION == "ai_observation_pipeline_v6_1"
    assert AI_OBSERVATION_PIPELINE_SCHEMA_VERSION == "ai_observation_pipeline_v6"
    assert AI_OBSERVATION_PIPELINE_PROMPT_VERSION != AI_OBSERVATION_PIPELINE_SCHEMA_VERSION


def test_system_prompt_is_french_and_covers_dual_context():
    prompt = _system_prompt()
    assert prompt == _OBSERVATION_PIPELINE_SYSTEM_PROMPT
    assert "Tu es un analyste qualité opérationnel" in prompt
    assert "validated_text" in prompt
    assert "establishment_context" in prompt
    assert "routing_taxonomy" in prompt
    assert "active_business_units" in prompt
    assert "contexte structurel" in prompt
    assert "seules clés runtime valides" in prompt
    assert "author_scope_business_unit_routing_keys" in prompt
    assert f"max {MAX_CANDIDATES_PER_OBSERVATION}" in prompt
    assert "MÉTHODE — ANALYSE FAIT PAR FAIT" in prompt
    assert "QUAND ÉMETTRE 0 / 1 / N CANDIDATS" in prompt
    assert "ANTI-SUR-SEGMENTATION" in prompt
    assert "ISSUE_FOCUS" in prompt
    assert "canonical_object" in prompt
    assert "signal_kind" in prompt
    assert "informational" in prompt
    assert "information_type" in prompt
    assert "schedule_update" in prompt
    assert "Les plannings sont disponibles, venez les demander" in prompt
    assert "exactement 1" in prompt
    assert "aggregate_into_signal_id" not in prompt
    assert "active_signals_context" not in prompt
    assert "establishment_taxonomy" not in prompt
    assert "PRIORITÉ TRANSVERSALE" in prompt
    assert "issue_focus" in prompt
    assert "affected_business_unit_routing_key" in prompt
    assert "responsible_business_unit_routing_key" in prompt
    assert "activity_subject_routing_key" in prompt
    assert "business_unit_routing_key" in prompt
    assert "routing_key" in prompt
    assert "specific_name" in prompt
    assert "generic_label" in prompt
    assert "instance_description" in prompt
    assert "business_unit_key" not in prompt
    assert "normalized_name" not in prompt
    assert "location_text" in prompt
    assert "routing_status" in prompt  # listed as hors périmètre
    assert AI_OBSERVATION_PIPELINE_SCHEMA_VERSION in prompt


@pytest.mark.django_db
def test_build_pipeline_input_includes_prompt_version_not_system_text():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hotel",
        description="Chambres et couloirs.",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    observation = create_observation(membership=membership, text="Fuite d'eau chambre 204.")

    payload = build_pipeline_input(observation=observation)

    assert payload["prompt_version"] == AI_OBSERVATION_PIPELINE_PROMPT_VERSION
    assert payload["prompt_version"] == "ai_observation_pipeline_v6_1"
    assert payload["schema_version"] == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    assert payload["validated_text"] == observation.raw_text
    assert "establishment_context" in payload
    assert "routing_taxonomy" in payload
    assert "submission_context" in payload
    assert set(payload.keys()) == {
        "observation_id",
        "establishment_id",
        "validated_text",
        "submitted_at",
        "media_count",
        "establishment_context",
        "routing_taxonomy",
        "submission_context",
        "schema_version",
        "prompt_version",
    }
    assert "action_plan_context" not in payload
    assert "active_signals_context" not in payload
    assert "establishment_taxonomy" not in payload
    assert payload["media_count"] == 0
    assert payload["establishment_context"]["active_business_units"][0][
        "instance_description"
    ] == ("Chambres et couloirs.")

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "Tu es un analyste qualité opérationnel" not in serialized


@pytest.mark.django_db
def test_build_pipeline_input_omits_active_signals_context():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hotel",
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    observation = create_observation(membership=membership, text="Nouvelle fuite chambre 204.")

    from django.utils import timezone

    from houston.signals.models import Signal

    Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Fuite existante",
        structured_summary="Fuite déjà signalée au couloir nord.",
        issue_focus="fuite couloir nord",
        routing_status=Signal.RoutingStatus.RESOLVED,
        last_activity_at=timezone.now(),
    )

    payload = build_pipeline_input(observation=observation)

    assert "active_signals_context" not in payload
    assert "routing_taxonomy" in payload
