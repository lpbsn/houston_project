"""Hand-authored editorial sample. This is not the 420-signal corpus."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from houston.establishments.mama_nice_dataset_archetypes import (
    ARCHETYPES,
    archetype_errors,
    continuous_improvement_justified,
)
from houston.establishments.mama_nice_dataset_compiler import (
    CompiledOccurrence,
    CompiledOneshot,
    _compile_schedule_occurrences,
    _expand_dated_oneshots,
    _month_key,
)
from houston.establishments.mama_nice_dataset_constants import (
    FUTURE_BY_MONTH,
    MAMA_NICE_ACTIVITIES,
    NARRATIVE_FAMILIES,
    PARIS_TZ,
    SNAPSHOT,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_manifest import load_mama_nice_manifest
from houston.establishments.mama_nice_dataset_scenarios import (
    ROOFTOP_CLOSURE_TASKS,
    OverdueExecutionSpec,
    overdue_execution_specs,
)

BRINGUE_SIGNAGE_TASKS = (
    "Consolider les contenus et parcours",
    "Faire valider les supports par Communication",
    "Transmettre le BAT à l'impression",
    "Planifier la pose",
)
RH_INTEGRATION_TASKS = (
    "Remettre badge et accès réception",
    "Cocher les modules d'intégration",
    "Planifier les shifts d'accompagnement",
    "Confirmer l'autonomie sur le poste",
)
@dataclass(frozen=True)
class SampleRecord:
    seed_key: str
    archetype: str
    section: str
    pole: str
    author_pole: str
    subject: str
    activity: str
    narrative_family: str
    status: str
    operational_unit: str
    issue_focus: str
    observations: tuple[str, ...]
    occurred_at: datetime
    pattern_seed_key: str | None = None
    plan_seed_key: str | None = None
    execution_seed_key: str | None = None
    cancel_reason: str | None = None
    interesting_kind: str | None = None
    routing_unassigned: bool = False
    journey: str | None = None


@dataclass(frozen=True)
class SampleCalendarProject:
    title: str
    pole: str
    activity: str
    plan_seed_key: str
    plan_title: str
    plan_created_at: datetime
    execution_seed_key: str
    execution_status: str
    start_at: datetime
    end_at: datetime
    schedule_id: str | None
    counted_month: tuple[int, int]
    kind: str
    context: str
    oneshot_title: str | None = None
    oneshot_tasks: tuple[str, ...] = ()


def _dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=PARIS_TZ)


def frozen_future_executions() -> tuple[CompiledOneshot | CompiledOccurrence, ...]:
    manifest = load_mama_nice_manifest()
    errors: list[str] = []
    horizon, extras, _sept22 = _compile_schedule_occurrences(manifest, errors)
    if errors:
        raise MamaNiceDatasetError(errors)
    oneshots = _expand_dated_oneshots(manifest)
    future: list[CompiledOneshot | CompiledOccurrence] = []
    future.extend(item for item in horizon if item.start_at > SNAPSHOT)
    future.extend(item for item in extras if item.start_at > SNAPSHOT)
    future.extend(item for item in oneshots if item.start_at > SNAPSHOT)
    return tuple(future)


def future_execution_identity(item: CompiledOneshot | CompiledOccurrence) -> str:
    if isinstance(item, CompiledOneshot):
        return item.seed_key
    return f"{item.schedule_seed_key}:{item.occurrence_date.isoformat()}"


def _future_by_id() -> dict[str, CompiledOneshot | CompiledOccurrence]:
    return {future_execution_identity(item): item for item in frozen_future_executions()}


def _bind_oneshot(
    *,
    identity: str,
    activity: str,
    plan_created_at: datetime,
    context: str,
    plan_title: str | None = None,
) -> SampleCalendarProject:
    item = _future_by_id()[identity]
    if not isinstance(item, CompiledOneshot):
        raise MamaNiceDatasetError([f"{identity} is not a frozen oneshot"])
    return SampleCalendarProject(
        title=item.title,
        pole=item.pole,
        activity=activity,
        plan_seed_key=item.plan_seed_key,
        plan_title=plan_title or item.title,
        plan_created_at=plan_created_at,
        execution_seed_key=identity,
        execution_status="scheduled",
        start_at=item.start_at,
        end_at=item.end_at,
        schedule_id=None,
        counted_month=_month_key(item.start_at),
        kind="oneshot",
        context=context,
    )


def _bind_schedule(
    *,
    identity: str,
    title: str,
    pole: str,
    activity: str,
    plan_seed_key: str,
    plan_title: str,
    plan_created_at: datetime,
    context: str,
    oneshot_title: str | None = None,
    oneshot_tasks: tuple[str, ...] = (),
) -> SampleCalendarProject:
    item = _future_by_id()[identity]
    if not isinstance(item, CompiledOccurrence):
        raise MamaNiceDatasetError([f"{identity} is not a frozen schedule occurrence"])
    return SampleCalendarProject(
        title=title,
        pole=pole,
        activity=activity,
        plan_seed_key=plan_seed_key,
        plan_title=plan_title,
        plan_created_at=plan_created_at,
        execution_seed_key=identity,
        execution_status="scheduled",
        start_at=item.start_at,
        end_at=item.end_at,
        schedule_id=item.schedule_seed_key,
        counted_month=_month_key(item.start_at),
        kind="schedule",
        context=context,
        oneshot_title=oneshot_title,
        oneshot_tasks=oneshot_tasks,
    )


def sample_records() -> tuple[SampleRecord, ...]:
    return (
        *_interesting(),
        *_canceled(),
        *_journeys(),
        *_representatives(),
    )


def sample_overdues() -> tuple[OverdueExecutionSpec, ...]:
    adapted: list[OverdueExecutionSpec] = []
    for spec in overdue_execution_specs():
        if spec.seed_key == "exec:overdue:integration-reception":
            adapted.append(
                replace(
                    spec,
                    plan_seed_key="oneshot:integration-receptionniste",
                    oneshot_title="Intégration de la réceptionniste",
                    oneshot_tasks=RH_INTEGRATION_TASKS,
                )
            )
        elif spec.seed_key == "exec:overdue:signaletique-bringue":
            adapted.append(
                replace(
                    spec,
                    title="Valider le BAT de la signalétique de La Bringue",
                    context=(
                        "Le BAT n'est pas encore transmis à l'impression. "
                        "La pose n'est pas commencée au 20 septembre."
                    ),
                    plan_seed_key="oneshot:bat-signaletique-bringue",
                    oneshot_title="BAT de la signalétique de La Bringue",
                    oneshot_tasks=BRINGUE_SIGNAGE_TASKS,
                )
            )
        else:
            adapted.append(spec)
    return tuple(adapted)


def sample_proactive_projects() -> tuple[SampleCalendarProject, ...]:
    return (
        _bind_oneshot(
            identity="oneshot:public:tim-lienderss",
            activity="dj_sets",
            plan_created_at=_dt(2026, 9, 23, 10, 0),
            plan_title="Préparation d'un événement DJ",
            context=(
                "Préparation du DJ set du 24 au 26 septembre, sur la ligne déjà comptée "
                "dans les 60 exécutions de septembre. Pas d'exécution supplémentaire."
            ),
        ),
        _bind_oneshot(
            identity="oneshot:public:club-sonore-2026-10-22",
            activity="mama_club_sonore",
            plan_created_at=_dt(2026, 10, 15, 10, 0),
            plan_title="Préparation d'un événement DJ",
            context=(
                "One-shot public déjà prévu le 22 octobre 16 h–19 h. "
                "Cette ligne est l'une des 50 exécutions d'octobre."
            ),
        ),
        _bind_oneshot(
            identity="oneshot:private:horizon-azur-2026-11-12",
            activity="seminaires",
            plan_created_at=_dt(2026, 10, 20, 9, 0),
            plan_title="Préparation d'un séminaire",
            context=(
                "Le plan catalogue a été créé le 20 octobre. "
                "L'exécution réelle démarre le 10 novembre et se termine le 13 ; "
                "elle est comptée en novembre, pas en octobre."
            ),
        ),
        _bind_schedule(
            identity="schedule:controle-rooftop:2026-09-23",
            title="Fermeture de saison rooftop et piscine",
            pole="evenements_privatisations",
            activity="rooftop_piscine",
            plan_seed_key="schedule:controle-rooftop",
            plan_title="Fermeture de saison rooftop et piscine",
            plan_created_at=_dt(2026, 4, 1, 9, 0),
            context=(
                "Occurrence du 23 septembre du schedule Contrôle d'exploitation du rooftop, "
                "déjà comptée dans les 60 exécutions de septembre. "
                "Les tâches de cette occurrence sont celles de la fermeture de saison."
            ),
            oneshot_title="Fermeture de saison rooftop et piscine",
            oneshot_tasks=ROOFTOP_CLOSURE_TASKS,
        ),
        _bind_schedule(
            identity="schedule:reouverture-rooftop-piscine:2027-03-01",
            title="Réouverture rooftop et piscine",
            pole="evenements_privatisations",
            activity="rooftop_piscine",
            plan_seed_key="plan:ouverture-saison-rooftop-piscine",
            plan_title="Ouverture de saison rooftop et piscine",
            plan_created_at=_dt(2027, 3, 1, 9, 0),
            context=(
                "Occurrence unique du schedule #28 le 1er mars 2027 09 h–12 h, "
                "déjà comptée dans les 15 exécutions de mars."
            ),
        ),
        _bind_schedule(
            identity="schedule:super-sunday:2026-09-27",
            title="Super Sunday — concert",
            pole="evenements_privatisations",
            activity="super_sunday",
            plan_seed_key="schedule:super-sunday",
            plan_title="Préparation opérationnelle Super Sunday",
            plan_created_at=_dt(2026, 9, 22, 16, 0),
            context=(
                "Occurrence du schedule #7 le 27 septembre 16 h–19 h. "
                "Pas de second one-shot et pas le libellé « Préparation d'un événement DJ »."
            ),
        ),
    )


def _interesting() -> tuple[SampleRecord, ...]:
    return (
        SampleRecord(
            seed_key="signal:interesting-bruit-3e",
            archetype="bruit_chambre",
            section="interesting",
            pole="hotel",
            author_pole="hotel",
            subject="hotel__experience_client",
            activity="hebergement_chambres",
            narrative_family="opportunity",
            status="interesting",
            interesting_kind="opportunity",
            operational_unit="circulations_chambres",
            issue_focus="Les départs du 3e mentionnent le bruit du couloir, sans chambre en cause",
            observations=(
                (
                    "Trois départs du 3e cette semaine parlent du bruit dans le couloir, sans "
                    "numéro de chambre."
                ),
            ),
            occurred_at=_dt(2026, 9, 16, 11, 20),
        ),
        SampleRecord(
            seed_key="signal:interesting-late-sunday",
            archetype="accueil_lobby",
            section="interesting",
            pole="hotel",
            author_pole="hotel",
            subject="hotel__check_in_out",
            activity="reception",
            narrative_family="opportunity",
            status="interesting",
            interesting_kind="opportunity",
            operational_unit="reception_lobby",
            issue_focus="Des clients demandent un check-out tardif le dimanche de Super Sunday",
            observations=(
                (
                    "À la réception, plusieurs clients demandent un check-out tardif le dimanche "
                    "de Super Sunday."
                ),
            ),
            occurred_at=_dt(2026, 9, 15, 16, 10),
        ),
        SampleRecord(
            seed_key="signal:interesting-sans-gluten",
            archetype="buffet_pdj",
            section="interesting",
            pole="petit_dejeuner",
            author_pole="petit_dejeuner",
            subject="petit_dejeuner__menu",
            activity="petit_dejeuner",
            narrative_family="opportunity",
            status="interesting",
            interesting_kind="opportunity",
            operational_unit="restaurant_rdc",
            issue_focus="Des clients cherchent une option sans gluten plus visible sur le buffet",
            observations=(
                (
                    "Au buffet, des clients cherchent une option sans gluten plus visible, sans "
                    "rupture ce matin."
                ),
            ),
            occurred_at=_dt(2026, 9, 14, 8, 25),
        ),
        SampleRecord(
            seed_key="signal:interesting-file-vendredi",
            archetype="service_restaurant",
            section="interesting",
            pole="restaurant",
            author_pole="restaurant",
            subject="restaurant__service_accueil",
            activity="restaurant_cuisine_salle",
            narrative_family="opportunity",
            status="interesting",
            interesting_kind="opportunity",
            operational_unit="restaurant_rdc",
            issue_focus="La file du vendredi s'allonge avant 20 h, sous le seuil d'incident",
            observations=(
                (
                    "Vendredi, la file du restaurant s'allonge avant 20 h sans encore bloquer "
                    "l'entrée."
                ),
            ),
            occurred_at=_dt(2026, 9, 12, 20, 5),
        ),
        SampleRecord(
            seed_key="signal:interesting-table-rooftop",
            archetype="saison_rooftop",
            section="interesting",
            pole="restaurant",
            author_pole="restaurant",
            subject="restaurant__experience_client",
            activity="rooftop_piscine",
            narrative_family="opportunity",
            status="interesting",
            interesting_kind="opportunity",
            operational_unit="rooftop",
            issue_focus="Les groupes du rooftop aimeraient garder la table après le dessert",
            observations=(
                (
                    "En fin de saison, les groupes du rooftop demandent à garder la table après "
                    "le dessert."
                ),
            ),
            occurred_at=_dt(2026, 9, 13, 22, 10),
        ),
        SampleRecord(
            seed_key="signal:interesting-brunch",
            archetype="avis_client",
            section="interesting",
            pole="communication",
            author_pole="communication",
            subject="communication__communication_commerciale",
            activity="communication_avis",
            narrative_family="opportunity",
            status="interesting",
            interesting_kind="opportunity",
            operational_unit="back_office_administratif",
            issue_focus="Les avis citent le brunch du dimanche, piste d'offre avant Super Sunday",
            observations=(
                (
                    "Plusieurs avis citent le brunch du dimanche. Communication y voit une offre "
                    "à pousser avant Super Sunday."
                ),
            ),
            occurred_at=_dt(2026, 9, 11, 15, 40),
        ),
        SampleRecord(
            seed_key="signal:interesting-studios",
            archetype="seminaire_privatisation",
            section="interesting",
            pole="evenements_privatisations",
            author_pole="evenements_privatisations",
            subject="evenements_privatisations__commercialisation",
            activity="ateliers_studios",
            narrative_family="opportunity",
            status="interesting",
            interesting_kind="opportunity",
            operational_unit="studio_1",
            issue_focus="Des sociétés demandent le Studio 1 pour des demi-journées",
            observations=(
                (
                    "Deux sociétés ont demandé le Studio 1 à la demi-journée, pas seulement les "
                    "Ateliers."
                ),
            ),
            occurred_at=_dt(2026, 9, 10, 11, 50),
        ),
        SampleRecord(
            seed_key="signal:interesting-extras-sunday",
            archetype="staffing",
            section="interesting",
            pole="rh",
            author_pole="rh",
            subject="rh__planning",
            activity="staffing_rh",
            narrative_family="opportunity",
            status="interesting",
            interesting_kind="opportunity",
            operational_unit="breakroom",
            issue_focus="Les extras hésitent sur les Super Sunday, le planning n'est pas en trou",
            observations=(
                (
                    "Au breakroom, les extras hésitent à prendre les Super Sunday. Le planning "
                    "du 27 n'est pas encore en trou."
                ),
            ),
            occurred_at=_dt(2026, 9, 9, 17, 15),
        ),
        SampleRecord(
            seed_key="signal:interesting-wifi-4e",
            archetype="wifi_reseau",
            section="interesting",
            pole="maintenance",
            author_pole="hotel",
            subject="maintenance__reseau_informatique",
            activity="maintenance",
            narrative_family="operational_incident",
            status="interesting",
            interesting_kind="vanished_technical",
            operational_unit="chambres",
            issue_focus="Le wifi du 4e a décroché dix minutes, sans nouvel incident",
            observations=(
                (
                    "Le wifi du 4e a décroché dix minutes en chambre. Plus aucun appel depuis le "
                    "rétablissement."
                ),
            ),
            occurred_at=_dt(2026, 9, 8, 19, 5),
        ),
        SampleRecord(
            seed_key="signal:interesting-clickshare-atelier-1",
            archetype="audiovisuel_salle",
            section="interesting",
            pole="evenements_privatisations",
            author_pole="evenements_privatisations",
            subject="evenements_privatisations__preparation_logistique",
            activity="ateliers_studios",
            narrative_family="operational_incident",
            status="interesting",
            interesting_kind="vanished_technical",
            operational_unit="atelier_1",
            issue_focus="Le ClickShare de l'Atelier 1 a clignoté, sans nouvel incident",
            observations=(
                (
                    "Le ClickShare de l'Atelier 1 a clignoté une fois pendant un test. Aucun "
                    "nouvel incident depuis."
                ),
            ),
            occurred_at=_dt(2026, 9, 8, 10, 35),
        ),
    )


def _canceled() -> tuple[SampleRecord, ...]:
    return (
        SampleRecord(
            seed_key="signal:canceled-groupe-20",
            archetype="accueil_lobby",
            section="canceled",
            pole="hotel",
            author_pole="hotel",
            subject="hotel__commercialisation",
            activity="reception",
            narrative_family="guest_experience",
            status="canceled",
            operational_unit="reception_lobby",
            issue_focus="La prépa du groupe du 20 n'a plus lieu au lobby",
            observations=(
                (
                    "Le groupe du 20 septembre a déplacé son arrivée au 4 octobre. La prépa "
                    "lobby est sans objet."
                ),
            ),
            occurred_at=_dt(2026, 9, 10, 11, 0),
            cancel_reason="Le groupe a déplacé son arrivée du 20 septembre au 4 octobre.",
        ),
        SampleRecord(
            seed_key="signal:canceled-privatisation-atelier-2",
            archetype="seminaire_privatisation",
            section="canceled",
            pole="evenements_privatisations",
            author_pole="restaurant",
            subject="evenements_privatisations__commercialisation",
            activity="privatisations",
            narrative_family="cross_pole_coordination",
            status="canceled",
            operational_unit="atelier_2",
            issue_focus="La privatisation de l'Atelier 2 du 18 a été retirée",
            observations=(
                (
                    "Le client a annulé la privatisation de l'Atelier 2 prévue le 18. Cuisine et "
                    "accueil n'ont plus à dresser."
                ),
            ),
            occurred_at=_dt(2026, 9, 9, 14, 20),
            cancel_reason=(
                "Le client a annulé la privatisation de l'Atelier 2 prévue le 18 septembre."
            ),
        ),
        SampleRecord(
            seed_key="signal:canceled-doublon-406",
            archetype="chambre_non_prete",
            section="canceled",
            pole="hotel",
            author_pole="hotel",
            subject="hotel__menage",
            activity="hebergement_chambres",
            narrative_family="process_inefficiency",
            status="canceled",
            operational_unit="chambres",
            issue_focus="La chambre 406 déjà ouverte ce matin a été ressaisie",
            observations=(
                "Une seconde fiche 406 a été créée à 16 h 40. C'est le même client déjà au lobby.",
            ),
            occurred_at=_dt(2026, 9, 21, 16, 40),
            cancel_reason="Doublon du Signal ouvert à 16 h 20 sur la chambre 406.",
        ),
        SampleRecord(
            seed_key="signal:canceled-avis-retire",
            archetype="avis_client",
            section="canceled",
            pole="communication",
            author_pole="communication",
            subject="communication__e_reputation",
            activity="communication_avis",
            narrative_family="guest_experience",
            status="canceled",
            operational_unit="back_office_administratif",
            issue_focus="L'avis Google sur l'attente au petit-déjeuner a disparu",
            observations=(
                (
                    "L'avis Google qui parlait de l'attente au petit-déjeuner a été retiré par "
                    "l'auteur avant réponse."
                ),
            ),
            occurred_at=_dt(2026, 9, 7, 10, 15),
            cancel_reason="L'auteur a retiré l'avis avant la réponse publique.",
        ),
        SampleRecord(
            seed_key="signal:canceled-extra-presente",
            archetype="staffing",
            section="canceled",
            pole="rh",
            author_pole="rh",
            subject="rh__planning",
            activity="staffing_rh",
            narrative_family="process_inefficiency",
            status="canceled",
            operational_unit="breakroom",
            issue_focus="L'extra du dîner de samedi s'est présenté",
            observations=(
                (
                    "L'extra prévu au restaurant samedi soir a fini par arriver. Le trou de "
                    "planning n'a plus lieu."
                ),
            ),
            occurred_at=_dt(2026, 9, 6, 17, 40),
            cancel_reason="L'extra s'est présenté, le service du samedi soir est couvert.",
        ),
        SampleRecord(
            seed_key="signal:canceled-clim-108",
            archetype="clim_chambre",
            section="canceled",
            pole="maintenance",
            author_pole="hotel",
            subject="maintenance__cvc",
            activity="hebergement_chambres",
            narrative_family="operational_incident",
            status="canceled",
            operational_unit="chambres",
            issue_focus="La clim de la chambre 108 est revenue avant le passage",
            observations=(
                (
                    "Réception avait signalé la 108 trop chaude. À 11 h le client dit que l'air "
                    "est froid à nouveau."
                ),
            ),
            occurred_at=_dt(2026, 8, 19, 9, 50),
            cancel_reason=(
                "Le client a confirmé que la clim de la 108 refroidit à nouveau, avant "
                "intervention."
            ),
        ),
        SampleRecord(
            seed_key="signal:canceled-file-table-8",
            archetype="service_restaurant",
            section="canceled",
            pole="restaurant",
            author_pole="restaurant",
            subject="restaurant__service_accueil",
            activity="restaurant_cuisine_salle",
            narrative_family="service_quality",
            status="canceled",
            operational_unit="restaurant_rdc",
            issue_focus="La file devant la table 8 s'est résorbée",
            observations=(
                "La table 8 de huit a été réinstallée. La file à l'entrée du restaurant a disparu.",
            ),
            occurred_at=_dt(2026, 8, 14, 20, 25),
            cancel_reason="La table 8 a été réinstallée, plus de file à l'entrée.",
        ),
        SampleRecord(
            seed_key="signal:canceled-mauvaise-chambre",
            archetype="fuite_sanitaire",
            section="canceled",
            pole="maintenance",
            author_pole="hotel",
            subject="maintenance__plomberie_eau",
            activity="hebergement_chambres",
            narrative_family="operational_incident",
            status="canceled",
            operational_unit="chambres",
            issue_focus="La fuite signalée en 412 était celle de la 414",
            observations=(
                (
                    "Ménage avait ouvert une fiche 412. Le siphon qui fuit est en 414, déjà pris "
                    "en charge."
                ),
            ),
            occurred_at=_dt(2026, 8, 3, 10, 5),
            cancel_reason="Mauvaise chambre : la fuite est celle de la 414, déjà ouverte.",
        ),
        SampleRecord(
            seed_key="signal:canceled-seminaire-deplace",
            archetype="seminaire_privatisation",
            section="canceled",
            pole="evenements_privatisations",
            author_pole="restaurant",
            subject="evenements_privatisations__experience_client",
            activity="seminaires",
            narrative_family="cross_pole_coordination",
            status="canceled",
            operational_unit="atelier_1",
            issue_focus="Le séminaire interne cuisine ne se tient plus à l'Atelier 1",
            observations=(
                (
                    "Le séminaire interne cuisine prévu à l'Atelier 1 passe en salle du "
                    "restaurant. Plus de montage Atelier."
                ),
            ),
            occurred_at=_dt(2026, 7, 22, 9, 10),
            cancel_reason=(
                "Le séminaire a été déplacé en salle restaurant, l'Atelier 1 n'est plus à monter."
            ),
        ),
        SampleRecord(
            seed_key="signal:canceled-wifi-2e",
            archetype="wifi_reseau",
            section="canceled",
            pole="maintenance",
            author_pole="hotel",
            subject="maintenance__reseau_informatique",
            activity="maintenance",
            narrative_family="operational_incident",
            status="canceled",
            operational_unit="chambres",
            issue_focus="Le wifi du 2e est revenu avant le prestataire",
            observations=(
                (
                    "Deux chambres du 2e n'avaient plus le wifi. Le réseau est revenu avant "
                    "l'arrivée du prestataire."
                ),
            ),
            occurred_at=_dt(2026, 7, 2, 18, 40),
            cancel_reason="Le wifi du 2e est revenu avant l'intervention du prestataire.",
        ),
        SampleRecord(
            seed_key="signal:canceled-clickshare-test",
            archetype="audiovisuel_salle",
            section="canceled",
            pole="evenements_privatisations",
            author_pole="maintenance",
            subject="evenements_privatisations__preparation_logistique",
            activity="ateliers_studios",
            narrative_family="cross_pole_coordination",
            status="canceled",
            operational_unit="studio_2",
            issue_focus="Le ClickShare du Studio 2 a été un faux test à vide",
            observations=(
                (
                    "Maintenance a testé le ClickShare du Studio 2 à vide. L'écran noir venait "
                    "d'un HDMI non enclenché."
                ),
            ),
            occurred_at=_dt(2026, 6, 18, 11, 30),
            cancel_reason=(
                "Faux incident : le HDMI n'était pas enclenché, l'image est revenue au test."
            ),
        ),
        SampleRecord(
            seed_key="signal:canceled-promo-site",
            archetype="accueil_lobby",
            section="canceled",
            pole="hotel",
            author_pole="hotel",
            subject="hotel__commercialisation",
            activity="reception",
            narrative_family="guest_experience",
            status="canceled",
            operational_unit="reception_lobby",
            issue_focus="Le tarif site d'un early check-in a déjà été corrigé au PMS",
            observations=(
                (
                    "Une réservation vendait un early check-in. Réception a corrigé le PMS avant "
                    "l'arrivée."
                ),
            ),
            occurred_at=_dt(2026, 6, 4, 8, 15),
            cancel_reason="L'écart de tarif early check-in a été corrigé au PMS avant l'arrivée.",
        ),
        SampleRecord(
            seed_key="signal:canceled-swap-planning",
            archetype="staffing",
            section="canceled",
            pole="rh",
            author_pole="hotel",
            subject="rh__planning",
            activity="staffing_rh",
            narrative_family="process_inefficiency",
            status="canceled",
            operational_unit="breakroom",
            issue_focus="Le trou réception de jeudi a été couvert par un échange",
            observations=(
                (
                    "Le trou à la réception jeudi matin a été couvert par un échange de shift "
                    "affiché au breakroom."
                ),
            ),
            occurred_at=_dt(2026, 5, 21, 16, 0),
            cancel_reason="Échange de shift : la réception de jeudi matin est couverte.",
        ),
        SampleRecord(
            seed_key="signal:canceled-note-table-12",
            archetype="caisse",
            section="canceled",
            pole="restaurant",
            author_pole="restaurant",
            subject="restaurant__admin",
            activity="restaurant_cuisine_salle",
            narrative_family="process_inefficiency",
            status="canceled",
            operational_unit="restaurant_rdc",
            issue_focus="La note de la table 12 a été recréditée avant réclamation",
            observations=(
                (
                    "La note de la table 12 ne collait pas. Le directeur de salle a recrédité le "
                    "dessert en trop avant le client."
                ),
            ),
            occurred_at=_dt(2026, 5, 8, 22, 10),
            cancel_reason="La note de la table 12 a été corrigée avant toute réclamation client.",
        ),
        SampleRecord(
            seed_key="signal:canceled-piscine-saison",
            archetype="saison_rooftop",
            section="canceled",
            pole="hotel",
            author_pole="hotel",
            subject="hotel__experience_client",
            activity="rooftop_piscine",
            narrative_family="prevention",
            status="canceled",
            operational_unit="piscine",
            issue_focus=(
                "Le contrôle d'ouverture au public de lundi n'a plus lieu, bassin à l'arrêt"
            ),
            observations=(
                (
                    "Le contrôle d'ouverture au public prévu lundi est annulé : le bassin est "
                    "arrêté pour un changement de filtre. Un nouveau contrôle d'ouverture au "
                    "public sera planifié après remise en eau."
                ),
            ),
            occurred_at=_dt(2026, 9, 21, 9, 10),
            cancel_reason=(
                "Le bassin est arrêté pour un changement de filtre ; "
                "un nouveau contrôle d'ouverture au public sera planifié après remise en eau."
            ),
        ),
    )


def _journeys() -> tuple[SampleRecord, ...]:
    return (
        SampleRecord(
            seed_key="signal:clim-214",
            archetype="clim_chambre",
            section="journey",
            journey="clim-chambres",
            pole="maintenance",
            author_pole="hotel",
            subject="maintenance__cvc",
            activity="hebergement_chambres",
            narrative_family="operational_incident",
            status="resolved",
            operational_unit="chambres",
            issue_focus="La clim de la chambre 214 souffle tiède",
            observations=(
                (
                    "En chambre 214 la clim tourne et l'air reste tiède. Le client l'a dit à la "
                    "réception hier soir."
                ),
            ),
            occurred_at=_dt(2025, 11, 12, 9, 10),
            pattern_seed_key="pattern:clim-chambres",
            plan_seed_key="plan:diagnostic-clim",
            execution_seed_key="exec:signal:signal:clim-214",
        ),
        SampleRecord(
            seed_key="signal:clim-426",
            archetype="clim_chambre",
            section="journey",
            journey="clim-chambres",
            pole="maintenance",
            author_pole="hotel",
            subject="maintenance__cvc",
            activity="hebergement_chambres",
            narrative_family="operational_incident",
            status="resolved",
            operational_unit="chambres",
            issue_focus="La clim de la chambre 426 s'est coupée",
            observations=(
                (
                    "La clim de la chambre 426 s'est arrêtée dans la nuit. Le client a appelé la "
                    "réception à 6 h."
                ),
            ),
            occurred_at=_dt(2026, 7, 8, 10, 5),
            pattern_seed_key="pattern:clim-chambres",
            plan_seed_key="plan:diagnostic-clim",
            execution_seed_key="exec:signal:signal:clim-426",
        ),
        SampleRecord(
            seed_key="signal:golden-clim-318",
            archetype="clim_chambre",
            section="journey",
            journey="clim-chambres",
            pole="maintenance",
            author_pole="hotel",
            subject="maintenance__cvc",
            activity="hebergement_chambres",
            narrative_family="operational_incident",
            status="resolved",
            operational_unit="chambres",
            issue_focus="La clim de la chambre 318 ne refroidit plus",
            observations=(
                "La clim de la 318 souffle mais ne refroidit plus, le client revient vers 18 h.",
                "Passage étage : air tiède en chambre 318, le client l'a redit à la réception.",
            ),
            occurred_at=_dt(2026, 9, 21, 8, 12),
            pattern_seed_key="pattern:clim-chambres",
            plan_seed_key="plan:diagnostic-clim",
            execution_seed_key="exec:signal:signal:golden-clim-318",
        ),
        SampleRecord(
            seed_key="signal:buffet-viennoiseries",
            archetype="buffet_pdj",
            section="journey",
            journey="ruptures-buffet",
            pole="petit_dejeuner",
            author_pole="petit_dejeuner",
            subject="petit_dejeuner__stock",
            activity="petit_dejeuner",
            narrative_family="service_quality",
            status="resolved",
            operational_unit="restaurant_rdc",
            issue_focus="Les viennoiseries manquent au buffet dès 8 h",
            observations=(
                "Au buffet, les viennoiseries sont vides dès 8 h, deuxième matin de la semaine.",
            ),
            occurred_at=_dt(2026, 4, 15, 8, 10),
            pattern_seed_key="pattern:ruptures-buffet",
            plan_seed_key="plan:reassort-buffet-pdj",
            execution_seed_key="exec:signal:signal:buffet-viennoiseries",
        ),
        SampleRecord(
            seed_key="signal:jus-orange",
            archetype="buffet_pdj",
            section="journey",
            journey="ruptures-buffet",
            pole="petit_dejeuner",
            author_pole="restaurant",
            subject="petit_dejeuner__stock",
            activity="petit_dejeuner",
            narrative_family="cross_pole_coordination",
            status="open",
            operational_unit="restaurant_rdc",
            issue_focus="Il manque les jus d'orange au buffet à l'ouverture",
            observations=(
                (
                    "Il manque les jus d'orange sur le buffet à l'ouverture, deuxième fois cette "
                    "semaine."
                ),
                "En cuisine, plus de bidons de jus pour le buffet de 7 h.",
            ),
            occurred_at=_dt(2026, 9, 22, 7, 12),
            pattern_seed_key="pattern:ruptures-buffet",
        ),
        SampleRecord(
            seed_key="signal:clickshare-atelier-1-historique",
            archetype="audiovisuel_salle",
            section="journey",
            journey="audiovisuel-ateliers",
            pole="evenements_privatisations",
            author_pole="evenements_privatisations",
            subject="evenements_privatisations__preparation_logistique",
            activity="ateliers_studios",
            narrative_family="operational_incident",
            status="resolved",
            operational_unit="atelier_1",
            issue_focus="Le ClickShare de l'Atelier 1 ne projetait plus en mai",
            observations=(
                "En Atelier 1, le ClickShare ne projetait plus pour un brief de deux heures.",
            ),
            occurred_at=_dt(2026, 5, 12, 9, 30),
            pattern_seed_key="pattern:audiovisuel-ateliers",
            plan_seed_key="plan:verification-clickshare",
            execution_seed_key="exec:signal:signal:clickshare-atelier-1-historique",
        ),
        SampleRecord(
            seed_key="signal:clickshare-atelier-2",
            archetype="audiovisuel_salle",
            section="journey",
            journey="audiovisuel-ateliers",
            pole="evenements_privatisations",
            author_pole="maintenance",
            subject="evenements_privatisations__preparation_logistique",
            activity="ateliers_studios",
            narrative_family="cross_pole_coordination",
            status="in_progress",
            operational_unit="atelier_2",
            issue_focus="Le ClickShare de l'Atelier 2 ne détecte aucun écran",
            observations=(
                "Le ClickShare de l'Atelier 2 ne détecte aucun écran depuis ce matin.",
                "Maintenance : HDMI et réseau testés, toujours pas d'image en Atelier 2.",
                "L'accueil du séminaire a le même écran noir à l'ouverture de salle.",
            ),
            occurred_at=_dt(2026, 9, 18, 9, 20),
            pattern_seed_key="pattern:audiovisuel-ateliers",
            plan_seed_key="plan:verification-clickshare",
            execution_seed_key="exec:signal:signal:clickshare-atelier-2",
        ),
    )


def _representatives() -> tuple[SampleRecord, ...]:
    return (
        SampleRecord(
            seed_key="signal:ci-clim-filtres",
            archetype="clim_chambre",
            section="representative",
            pole="maintenance",
            author_pole="hotel",
            subject="maintenance__cvc",
            activity="hebergement_chambres",
            narrative_family="continuous_improvement",
            status="open",
            operational_unit="chambres",
            issue_focus=(
                "Les clim du 3e reviennent tièdes à chaque arrivée, le filtre n'est jamais changé"
            ),
            observations=(
                "Trois chambres du 3e ont eu la même clim tiède depuis juillet. "
                "La cause commune est le filtre laissé en place entre deux séjours. "
                "Il faut améliorer le processus : changer le filtre au départ, pas seulement "
                "diagnostiquer pièce par pièce.",
            ),
            occurred_at=_dt(2026, 9, 20, 9, 15),
            pattern_seed_key="pattern:clim-chambres",
        ),
        SampleRecord(
            seed_key="signal:chambre-406",
            archetype="chambre_non_prete",
            section="representative",
            pole="hotel",
            author_pole="hotel",
            subject="hotel__menage",
            activity="hebergement_chambres",
            narrative_family="process_inefficiency",
            status="open",
            operational_unit="chambres",
            issue_focus="La chambre 406 n'est pas prête, le client est au lobby",
            observations=(
                "La chambre 406 n'est pas prête. Le client attend au lobby avec ses bagages.",
            ),
            occurred_at=_dt(2026, 9, 21, 16, 20),
            pattern_seed_key="pattern:chambres-non-pretes",
        ),
        SampleRecord(
            seed_key="signal:unassigned-lobby",
            archetype="accueil_lobby",
            section="representative",
            pole="hotel",
            author_pole="hotel",
            subject="hotel__experience_client",
            activity="reception",
            narrative_family="guest_experience",
            status="open",
            operational_unit="reception_lobby",
            issue_focus="Un client attend au lobby sans chambre identifiée",
            observations=(
                "Un client tourne dans le lobby. Sa réservation n'est pas encore identifiée.",
            ),
            occurred_at=_dt(2026, 9, 22, 7, 40),
            routing_unassigned=True,
        ),
        SampleRecord(
            seed_key="signal:file-diner",
            archetype="service_restaurant",
            section="representative",
            pole="restaurant",
            author_pole="restaurant",
            subject="restaurant__service_accueil",
            activity="restaurant_cuisine_salle",
            narrative_family="service_quality",
            status="open",
            operational_unit="restaurant_rdc",
            issue_focus="La file du dîner dépasse le lobby depuis vingt minutes",
            observations=(
                (
                    "La file du dîner dépasse le lobby depuis vingt minutes. Les clients "
                    "s'impatientent au restaurant."
                ),
            ),
            occurred_at=_dt(2026, 9, 21, 20, 40),
            pattern_seed_key="pattern:attente-restaurant",
        ),
        SampleRecord(
            seed_key="signal:avis-attente-pdj",
            archetype="avis_client",
            section="representative",
            pole="communication",
            author_pole="communication",
            subject="communication__e_reputation",
            activity="communication_avis",
            narrative_family="guest_experience",
            status="open",
            operational_unit="back_office_administratif",
            issue_focus="Trois avis de la semaine parlent de l'attente au petit-déjeuner",
            observations=(
                (
                    "Trois avis de la semaine parlent de l'attente au petit-déjeuner. Une "
                    "réponse publique est encore à écrire."
                ),
            ),
            occurred_at=_dt(2026, 9, 19, 14, 30),
            pattern_seed_key="pattern:avis-negatifs",
        ),
        SampleRecord(
            seed_key="signal:fuite-512",
            archetype="fuite_sanitaire",
            section="representative",
            pole="maintenance",
            author_pole="hotel",
            subject="maintenance__plomberie_eau",
            activity="hebergement_chambres",
            narrative_family="operational_incident",
            status="in_progress",
            operational_unit="chambres",
            issue_focus="Le siphon de la chambre 512 fuit encore",
            observations=(
                "Le siphon de la chambre 512 fuit encore. Une flaque revient sous le lavabo.",
            ),
            occurred_at=_dt(2026, 9, 19, 9, 40),
            pattern_seed_key="pattern:fuites",
            plan_seed_key="plan:fuite-sanitaire",
            execution_seed_key="exec:signal:signal:fuite-512",
        ),
        SampleRecord(
            seed_key="signal:borne-2",
            archetype="borne_parking",
            section="representative",
            pole="maintenance",
            author_pole="maintenance",
            subject="maintenance__equipements_dexploitation",
            activity="maintenance",
            narrative_family="operational_incident",
            status="open",
            operational_unit="bornes_electriques",
            issue_focus="La borne 2 ne démarre plus la charge",
            observations=(
                "La borne 2 du parking ne démarre plus la charge. Un badge clignote rouge.",
            ),
            occurred_at=_dt(2026, 9, 20, 11, 10),
            pattern_seed_key="pattern:bornes",
        ),
        SampleRecord(
            seed_key="signal:controle-eclairage-3e",
            archetype="eclairage",
            section="representative",
            pole="maintenance",
            author_pole="maintenance",
            subject="maintenance__electricite",
            activity="maintenance",
            narrative_family="prevention",
            status="resolved",
            operational_unit="circulations_chambres",
            issue_focus="Le contrôle éclairage du 3e a trouvé deux ampoules mortes",
            observations=(
                (
                    "Ronde du 14 septembre : deux ampoules mortes au palier du 3e, changées le "
                    "jour même."
                ),
            ),
            occurred_at=_dt(2026, 9, 14, 15, 0),
            pattern_seed_key="pattern:eclairage",
            plan_seed_key="plan:defaut-eclairage",
            execution_seed_key="exec:signal:signal:controle-eclairage-3e",
        ),
        SampleRecord(
            seed_key="signal:extras-dimanche",
            archetype="staffing",
            section="representative",
            pole="rh",
            author_pole="rh",
            subject="rh__planning",
            activity="staffing_rh",
            narrative_family="process_inefficiency",
            status="open",
            operational_unit="breakroom",
            issue_focus="Le planning du dimanche 27 Super Sunday est encore à deux extras près",
            observations=(
                "Le planning affiché au breakroom laisse Super Sunday le 27 à deux extras près.",
            ),
            occurred_at=_dt(2026, 9, 17, 10, 15),
            pattern_seed_key="pattern:sous-effectif",
        ),
        SampleRecord(
            seed_key="signal:prepa-lienders",
            archetype="audiovisuel_salle",
            section="representative",
            pole="evenements_privatisations",
            author_pole="maintenance",
            subject="evenements_privatisations__preparation_logistique",
            activity="dj_sets",
            narrative_family="cross_pole_coordination",
            status="in_progress",
            operational_unit="atelier_1",
            issue_focus="Le ClickShare de l'Atelier 1 reste à tester pour TIM LIENDERSS",
            observations=(
                "Le ClickShare de l'Atelier 1 reste à tester pour le DJ set TIM LIENDERSS du 26.",
                "Maintenance doit valider HDMI et sono avant l'accueil du 24.",
            ),
            occurred_at=_dt(2026, 9, 19, 10, 0),
            pattern_seed_key="pattern:audiovisuel-ateliers",
            plan_seed_key="plan:verification-clickshare",
            execution_seed_key="exec:signal:signal:prepa-lienders",
        ),
        SampleRecord(
            seed_key="signal:bringue-fichiers",
            archetype="evenement_public",
            section="representative",
            pole="evenements_privatisations",
            author_pole="communication",
            subject="evenements_privatisations__communication",
            activity="la_bringue",
            narrative_family="cross_pole_coordination",
            status="resolved",
            operational_unit="atelier_2",
            issue_focus="La signalétique de l'Atelier 2 pour La Bringue n'était pas calée",
            observations=(
                (
                    "Les fichiers de signalétique de l'Atelier 2 pour La Bringue du 15 octobre "
                    "n'étaient pas calés."
                ),
            ),
            occurred_at=_dt(2026, 9, 4, 11, 20),
            pattern_seed_key="pattern:signaletique-event",
        ),
        SampleRecord(
            seed_key="signal:club-sonore-sono",
            archetype="evenement_public",
            section="representative",
            pole="evenements_privatisations",
            author_pole="maintenance",
            subject="evenements_privatisations__preparation_logistique",
            activity="mama_club_sonore",
            narrative_family="prevention",
            status="resolved",
            operational_unit="atelier_1",
            issue_focus="La sono de l'Atelier 1 pour Mama Club Sonore a été testée à vide",
            observations=(
                (
                    "Test à vide le 20 août : la sono de l'Atelier 1 pour Mama Club Sonore du 22 "
                    "octobre passe."
                ),
            ),
            occurred_at=_dt(2026, 8, 20, 16, 0),
        ),
        SampleRecord(
            seed_key="signal:horizon-azur-brief",
            archetype="seminaire_privatisation",
            section="representative",
            pole="evenements_privatisations",
            author_pole="hotel",
            subject="evenements_privatisations__experience_client",
            activity="seminaires",
            narrative_family="cross_pole_coordination",
            status="open",
            operational_unit="atelier_1",
            issue_focus="Le brief de l'Atelier 1 pour le séminaire Horizon Azur n'est pas figé",
            observations=(
                "Horizon Azur, jauge 80 : le brief Atelier 1 n'est pas figé avant le 20 octobre.",
            ),
            occurred_at=_dt(2026, 9, 16, 9, 40),
        ),
        SampleRecord(
            seed_key="signal:privatisation-atelier-2-devis",
            archetype="seminaire_privatisation",
            section="representative",
            pole="evenements_privatisations",
            author_pole="restaurant",
            subject="evenements_privatisations__commercialisation",
            activity="privatisations",
            narrative_family="cross_pole_coordination",
            status="open",
            operational_unit="atelier_2",
            issue_focus="Une privatisation de l'Atelier 2 demande un devis demi-journée",
            observations=(
                (
                    "Une société demande un devis pour privatiser l'Atelier 2 une demi-journée, "
                    "sans brief restauration."
                ),
            ),
            occurred_at=_dt(2026, 9, 12, 14, 15),
        ),
        SampleRecord(
            seed_key="signal:linge-draps-8-sept",
            archetype="linge",
            section="representative",
            pole="hotel",
            author_pole="hotel",
            subject="hotel__linge",
            activity="hebergement_chambres",
            narrative_family="process_inefficiency",
            status="resolved",
            operational_unit="chambres",
            issue_focus="Le comptage du 8 septembre trouve 40 draps d'écart",
            observations=(
                "Le comptage linge du 8 septembre trouve 40 draps d'écart avec la blanchisserie.",
            ),
            occurred_at=_dt(2026, 9, 8, 7, 30),
            pattern_seed_key="pattern:linge",
            plan_seed_key="plan:rupture-linge",
            execution_seed_key="exec:signal:signal:linge-draps-8-sept",
        ),
    )


def coverage_family_records() -> dict[str, SampleRecord]:
    records = sample_records()
    preferred = [item for item in records if item.section == "representative"]
    fallback = [item for item in records if item.section != "representative"]
    chosen: dict[str, SampleRecord] = {}
    for item in preferred + fallback:
        chosen.setdefault(item.narrative_family, item)
    return chosen


def coverage_activity_records() -> dict[str, SampleRecord]:
    records = sample_records()
    preferred = [item for item in records if item.section == "representative"]
    fallback = [item for item in records if item.section != "representative"]
    chosen: dict[str, SampleRecord] = {}
    for item in preferred + fallback:
        chosen.setdefault(item.activity, item)
    return chosen


def coverage_activity_projects() -> dict[str, OverdueExecutionSpec | SampleCalendarProject]:
    chosen: dict[str, OverdueExecutionSpec | SampleCalendarProject] = {}
    for item in (*sample_overdues(), *sample_proactive_projects()):
        chosen.setdefault(item.activity, item)
    return chosen


def sample_errors() -> list[str]:
    errors: list[str] = []
    records = sample_records()
    interesting = [item for item in records if item.section == "interesting"]
    canceled = [item for item in records if item.section == "canceled"]
    journeys = [item for item in records if item.section == "journey"]
    if len(interesting) != 10:
        errors.append(f"interesting sample {len(interesting)} != 10")
    if sum(1 for item in interesting if item.interesting_kind == "vanished_technical") != 2:
        errors.append("interesting sample must include 2 vanished technical")
    if sum(1 for item in interesting if item.narrative_family == "opportunity") != 8:
        errors.append("interesting sample must include 8 opportunities")
    if len(canceled) != 15:
        errors.append(f"canceled sample {len(canceled)} != 15")
    if any(not item.cancel_reason for item in canceled):
        errors.append("every canceled sample needs its own reason")
    if {item.days_late for item in sample_overdues()} != {2, 3, 4, 5, 6, 7}:
        errors.append("overdue sample days must be 2 through 7")
    if len(sample_proactive_projects()) < 5:
        errors.append("proactive sample is incomplete")
    if {item.journey for item in journeys} != {
        "clim-chambres",
        "ruptures-buffet",
        "audiovisuel-ateliers",
    }:
        errors.append("sample must contain three named Pattern journeys")
    family_coverage = coverage_family_records()
    if set(NARRATIVE_FAMILIES) - family_coverage.keys():
        missing_families = sorted(set(NARRATIVE_FAMILIES) - family_coverage.keys())
        errors.append(f"representative file misses families: {missing_families}")
    activity_coverage = coverage_activity_records() | coverage_activity_projects()
    if set(MAMA_NICE_ACTIVITIES) - activity_coverage.keys():
        missing_activities = sorted(set(MAMA_NICE_ACTIVITIES) - activity_coverage.keys())
        errors.append(f"representative file misses activities: {missing_activities}")
    if any(
        item.plan_seed_key or item.execution_seed_key for item in records if item.status == "open"
    ):
        errors.append("open Signals cannot already have a plan or execution")
    if any(
        not item.plan_seed_key or not item.execution_seed_key
        for item in records
        if item.status == "in_progress"
    ):
        errors.append("in_progress Signals need both a plan and an execution")
    if any(
        item.archetype == "accueil_lobby" and "bruit" in item.issue_focus.casefold()
        for item in records
    ):
        errors.append("room noise cannot use the lobby archetype")
    if not any(item.activity == "super_sunday" for item in sample_proactive_projects()):
        errors.append("Super Sunday must appear as a proactive project without Signal")
    if any(item.activity == "super_sunday" for item in records):
        errors.append("Super Sunday must not also have a Signal in the sample")
    for spec in sample_overdues():
        if spec.seed_key in {
            "exec:overdue:integration-reception",
            "exec:overdue:signaletique-bringue",
        }:
            if not spec.oneshot_tasks or spec.plan_seed_key.startswith("plan:"):
                errors.append(f"{spec.seed_key} needs an adapted one-shot plan")
    bringue = next(item for item in sample_overdues() if item.days_late == 2)
    if bringue.title != "Valider le BAT de la signalétique de La Bringue":
        errors.append("La Bringue overdue title must be the BAT one-shot")
    if any(
        "photograph" in task.casefold() or task.casefold().startswith("imprimer")
        for task in bringue.oneshot_tasks
    ):
        errors.append("La Bringue BAT must not treat pose or photo as already done")
    if any("plus de repro" in item.issue_focus.casefold() for item in records):
        errors.append("flagged labels still use plus de repro")
    if any(
        "18 octobre" in (item.cancel_reason or "")
        for item in canceled
        if "piscine" in item.seed_key
    ):
        errors.append("pool cancellation cannot use the October seasonal closure")
    if any(
        "contrôle eau client"
        in " ".join((item.issue_focus, *item.observations, item.cancel_reason or "")).casefold()
        for item in records
    ):
        errors.append("pool copy still uses contrôle eau client")
    if any(
        "contrôle chlore client"
        in " ".join((item.issue_focus, *item.observations, item.cancel_reason or "")).casefold()
        for item in records
    ):
        errors.append("pool copy still uses contrôle chlore client")
    if any("recreditee" in item.issue_focus.casefold() for item in records):
        errors.append("table 12 still uses recréditee")
    ci_example = coverage_family_records().get("continuous_improvement")
    if (
        ci_example is None
        or ci_example.seed_key != "signal:ci-clim-filtres"
        or ci_example.plan_seed_key
    ):
        errors.append(
            "representative CI example must be the open clim process Signal without a plan"
        )
    if any(
        item.section == "journey" and item.narrative_family == "continuous_improvement"
        for item in journeys
    ):
        errors.append("unit Pattern incidents cannot be labeled continuous improvement")
    future = frozen_future_executions()
    month_counts = Counter(_month_key(item.start_at) for item in future)
    if dict(month_counts) != FUTURE_BY_MONTH:
        errors.append(f"frozen future month totals changed: {dict(sorted(month_counts.items()))}")
    identities = {future_execution_identity(item) for item in future}
    bound: list[str] = []
    by_id = _future_by_id()
    for project in sample_proactive_projects():
        if project.execution_seed_key not in identities:
            errors.append(f"{project.title}: no identifiable frozen execution")
            continue
        if project.execution_seed_key in bound:
            errors.append(f"{project.execution_seed_key} is bound twice")
        bound.append(project.execution_seed_key)
        match = by_id[project.execution_seed_key]
        if project.kind == "schedule" and not isinstance(match, CompiledOccurrence):
            errors.append(f"{project.title}: schedule presented as a oneshot")
        if project.kind == "oneshot" and not isinstance(match, CompiledOneshot):
            errors.append(f"{project.title}: oneshot presented as a schedule")
        if project.start_at != match.start_at or project.end_at != match.end_at:
            errors.append(f"{project.title}: dates diverge from the frozen calendar")
        if project.counted_month != _month_key(match.start_at):
            errors.append(f"{project.title}: counted month diverges from the frozen calendar")
        if project.kind == "schedule" and project.schedule_id is None:
            errors.append(f"{project.title}: schedule_id missing")
        if project.kind == "oneshot" and project.schedule_id is not None:
            errors.append(f"{project.title}: oneshot cannot carry a schedule_id")
    super_sunday = next(
        item for item in sample_proactive_projects() if item.activity == "super_sunday"
    )
    if super_sunday.kind != "schedule" or super_sunday.schedule_id != "schedule:super-sunday":
        errors.append("Super Sunday must reuse schedule #7")
    if (
        "événement dj" in super_sunday.plan_title.casefold()
        or super_sunday.plan_seed_key == "plan:preparation-evenement-dj"
    ):
        errors.append("Super Sunday must not use the DJ event-prep plan label")
    horizon = next(
        item for item in sample_proactive_projects() if "horizon" in item.execution_seed_key
    )
    if horizon.counted_month != (2026, 11) or horizon.start_at.date() != date(2026, 11, 10):
        errors.append("Horizon Azur must be counted in November")
    if horizon.plan_created_at.date() != date(2026, 10, 20):
        errors.append("Horizon Azur plan creation must stay on 20 October")
    tim = next(
        item for item in sample_proactive_projects() if "tim-lienderss" in item.execution_seed_key
    )
    if tim.start_at.date() != date(2026, 9, 24) or tim.end_at.date() != date(2026, 9, 26):
        errors.append("TIM LIENDERSS must cover 24-26 September on its existing future line")
    if (super_sunday.end_at - super_sunday.start_at) > timedelta(hours=4):
        errors.append("Super Sunday must stay an hourly schedule occurrence")
    for item in records:
        texts = (item.issue_focus, *item.observations, item.cancel_reason or "")
        if item.narrative_family == "continuous_improvement" and not (
            continuous_improvement_justified(texts)
        ):
            errors.append(
                f"{item.seed_key}: continuous improvement is not justified by the content"
            )
    keys = [item.seed_key for item in records]
    if len(keys) != len(set(keys)):
        errors.append("sample seed keys must be unique")
    focuses = [item.issue_focus for item in records]
    if len(focuses) != len(set(focuses)):
        errors.append("sample focuses must be unique")
    for item in records:
        if item.archetype not in ARCHETYPES:
            errors.append(f"{item.seed_key}: unknown archetype")
            continue
        errors.extend(
            archetype_errors(
                archetype_key=item.archetype,
                family=item.narrative_family,
                author_pole=item.author_pole,
                responsible_pole=item.pole,
                activity=item.activity,
                status=item.status,
                pattern_seed_key=item.pattern_seed_key,
                plan_seed_key=item.plan_seed_key,
                texts=(item.issue_focus, *item.observations, item.cancel_reason or ""),
                routing_unassigned=item.routing_unassigned,
                execution_seed_key=item.execution_seed_key,
            )
        )
        if item.status == "canceled" and item.cancel_reason:
            if (
                item.cancel_reason.casefold().split()[0:3]
                == item.issue_focus.casefold().split()[0:3]
            ):
                pass
    return errors
