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


def test_prompt_version_constant_is_v4():
    assert AI_OBSERVATION_PIPELINE_PROMPT_VERSION == "ai_observation_pipeline_v4"


def test_system_prompt_is_french_and_covers_v4_rules():
    prompt = _system_prompt()
    assert prompt == _OBSERVATION_PIPELINE_SYSTEM_PROMPT
    assert "Tu es un analyste qualité opérationnel" in prompt
    assert "validated_text" in prompt
    assert "establishment_taxonomy" in prompt
    assert f"max {MAX_CANDIDATES_PER_OBSERVATION}" in prompt
    assert "MÉTHODE — ANALYSE PROBLÈME PAR PROBLÈME" in prompt
    assert "ISSUE_FOCUS" in prompt
    assert "DÉSAMBIGUÏSATION" in prompt
    assert "Anti-biais active_signals_context" in prompt
    assert "PRIORITÉ TRANSVERSALE" in prompt
    assert "issue_focus" in prompt
    assert "affected_business_unit_key" in prompt
    assert "responsible_business_unit_key" in prompt
    assert "activity_subject_key" in prompt
    assert "location_text" in prompt
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
    assert payload["schema_version"] == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    assert payload["validated_text"] == observation.raw_text
    assert "establishment_taxonomy" in payload
    assert set(payload.keys()) == {
        "observation_id",
        "establishment_id",
        "validated_text",
        "submitted_at",
        "media_count",
        "establishment_taxonomy",
        "active_signals_context",
        "schema_version",
        "prompt_version",
    }
    assert "checklist_context" not in payload
    assert payload["active_signals_context"] == []
    assert payload["establishment_taxonomy"]["business_units"][0]["description"] == (
        "Chambres et couloirs."
    )

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "Tu es un analyste qualité opérationnel" not in serialized


@pytest.mark.django_db
def test_build_pipeline_input_includes_active_signals_context_with_issue_focus():
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

    signal = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Fuite existante",
        structured_summary="Fuite déjà signalée au couloir nord.",
        issue_focus="fuite couloir nord",
        last_activity_at=timezone.now(),
    )

    payload = build_pipeline_input(observation=observation)

    assert len(payload["active_signals_context"]) == 1
    entry = payload["active_signals_context"][0]
    assert entry["signal_id"] == str(signal.id)
    assert entry["status"] == Signal.Status.OPEN
    assert entry["title"] == "Fuite existante"
    assert entry["affected_business_unit_key"] == "hotel"
    assert entry["responsible_business_unit_key"] == "hotel"
    assert entry["activity_subject_key"] == subject.normalized_name
    assert entry["operational_unit_key"] is None
    assert entry["issue_focus"] == "fuite couloir nord"


@pytest.mark.django_db
def test_build_pipeline_input_includes_checklist_context_for_checklist_task_origin():
    from django.utils import timezone

    from houston.checklists.constants import EXECUTION_SOURCE_TEMPLATE
    from houston.checklists.models import (
        ChecklistExecution,
        ChecklistTaskExecution,
        ChecklistTemplate,
    )
    from houston.checklists.services import create_checklist_template
    from houston.checklists.tests.conftest import add_task_template
    from houston.establishments.models import EstablishmentMembership
    from houston.establishments.tests.taxonomy_helpers import (
        create_membership_with_business_unit_scope,
    )
    from houston.observations.models import Observation
    from houston.observations.services import submit_observation

    staff_membership = build_membership(role=EstablishmentMembership.Role.STAFF)
    business_unit = create_business_unit(
        establishment=staff_membership.establishment,
        key="kitchen",
        label="Kitchen",
    )
    create_membership_with_business_unit_scope(
        membership=staff_membership,
        business_unit=business_unit,
    )

    template = create_checklist_template(
        establishment_id=staff_membership.establishment_id,
        actor=staff_membership,
        business_unit_id=business_unit.id,
        title="Morning routine",
    )
    add_task_template(template=template, task="Check fridge", position=1)
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])

    execution = ChecklistExecution.objects.create(
        checklist_template=template,
        execution_source=EXECUTION_SOURCE_TEMPLATE,
        establishment_id=staff_membership.establishment_id,
        assigned_to=staff_membership,
        assigned_by=None,
        business_unit=business_unit,
        template_title=template.title,
        template_description=template.description,
        last_activity_at=timezone.now(),
    )
    task_execution = ChecklistTaskExecution.objects.create(
        checklist_execution=execution,
        task="Check fridge",
        position=1,
    )

    observation = submit_observation(
        membership=staff_membership,
        text="Fridge temperature too high in kitchen area today",
        temporary_upload_ids=[],
        origin=Observation.Origin.CHECKLIST_TASK,
        checklist_execution=execution,
        checklist_task_execution=task_execution,
    )

    payload = build_pipeline_input(observation=observation)

    assert payload["checklist_context"] == {
        "origin": "checklist_task",
        "checklist_execution_id": str(execution.id),
        "checklist_task_execution_id": str(task_execution.id),
        "template_title": "Morning routine",
        "task": "Check fridge",
        "business_unit_key": "kitchen",
    }
