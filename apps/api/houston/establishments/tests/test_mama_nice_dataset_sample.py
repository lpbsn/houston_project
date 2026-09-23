from houston.establishments.mama_nice_dataset_constants import (
    FUTURE_BY_MONTH,
    NARRATIVE_FAMILY_COUNTS,
)
from houston.establishments.mama_nice_dataset_sample import (
    frozen_future_executions,
    sample_errors,
    sample_proactive_projects,
)
from houston.establishments.mama_nice_dataset_sample_export import write_mama_nice_sample_export


def test_family_quotas_are_unchanged():
    assert NARRATIVE_FAMILY_COUNTS == {
        "operational_incident": 74,
        "guest_experience": 52,
        "service_quality": 50,
        "prevention": 44,
        "process_inefficiency": 44,
        "cross_pole_coordination": 50,
        "continuous_improvement": 98,
        "opportunity": 8,
    }


def test_editorial_sample_is_coherent():
    assert sample_errors() == []


def test_proactive_projects_bind_frozen_calendar_without_changing_totals():
    from collections import Counter

    from houston.establishments.mama_nice_dataset_compiler import _month_key

    future = frozen_future_executions()
    assert Counter(_month_key(item.start_at) for item in future) == FUTURE_BY_MONTH
    projects = sample_proactive_projects()
    assert len({item.execution_seed_key for item in projects}) == len(projects)
    super_sunday = next(item for item in projects if item.activity == "super_sunday")
    assert super_sunday.kind == "schedule"
    assert super_sunday.execution_seed_key == "schedule:super-sunday:2026-09-27"
    assert super_sunday.plan_title == "Préparation opérationnelle Super Sunday"
    horizon = next(item for item in projects if "horizon" in item.execution_seed_key)
    assert horizon.counted_month == (2026, 11)
    assert horizon.kind == "oneshot"
    tim = next(item for item in projects if "tim-lienderss" in item.execution_seed_key)
    assert tim.start_at.date().isoformat() == "2026-09-24"
    assert tim.end_at.date().isoformat() == "2026-09-26"
    assert tim.counted_month == (2026, 9)


def test_export_mama_nice_sample_is_readable(tmp_path):
    written = write_mama_nice_sample_export(tmp_path)
    names = {path.name for path in written}
    assert names == {
        "00-archetypes.md",
        "01-interesting.md",
        "02-canceled.md",
        "03-retards.md",
        "04-projets-proactifs.md",
        "05-parcours-patterns.md",
        "06-representatifs.md",
    }
    archetypes = (tmp_path / "00-archetypes.md").read_text(encoding="utf-8")
    assert "Appartenir à un Pattern ne suffit pas" in archetypes
    interesting = (tmp_path / "01-interesting.md").read_text(encoding="utf-8")
    assert "Les départs du 3e mentionnent le bruit du couloir" in interesting
    assert "Bruit en chambre ou circulation" in interesting
    assert "plus de repro" not in interesting
    canceled = (tmp_path / "02-canceled.md").read_text(encoding="utf-8")
    assert "recréditée" in canceled
    assert "contrôle d'ouverture au public" in canceled
    assert "après remise en eau" in canceled
    assert "contrôle eau client" not in canceled
    journeys = (tmp_path / "05-parcours-patterns.md").read_text(encoding="utf-8")
    assert "La clim de la chambre 318 ne refroidit plus" in journeys
    assert "Famille : Incident opérationnel" in journeys
    assert "Famille : Qualité de service" in journeys
    assert "Famille : Amélioration continue" not in journeys
    overdue = (tmp_path / "03-retards.md").read_text(encoding="utf-8")
    assert "Valider le BAT de la signalétique de La Bringue" in overdue
    assert "Transmettre le BAT à l'impression" in overdue
    assert "Planifier la pose" in overdue
    assert "Photographier" not in overdue
    proactive = (tmp_path / "04-projets-proactifs.md").read_text(encoding="utf-8")
    assert "seed_key de l'exécution : schedule:super-sunday:2026-09-27" in proactive
    assert "schedule_id : schedule:super-sunday" in proactive
    assert "Mois comptabilisé : 2026-11" in proactive
    assert "Date de création du plan : 2026-10-20" in proactive
    assert "oneshot:public:super-sunday-2026-09-27" not in proactive
    assert "oneshot:fermeture-saison-rooftop" not in proactive
    representatifs = (tmp_path / "06-representatifs.md").read_text(encoding="utf-8")
    assert "signal:ci-clim-filtres" in representatifs
    assert "cause commune" in representatifs
    assert "améliorer le processus" in representatifs
    assert "Plan : aucun" in representatifs
    assert "Super Sunday" in representatifs
