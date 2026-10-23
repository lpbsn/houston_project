"""Deterministic guards for title-wording archives. No OpenAI calls."""

from __future__ import annotations

from houston.signals.pipeline_v6_smoke_archive import latest_smoke_archive, write_smoke_archive
from houston.signals.tests.title_wording_archive import (
    compare_title_wording_archives,
    title_archive_kind,
    title_writing_criteria_apply,
)


def test_older_prompts_do_not_apply_current_writing_criteria():
    assert title_writing_criteria_apply("ai_observation_pipeline_v6_3") is False
    assert title_writing_criteria_apply("ai_observation_pipeline_v6_4") is False
    assert title_writing_criteria_apply("ai_observation_pipeline_v6_5") is True


def test_before_and_after_title_archives_stay_distinct(tmp_path):
    before_kind = title_archive_kind("ai_observation_pipeline_v6_3")
    after_kind = title_archive_kind("ai_observation_pipeline_v6_4")
    assert before_kind != after_kind

    before = write_smoke_archive(
        kind=before_kind,
        payload={"passed": True, "summary": "reference v6_3"},
        archive_dir=tmp_path,
    )
    after = write_smoke_archive(
        kind=after_kind,
        payload={"passed": True, "summary": "after v6_4"},
        archive_dir=tmp_path,
    )

    assert before.exists()
    assert after.exists()
    assert before != after
    assert before.with_suffix(".md").exists()
    assert after.with_suffix(".md").exists()
    assert latest_smoke_archive(kind=before_kind, archive_dir=tmp_path) == before
    assert latest_smoke_archive(kind=after_kind, archive_dir=tmp_path) == after
    assert before.read_text(encoding="utf-8") != after.read_text(encoding="utf-8")


def test_same_business_routing_ignores_fresh_uuid_keys():
    before = _archive(_scenario("aaaaaaaaaaaaaaaa"))
    after = _archive(
        _scenario(
            "bbbbbbbbbbbbbbbb",
            title="Fuite d'eau au couloir nord",
            issue_focus="fuite au couloir nord",
            structured_summary="Il y a une fuite au couloir nord.",
        )
    )

    result = compare_title_wording_archives(before=before, after=after)

    assert result["regressions"] == []
    assert _codes(result["fluctuations"]) >= {
        "title_wording",
        "issue_focus_wording",
        "summary_wording",
    }


def test_different_subject_in_the_same_taxonomy_is_a_routing_regression():
    before = _archive(_scenario("aaaaaaaaaaaaaaaa"))
    after_scenario = _scenario("bbbbbbbbbbbbbbbb")
    after_scenario["routing_context"]["business_units"][0]["activity_subjects"].append(
        {
            "routing_key": "custom--maintenance--bbbbbbbbbbbbbbbb",
            "label": "Maintenance",
            "catalog_key": None,
        }
    )
    before["scenarios"][0]["routing_context"]["business_units"][0]["activity_subjects"].append(
        {
            "routing_key": "custom--maintenance--aaaaaaaaaaaaaaaa",
            "label": "Maintenance",
            "catalog_key": None,
        }
    )
    after_scenario["candidates"][0]["activity_subject_routing_key"] = (
        "custom--maintenance--bbbbbbbbbbbbbbbb"
    )

    result = compare_title_wording_archives(before=before, after=_archive(after_scenario))

    assert _codes(result["regressions"]) == {"routing_changed"}


def test_null_route_versus_resolved_route_is_uncertainty_not_a_regression():
    before = _archive(_scenario("aaaaaaaaaaaaaaaa"))
    after = _archive(_scenario("bbbbbbbbbbbbbbbb", affected_business_unit_routing_key=None))

    result = compare_title_wording_archives(before=before, after=after)

    assert result["regressions"] == []
    assert "routing_uncertain" in _codes(result["fluctuations"])


def test_routing_change_is_context_when_the_available_taxonomy_differs():
    before = _archive(_scenario("aaaaaaaaaaaaaaaa"))
    after_scenario = _scenario("bbbbbbbbbbbbbbbb")
    after_scenario["routing_context"] = {
        "business_units": [
            {
                "routing_key": "restaurant--restaurant--bbbbbbbbbbbbbbbb",
                "catalog_key": "restaurant",
                "specific_name": "Restaurant",
                "activity_subjects": [
                    {
                        "routing_key": "custom--salle--bbbbbbbbbbbbbbbb",
                        "label": "Salle",
                        "catalog_key": None,
                    }
                ],
            }
        ],
        "operational_units": [],
    }
    candidate = after_scenario["candidates"][0]
    candidate["affected_business_unit_routing_key"] = "restaurant--restaurant--bbbbbbbbbbbbbbbb"
    candidate["responsible_business_unit_routing_key"] = "restaurant--restaurant--bbbbbbbbbbbbbbbb"
    candidate["activity_subject_routing_key"] = "custom--salle--bbbbbbbbbbbbbbbb"

    result = compare_title_wording_archives(before=before, after=_archive(after_scenario))

    assert "routing_changed" not in _codes(result["regressions"])
    assert "routing_context" in _codes(result["fluctuations"])


def test_unknown_routing_key_is_a_regression():
    before = _archive(_scenario("aaaaaaaaaaaaaaaa"))
    after = _archive(
        _scenario(
            "bbbbbbbbbbbbbbbb",
            affected_business_unit_routing_key="hotel--hotel--not-in-context",
        )
    )

    result = compare_title_wording_archives(before=before, after=after)

    assert "routing_unknown_key" in _codes(result["regressions"])


def test_missing_taxonomy_does_not_compare_raw_routing_keys():
    before = _archive(_scenario("aaaaaaaaaaaaaaaa"))
    after = _archive(_scenario("bbbbbbbbbbbbbbbb"))
    before["scenarios"][0].pop("routing_context")
    after["scenarios"][0].pop("routing_context")

    result = compare_title_wording_archives(before=before, after=after)

    assert result["regressions"] == []
    assert "routing_context_missing" in _codes(result["fluctuations"])


def test_lost_title_number_is_a_regression_and_summary_paraphrase_is_not():
    before = _archive(
        _scenario(
            "aaaaaaaaaaaaaaaa",
            title="Clim en panne chambre 104",
            structured_summary="La clim de la chambre 104 est en panne.",
            text="La clim de la chambre 104 est en panne.",
        )
    )
    after = _archive(
        _scenario(
            "bbbbbbbbbbbbbbbb",
            title="Clim en panne",
            structured_summary="La climatisation est en panne.",
            text="La clim de la chambre 104 est en panne.",
        )
    )

    result = compare_title_wording_archives(before=before, after=after)

    assert "title_discriminant" in _codes(result["regressions"])
    assert "summary_detail" not in _codes(result["regressions"])
    assert "summary_detail" in _codes(result["fluctuations"])


def test_candidate_count_and_signal_kind_are_regressions():
    before = _archive(_scenario("aaaaaaaaaaaaaaaa"))
    after = _archive(_scenario("bbbbbbbbbbbbbbbb", signal_kind="informational"))
    extra = _scenario("bbbbbbbbbbbbbbbb")
    extra["candidates"].append(dict(extra["candidates"][0]))
    counted = compare_title_wording_archives(before=before, after=_archive(extra))
    retargeted = compare_title_wording_archives(before=before, after=after)

    assert "candidate_count" in _codes(counted["regressions"])
    assert "signal_kind" in _codes(retargeted["regressions"])


def test_swapped_candidates_are_not_a_regression():
    before = _archive(_multi("aaaaaaaaaaaaaaaa"))
    after = _archive(_multi("bbbbbbbbbbbbbbbb", reverse=True))

    result = compare_title_wording_archives(before=before, after=after)

    assert result["regressions"] == []


def test_disjoint_issue_focus_and_conflicting_action_are_regressions():
    before = _archive(_scenario("aaaaaaaaaaaaaaaa"))
    focus = compare_title_wording_archives(
        before=before,
        after=_archive(_scenario("bbbbbbbbbbbbbbbb", issue_focus="planning etages")),
    )
    action = compare_title_wording_archives(
        before=before,
        after=_archive(_scenario("bbbbbbbbbbbbbbbb", expected_action="inspect")),
    )
    uncertain = compare_title_wording_archives(
        before=before,
        after=_archive(_scenario("bbbbbbbbbbbbbbbb", expected_action=None)),
    )

    assert "issue_focus" in _codes(focus["regressions"])
    assert "expected_action" in _codes(action["regressions"])
    assert uncertain["regressions"] == []
    assert "expected_action_uncertain" in _codes(uncertain["fluctuations"])


def _codes(entries: list[dict[str, str]]) -> set[str]:
    return {entry["code"] for entry in entries}


def _archive(scenario: dict) -> dict:
    return {"scenarios": [scenario]}


def _context(suffix: str) -> dict:
    return {
        "business_units": [
            {
                "routing_key": f"hotel--hotel--{suffix}",
                "catalog_key": "hotel",
                "specific_name": "Hôtel",
                "activity_subjects": [
                    {
                        "routing_key": f"custom--plomberie--{suffix}",
                        "label": "Plomberie",
                        "catalog_key": None,
                    }
                ],
            }
        ],
        "operational_units": [],
    }


def _scenario(suffix: str, **overrides) -> dict:
    text = overrides.pop("text", "Fuite couloir nord")
    candidate = {
        "title": "Fuite au couloir nord",
        "signal_kind": "actionable",
        "issue_focus": "fuite couloir nord",
        "canonical_object": "fuite",
        "expected_action": "repair",
        "information_type": None,
        "affected_business_unit_routing_key": f"hotel--hotel--{suffix}",
        "responsible_business_unit_routing_key": f"hotel--hotel--{suffix}",
        "activity_subject_routing_key": f"custom--plomberie--{suffix}",
        "operational_unit_key": None,
        "location_text": "couloir nord",
        "structured_summary": "Fuite au couloir nord.",
    }
    candidate.update(overrides)
    return {
        "id": "leak_corridor",
        "text": text,
        "routing_context": _context(suffix),
        "candidates": [candidate],
    }


def _multi(suffix: str, *, reverse: bool = False) -> dict:
    leak = _scenario(suffix)["candidates"][0]
    planning = {
        "title": "Planning des étages disponible",
        "signal_kind": "informational",
        "issue_focus": "planning etages disponible",
        "canonical_object": "planning",
        "expected_action": "inform",
        "information_type": "schedule_update",
        "affected_business_unit_routing_key": None,
        "responsible_business_unit_routing_key": None,
        "activity_subject_routing_key": None,
        "operational_unit_key": None,
        "location_text": None,
        "structured_summary": "Les plannings des étages sont disponibles.",
    }
    candidates = [planning, leak] if reverse else [leak, planning]
    return {
        "id": "leak_and_planning",
        "text": "Fuite couloir nord et planning étages disponible",
        "routing_context": _context(suffix),
        "candidates": candidates,
    }
