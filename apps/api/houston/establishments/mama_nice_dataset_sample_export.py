"""Read-only sample export of the Mama Nice editorial model."""

from __future__ import annotations

from pathlib import Path

from houston.establishments.mama_nice_dataset_archetypes import (
    ARCHETYPES,
    CONTINUOUS_IMPROVEMENT_CONTRACT,
)
from houston.establishments.mama_nice_dataset_constants import (
    MAMA_NICE_ACTIVITIES,
    NARRATIVE_FAMILIES,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_export import (
    ABSENT,
    ACTIVITY_LABELS,
    FAMILY_LABELS,
    _pattern_labels,
    _plan_catalog,
    _relation,
)
from houston.establishments.mama_nice_dataset_sample import (
    SampleCalendarProject,
    SampleRecord,
    coverage_activity_projects,
    coverage_activity_records,
    coverage_family_records,
    sample_errors,
    sample_overdues,
    sample_proactive_projects,
    sample_records,
)


def render_mama_nice_sample_export() -> dict[str, str]:
    errors = sample_errors()
    if errors:
        raise MamaNiceDatasetError(errors)
    records = sample_records()
    plans = _plan_catalog()
    patterns = _pattern_labels()
    return {
        "00-archetypes.md": _archetypes_markdown(),
        "01-interesting.md": _records_markdown(
            "Les 10 Signals interesting",
            [item for item in records if item.section == "interesting"],
            plans,
            patterns,
        ),
        "02-canceled.md": _canceled_markdown(
            [item for item in records if item.section == "canceled"],
            plans,
            patterns,
        ),
        "03-retards.md": _overdue_markdown(plans),
        "04-projets-proactifs.md": _proactive_markdown(plans),
        "05-parcours-patterns.md": _journeys_markdown(
            [item for item in records if item.section == "journey"],
            plans,
            patterns,
        ),
        "06-representatifs.md": _coverage_markdown(plans, patterns),
    }


def write_mama_nice_sample_export(directory: Path) -> list[Path]:
    files = render_mama_nice_sample_export()
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, body in files.items():
        path = directory / name
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written


def _archetypes_markdown() -> str:
    lines = [
        "# Archétypes métier Mama Nice",
        "",
        "Les volumes globaux ne changent pas. Cet échantillon valide le modèle avant expansion.",
        "",
        CONTINUOUS_IMPROVEMENT_CONTRACT,
        "",
    ]
    for key, item in ARCHETYPES.items():
        lines.append(f"## {item.label} (`{key}`)")
        lines.append("")
        lines.append(f"- Familles : {', '.join(sorted(item.families))}")
        lines.append(f"- Pôles observateurs : {', '.join(sorted(item.observer_poles))}")
        lines.append(f"- Pôles responsables : {', '.join(sorted(item.responsible_poles))}")
        lines.append(f"- Activités : {', '.join(sorted(item.activities))}")
        lines.append(f"- Patterns : {', '.join(sorted(item.patterns)) or ABSENT}")
        lines.append(f"- Plans : {', '.join(sorted(item.plans)) or ABSENT}")
        lines.append(f"- Statuts : {', '.join(sorted(item.statuses))}")
        lines.append("")
    return "\n".join(lines)


def _card(item: SampleRecord, plans: dict, patterns: dict) -> list[str]:
    plan = plans.get(item.plan_seed_key or "")
    pattern_label = patterns.get(item.pattern_seed_key or "")
    lines = [
        f"### {item.seed_key} — {item.issue_focus}",
        "",
        f"- Archétype : {ARCHETYPES[item.archetype].label}",
        f"- Date : {item.occurred_at}",
        f"- Lieu : {item.operational_unit}",
        f"- Auteur : {item.author_pole}",
        f"- Responsable : {item.pole}",
        f"- Signal : {item.seed_key}",
        f"- Statut : {item.status}",
        f"- Famille : {FAMILY_LABELS[item.narrative_family]}",
        f"- Activité : {ACTIVITY_LABELS[item.activity]}",
        f"- Pattern : {_relation(item.pattern_seed_key, present_label=pattern_label)}",
        f"- Plan : {_relation(item.plan_seed_key, present_label=plan['title'] if plan else None)}",
        f"- Exécution : {_relation(item.execution_seed_key)}",
    ]
    if item.cancel_reason:
        lines.append(f"- Motif d'annulation : {item.cancel_reason}")
    if item.routing_unassigned:
        lines.append("- Routage : non qualifié")
    if item.interesting_kind:
        lines.append(f"- Interesting : {item.interesting_kind}")
    lines.append("- Observations :")
    for text in item.observations:
        lines.append(f"  - {text}")
    if plan:
        lines.append("- Tâches principales :")
        for task in plan["tasks"]:
            lines.append(f"  - {task['task']}")
    else:
        lines.append("- Tâches principales : aucune")
    lines.append("")
    return lines


def _records_markdown(title: str, rows: list[SampleRecord], plans: dict, patterns: dict) -> str:
    lines = [f"# {title}", ""]
    for item in rows:
        lines.extend(_card(item, plans, patterns))
    return "\n".join(lines)


def _canceled_markdown(rows: list[SampleRecord], plans: dict, patterns: dict) -> str:
    lines = ["# Les 15 Signals canceled", ""]
    for item in rows:
        lines.extend(_card(item, plans, patterns))
    return "\n".join(lines)


def _bound_plan(item, plans: dict) -> tuple[str | None, list[str]]:
    if getattr(item, "oneshot_title", None):
        return item.oneshot_title, list(item.oneshot_tasks)
    plan = plans.get(item.plan_seed_key or "")
    if plan:
        return plan["title"], [task["task"] for task in plan["tasks"]]
    return None, []


def _project_card(item, plans: dict, *, extra: list[str]) -> list[str]:
    plan_title, tasks = _bound_plan(item, plans)
    lines = [
        f"### {item.title}",
        "",
        *extra,
        f"- Pôle : {item.pole}",
        f"- Activité : {ACTIVITY_LABELS[item.activity]}",
        f"- Signal : {ABSENT}",
        f"- Pattern : {ABSENT}",
        f"- Plan : {_relation(item.plan_seed_key, present_label=plan_title)}",
        f"- Contexte : {item.context}",
    ]
    if tasks:
        lines.append("- Tâches principales :")
        for task in tasks:
            lines.append(f"  - {task}")
    else:
        lines.append("- Tâches principales : aucune")
    lines.append("")
    return lines


def _overdue_markdown(plans: dict) -> str:
    lines = ["# Six exécutions en retard", ""]
    for item in sample_overdues():
        extra = [
            f"- Retard : {item.days_late} jours",
            f"- Famille : {FAMILY_LABELS[item.narrative_family]}",
        ]
        lines.extend(_project_card(item, plans, extra=extra))
    return "\n".join(lines)


def _calendar_project_card(item: SampleCalendarProject) -> list[str]:
    month = f"{item.counted_month[0]}-{item.counted_month[1]:02d}"
    lines = [
        f"### {item.title}",
        "",
        f"- Date de création du plan : {item.plan_created_at}",
        f"- Plan utilisé : {_relation(item.plan_seed_key, present_label=item.plan_title)}",
        f"- seed_key de l'exécution : {item.execution_seed_key}",
        f"- Statut de l'exécution : {item.execution_status}",
        f"- start_at : {item.start_at}",
        f"- end_at : {item.end_at}",
        f"- schedule_id : {item.schedule_id or ABSENT}",
        f"- Mois comptabilisé : {month}",
        f"- Signal : {ABSENT}",
        f"- Pôle : {item.pole}",
        f"- Activité : {ACTIVITY_LABELS[item.activity]}",
        f"- Nature : {item.kind}",
        f"- Contexte : {item.context}",
    ]
    if item.oneshot_tasks:
        lines.append("- Tâches principales :")
        for task in item.oneshot_tasks:
            lines.append(f"  - {task}")
    else:
        lines.append("- Tâches principales : aucune")
    lines.append("")
    return lines


def _proactive_markdown(plans: dict) -> str:
    lines = ["# Projets proactifs sans Signal", ""]
    for item in sample_proactive_projects():
        lines.extend(_calendar_project_card(item))
    return "\n".join(lines)


def _coverage_markdown(plans: dict, patterns: dict) -> str:
    lines = [
        "# Couverture réelle par famille et activité",
        "",
        "Chaque famille et chaque activité apparaît ici avec un scénario réellement authored,",
        (
            "un retard ou un projet proactif. "
            "Les absences de Signal, Pattern ou plan restent explicites."
        ),
        "",
        "## Familles",
        "",
    ]
    families = coverage_family_records()
    for key in NARRATIVE_FAMILIES:
        lines.extend(_card(families[key], plans, patterns))
    lines.extend(["## Activités", ""])
    activity_records = coverage_activity_records()
    activity_projects = coverage_activity_projects()
    for key in MAMA_NICE_ACTIVITIES:
        if key in activity_records:
            lines.extend(_card(activity_records[key], plans, patterns))
            continue
        item = activity_projects[key]
        if isinstance(item, SampleCalendarProject):
            lines.extend(_calendar_project_card(item))
            continue
        extra = [f"- Famille : {FAMILY_LABELS[item.narrative_family]}"]
        extra.append(f"- Retard : {item.days_late} jours")
        extra.append("- Origine : projet ou exécution sans Signal")
        lines.extend(_project_card(item, plans, extra=extra))
    return "\n".join(lines)


def _journeys_markdown(rows: list[SampleRecord], plans: dict, patterns: dict) -> str:
    lines = ["# Trois parcours Pattern", ""]
    by_journey: dict[str, list[SampleRecord]] = {}
    for item in rows:
        by_journey.setdefault(item.journey or "", []).append(item)
    labels = {
        "clim-chambres": "Clim des chambres",
        "ruptures-buffet": "Ruptures du buffet",
        "audiovisuel-ateliers": "Audiovisuel des Ateliers",
    }
    for key in ("clim-chambres", "ruptures-buffet", "audiovisuel-ateliers"):
        lines.append(f"## {labels[key]}")
        lines.append("")
        for item in by_journey[key]:
            lines.extend(_card(item, plans, patterns))
    return "\n".join(lines)
