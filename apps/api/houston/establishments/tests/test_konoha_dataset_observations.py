from __future__ import annotations

from datetime import timedelta

import pytest

from houston.establishments.konoha_dataset_actors import (
    ESTABLISHMENT_AKATSUKI,
    ESTABLISHMENT_ANBU,
    POLE_BASIC_FIT,
    POLE_COMMERCE,
    POLE_COMMUNICATION,
    POLE_COWORKING,
    POLE_EMEA,
    POLE_EVENEMENTS,
    POLE_HOTEL,
    POLE_ISHIRAKU,
    POLE_MAINTENANCE,
    POLE_YAKINUKU,
)
from houston.establishments.konoha_dataset_observations import (
    AUTHOR_DIRECTORY,
    AUTHOR_NAME_ALIASES,
    ORIGIN_POLE_COUNTS,
    SCHEMA_VERSION,
    candidate_as_pipeline_output,
    load_akatsuki_dataset_observations,
    load_anbu_dataset_observations,
    load_konoha_dataset_observations,
    validate_konoha_dataset_observations,
)


def test_author_alias_choji_maps_to_ascii():
    assert AUTHOR_NAME_ALIASES["Chôji"] == "Choji"
    assert "choji@konoha.com" in AUTHOR_DIRECTORY
    assert "ishiraku@konoha.com" in AUTHOR_DIRECTORY


def test_validate_konoha_dataset_observations_is_clean():
    assert validate_konoha_dataset_observations() == []


def test_corpus_counts_and_schema():
    anbu = load_anbu_dataset_observations()
    akatsuki = load_akatsuki_dataset_observations()
    assert anbu["schema_version"] == SCHEMA_VERSION
    assert akatsuki["schema_version"] == SCHEMA_VERSION
    rows = load_konoha_dataset_observations()
    assert len(anbu["observations"]) == 135
    assert len(akatsuki["observations"]) == 65
    assert len(rows) == 200
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["establishment"], row["origin_pole_specific_name"])
        counts[key] = counts.get(key, 0) + 1
    hotel_key = (ESTABLISHMENT_ANBU, POLE_HOTEL)
    assert counts[hotel_key] == ORIGIN_POLE_COUNTS[hotel_key]
    assert counts[(ESTABLISHMENT_ANBU, POLE_ISHIRAKU)] == 24
    assert counts[(ESTABLISHMENT_ANBU, POLE_YAKINUKU)] == 25
    assert counts[(ESTABLISHMENT_ANBU, POLE_COWORKING)] == 24
    assert counts[(ESTABLISHMENT_ANBU, POLE_MAINTENANCE)] == 17
    assert counts[(ESTABLISHMENT_ANBU, POLE_COMMUNICATION)] == 10
    assert counts[(ESTABLISHMENT_AKATSUKI, POLE_COMMERCE)] == 15
    assert counts[(ESTABLISHMENT_AKATSUKI, POLE_BASIC_FIT)] == 14
    assert counts[(ESTABLISHMENT_AKATSUKI, POLE_EMEA)] == 12
    assert counts[(ESTABLISHMENT_AKATSUKI, POLE_EVENEMENTS)] == 9
    assert counts[(ESTABLISHMENT_AKATSUKI, POLE_MAINTENANCE)] == 10
    assert counts[(ESTABLISHMENT_AKATSUKI, POLE_COMMUNICATION)] == 5


def test_ids_are_stable_and_unique():
    rows = load_konoha_dataset_observations()
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert "anbu.hotel.01" in ids
    assert "anbu.communication.10" in ids
    assert "akatsuki.commerce.01" in ids
    assert "akatsuki.communication.05" in ids


def test_same_signal_and_pattern_graph_invariants():
    rows = {row["id"]: row for row in load_konoha_dataset_observations()}
    assert rows["anbu.hotel.02"]["relation"] == "same_signal"
    assert rows["anbu.hotel.02"]["same_signal_of"] == "anbu.hotel.01"
    assert rows["anbu.hotel.02"]["signal_group"] == rows["anbu.hotel.01"]["signal_group"]
    assert rows["anbu.hotel.03"]["relation"] == "new_signal_same_pattern"
    assert rows["anbu.hotel.03"]["pattern_group"] == rows["anbu.hotel.01"]["pattern_group"]
    assert rows["anbu.hotel.03"]["signal_group"] != rows["anbu.hotel.01"]["signal_group"]
    assert rows["anbu.hotel.01"]["cycle"]["resolution"] == "linked_plan"
    assert rows["anbu.hotel.03"]["cycle"]["resolution"] == "manual"
    assert rows["anbu.ishiraku.15"]["pattern_group"] == rows["anbu.ishiraku.01"]["pattern_group"]
    tourniquet = rows["akatsuki.basic_fit.10"]["pattern_group"]
    assert rows["akatsuki.maintenance.08"]["pattern_group"] == tourniquet


INTERESTING_GROUPS = (
    "anbu.hotel.sg.05",
    "anbu.hotel.sg.20",
    "anbu.coworking.sg.11",
    "anbu.maintenance.sg.02",
    "anbu.maintenance.sg.14",
    "akatsuki.commerce.sg.13",
    "akatsuki.emea.sg.09",
    "akatsuki.maintenance.sg.06",
)


def test_interesting_cycles_are_window_concluded_without_resolved_at():
    rows = load_konoha_dataset_observations()
    by_group: dict[str, list[dict]] = {}
    for row in rows:
        by_group.setdefault(row["signal_group"], []).append(row)
    for group in INTERESTING_GROUPS:
        cycle = by_group[group][0]["cycle"]
        assert cycle["resolution"] == "interesting"
        assert cycle["open_at_cutoff"] is False
        assert cycle["resolved_at"] is None
        assert cycle["planned_action_at"] is None
        assert cycle["marked_interesting_at"]


def test_interesting_groups_have_no_successor_requiring_their_resolved_at():
    rows = load_konoha_dataset_observations()
    by_group: dict[str, list[dict]] = {}
    for row in rows:
        by_group.setdefault(row["signal_group"], []).append(row)
    hotel_eight = by_group["anbu.hotel.sg.08"][0]["cycle"]
    assert hotel_eight["open_at_cutoff"] is False
    assert hotel_eight["resolved_at"]
    for group in INTERESTING_GROUPS:
        pattern = by_group[group][0]["pattern_group"]
        later = [
            row
            for row in rows
            if row["pattern_group"] == pattern
            and row["signal_group"] != group
            and row["relation"] == "new_signal_same_pattern"
            and row["occurred_at"] > max(item["occurred_at"] for item in by_group[group])
        ]
        assert later == []


def test_action_overlay_deadlines_and_overdue_cutoff():
    from houston.establishments.konoha_dataset_action_cycles import (
        load_konoha_dataset_action_overrides,
    )

    payload = load_konoha_dataset_action_overrides()
    overrides = payload["overrides"]
    assert overrides["anbu.coworking.sg.23"]["end_at"] == "2026-08-29T18:00:00+02:00"
    assert overrides["anbu.ishiraku.sg.24"]["end_at"] == "2026-08-29T10:00:00+02:00"
    assert overrides["anbu.yakinuku.sg.25"]["end_at"] == "2026-10-20T09:00:00+02:00"
    for group in (
        "anbu.hotel.sg.08",
        "anbu.yakinuku.sg.15",
        "anbu.maintenance.sg.05",
        "akatsuki.commerce.sg.03",
        "akatsuki.commerce.sg.10",
    ):
        assert "end_at" in overrides[group]
        assert overrides[group]["end_at"] is None
    assert overrides["anbu.hotel.sg.01"]["end_at"] == "2025-08-08T06:00:00+02:00"


def test_closed_plan_default_end_at_hash_margins():
    from houston.establishments.konoha_dataset_action_cycles import (
        CLOSED_PLAN_END_AT_MARGINS,
        CLOSED_PLAN_NEAR_MARGIN_INDEXES,
        RESOLUTION_LINKED_PLAN,
        _closed_plan_created_at,
        _default_closed_plan_end_at,
        closed_plan_end_at_margin_index,
        load_konoha_dataset_action_overrides,
    )
    from houston.establishments.konoha_dataset_replay import parse_corpus_datetime

    created_at = parse_corpus_datetime("2025-08-07T09:40:00+02:00")
    resolved_at = parse_corpus_datetime("2025-08-08T18:00:00+02:00")
    groups_by_index: dict[int, str] = {}
    for row in load_konoha_dataset_observations():
        group = row["signal_group"]
        groups_by_index.setdefault(closed_plan_end_at_margin_index(group), group)
    near_group = next(
        group
        for index, group in groups_by_index.items()
        if index in CLOSED_PLAN_NEAR_MARGIN_INDEXES
    )
    early_group = next(
        group
        for index, group in groups_by_index.items()
        if index not in CLOSED_PLAN_NEAR_MARGIN_INDEXES
    )
    near_end = _default_closed_plan_end_at(
        created_at=created_at,
        resolved_at=resolved_at,
        signal_group=near_group,
    )
    assert near_end == _default_closed_plan_end_at(
        created_at=created_at,
        resolved_at=resolved_at,
        signal_group=near_group,
    )
    assert near_end == resolved_at + CLOSED_PLAN_END_AT_MARGINS[
        closed_plan_end_at_margin_index(near_group)
    ]
    assert near_end - resolved_at in {timedelta(hours=1), timedelta(hours=2)}
    early_end = _default_closed_plan_end_at(
        created_at=created_at,
        resolved_at=resolved_at,
        signal_group=early_group,
    )
    assert early_end - resolved_at in {
        timedelta(hours=12),
        timedelta(days=1),
        timedelta(days=2),
    }

    payload = load_konoha_dataset_action_overrides()
    overrides = payload["overrides"]
    first_by_group: dict[str, dict] = {}
    last_by_group: dict[str, dict] = {}
    for row in load_konoha_dataset_observations():
        first_by_group.setdefault(row["signal_group"], row)
        last_by_group[row["signal_group"]] = row
    near_count = 0
    early_count = 0
    for group, first in first_by_group.items():
        cycle = first["cycle"]
        if cycle.get("resolution") != RESOLUTION_LINKED_PLAN:
            continue
        if cycle.get("open_at_cutoff") is True:
            continue
        overlay = overrides.get(group) or {}
        if "end_at" in overlay:
            continue
        last = last_by_group[group]
        last_obs = parse_corpus_datetime(last["occurred_at"])
        resolved_at = parse_corpus_datetime(cycle["resolved_at"])
        created_at = _closed_plan_created_at(
            last_obs=last_obs,
            resolved_at=resolved_at,
            group=group,
        )
        end_at = _default_closed_plan_end_at(
            created_at=created_at,
            resolved_at=resolved_at,
            signal_group=group,
        )
        assert end_at > created_at
        assert end_at > resolved_at
        index = closed_plan_end_at_margin_index(group)
        if index in CLOSED_PLAN_NEAR_MARGIN_INDEXES:
            near_count += 1
        else:
            early_count += 1
    assert near_count > 0
    assert early_count > 0

    payload = load_konoha_dataset_action_overrides()
    overrides = payload["overrides"]
    first_by_group: dict[str, dict] = {}
    last_by_group: dict[str, dict] = {}
    for row in load_konoha_dataset_observations():
        first_by_group.setdefault(row["signal_group"], row)
        last_by_group[row["signal_group"]] = row
    near_count = 0
    early_count = 0
    for group, first in first_by_group.items():
        cycle = first["cycle"]
        if cycle.get("resolution") != RESOLUTION_LINKED_PLAN:
            continue
        if cycle.get("open_at_cutoff") is True:
            continue
        overlay = overrides.get(group) or {}
        if "end_at" in overlay:
            continue
        last = last_by_group[group]
        last_obs = parse_corpus_datetime(last["occurred_at"])
        resolved_at = parse_corpus_datetime(cycle["resolved_at"])
        created_at = _closed_plan_created_at(
            last_obs=last_obs,
            resolved_at=resolved_at,
            group=group,
        )
        end_at = _default_closed_plan_end_at(
            created_at=created_at,
            resolved_at=resolved_at,
            signal_group=group,
        )
        assert end_at > created_at
        assert end_at > resolved_at
        index = closed_plan_end_at_margin_index(group)
        if index in CLOSED_PLAN_NEAR_MARGIN_INDEXES:
            near_count += 1
        else:
            early_count += 1
    assert near_count > 0
    assert early_count > 0


def test_pattern_labels_prefer_issue_focus_then_title():
    from houston.establishments.konoha_dataset_replay import _pattern_labels_by_group

    rows = load_konoha_dataset_observations()
    labels = _pattern_labels_by_group(rows)
    cvc_rows = [row for row in rows if row["pattern_group"] == "anbu.hotel.pg.cvc"]
    first_cvc = min(cvc_rows, key=lambda row: (row["occurred_at"], row["id"]))
    assert labels["anbu.hotel.pg.cvc"] == first_cvc["candidate"]["issue_focus"]
    untitled = {
        **first_cvc,
        "id": "label.title.only",
        "pattern_group": "label.title.only.pg",
        "occurred_at": "2025-08-01T08:00:00+02:00",
        "candidate": {**first_cvc["candidate"], "issue_focus": "", "title": "Fuite visible"},
    }
    assert _pattern_labels_by_group([untitled])["label.title.only.pg"] == "Fuite visible"


@pytest.mark.django_db
def test_catalog_keys_and_pipeline_envelope(imported_catalog):
    from houston.establishments.models import CatalogActivitySubject

    catalog_keys = set(CatalogActivitySubject.objects.values_list("key", flat=True))
    for row in load_konoha_dataset_observations():
        subject = row["candidate"]["activity_subject_catalog_key"]
        assert subject in catalog_keys
        parsed = candidate_as_pipeline_output(row["candidate"])
        assert parsed.operational_unit_key is None
        assert parsed.affected_business_unit_routing_key.endswith("placeholder")
        assert parsed.responsible_business_unit_routing_key.endswith("placeholder")
