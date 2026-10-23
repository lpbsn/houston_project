"""Live OpenAI title-wording smoke — opt-in, not CI.

The archive test records a fixed comparison set and does not apply current writing
criteria, so it can snapshot an older prompt. Writing checks run only when the
runtime prompt is ai_observation_pipeline_v6_5.

Archives use write_smoke_archive. The kind includes the prompt version, so
successive prompt versions stay separate files. Each scenario stores that
run's taxonomy. Routing is compared by business identity, not by raw keys.

Requires HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 and OPENAI_API_KEY.
Do not set that variable during ordinary implementation or CI.
"""

from __future__ import annotations

import os
import unicodedata

import pytest
from django.conf import settings

from houston.ai.observation_pipeline import (
    OpenAIObservationPipelineProvider,
    build_pipeline_input,
    parse_pipeline_output,
)
from houston.ai.observation_pipeline_schema import PipelineCandidateOutput
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
)
from houston.signals.pipeline_v6_smoke_archive import write_smoke_archive
from houston.signals.tests.conftest import create_observation
from houston.signals.tests.title_wording_archive import (
    TITLE_WRITING_CRITERIA_PROMPT_VERSION,
    business_routing_for_candidate,
    routing_context_from_taxonomy,
    title_archive_kind,
    title_writing_criteria_apply,
)
from houston.testing.factories import build_membership

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.openai_observation_smoke,
]

CANDIDATE_ARCHIVE_FIELDS = (
    "title",
    "signal_kind",
    "issue_focus",
    "canonical_object",
    "expected_action",
    "information_type",
    "affected_business_unit_routing_key",
    "responsible_business_unit_routing_key",
    "activity_subject_routing_key",
    "operational_unit_key",
    "location_text",
    "structured_summary",
)

COMPARISON_CASES = (
    {
        "id": "deposit_cheques",
        "text": "Déposer les chèques du Palais Fit le 3 novembre.",
    },
    {
        "id": "call_client",
        "text": (
            "Ah là là là là, il faut que j'appelle la cliente pour le 31 "
            "pour la faire décaler."
        ),
    },
    {"id": "leak_corridor", "text": "Fuite couloir nord"},
    {
        "id": "planning_available",
        "text": "Les plannings sont disponibles, venez les demander.",
    },
    {
        "id": "clim_room_104",
        "text": "La clim de la chambre 104 est en panne.",
    },
    {
        "id": "fridge_and_floor",
        "text": "Frigo chaud et sol trempé dans le restaurant.",
    },
    {
        "id": "leak_and_planning",
        "text": "Fuite couloir nord et planning étages disponible",
    },
    {
        "id": "oral_broken_glass",
        "text": "Euh attends, la vitre du hall elle est fendue là, au niveau de l'entrée.",
    },
    {
        "id": "oral_brief_time",
        "text": "Du coup demain le brief il passe à 17h au lieu de 16h hein.",
    },
)

_FORBIDDEN_NOMINALIZATIONS = (
    "instruction de",
    "necessite de",
    "besoin de",
    "obligation de",
    "constat de",
)


def _openai_smoke_enabled() -> bool:
    return os.environ.get("HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST") == "1"


def _skip_if_smoke_not_enabled() -> None:
    if not _openai_smoke_enabled():
        pytest.skip(
            "Set HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 to run the live OpenAI "
            "observation pipeline title smoke."
        )
    if not settings.OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY is not configured.")


def _skip_unless_writing_criteria() -> None:
    _skip_if_smoke_not_enabled()
    if not title_writing_criteria_apply(AI_OBSERVATION_PIPELINE_PROMPT_VERSION):
        pytest.skip(
            "Title writing criteria apply only to "
            f"{TITLE_WRITING_CRITERIA_PROMPT_VERSION}; current prompt is "
            f"{AI_OBSERVATION_PIPELINE_PROMPT_VERSION}. "
            "Run test_archive_title_wording_reference for a reference snapshot."
        )


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _setup_taxonomy(establishment) -> None:
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Organisation",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Plomberie",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    restaurant = create_business_unit(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=restaurant,
        label="Salle",
    )


def _propose(text: str):
    output, _routing_context = _propose_in_context(text)
    return output


def _propose_in_context(text: str):
    membership = build_membership()
    _setup_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text=text)
    input_payload = build_pipeline_input(observation=observation)
    assert input_payload["prompt_version"] == AI_OBSERVATION_PIPELINE_PROMPT_VERSION
    assert input_payload["schema_version"] == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    provider = OpenAIObservationPipelineProvider()
    response = provider.propose(input_payload=input_payload)
    output = parse_pipeline_output(response.payload)
    routing_context = routing_context_from_taxonomy(input_payload["routing_taxonomy"])
    return output, routing_context


def _candidate_record(
    candidate: PipelineCandidateOutput,
    routing_context: dict[str, object],
) -> dict[str, object]:
    payload = candidate.model_dump(mode="json")
    record = {key: payload[key] for key in CANDIDATE_ARCHIVE_FIELDS}
    record["business_routing"] = business_routing_for_candidate(record, routing_context)
    return record


def _assert_parsable(candidate: PipelineCandidateOutput) -> None:
    assert candidate.issue_focus.strip()
    assert candidate.canonical_object.strip()
    assert 1 <= len(candidate.title.strip()) <= 80


def _assert_no_nominalization(title: str) -> None:
    folded = _fold(title)
    for pattern in _FORBIDDEN_NOMINALIZATIONS:
        assert pattern not in folded, title


def _assert_not_starting_with(title: str, verbs: tuple[str, ...]) -> None:
    folded = _fold(title).lstrip()
    for verb in verbs:
        assert not folded.startswith(verb), title


def test_archive_title_wording_reference():
    """Record the comparison set for whichever prompt is running.

    Does not apply current writing criteria. The archive kind includes the
    prompt version, so successive snapshots stay separate files.
    """
    _skip_if_smoke_not_enabled()

    scenario_results: list[dict[str, object]] = []
    errors: list[str] = []
    for case in COMPARISON_CASES:
        try:
            output, routing_context = _propose_in_context(case["text"])
            scenario_results.append(
                {
                    "id": case["id"],
                    "text": case["text"],
                    "passed": True,
                    "candidate_count": len(output.candidates),
                    "routing_context": routing_context,
                    "candidates": [
                        _candidate_record(candidate, routing_context)
                        for candidate in output.candidates
                    ],
                }
            )
            assert output.schema_version == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
        except Exception as exc:  # noqa: BLE001 — archive the failure, then fail
            errors.append(f"{case['id']}: {exc}")
            scenario_results.append(
                {
                    "id": case["id"],
                    "text": case["text"],
                    "passed": False,
                    "error": str(exc),
                }
            )

    passed = not errors
    prompt_version = AI_OBSERVATION_PIPELINE_PROMPT_VERSION
    archive_path = write_smoke_archive(
        kind=title_archive_kind(prompt_version),
        payload={
            "passed": passed,
            "scenarios": scenario_results,
            "errors": errors,
            "summary": (
                "Title wording comparison archive. "
                f"prompt {prompt_version}, {len(scenario_results)} scenarios. "
                "Writing criteria are not applied. Routing is resolved inside "
                "each run's taxonomy, not compared as raw keys."
            ),
        },
    )
    assert archive_path.exists()
    assert passed, f"Title archive failed: {errors}; archive={archive_path}"


def test_live_title_cheques_deposit_is_direct_infinitive():
    _skip_unless_writing_criteria()
    output = _propose("Déposer les chèques du Palais Fit le 3 novembre.")
    assert len(output.candidates) == 1
    candidate = output.candidates[0]
    _assert_parsable(candidate)
    assert candidate.signal_kind == "actionable"
    assert candidate.information_type is None
    folded = _fold(candidate.title)
    assert "deposer" in folded
    assert "cheque" in folded
    assert "palais fit" in folded
    assert "3" in folded
    assert "novembre" in folded
    _assert_no_nominalization(candidate.title)


def test_live_title_client_reschedule_drops_oral_noise():
    _skip_unless_writing_criteria()
    output = _propose(
        "Ah là là là là, il faut que j'appelle la cliente pour le 31 pour la faire décaler."
    )
    assert len(output.candidates) == 1
    candidate = output.candidates[0]
    _assert_parsable(candidate)
    assert candidate.signal_kind == "actionable"
    assert candidate.information_type is None
    folded = _fold(candidate.title)
    assert "cliente" in folded
    assert "31" in folded
    assert "appeler" in folded or "contacter" in folded
    assert "decaler" in folded or "decalage" in folded
    assert "ah la la" not in folded
    assert "il faut que" not in folded
    _assert_no_nominalization(candidate.title)


def test_live_title_leak_stays_a_fact_when_actionable():
    _skip_unless_writing_criteria()
    output = _propose("Fuite couloir nord")
    assert len(output.candidates) == 1
    candidate = output.candidates[0]
    _assert_parsable(candidate)
    assert candidate.signal_kind == "actionable"
    assert candidate.information_type is None
    folded = _fold(candidate.title)
    assert "fuite" in folded
    assert "couloir" in folded
    _assert_not_starting_with(candidate.title, ("reparer", "depanner", "intervenir"))
    _assert_no_nominalization(candidate.title)


def test_live_title_planning_availability_stays_informational():
    _skip_unless_writing_criteria()
    output = _propose("Les plannings sont disponibles, venez les demander.")
    assert len(output.candidates) == 1
    candidate = output.candidates[0]
    _assert_parsable(candidate)
    assert candidate.signal_kind == "informational"
    assert candidate.information_type
    folded = _fold(candidate.title)
    assert "planning" in folded
    _assert_not_starting_with(candidate.title, ("demander", "venir"))
    _assert_no_nominalization(candidate.title)


def test_live_title_room_104_keeps_discriminant_fact():
    _skip_unless_writing_criteria()
    output = _propose("La clim de la chambre 104 est en panne.")
    assert len(output.candidates) == 1
    candidate = output.candidates[0]
    _assert_parsable(candidate)
    assert candidate.signal_kind == "actionable"
    assert candidate.information_type is None
    folded = _fold(candidate.title)
    assert "104" in folded
    assert "clim" in folded or "climatisation" in folded
    _assert_not_starting_with(candidate.title, ("reparer", "depanner"))
    _assert_no_nominalization(candidate.title)
