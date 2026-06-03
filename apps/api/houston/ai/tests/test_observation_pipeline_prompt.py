from __future__ import annotations

import json

import pytest

from houston.ai.observation_pipeline import (
    _OBSERVATION_PIPELINE_SYSTEM_PROMPT,
    _system_prompt,
    build_pipeline_input,
)
from houston.establishments.tests.test_permissions import build_membership
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    MAX_CANDIDATES_PER_OBSERVATION,
)
from houston.signals.tests.conftest import create_observation, create_taxonomy


def test_prompt_version_constant_is_v2():
    assert AI_OBSERVATION_PIPELINE_PROMPT_VERSION == "ai_observation_pipeline_v2"


def test_system_prompt_is_french_and_covers_rules():
    prompt = _system_prompt()
    assert prompt == _OBSERVATION_PIPELINE_SYSTEM_PROMPT
    assert "Tu es un analyste qualité opérationnel" in prompt
    assert "validated_text" in prompt
    assert "taxonomy" in prompt
    assert f"max {MAX_CANDIDATES_PER_OBSERVATION}" in prompt
    assert "SEGMENTATION" in prompt
    assert "SPLITTING RULES" in prompt
    assert "mojito syrup" in prompt
    assert "flickering at the restaurant entrance" in prompt
    assert "HORS PÉRIMÈTRE" in prompt
    assert "detected_domains" in prompt
    assert "candidates" in prompt
    assert AI_OBSERVATION_PIPELINE_SCHEMA_VERSION in prompt
    assert "operational_module_key" in prompt
    assert "location_text" in prompt
    assert "aggregate_into_signal_id" in prompt
    assert "active_signals_context" in prompt


def test_system_prompt_does_not_repeat_v1_english_opening():
    prompt = _system_prompt()
    assert "You structure operational" not in prompt


@pytest.mark.django_db
def test_build_pipeline_input_includes_prompt_version_not_system_text():
    membership = build_membership()
    create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text="Fuite d'eau chambre 204.")

    payload = build_pipeline_input(observation=observation)

    assert payload["prompt_version"] == AI_OBSERVATION_PIPELINE_PROMPT_VERSION
    assert payload["schema_version"] == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    assert payload["validated_text"] == observation.raw_text
    assert "taxonomy" in payload
    assert set(payload.keys()) == {
        "observation_id",
        "establishment_id",
        "validated_text",
        "submitted_at",
        "media_count",
        "taxonomy",
        "active_signals_context",
        "schema_version",
        "prompt_version",
    }
    assert payload["active_signals_context"] == []

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "Tu es un analyste qualité opérationnel" not in serialized
    assert "MISSION" not in serialized
    assert "HORS PÉRIMÈTRE" not in serialized


@pytest.mark.django_db
def test_build_pipeline_input_includes_active_signals_context():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text="Nouvelle fuite chambre 204.")

    from django.utils import timezone

    from houston.signals.models import Signal

    signal = Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        title="Fuite existante",
        structured_summary="Fuite déjà signalée au couloir nord.",
        last_activity_at=timezone.now(),
    )

    payload = build_pipeline_input(observation=observation)

    assert len(payload["active_signals_context"]) == 1
    entry = payload["active_signals_context"][0]
    assert entry["signal_id"] == str(signal.id)
    assert entry["status"] == Signal.Status.OPEN
    assert entry["title"] == "Fuite existante"
    assert entry["operational_module_key"] == module.key
    assert entry["operational_domain_key"] == domain.key
    assert entry["operational_subject_key"] == subject.key
    assert entry["operational_unit_key"] is None
