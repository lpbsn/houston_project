from __future__ import annotations

from datetime import date, timedelta

from houston.action_plans.materialization import iter_occurrence_dates
from houston.establishments.mama_nice_dataset_archetypes import (
    continuous_improvement_justified,
    in_progress_relation_errors,
    infer_archetype,
    is_oneshot_plan,
)
from houston.establishments.mama_nice_dataset_compiler import (
    CompiledOccurrence,
    CompiledOneshot,
    compile_mama_nice_dataset,
    validate_mama_nice_dataset_manifest,
)
from houston.establishments.mama_nice_dataset_constants import (
    ACTIVE_SIGNAL_MAX_AGE_DAYS,
    FUTURE_BY_MONTH,
    FUTURE_EXECUTION_COUNT,
    SNAPSHOT,
)
from houston.establishments.mama_nice_dataset_manifest import load_mama_nice_manifest
from houston.establishments.mama_nice_dataset_roster import validate_roster


def test_validate_mama_nice_dataset_manifest_is_clean():
    assert validate_mama_nice_dataset_manifest() == []


def test_signal_titles_describe_operational_situations():
    corpus = compile_mama_nice_dataset()
    assert corpus.errors == []
    golden = next(
        signal for signal in corpus.signal_specs if signal["seed_key"] == "signal:golden-clim-318"
    )
    assert golden["title"] == "La clim de la chambre 318 ne refroidit plus"
    assert golden["operational_unit"] == "chambres"
    for signal in corpus.signal_specs:
        assert "_" not in signal["title"]
        assert "incident " not in signal["title"]
    informational = [obs for obs in corpus.observation_specs if obs["informational"]]
    assert len(informational) == 104
    assert all(obs["signal_seed_key"] is None for obs in informational)
    grouped: dict[str, list] = {}
    for obs in corpus.observation_specs:
        if obs["signal_seed_key"]:
            grouped.setdefault(obs["signal_seed_key"], []).append(obs)
    for signal in corpus.signal_specs:
        group = grouped[signal["seed_key"]]
        assert len({obs["raw_text"] for obs in group}) == len(group)
        if signal["routing_unassigned"]:
            assert len(group) == 1


def test_roster_invariants():
    assert validate_roster() == []


def test_compiler_has_no_chat_events():
    corpus = compile_mama_nice_dataset()
    assert corpus.chat_event_count == 0
    assert all("chat" not in name for name in load_mama_nice_manifest())


def test_schedule_20_and_25_moved_to_november():
    manifest = load_mama_nice_manifest()
    rows = {row["n"]: row for row in manifest["schedules"]["schedules"]}
    assert rows[20]["start_date"] == rows[20]["end_date"] == "2026-11-02"
    assert rows[25]["start_date"] == rows[25]["end_date"] == "2026-11-03"
    assert rows[20]["recurrence_days"] == ["monday"]
    assert rows[25]["recurrence_days"] == ["tuesday"]


def test_iter_occurrence_dates_matches_frozen_windows():
    from houston.establishments.mama_nice_dataset_compiler import _schedule_proxy

    manifest = load_mama_nice_manifest()
    bornes = next(row for row in manifest["schedules"]["schedules"] if row["n"] == 20)
    fournisseurs = next(row for row in manifest["schedules"]["schedules"] if row["n"] == 25)
    assert iter_occurrence_dates(
        schedule=_schedule_proxy(bornes),
        from_date=date(2026, 9, 22),
        until_date=date(2026, 10, 6),
    ) == []
    assert iter_occurrence_dates(
        schedule=_schedule_proxy(bornes),
        from_date=date(2026, 11, 2),
        until_date=date(2026, 11, 2),
    ) == [date(2026, 11, 2)]
    assert iter_occurrence_dates(
        schedule=_schedule_proxy(fournisseurs),
        from_date=date(2026, 11, 3),
        until_date=date(2026, 11, 3),
    ) == [date(2026, 11, 3)]


def test_future_180_and_month_split():
    corpus = compile_mama_nice_dataset()
    assert corpus.errors == []
    assert len(corpus.future_executions) == FUTURE_EXECUTION_COUNT
    from houston.establishments.mama_nice_dataset_compiler import _month_key

    months = {}
    for item in corpus.future_executions:
        key = _month_key(item.start_at)
        months[key] = months.get(key, 0) + 1
    assert months == FUTURE_BY_MONTH


DAILY_SCHEDULE_KEYS = {
    "schedule:ouverture-restaurant",
    "schedule:fermeture-restaurant",
    "schedule:passation-reception",
    "schedule:ouverture-pdj",
    "schedule:cloture-pdj",
}
WEEKLY_SCHEDULE_KEYS = {
    "schedule:brunch",
    "schedule:revue-stocks-resto",
    "schedule:inventaire-bar",
    "schedule:stocks-buffet-pdj",
    "schedule:audit-chambres",
    "schedule:revue-linge",
    "schedule:revue-e-reputation",
    "schedule:revue-editoriale",
    "schedule:prepa-comm-evenements",
    "schedule:pipeline-seminaires",
    "schedule:controle-av-ateliers",
    "schedule:controle-rooftop",
    "schedule:controle-piscine",
    "schedule:revue-planning-rh",
}
OCTOBER_MONTHLY_KEYS = {
    "schedule:controle-securite",
    "schedule:controle-eclairage",
    "schedule:integration-formation",
}


def test_october_november_amended_composition():
    corpus = compile_mama_nice_dataset()
    october = [item for item in corpus.future_executions if item.start_at.month == 10]
    november = [item for item in corpus.future_executions if item.start_at.month == 11]
    assert len(october) == 50
    assert len(november) == 14

    october_occurrences = [item for item in october if isinstance(item, CompiledOccurrence)]
    october_oneshots = [item for item in october if isinstance(item, CompiledOneshot)]
    october_dailies = [
        item
        for item in october_occurrences
        if item.schedule_seed_key in DAILY_SCHEDULE_KEYS
    ]
    october_named_weeklies = [
        item for item in october_occurrences if item.schedule_seed_key in WEEKLY_SCHEDULE_KEYS
    ]
    october_super_sunday = [
        item for item in october_occurrences if item.schedule_seed_key == "schedule:super-sunday"
    ]
    october_monthlies = [
        item.schedule_seed_key
        for item in october_occurrences
        if item.schedule_seed_key in OCTOBER_MONTHLY_KEYS
    ]
    assert len(october_dailies) == 30
    october_schedule_keys = {item.schedule_seed_key for item in october_occurrences}
    assert october_schedule_keys <= (
        DAILY_SCHEDULE_KEYS
        | WEEKLY_SCHEDULE_KEYS
        | OCTOBER_MONTHLY_KEYS
        | {"schedule:super-sunday"}
    )
    assert "schedule:bornes-electriques" not in october_schedule_keys
    assert "schedule:revue-fournisseurs" not in october_schedule_keys
    assert set(october_monthlies) == OCTOBER_MONTHLY_KEYS
    assert {item.occurrence_date.isoformat() for item in october_super_sunday} == {
        "2026-10-04",
        "2026-10-11",
        "2026-10-18",
        "2026-10-25",
    }
    # 11 weeklies in the horizon plus Super Sunday on 4 October.
    # The other three Super Sunday dates stay outside that horizon count.
    assert len(october_named_weeklies) + 1 == 12
    assert len(october_super_sunday) == 4
    october_super_sunday_outside_horizon = {
        item.occurrence_date.isoformat()
        for item in october_super_sunday
        if item.occurrence_date != date(2026, 10, 4)
    }
    assert october_super_sunday_outside_horizon == {
        "2026-10-11",
        "2026-10-18",
        "2026-10-25",
    }
    public_october = [item for item in october_oneshots if item.public]
    assert {item.title for item in public_october} == {
        "La Bringue à Mémé × French Riviera Agency",
        "Mama ❤️ Club Sonore — DJ set",
    }
    assert {item.start_at.date().isoformat() for item in public_october} == {
        "2026-10-15",
        "2026-10-22",
    }
    assert len(october_dailies) + 12 + 3 + 3 + 2 == 50

    november_occurrences = [item for item in november if isinstance(item, CompiledOccurrence)]
    november_oneshots = [item for item in november if isinstance(item, CompiledOneshot)]
    november_super_sunday = [
        item.occurrence_date.isoformat()
        for item in november_occurrences
        if item.schedule_seed_key == "schedule:super-sunday"
    ]
    assert set(november_super_sunday) == {
        "2026-11-01",
        "2026-11-08",
        "2026-11-15",
        "2026-11-22",
        "2026-11-29",
    }
    november_schedule_dates = {
        item.schedule_seed_key: item.occurrence_date.isoformat()
        for item in november_occurrences
        if item.schedule_seed_key != "schedule:super-sunday"
    }
    assert november_schedule_dates == {
        "schedule:bornes-electriques": "2026-11-02",
        "schedule:revue-fournisseurs": "2026-11-03",
    }
    public_november = {item.seed_key for item in november_oneshots if item.public}
    assert public_november == {"oneshot:public:bringue-2026-11-05"}
    private_november = {item.seed_key for item in november_oneshots if not item.public}
    assert "oneshot:private:horizon-azur-2026-11-12" in private_november
    assert len(private_november) == 6
    assert not any(key.endswith("2026-11-13") for key in private_november)
    assert not any(key.endswith("2026-11-24") for key in private_november)
    assert 5 + 1 + 1 + 2 + 5 == 14


def test_sept22_historical_routines_are_seven():
    corpus = compile_mama_nice_dataset()
    assert len(corpus.historical_sept22_occurrences) == 7


def test_every_schedule_targets_an_active_reusable_plan():
    manifest = load_mama_nice_manifest()
    plans = manifest["reusable_plans"]["plans"]
    active = {row["seed_key"] for row in plans if row["status"] == "active"}
    inactive = {row["seed_key"] for row in plans if row["status"] == "inactive"}
    schedules = manifest["schedules"]["schedules"]
    referenced = {row["plan_seed_key"] for row in schedules}

    assert len(schedules) == 28
    assert referenced <= active
    assert referenced.isdisjoint(inactive)
    assert {
        row["seed_key"]
        for row in schedules
        if row["plan_seed_key"] == "plan:runtime-rh-routines"
    } == {"schedule:revue-planning-rh", "schedule:integration-formation"}
    plan = next(row for row in plans if row["n"] == 21)
    assert plan["seed_key"] == "plan:runtime-rh-routines"
    assert plan["title"] == "Routines planning RH"
    assert plan["status"] == "active"
    assert plan["kind"] == "mono"
    assert plan["pilot"] == "rh"


def test_authored_scenarios_have_families_and_no_fallback():
    from houston.establishments.mama_nice_dataset_constants import NARRATIVE_FAMILY_COUNTS
    from houston.establishments.mama_nice_dataset_scenarios import overdue_execution_specs

    corpus = compile_mama_nice_dataset()
    assert corpus.errors == []
    counts = {}
    for item in corpus.scenario_specs:
        counts[item["narrative_family"]] = counts.get(item["narrative_family"], 0) + 1
        assert item["activity"]
        assert item["relations"]["observations"]
        if item["status"] == "interesting":
            assert item["plan_seed_key"] is None
    assert counts == NARRATIVE_FAMILY_COUNTS
    interesting = [item for item in corpus.signal_specs if item["status"] == "interesting"]
    vanished = [
        item for item in interesting if item.get("interesting_kind") == "vanished_technical"
    ]
    assert len(interesting) == 10
    assert len(vanished) == 2
    overdue = overdue_execution_specs()
    assert {item.days_late for item in overdue} == {2, 3, 4, 5, 6, 7}
    horizon = next(item for item in corpus.oneshots if "horizon-azur" in item.seed_key)
    assert (horizon.end_at - horizon.start_at).days >= 2
    from houston.establishments.mama_nice_dataset_editorial import EVENT_KEYWORDS
    from houston.establishments.mama_nice_dataset_scenarios import PLAN_BY_PATTERN

    for item in corpus.scenario_specs:
        if item["status"] == "canceled":
            assert item.get("cancel_reason")
        if item["activity"] in EVENT_KEYWORDS:
            folded = item["issue_focus"].casefold()
            assert any(token in folded for token in EVENT_KEYWORDS[item["activity"]])
        if item["narrative_family"] == "continuous_improvement":
            texts = (
                item["issue_focus"],
                *item.get("observation_texts", ()),
                item.get("cancel_reason") or "",
            )
            assert continuous_improvement_justified(texts)
            assert item["pattern_seed_key"]
            if item["status"] in {"resolved", "in_progress"}:
                assert PLAN_BY_PATTERN[item["pattern_seed_key"]] == item["plan_seed_key"]
            if item["status"] == "open":
                assert item["plan_seed_key"] is None


def test_export_mama_nice_corpus_is_readable(tmp_path):
    from houston.establishments.mama_nice_dataset_export import write_mama_nice_corpus_export

    written = write_mama_nice_corpus_export(tmp_path)
    names = {path.name for path in written}
    assert names == {
        "00-familles.md",
        "01-activites.md",
        "02-parcours.md",
        "03-retards.md",
        "04-projets-proactifs.md",
    }
    families = (tmp_path / "00-familles.md").read_text(encoding="utf-8")
    assert "Amélioration continue : 98" in families
    overdue = (tmp_path / "03-retards.md").read_text(encoding="utf-8")
    assert "Valider la revue linge de la semaine" in overdue
    assert "Signal : aucun" in overdue
    cards = (tmp_path / "01-activites.md").read_text(encoding="utf-8")
    assert "Auteur :" in cards
    assert "Pattern : aucun" in cards or "Pattern : pattern:" in cards
    proactive = (tmp_path / "04-projets-proactifs.md").read_text(encoding="utf-8")
    assert "Signal : aucun" in proactive
    assert "Séminaire Horizon Azur" in proactive
    assert "Fermeture de saison rooftop et piscine" in proactive
    assert "Ranger et sécuriser le mobilier rooftop" in proactive
    fermeture = proactive.split("### Fermeture de saison rooftop et piscine", 1)[1].split(
        "###", 1
    )[0]
    assert "Valider l'ouverture" not in fermeture
    assert "plan:ouverture-saison-rooftop-piscine" not in fermeture


def test_in_progress_plans_are_archetype_compatible_without_pole_default():
    import houston.establishments.mama_nice_dataset_scenarios as scenarios

    assert not hasattr(scenarios, "POLE_DEFAULT_PLAN")
    corpus = compile_mama_nice_dataset()
    assert corpus.errors == []

    in_progress = [item for item in corpus.scenario_specs if item["status"] == "in_progress"]
    assert len(in_progress) == 23
    for item in in_progress:
        assert item["plan_seed_key"]
        assert item["execution_seed_key"]
        archetype = infer_archetype(
            pattern_seed_key=item.get("pattern_seed_key"),
            topic=item.get("topic"),
            activity=item["activity"],
            focus=item["issue_focus"],
        )
        assert archetype
        assert in_progress_relation_errors(
            archetype_key=archetype,
            plan_seed_key=item["plan_seed_key"],
            execution_seed_key=item["execution_seed_key"],
        ) == []
        if is_oneshot_plan(item["plan_seed_key"]):
            assert item["oneshot_title"]
            assert item["oneshot_tasks"]
    active = [
        item
        for item in corpus.signal_specs
        if item["status"] in {"open", "in_progress", "interesting"}
    ]
    assert len(active) == 55
    cutoff = SNAPSHOT - timedelta(days=ACTIVE_SIGNAL_MAX_AGE_DAYS)
    assert all(cutoff <= item["occurred_at"] <= SNAPSHOT for item in active)


def test_compiler_keeps_proactive_windows_and_six_overdues_only():
    from houston.establishments.mama_nice_dataset_constants import OVERDUE_EXECUTION_COUNT

    corpus = compile_mama_nice_dataset()
    assert corpus.errors == []
    tim = next(item for item in corpus.oneshots if item.seed_key == "oneshot:public:tim-lienderss")
    assert tim.start_at.date() == date(2026, 9, 24)
    assert tim.end_at.date() == date(2026, 9, 26)
    assert (2026, 9) == (tim.start_at.year, tim.start_at.month)
    horizon = next(item for item in corpus.oneshots if "horizon-azur" in item.seed_key)
    assert horizon.end_at - horizon.start_at >= timedelta(days=2)
    sunday = next(
        item
        for item in corpus.future_executions
        if getattr(item, "schedule_seed_key", None) == "schedule:super-sunday"
        and item.occurrence_date == date(2026, 9, 27)
    )
    assert (sunday.end_at - sunday.start_at) <= timedelta(hours=4)
    assert len(corpus.overdue_specs) == OVERDUE_EXECUTION_COUNT
    assert all(item.end_at < SNAPSHOT for item in corpus.overdue_specs)
    assert all(
        item.end_at >= SNAPSHOT or item.start_at > SNAPSHOT for item in corpus.future_executions
    )
