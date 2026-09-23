"""Read-only markdown export of the compiled Mama Nice corpus."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from houston.establishments.mama_nice_dataset_compiler import compile_mama_nice_dataset
from houston.establishments.mama_nice_dataset_constants import (
    MAMA_NICE_ACTIVITIES,
    NARRATIVE_FAMILY_COUNTS,
)
from houston.establishments.mama_nice_dataset_copy import execution_tasks
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_manifest import load_mama_nice_manifest
from houston.establishments.mama_nice_dataset_scenarios import (
    overdue_execution_specs,
    proactive_project_specs,
)

FAMILY_LABELS = {
    "operational_incident": "Incident opérationnel",
    "guest_experience": "Expérience client",
    "service_quality": "Qualité de service",
    "prevention": "Prévention",
    "process_inefficiency": "Inefficacité de processus",
    "cross_pole_coordination": "Coordination cross-pôles",
    "continuous_improvement": "Amélioration continue",
    "opportunity": "Opportunité",
}

ACTIVITY_LABELS = {
    "hebergement_chambres": "Hébergement et chambres",
    "reception": "Réception",
    "petit_dejeuner": "Petit-déjeuner",
    "restaurant_cuisine_salle": "Restaurant, cuisine et salle",
    "rooftop_piscine": "Rooftop et piscine",
    "maintenance": "Maintenance",
    "communication_avis": "Communication et avis",
    "ateliers_studios": "Ateliers et Studios",
    "dj_sets": "DJ sets",
    "super_sunday": "Super Sunday",
    "la_bringue": "La Bringue à Mémé",
    "mama_club_sonore": "Mama Club Sonore",
    "seminaires": "Séminaires",
    "privatisations": "Privatisations",
    "staffing_rh": "Staffing et RH",
}

ABSENT = "aucun"


def _plan_catalog() -> dict[str, dict]:
    plans = load_mama_nice_manifest()["reusable_plans"]["plans"]
    return {row["seed_key"]: row for row in plans}


def _pattern_labels() -> dict[str, str]:
    patterns = load_mama_nice_manifest()["patterns"]["patterns"]
    return {row["seed_key"]: row["label"] for row in patterns}


def render_mama_nice_corpus_export() -> dict[str, str]:
    corpus = compile_mama_nice_dataset()
    if corpus.errors:
        raise MamaNiceDatasetError(corpus.errors)
    families = Counter(item["narrative_family"] for item in corpus.signal_specs)
    if dict(families) != NARRATIVE_FAMILY_COUNTS:
        raise MamaNiceDatasetError([f"export families {dict(families)}"])
    by_activity: dict[str, list[dict]] = defaultdict(list)
    for item in corpus.scenario_specs:
        by_activity[item["activity"]].append(item)
    missing = [
        key
        for key in MAMA_NICE_ACTIVITIES
        if key
        in {
            "hebergement_chambres",
            "reception",
            "petit_dejeuner",
            "restaurant_cuisine_salle",
            "rooftop_piscine",
            "maintenance",
            "communication_avis",
            "ateliers_studios",
            "staffing_rh",
        }
        and not by_activity[key]
    ]
    if missing:
        raise MamaNiceDatasetError([f"empty activity chapters: {missing}"])
    journeys = [
        item
        for item in corpus.scenario_specs
        if item["narrative_family"] == "continuous_improvement"
        and item.get("pattern_seed_key")
        and item.get("plan_seed_key")
        and item.get("execution_seed_key")
    ]
    unfinished_ci = [
        item["seed_key"]
        for item in corpus.scenario_specs
        if item["narrative_family"] == "continuous_improvement"
        and item["status"] in {"resolved", "in_progress"}
        and not (
            item.get("pattern_seed_key")
            and item.get("plan_seed_key")
            and item.get("execution_seed_key")
        )
    ]
    if unfinished_ci:
        raise MamaNiceDatasetError([f"incomplete journeys: {unfinished_ci[:8]}"])
    if not journeys:
        raise MamaNiceDatasetError(["export needs treated continuous-improvement journeys"])
    public_titles = {item.title for item in corpus.oneshots if item.public}
    expected_public = {
        "TIM LIENDERSS — DJ set",
        "La Bringue à Mémé × French Riviera Agency",
        "Mama ❤️ Club Sonore — DJ set",
    }
    if not expected_public <= public_titles:
        raise MamaNiceDatasetError(["public events missing from export"])
    plans = _plan_catalog()
    patterns = _pattern_labels()
    files = {
        "00-familles.md": _families_markdown(families),
        "01-activites.md": _activities_markdown(by_activity, plans, patterns),
        "02-parcours.md": _journeys_markdown(journeys, plans, patterns),
        "03-retards.md": _overdue_markdown(plans),
        "04-projets-proactifs.md": _proactive_markdown(plans),
    }
    return files


def write_mama_nice_corpus_export(directory: Path) -> list[Path]:
    files = render_mama_nice_corpus_export()
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, body in files.items():
        path = directory / name
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written


def _families_markdown(families: Counter) -> str:
    lines = ["# Répartition par famille narrative", ""]
    for key, expected in NARRATIVE_FAMILY_COUNTS.items():
        lines.append(f"- {FAMILY_LABELS[key]} : {families[key]} (attendu {expected})")
    return "\n".join(lines) + "\n"


def _relation(value: str | None, *, present_label: str | None = None) -> str:
    if not value:
        return ABSENT
    if present_label:
        return f"{value} — {present_label}"
    return value


def _tasks_for(item: dict, plans: dict[str, dict]) -> list[str]:
    if item.get("oneshot_tasks"):
        return list(item["oneshot_tasks"])
    plan = plans.get(item.get("plan_seed_key") or "")
    if plan:
        return [task["task"] for task in plan["tasks"]]
    if item.get("execution_seed_key"):
        return list(execution_tasks(item["canonical_object"]))
    return []


def _scenario_card(item: dict, plans: dict[str, dict], patterns: dict[str, str]) -> list[str]:
    observations = item.get("observations") or []
    if not observations and item.get("relations", {}).get("observations"):
        observations = []
    plan = plans.get(item.get("plan_seed_key") or "")
    pattern_label = patterns.get(item.get("pattern_seed_key") or "")
    tasks = _tasks_for(item, plans)
    lines = [
        f"### {item['seed_key']} — {item['issue_focus']}",
        "",
        f"- Date : {item['occurred_at']}",
        f"- Lieu : {item['operational_unit']}",
        f"- Auteur : {item['author_pole']}",
        f"- Responsable : {item['pole']}",
        f"- Signal : {item['seed_key']}",
        f"- Statut : {item['status']}",
        f"- Famille : {FAMILY_LABELS[item['narrative_family']]}",
        f"- Activité : {ACTIVITY_LABELS[item['activity']]}",
        f"- Pattern : {_relation(item.get('pattern_seed_key'), present_label=pattern_label)}",
        (
            "- Plan : "
            + _relation(
                item.get("plan_seed_key"),
                present_label=item.get("oneshot_title") or (plan["title"] if plan else None),
            )
        ),
        f"- Exécution : {_relation(item.get('execution_seed_key'))}",
    ]
    if item.get("cancel_reason"):
        lines.append(f"- Motif d'annulation : {item['cancel_reason']}")
    if item.get("routing_unassigned"):
        lines.append("- Routage : non qualifié")
    lines.append("- Observations :")
    texts = item.get("observation_texts") or []
    if texts:
        for text in texts:
            lines.append(f"  - {text}")
    else:
        lines.append("  - (voir le corpus compilé, relation observation présente)")
    if tasks:
        lines.append("- Tâches principales :")
        for task in tasks:
            lines.append(f"  - {task}")
    else:
        lines.append("- Tâches principales : aucune")
    lines.append("")
    return lines


def _activities_markdown(
    by_activity: dict[str, list[dict]],
    plans: dict[str, dict],
    patterns: dict[str, str],
) -> str:
    lines = ["# Scénarios par activité Mama Nice", ""]
    for key in MAMA_NICE_ACTIVITIES:
        rows = by_activity.get(key, [])
        lines.append(f"## {ACTIVITY_LABELS[key]}")
        lines.append("")
        if not rows:
            lines.append(
                "Aucun Signal dans cette activité ; voir les projets proactifs et le planning."
            )
            lines.append("")
            continue
        for item in rows:
            lines.extend(_scenario_card(item, plans, patterns))
    return "\n".join(lines)


def _journeys_markdown(
    journeys: list[dict],
    plans: dict[str, dict],
    patterns: dict[str, str],
) -> str:
    lines = ["# Parcours Signal → Pattern → Plan → Exécution", ""]
    for item in journeys:
        plan = plans.get(item.get("plan_seed_key") or "")
        pattern_label = patterns.get(item.get("pattern_seed_key") or "")
        lines.append(
            f"- {item['issue_focus']} → "
            f"{_relation(item.get('pattern_seed_key'), present_label=pattern_label)} → "
            f"{_relation(item.get('plan_seed_key'), present_label=plan['title'] if plan else None)}"
            " → "
            f"{_relation(item.get('execution_seed_key'))}"
        )
        tasks = _tasks_for(item, plans)
        if tasks:
            lines.append(f"  Tâches : {'; '.join(tasks)}")
        else:
            lines.append("  Tâches : aucune")
    return "\n".join(lines) + "\n"


def _overdue_markdown(plans: dict[str, dict]) -> str:
    lines = ["# Six exécutions en retard", ""]
    for item in overdue_execution_specs():
        plan = plans.get(item.plan_seed_key)
        lines.append(
            f"- {item.days_late} jours · {item.pole} · {item.title} — {item.context}"
        )
        lines.append(
            "  Plan : "
            + _relation(item.plan_seed_key, present_label=plan["title"] if plan else None)
        )
        lines.append("  Signal : aucun")
    return "\n".join(lines) + "\n"


def _proactive_markdown(plans: dict[str, dict]) -> str:
    lines = ["# Projets proactifs sans Signal", ""]
    for item in proactive_project_specs():
        plan = plans.get(item.plan_seed_key)
        plan_title = item.oneshot_title or (plan["title"] if plan else None)
        lines.append(f"### {item.title}")
        lines.append("")
        lines.append(f"- start_at : {item.start_at}")
        lines.append(f"- end_at : {item.end_at}")
        lines.append(f"- seed_key de l'exécution : {item.seed_key}")
        lines.append(f"- Pôle : {item.pole}")
        lines.append(f"- Activité : {ACTIVITY_LABELS[item.activity]}")
        lines.append(f"- Signal : {ABSENT}")
        lines.append(f"- Pattern : {ABSENT}")
        lines.append(f"- Plan : {_relation(item.plan_seed_key, present_label=plan_title)}")
        lines.append(f"- Contexte : {item.context}")
        tasks = list(item.oneshot_tasks) if item.oneshot_tasks else (
            [task["task"] for task in plan["tasks"]] if plan else []
        )
        if tasks:
            lines.append("- Tâches principales :")
            for task in tasks:
                lines.append(f"  - {task}")
        else:
            lines.append("- Tâches principales : aucune")
        lines.append("")
    return "\n".join(lines)
