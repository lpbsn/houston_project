"""Authored Mama Nice scenarios. The compiler expands these records only."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from houston.establishments.mama_nice_dataset_archetypes import (
    ARCHETYPES,
    FORBIDDEN_GENERIC_CLAUSES,
    continuous_improvement_justified,
    in_progress_relation_errors,
    infer_archetype,
    is_oneshot_plan,
)
from houston.establishments.mama_nice_dataset_clock import operational_now, overdue_end_at
from houston.establishments.mama_nice_dataset_constants import (
    ACTIVE_SIGNAL_MAX_AGE_DAYS,
    ESTABLISHMENT_NAME_FRAGMENTS,
    INFORMATIONAL_OBSERVATION_COUNT,
    INTERESTING_VANISHED_TECHNICAL_MAX,
    MAMA_NICE_ACTIVITIES,
    NARRATIVE_FAMILIES,
    NARRATIVE_FAMILY_COUNTS,
    OBSERVATION_SOURCE_LAYOUT,
    OVERDUE_EXECUTION_COUNT,
    OVERDUE_MAX_DAYS,
    OVERDUE_MIN_DAYS,
    PARIS_TZ,
    SIGNAL_COUNTS_BY_POLE,
    SIGNAL_STATUS_COUNTS,
    SNAPSHOT,
    TOTAL_SIGNALS,
    UNASSIGNED_OPEN_SIGNALS,
)
from houston.establishments.mama_nice_dataset_copy import (
    PATTERN_BY_TOPIC,
    PATTERN_POLE,
    PATTERN_QUOTA,
    POLE_UNITS,
    SUBJECT_HINTS,
    UNIT_HINTS,
    informational_texts,
)
from houston.establishments.mama_nice_dataset_editorial import (
    EVENT_KEYWORDS,
    author_for,
    cancel_reason_for,
    infer_activity,
    infer_family,
    infer_topic,
    pattern_for,
)
from houston.establishments.mama_nice_dataset_justifications import (
    justify_family,
    rewrite_for_topic,
)
from houston.establishments.mama_nice_dataset_situations import ROWS

FAMILIES = NARRATIVE_FAMILIES


@dataclass(frozen=True)
class ScenarioRelations:
    observation_seed_keys: tuple[str, ...]
    signal_seed_key: str
    pattern_seed_key: str | None = None
    plan_seed_key: str | None = None
    execution_seed_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuthoredScenario:
    seed_key: str
    pole: str
    subject: str
    activity: str
    narrative_family: str
    status: str
    operational_unit: str
    issue_focus: str
    canonical_object: str
    observations: tuple[str, ...]
    occurred_at: datetime
    author_pole: str
    routing_unassigned: bool = False
    pattern_seed_key: str | None = None
    plan_seed_key: str | None = None
    execution_seed_key: str | None = None
    interesting_kind: str | None = None
    topic: str | None = None
    cancel_reason: str | None = None
    oneshot_title: str | None = None
    oneshot_tasks: tuple[str, ...] = ()

    @property
    def relations(self) -> ScenarioRelations:
        obs = tuple(f"obs:{self.seed_key}:{index + 1}" for index in range(len(self.observations)))
        executions = (self.execution_seed_key,) if self.execution_seed_key else ()
        return ScenarioRelations(
            observation_seed_keys=obs,
            signal_seed_key=self.seed_key,
            pattern_seed_key=self.pattern_seed_key,
            plan_seed_key=self.plan_seed_key,
            execution_seed_keys=executions,
        )


@dataclass(frozen=True)
class ProactiveProjectSpec:
    seed_key: str
    title: str
    pole: str
    activity: str
    plan_seed_key: str
    start_at: datetime
    end_at: datetime
    context: str
    signal_seed_key: None = None
    oneshot_title: str | None = None
    oneshot_tasks: tuple[str, ...] = ()


@dataclass(frozen=True)
class OverdueExecutionSpec:
    seed_key: str
    title: str
    pole: str
    activity: str
    narrative_family: str
    days_late: int
    end_at: datetime
    context: str
    plan_seed_key: str
    oneshot_title: str | None = None
    oneshot_tasks: tuple[str, ...] = ()


ROOFTOP_CLOSURE_IDENTITY = "schedule:controle-rooftop:2026-09-23"
ROOFTOP_CLOSURE_TASKS = (
    "Ranger et sécuriser le mobilier rooftop",
    "Isoler les arrivées d'eau et l'alimentation du rooftop",
    "Couvrir ou hiverner les équipements piscine",
    "Retirer la communication saisonnière rooftop et piscine",
    "Consigner la fermeture de saison",
)
ROOFTOP_OPENING_TOKENS = ("ouverture", "valider l'ouverture")

PLAN_BY_PATTERN = {
    "pattern:clim-chambres": "plan:diagnostic-clim",
    "pattern:linge": "plan:rupture-linge",
    "pattern:chambres-non-pretes": "plan:rattrapage-chambre",
    "pattern:attente-checkin": "plan:rattrapage-chambre",
    "pattern:facturation-caisse": "plan:anomalie-caisse",
    "pattern:piscine": "plan:ouverture-saison-rooftop-piscine",
    "pattern:ruptures-buffet": "plan:reassort-buffet-pdj",
    "pattern:equipements-cafe": "plan:reassort-buffet-pdj",
    "pattern:proprete-buffet": "plan:remise-conformite-buffet",
    "pattern:attente-restaurant": "plan:incident-service-resto",
    "pattern:erreurs-service": "plan:incident-service-resto",
    "pattern:ruptures-bar": "plan:incident-service-resto",
    "pattern:cloture-caisse": "plan:anomalie-caisse",
    "pattern:evacuations-cuisine": "plan:incident-service-resto",
    "pattern:equipements-rooftop": "plan:ouverture-saison-rooftop-piscine",
    "pattern:audiovisuel-ateliers": "plan:verification-clickshare",
    "pattern:eclairage": "plan:defaut-eclairage",
    "pattern:fuites": "plan:fuite-sanitaire",
    "pattern:bornes": "plan:borne-electrique",
    "pattern:signaletique-event": "plan:preparation-evenement-dj",
    "pattern:avis-negatifs": "plan:avis-client-negatif",
    "pattern:sous-effectif": "plan:runtime-rh-routines",
}

FOLLOW_UPS = (
    "Je le vois aussi au passage d'étage.",
    "La réception a la même info à l'instant.",
    "Cuisine et salle ont le même constat.",
    "Maintenance confirme sur place.",
    "L'accueil événement le voit aussi.",
    "Le client vient de le redire au lobby.",
    "Le brief de shift retombe sur le même écart.",
    "Le responsable de zone vient de le valider.",
)


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(hint.casefold() in folded for hint in hints)


def activity_for(*, pole: str, unit: str, focus: str) -> str:
    return infer_activity(pole=pole, unit=unit, focus=focus)


def _named_overrides() -> dict[str, dict]:
    return {
        "signal:golden-clim-318": {
            "pole": "maintenance",
            "subject": "maintenance__cvc",
            "activity": "hebergement_chambres",
            "narrative_family": "operational_incident",
            "status": "resolved",
            "operational_unit": "chambres",
            "issue_focus": "La clim de la chambre 318 ne refroidit plus",
            "canonical_object": "la climatisation",
            "observations": (
                "La clim de la 318 souffle mais ne refroidit plus, le client revient vers 18 h.",
                (
                    "Je confirme à l'étage : air tiède en chambre 318, le client l'a redit à la "
                    "réception."
                ),
            ),
            "occurred_at": datetime(2026, 9, 21, 8, 12, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
            "pattern_seed_key": "pattern:clim-chambres",
            "plan_seed_key": "plan:diagnostic-clim",
            "execution_seed_key": "exec:signal:signal:golden-clim-318",
            "topic": "clim",
        },
        "signal:clim-214": {
            "pole": "maintenance",
            "subject": "maintenance__cvc",
            "activity": "hebergement_chambres",
            "narrative_family": "operational_incident",
            "status": "resolved",
            "operational_unit": "chambres",
            "issue_focus": "La clim de la chambre 214 souffle tiède",
            "canonical_object": "la climatisation",
            "observations": (
                (
                    "En chambre 214 la clim tourne et l'air reste tiède, le client l'a signalé "
                    "hier soir."
                ),
            ),
            "occurred_at": datetime(2025, 11, 12, 9, 10, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
            "pattern_seed_key": "pattern:clim-chambres",
            "plan_seed_key": "plan:diagnostic-clim",
            "execution_seed_key": "exec:signal:signal:clim-214",
            "topic": "clim",
        },
        "signal:clim-426": {
            "pole": "maintenance",
            "subject": "maintenance__cvc",
            "activity": "hebergement_chambres",
            "narrative_family": "operational_incident",
            "status": "resolved",
            "operational_unit": "chambres",
            "issue_focus": "La clim de la chambre 426 s'est coupée",
            "canonical_object": "la climatisation",
            "observations": (
                (
                    "La clim de la chambre 426 s'est arrêtée dans la nuit, le client a appelé la "
                    "réception à 6 h."
                ),
            ),
            "occurred_at": datetime(2026, 7, 8, 10, 5, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
            "pattern_seed_key": "pattern:clim-chambres",
            "plan_seed_key": "plan:diagnostic-clim",
            "execution_seed_key": "exec:signal:signal:clim-426",
            "topic": "clim",
        },
        "signal:jus-orange": {
            "pole": "petit_dejeuner",
            "subject": "petit_dejeuner__stock",
            "activity": "petit_dejeuner",
            "narrative_family": "cross_pole_coordination",
            "status": "open",
            "operational_unit": "restaurant_rdc",
            "issue_focus": "Il manque les jus d'orange au buffet à l'ouverture",
            "canonical_object": "les jus d'orange",
            "observations": (
                (
                    "Il manque encore les jus d'orange sur le buffet, deuxième fois cette "
                    "semaine à l'ouverture."
                ),
                "En cuisine on n'a plus de bidons de jus pour le buffet de 7 h.",
            ),
            "occurred_at": datetime(2026, 9, 22, 7, 12, tzinfo=PARIS_TZ),
            "author_pole": "restaurant",
            "pattern_seed_key": "pattern:ruptures-buffet",
            "topic": "buffet",
        },
        "signal:ci-clim-filtres": {
            "pole": "maintenance",
            "subject": "maintenance__cvc",
            "activity": "hebergement_chambres",
            "narrative_family": "continuous_improvement",
            "status": "open",
            "operational_unit": "chambres",
            "issue_focus": (
                "Les clim du 3e reviennent tièdes à chaque arrivée, le filtre n'est jamais changé"
            ),
            "canonical_object": "les filtres clim du 3e",
            "observations": (
                "Trois chambres du 3e ont eu la même clim tiède depuis juillet. "
                "La cause commune est le filtre laissé en place entre deux séjours. "
                "Il faut améliorer le processus : changer le filtre au départ, pas seulement "
                "diagnostiquer pièce par pièce.",
            ),
            "occurred_at": datetime(2026, 9, 20, 9, 15, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
            "pattern_seed_key": "pattern:clim-chambres",
            "topic": "clim",
        },
        "signal:clickshare-atelier-2": {
            "pole": "evenements_privatisations",
            "subject": "evenements_privatisations__preparation_logistique",
            "activity": "ateliers_studios",
            "narrative_family": "cross_pole_coordination",
            "status": "in_progress",
            "operational_unit": "atelier_2",
            "issue_focus": "Le ClickShare de l'Atelier 2 ne détecte aucun écran",
            "canonical_object": "le ClickShare",
            "observations": (
                "Le ClickShare de l'Atelier 2 ne détecte aucun écran depuis ce matin.",
                "Maintenance : HDMI et réseau testés, toujours pas d'image en Atelier 2.",
                "L'accueil du séminaire a le même écran noir à l'ouverture de salle.",
            ),
            "occurred_at": datetime(2026, 9, 18, 9, 20, tzinfo=PARIS_TZ),
            "author_pole": "maintenance",
            "pattern_seed_key": "pattern:audiovisuel-ateliers",
            "plan_seed_key": "plan:verification-clickshare",
            "execution_seed_key": "exec:signal:signal:clickshare-atelier-2",
            "topic": "audiovisuel",
        },
        "signal:chambre-406": {
            "pole": "hotel",
            "subject": "hotel__menage",
            "activity": "hebergement_chambres",
            "narrative_family": "process_inefficiency",
            "status": "open",
            "operational_unit": "chambres",
            "issue_focus": "La chambre 406 n'est pas prête, le client est au lobby",
            "canonical_object": "la chambre 406",
            "observations": (
                "La chambre 406 n'est pas prête, le client attend au lobby avec ses bagages.",
            ),
            "occurred_at": datetime(2026, 9, 21, 16, 20, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
            "pattern_seed_key": "pattern:chambres-non-pretes",
            "topic": "chambre_prete",
        },
        "signal:file-diner": {
            "pole": "restaurant",
            "subject": "restaurant__service_accueil",
            "activity": "restaurant_cuisine_salle",
            "narrative_family": "service_quality",
            "status": "open",
            "operational_unit": "restaurant_rdc",
            "issue_focus": "La file du dîner dépasse le lobby depuis vingt minutes",
            "canonical_object": "la file du dîner",
            "observations": (
                (
                    "La file du dîner dépasse le lobby depuis vingt minutes, les clients "
                    "s'impatientent au restaurant."
                ),
            ),
            "occurred_at": datetime(2026, 9, 21, 20, 40, tzinfo=PARIS_TZ),
            "author_pole": "restaurant",
            "pattern_seed_key": "pattern:attente-restaurant",
            "topic": "attente_resto",
        },
        "signal:borne-2": {
            "pole": "maintenance",
            "subject": "maintenance__equipements_dexploitation",
            "activity": "maintenance",
            "narrative_family": "operational_incident",
            "status": "open",
            "operational_unit": "bornes_electriques",
            "issue_focus": "La borne 2 ne démarre plus la charge",
            "canonical_object": "la borne 2",
            "observations": (
                "La borne 2 du parking ne démarre plus la charge, un badge clignote rouge.",
            ),
            "occurred_at": datetime(2026, 9, 20, 11, 10, tzinfo=PARIS_TZ),
            "author_pole": "maintenance",
            "pattern_seed_key": "pattern:bornes",
            "topic": "borne",
        },
        "signal:avis-attente-pdj": {
            "pole": "communication",
            "subject": "communication__e_reputation",
            "activity": "communication_avis",
            "narrative_family": "guest_experience",
            "status": "open",
            "operational_unit": "back_office_administratif",
            "issue_focus": "Trois avis de la semaine parlent de l'attente au petit-déjeuner",
            "canonical_object": "les avis petit-déjeuner",
            "observations": (
                (
                    "Trois avis de la semaine parlent de l'attente au petit-déjeuner, le "
                    "back-office doit répondre."
                ),
            ),
            "occurred_at": datetime(2026, 9, 19, 14, 30, tzinfo=PARIS_TZ),
            "author_pole": "communication",
            "pattern_seed_key": "pattern:avis-negatifs",
            "topic": "avis",
        },
        "signal:extras-dimanche": {
            "pole": "rh",
            "subject": "rh__planning",
            "activity": "staffing_rh",
            "narrative_family": "process_inefficiency",
            "status": "open",
            "operational_unit": "breakroom",
            "issue_focus": "Le planning du dimanche 27 est encore à deux extras près",
            "canonical_object": "le staffing du dimanche",
            "observations": (
                (
                    "Le planning du dimanche 27 Super Sunday est encore à deux extras près, "
                    "affiché au breakroom."
                ),
            ),
            "occurred_at": datetime(2026, 9, 17, 10, 15, tzinfo=PARIS_TZ),
            "author_pole": "rh",
            "pattern_seed_key": "pattern:sous-effectif",
            "topic": "effectif",
        },
        "signal:fuite-512": {
            "pole": "maintenance",
            "subject": "maintenance__plomberie_eau",
            "activity": "hebergement_chambres",
            "narrative_family": "operational_incident",
            "status": "in_progress",
            "operational_unit": "chambres",
            "issue_focus": "Le siphon de la chambre 512 fuit encore",
            "canonical_object": "le siphon",
            "observations": (
                "Le siphon de la chambre 512 fuit encore, une flaque revient sous le lavabo.",
            ),
            "occurred_at": datetime(2026, 9, 19, 9, 40, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
            "pattern_seed_key": "pattern:fuites",
            "plan_seed_key": "plan:fuite-sanitaire",
            "execution_seed_key": "exec:signal:signal:fuite-512",
            "topic": "fuite",
        },
        "signal:unassigned-lobby": {
            "pole": "hotel",
            "subject": "hotel__experience_client",
            "activity": "reception",
            "narrative_family": "guest_experience",
            "status": "open",
            "operational_unit": "reception_lobby",
            "issue_focus": "Un client attend au lobby sans chambre identifiée",
            "canonical_object": "l'accueil",
            "observations": (
                "Un client tourne dans le lobby, sa réservation n'est pas encore identifiée.",
            ),
            "occurred_at": datetime(2026, 9, 22, 7, 40, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
            "routing_unassigned": True,
        },
        "signal:unassigned-note": {
            "pole": "restaurant",
            "subject": "restaurant__admin",
            "activity": "restaurant_cuisine_salle",
            "narrative_family": "service_quality",
            "status": "open",
            "operational_unit": "restaurant_rdc",
            "issue_focus": "La note de la table 12 du restaurant ne correspond pas à la commande",
            "canonical_object": "la note",
            "observations": (
                (
                    "La note de la table 12 du restaurant ne correspond pas à la commande, le "
                    "client attend en salle."
                ),
            ),
            "occurred_at": datetime(2026, 9, 22, 9, 5, tzinfo=PARIS_TZ),
            "author_pole": "restaurant",
            "routing_unassigned": True,
        },
        "signal:groupe-deplace": {
            "pole": "hotel",
            "subject": "hotel__commercialisation",
            "activity": "reception",
            "narrative_family": "guest_experience",
            "status": "canceled",
            "operational_unit": "reception_lobby",
            "issue_focus": "La réservation du groupe du 20 n'a plus de prépa au lobby",
            "canonical_object": "la prépa groupe",
            "observations": (
                "La réservation du groupe du 20 a été déplacée, plus de prépa à caler au lobby.",
            ),
            "occurred_at": datetime(2026, 9, 10, 11, 0, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
            "cancel_reason": "Le client a déplacé la date, la préparation n'a plus lieu.",
        },
        "signal:prepa-lienders": {
            "pole": "evenements_privatisations",
            "subject": "evenements_privatisations__preparation_logistique",
            "activity": "dj_sets",
            "narrative_family": "cross_pole_coordination",
            "status": "in_progress",
            "operational_unit": "atelier_1",
            "issue_focus": "Le ClickShare de l'Atelier 1 reste à tester pour TIM LIENDERSS",
            "canonical_object": "le ClickShare",
            "observations": (
                "Le ClickShare de l'Atelier 1 reste à tester pour le DJ set TIM LIENDERSS du 26.",
                "Maintenance doit valider HDMI et sono avant l'accueil du 24.",
            ),
            "occurred_at": datetime(2026, 9, 19, 10, 0, tzinfo=PARIS_TZ),
            "author_pole": "maintenance",
            "pattern_seed_key": "pattern:audiovisuel-ateliers",
            "plan_seed_key": "plan:verification-clickshare",
            "execution_seed_key": "exec:signal:signal:prepa-lienders",
            "topic": "audiovisuel",
        },
        "signal:super-sunday-jauge": {
            "pole": "evenements_privatisations",
            "subject": "evenements_privatisations__rh_planning",
            "activity": "super_sunday",
            "narrative_family": "cross_pole_coordination",
            "status": "open",
            "operational_unit": "studio_1",
            "issue_focus": "Le planning du Studio 1 n'a pas d'accueil dédié pour Super Sunday",
            "canonical_object": "l'accueil Super Sunday",
            "observations": (
                (
                    "Pour Super Sunday le 27, le Studio 1 n'a toujours pas d'accueil dédié au "
                    "planning."
                ),
            ),
            "occurred_at": datetime(2026, 9, 18, 15, 10, tzinfo=PARIS_TZ),
            "author_pole": "rh",
        },
        "signal:bringue-signaletique": {
            "pole": "evenements_privatisations",
            "subject": "evenements_privatisations__communication",
            "activity": "la_bringue",
            "narrative_family": "cross_pole_coordination",
            "status": "resolved",
            "operational_unit": "atelier_2",
            "issue_focus": "La signalétique de l'Atelier 2 pour La Bringue n'était pas calée",
            "canonical_object": "la signalétique Bringue",
            "observations": (
                "La signalétique de l'Atelier 2 pour La Bringue du 15 octobre n'était pas calée.",
            ),
            "occurred_at": datetime(2026, 9, 4, 11, 20, tzinfo=PARIS_TZ),
            "author_pole": "communication",
            "pattern_seed_key": "pattern:signaletique-event",
            "topic": "signaletique",
        },
        "signal:club-sonore-sono": {
            "pole": "evenements_privatisations",
            "subject": "evenements_privatisations__preparation_logistique",
            "activity": "mama_club_sonore",
            "narrative_family": "prevention",
            "status": "resolved",
            "operational_unit": "atelier_1",
            "issue_focus": "La sono de l'Atelier 1 pour Mama Club Sonore n'avait pas été testée",
            "canonical_object": "la sono Club Sonore",
            "observations": (
                (
                    "La sono de l'Atelier 1 pour Mama Club Sonore du 22 octobre n'avait pas été "
                    "testée."
                ),
            ),
            "occurred_at": datetime(2026, 8, 20, 16, 0, tzinfo=PARIS_TZ),
            "author_pole": "maintenance",
            "pattern_seed_key": "pattern:audiovisuel-ateliers",
            "topic": "audiovisuel",
        },
        "signal:horizon-azur-brief": {
            "pole": "evenements_privatisations",
            "subject": "evenements_privatisations__experience_client",
            "activity": "seminaires",
            "narrative_family": "cross_pole_coordination",
            "status": "open",
            "operational_unit": "atelier_1",
            "issue_focus": "Le brief de l'Atelier 1 pour le séminaire Horizon Azur n'est pas figé",
            "canonical_object": "le brief Horizon Azur",
            "observations": (
                "Horizon Azur, jauge 80 : le brief Atelier 1 n'est pas figé avant le 20 octobre.",
            ),
            "occurred_at": datetime(2026, 9, 16, 9, 40, tzinfo=PARIS_TZ),
            "author_pole": "evenements_privatisations",
        },
        "signal:privatisation-ateliers": {
            "pole": "evenements_privatisations",
            "subject": "evenements_privatisations__commercialisation",
            "activity": "privatisations",
            "narrative_family": "cross_pole_coordination",
            "status": "open",
            "operational_unit": "atelier_2",
            "issue_focus": "Une privatisation de l'Atelier 2 demande un devis demi-journée",
            "canonical_object": "le devis de privatisation",
            "observations": (
                (
                    "Une privatisation de l'Atelier 2 demande un devis demi-journée, sans brief "
                    "encore."
                ),
            ),
            "occurred_at": datetime(2026, 9, 12, 14, 15, tzinfo=PARIS_TZ),
            "author_pole": "evenements_privatisations",
        },
    }


def _interesting_overrides() -> dict[str, dict]:
    return {
        "signal:interesting-bruit-3e": {
            "pole": "hotel",
            "subject": "hotel__experience_client",
            "activity": "hebergement_chambres",
            "narrative_family": "opportunity",
            "status": "interesting",
            "interesting_kind": "opportunity",
            "operational_unit": "circulations_chambres",
            "issue_focus": "Les départs du 3e mentionnent le bruit du couloir en chambre",
            "canonical_object": "le bruit du couloir",
            "observations": (
                (
                    "Les départs du 3e mentionnent le bruit du couloir en chambre, sans numéro "
                    "en cause."
                ),
            ),
            "occurred_at": datetime(2026, 9, 16, 11, 20, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
        },
        "signal:interesting-late-sunday": {
            "pole": "hotel",
            "subject": "hotel__check_in_out",
            "activity": "reception",
            "narrative_family": "opportunity",
            "status": "interesting",
            "interesting_kind": "opportunity",
            "operational_unit": "reception_lobby",
            "issue_focus": "Des clients demandent un check-out tardif le dimanche de Super Sunday",
            "canonical_object": "le late check-out",
            "observations": (
                (
                    "Plusieurs clients demandent un check-out tardif à la réception le dimanche "
                    "de Super Sunday."
                ),
            ),
            "occurred_at": datetime(2026, 9, 15, 16, 10, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
        },
        "signal:interesting-sans-gluten": {
            "pole": "petit_dejeuner",
            "subject": "petit_dejeuner__menu",
            "activity": "petit_dejeuner",
            "narrative_family": "opportunity",
            "status": "interesting",
            "interesting_kind": "opportunity",
            "operational_unit": "restaurant_rdc",
            "issue_focus": (
                "Des clients cherchent une option sans gluten plus visible sur le buffet"
            ),
            "canonical_object": "l'offre sans gluten",
            "observations": (
                "Des clients cherchent une option sans gluten plus visible sur le buffet.",
            ),
            "occurred_at": datetime(2026, 9, 14, 8, 25, tzinfo=PARIS_TZ),
            "author_pole": "petit_dejeuner",
        },
        "signal:interesting-file-vendredi": {
            "pole": "restaurant",
            "subject": "restaurant__service_accueil",
            "activity": "restaurant_cuisine_salle",
            "narrative_family": "opportunity",
            "status": "interesting",
            "interesting_kind": "opportunity",
            "operational_unit": "restaurant_rdc",
            "issue_focus": "La file du vendredi s'allonge avant 20 h, sous le seuil d'incident",
            "canonical_object": "la file du vendredi",
            "observations": (
                "La file du vendredi s'allonge avant 20 h, sans encore bloquer le restaurant.",
            ),
            "occurred_at": datetime(2026, 9, 12, 20, 5, tzinfo=PARIS_TZ),
            "author_pole": "restaurant",
        },
        "signal:interesting-table-rooftop": {
            "pole": "restaurant",
            "subject": "restaurant__experience_client",
            "activity": "rooftop_piscine",
            "narrative_family": "opportunity",
            "status": "interesting",
            "interesting_kind": "opportunity",
            "operational_unit": "rooftop",
            "issue_focus": "Les groupes du rooftop aimeraient garder la table après le dessert",
            "canonical_object": "la table du rooftop",
            "observations": (
                (
                    "Les groupes du rooftop aimeraient garder la table après le dessert, en fin "
                    "de saison."
                ),
            ),
            "occurred_at": datetime(2026, 9, 13, 22, 10, tzinfo=PARIS_TZ),
            "author_pole": "restaurant",
        },
        "signal:interesting-brunch": {
            "pole": "communication",
            "subject": "communication__communication_commerciale",
            "activity": "communication_avis",
            "narrative_family": "opportunity",
            "status": "interesting",
            "interesting_kind": "opportunity",
            "operational_unit": "back_office_administratif",
            "issue_focus": (
                "Les avis citent le brunch du dimanche, piste d'offre avant Super Sunday"
            ),
            "canonical_object": "le brunch du dimanche",
            "observations": (
                (
                    "Les avis citent le brunch du dimanche, une offre à travailler au bureau "
                    "avant Super Sunday."
                ),
            ),
            "occurred_at": datetime(2026, 9, 11, 15, 40, tzinfo=PARIS_TZ),
            "author_pole": "communication",
        },
        "signal:interesting-studios": {
            "pole": "evenements_privatisations",
            "subject": "evenements_privatisations__commercialisation",
            "activity": "ateliers_studios",
            "narrative_family": "opportunity",
            "status": "interesting",
            "interesting_kind": "opportunity",
            "operational_unit": "studio_1",
            "issue_focus": "Des sociétés demandent le Studio 1 pour des demi-journées",
            "canonical_object": "le Studio 1",
            "observations": (
                (
                    "Des sociétés demandent le Studio 1 pour des demi-journées, pas seulement "
                    "les Ateliers."
                ),
            ),
            "occurred_at": datetime(2026, 9, 10, 11, 50, tzinfo=PARIS_TZ),
            "author_pole": "evenements_privatisations",
        },
        "signal:interesting-extras-sunday": {
            "pole": "rh",
            "subject": "rh__planning",
            "activity": "staffing_rh",
            "narrative_family": "opportunity",
            "status": "interesting",
            "interesting_kind": "opportunity",
            "operational_unit": "breakroom",
            "issue_focus": (
                "Les extras hésitent sur les Super Sunday, le planning n'est pas en trou"
            ),
            "canonical_object": "les extras du dimanche",
            "observations": (
                (
                    "Les extras hésitent sur les Super Sunday, le planning affiché au breakroom "
                    "n'est pas encore en trou."
                ),
            ),
            "occurred_at": datetime(2026, 9, 9, 17, 15, tzinfo=PARIS_TZ),
            "author_pole": "rh",
        },
        "signal:interesting-wifi-4e": {
            "pole": "maintenance",
            "subject": "maintenance__reseau_informatique",
            "activity": "maintenance",
            "narrative_family": "operational_incident",
            "status": "interesting",
            "interesting_kind": "vanished_technical",
            "operational_unit": "chambres",
            "issue_focus": "Le wifi du 4e a décroché dix minutes, sans nouvel incident",
            "canonical_object": "le wifi",
            "observations": (
                "Le wifi du 4e a décroché dix minutes en chambre, plus aucun retour depuis.",
            ),
            "occurred_at": datetime(2026, 9, 8, 19, 5, tzinfo=PARIS_TZ),
            "author_pole": "hotel",
        },
        "signal:interesting-clickshare-atelier-1": {
            "pole": "evenements_privatisations",
            "subject": "evenements_privatisations__preparation_logistique",
            "activity": "ateliers_studios",
            "narrative_family": "operational_incident",
            "status": "interesting",
            "interesting_kind": "vanished_technical",
            "operational_unit": "atelier_1",
            "issue_focus": "Le ClickShare de l'Atelier 1 a clignoté, sans nouvel incident",
            "canonical_object": "le ClickShare",
            "observations": (
                (
                    "Le ClickShare de l'Atelier 1 a clignoté une fois pendant un test. Aucun "
                    "nouvel incident depuis."
                ),
            ),
            "occurred_at": datetime(2026, 9, 8, 10, 35, tzinfo=PARIS_TZ),
            "author_pole": "evenements_privatisations",
        },
    }


def overdue_execution_specs(
    *, reference_at: datetime | None = None
) -> tuple[OverdueExecutionSpec, ...]:
    ref = reference_at or operational_now()
    return (
        OverdueExecutionSpec(
            seed_key="exec:overdue:revue-linge",
            title="Valider la revue linge de la semaine",
            pole="hotel",
            activity="hebergement_chambres",
            narrative_family="process_inefficiency",
            days_late=7,
            end_at=overdue_end_at(days_late=7, reference_at=ref),
            context="Le comptage du 8 septembre trouve 40 draps d'écart avec la blanchisserie.",
            plan_seed_key="plan:rupture-linge",
        ),
        OverdueExecutionSpec(
            seed_key="exec:overdue:cloture-caisse",
            title="Valider la clôture de caisse du samedi 12",
            pole="restaurant",
            activity="restaurant_cuisine_salle",
            narrative_family="process_inefficiency",
            days_late=6,
            end_at=overdue_end_at(days_late=6, reference_at=ref),
            context="Écart de 18 € expliqué par un pourboire mal ventilé.",
            plan_seed_key="plan:anomalie-caisse",
        ),
        OverdueExecutionSpec(
            seed_key="exec:overdue:integration-reception",
            title="Valider l'intégration de la réceptionniste",
            pole="rh",
            activity="staffing_rh",
            narrative_family="prevention",
            days_late=5,
            end_at=overdue_end_at(days_late=5, reference_at=ref),
            context="Arrivée le 7 septembre, modules cochés, badge et planning faits.",
            plan_seed_key="oneshot:integration-receptionniste",
            oneshot_title="Intégration de la réceptionniste",
            oneshot_tasks=(
                "Remettre badge et accès réception",
                "Cocher les modules d'intégration",
                "Planifier les shifts d'accompagnement",
                "Confirmer l'autonomie sur le poste",
            ),
        ),
        OverdueExecutionSpec(
            seed_key="exec:overdue:eclairage-circulations",
            title="Valider le contrôle éclairage des circulations",
            pole="maintenance",
            activity="maintenance",
            narrative_family="prevention",
            days_late=4,
            end_at=overdue_end_at(days_late=4, reference_at=ref),
            context="Passage du 14 septembre, ampoules du 3e changées, compte-rendu rédigé.",
            plan_seed_key="plan:defaut-eclairage",
        ),
        OverdueExecutionSpec(
            seed_key="exec:overdue:stocks-buffet",
            title="Valider le contrôle des stocks buffet",
            pole="petit_dejeuner",
            activity="petit_dejeuner",
            narrative_family="prevention",
            days_late=3,
            end_at=overdue_end_at(days_late=3, reference_at=ref),
            context="Jeudi 17, rupture de jus constatée et réassortie le jour même.",
            plan_seed_key="plan:reassort-buffet-pdj",
        ),
        OverdueExecutionSpec(
            seed_key="exec:overdue:signaletique-bringue",
            title="Valider le BAT de la signalétique de La Bringue",
            pole="evenements_privatisations",
            activity="la_bringue",
            narrative_family="cross_pole_coordination",
            days_late=2,
            end_at=overdue_end_at(days_late=2, reference_at=ref),
            context=(
                "Le BAT n'est pas encore transmis à l'impression. La pose n'est pas commencée au "
                "20 septembre."
            ),
            plan_seed_key="oneshot:bat-signaletique-bringue",
            oneshot_title="BAT de la signalétique de La Bringue",
            oneshot_tasks=(
                "Consolider les contenus et parcours",
                "Faire valider les supports par Communication",
                "Transmettre le BAT à l'impression",
                "Planifier la pose",
            ),
        ),
    )


def proactive_project_specs() -> tuple[ProactiveProjectSpec, ...]:
    return (
        ProactiveProjectSpec(
            seed_key="oneshot:public:tim-lienderss",
            title="TIM LIENDERSS — DJ set",
            pole="evenements_privatisations",
            activity="dj_sets",
            plan_seed_key="plan:preparation-evenement-dj",
            start_at=datetime(2026, 9, 24, 9, 0, tzinfo=PARIS_TZ),
            end_at=datetime(2026, 9, 26, 19, 0, tzinfo=PARIS_TZ),
            context=(
                "Préparation du DJ set du 24 au 26 septembre, sur la ligne déjà comptée "
                "dans les 60 exécutions de septembre. Pas d'exécution supplémentaire."
            ),
        ),
        ProactiveProjectSpec(
            seed_key="oneshot:public:club-sonore-2026-10-22",
            title="Mama ❤️ Club Sonore — DJ set",
            pole="evenements_privatisations",
            activity="mama_club_sonore",
            plan_seed_key="plan:preparation-evenement-dj",
            start_at=datetime(2026, 10, 22, 16, 0, tzinfo=PARIS_TZ),
            end_at=datetime(2026, 10, 22, 19, 0, tzinfo=PARIS_TZ),
            context="One-shot public déjà prévu le 22 octobre 16 h–19 h, dans les 50 d'octobre.",
        ),
        ProactiveProjectSpec(
            seed_key="oneshot:private:horizon-azur-2026-11-12",
            title="Séminaire Horizon Azur",
            pole="evenements_privatisations",
            activity="seminaires",
            plan_seed_key="plan:preparation-seminaire",
            start_at=datetime(2026, 11, 10, 9, 0, tzinfo=PARIS_TZ),
            end_at=datetime(2026, 11, 13, 18, 0, tzinfo=PARIS_TZ),
            context=(
                "Le plan catalogue a été créé le 20 octobre. "
                "L'exécution réelle démarre le 10 novembre et est comptée en novembre."
            ),
        ),
        ProactiveProjectSpec(
            seed_key="schedule:controle-rooftop:2026-09-23",
            title="Fermeture de saison rooftop et piscine",
            pole="evenements_privatisations",
            activity="rooftop_piscine",
            plan_seed_key="schedule:controle-rooftop",
            start_at=datetime(2026, 9, 23, 16, 0, tzinfo=PARIS_TZ),
            end_at=datetime(2026, 9, 23, 17, 0, tzinfo=PARIS_TZ),
            oneshot_title="Fermeture de saison rooftop et piscine",
            oneshot_tasks=ROOFTOP_CLOSURE_TASKS,
            context=(
                "Occurrence du 23 septembre du schedule Contrôle d'exploitation du rooftop, "
                "déjà comptée dans les 60 exécutions de septembre. "
                "Les tâches de cette occurrence sont celles de la fermeture de saison, "
                "pas celles du plan catalogue d'ouverture."
            ),
        ),
        ProactiveProjectSpec(
            seed_key="schedule:reouverture-rooftop-piscine:2027-03-01",
            title="Réouverture rooftop et piscine",
            pole="evenements_privatisations",
            activity="rooftop_piscine",
            plan_seed_key="plan:ouverture-saison-rooftop-piscine",
            start_at=datetime(2027, 3, 1, 9, 0, tzinfo=PARIS_TZ),
            end_at=datetime(2027, 3, 1, 12, 0, tzinfo=PARIS_TZ),
            context="Occurrence unique du schedule #28 le 1er mars 2027, déjà dans les 15 de mars.",
        ),
        ProactiveProjectSpec(
            seed_key="schedule:super-sunday:2026-09-27",
            title="Super Sunday — concert",
            pole="evenements_privatisations",
            activity="super_sunday",
            plan_seed_key="schedule:super-sunday",
            start_at=datetime(2026, 9, 27, 16, 0, tzinfo=PARIS_TZ),
            end_at=datetime(2026, 9, 27, 19, 0, tzinfo=PARIS_TZ),
            oneshot_title="Préparation opérationnelle Super Sunday",
            context=(
                "Occurrence du schedule #7 le 27 septembre 16 h–19 h. "
                "Pas de second one-shot."
            ),
        ),
    )


def _status_queue() -> list[str]:
    reserved = Counter()
    for row in {**_named_overrides(), **_interesting_overrides()}.values():
        reserved[row["status"]] += 1
    queue: list[str] = []
    for status, count in SIGNAL_STATUS_COUNTS.items():
        remaining = count - reserved[status]
        if remaining < 0:
            raise ValueError(f"{status}: named scenarios exceed {count}")
        queue.extend([status] * remaining)
    return queue


def _size_queue() -> list[int]:
    reserved = [
        len(row["observations"])
        for row in {**_named_overrides(), **_interesting_overrides()}.values()
    ]
    reserved_counts = Counter(reserved)
    queue: list[int] = []
    for size, count in OBSERVATION_SOURCE_LAYOUT:
        remaining = count - reserved_counts[size]
        if remaining < 0:
            raise ValueError(f"source size {size}: named scenarios exceed {count}")
        queue.extend([size] * remaining)
    return queue


def _observations_for(focus: str, proof: str, count: int, slot: int) -> tuple[str, ...]:
    first = f"{focus}, {proof}."
    extras = [
        (
            f"{focus} : "
            f"{FOLLOW_UPS[(slot + index) % len(FOLLOW_UPS)][0].lower()}"
            f"{FOLLOW_UPS[(slot + index) % len(FOLLOW_UPS)][1:]} {proof}."
        )
        for index in range(1, count)
    ]
    return (first, *extras)


def _occurred_for(status: str, index: int, pattern: str | None) -> datetime:
    if status in {"open", "in_progress", "interesting"}:
        earliest = SNAPSHOT - timedelta(days=ACTIVE_SIGNAL_MAX_AGE_DAYS)
        occurred = earliest + timedelta(hours=8 + (index % 500))
        if occurred >= SNAPSHOT:
            occurred = SNAPSHOT - timedelta(minutes=20 + (index % 40))
        return occurred
    if pattern in {
        "pattern:clim-chambres",
        "pattern:ruptures-buffet",
        "pattern:attente-restaurant",
        "pattern:audiovisuel-ateliers",
    } and index % 5 == 0:
        return datetime(2026, 9, 16, 9, 0, tzinfo=PARIS_TZ) + timedelta(hours=index % 40)
    occurred = datetime(2025, 9, 23, 8, 0, tzinfo=PARIS_TZ) + timedelta(hours=index * 11)
    if occurred > SNAPSHOT:
        occurred = SNAPSHOT - timedelta(minutes=30 + (index % 40))
    return occurred


def authored_scenarios() -> tuple[AuthoredScenario, ...]:
    named = {**_named_overrides(), **_interesting_overrides()}
    named_focuses = {row["issue_focus"] for row in named.values()}
    unused_rows: dict[str, list[tuple[str, ...]]] = {
        subject: [row for row in rows if row[1] not in named_focuses]
        for subject, rows in ROWS.items()
    }
    statuses = _status_queue()
    sizes = _size_queue()
    scenarios = [
        AuthoredScenario(seed_key=seed_key, **payload) for seed_key, payload in named.items()
    ]
    drafts: list[dict] = []
    index = 0
    for pole, count in SIGNAL_COUNTS_BY_POLE.items():
        subjects = [subject for subject in unused_rows if subject.startswith(f"{pole}__")]
        taken_for_pole = sum(1 for item in scenarios if item.pole == pole)
        for local_index in range(count - taken_for_pole):
            subject = subjects[local_index % len(subjects)]
            bank = unused_rows[subject]
            if not bank:
                raise ValueError(f"{subject}: authored catalog exhausted")
            raw = bank.pop(0)
            unit, focus, canonical, proof = raw[0], raw[1], raw[2], raw[3]
            topic = infer_topic(
                focus=focus,
                topic=raw[4] if len(raw) > 4 else None,
                subject=subject,
            )
            drafts.append(
                {
                    "pole": pole,
                    "subject": subject,
                    "unit": unit,
                    "focus": focus,
                    "canonical": canonical,
                    "proof": proof,
                    "topic": topic,
                    "index": index,
                }
            )
            index += 1
    cancel_needed = statuses.count("canceled")
    cancel_indexes = _select_cancel_indexes(drafts, cancel_needed)
    statuses = [status for status in statuses if status != "canceled"]
    for position, draft in enumerate(drafts):
        status = "canceled" if position in cancel_indexes else statuses.pop(0)
        size = sizes.pop(0)
        topic = draft["topic"]
        activity = infer_activity(pole=draft["pole"], unit=draft["unit"], focus=draft["focus"])
        observations = list(_observations_for(draft["focus"], draft["proof"], size, draft["index"]))
        cancel_reason = cancel_reason_for(draft["focus"]) if status == "canceled" else None
        family = infer_family(
            focus=draft["focus"],
            topic=topic,
            author_pole=draft["pole"],
            pole=draft["pole"],
            status=status,
            interesting_kind=None,
            observation_count=len(observations),
        )
        author = author_for(pole=draft["pole"], family=family, topic=topic, index=draft["index"])
        seed_key = f"signal:{len(scenarios) + 1:03d}"
        pattern = pattern_for(topic=topic, pole=draft["pole"])
        plan = None
        execution = None
        if status == "in_progress" and pattern:
            plan = PLAN_BY_PATTERN[pattern]
            execution = f"exec:signal:{seed_key}"
        scenarios.append(
            AuthoredScenario(
                seed_key=seed_key,
                pole=draft["pole"],
                subject=draft["subject"],
                activity=activity,
                narrative_family=family,
                status=status,
                operational_unit=draft["unit"],
                issue_focus=draft["focus"],
                canonical_object=draft["canonical"],
                observations=tuple(observations),
                occurred_at=_occurred_for(status, draft["index"], pattern),
                author_pole=author,
                topic=topic,
                cancel_reason=cancel_reason,
                pattern_seed_key=pattern,
                plan_seed_key=plan,
                execution_seed_key=execution,
            )
        )
    if statuses or sizes:
        raise ValueError("assignment queues were not consumed")
    return tuple(
        _repair_status_cycle(_finalize_relations(_rebalance_families(_assign_matching_patterns(scenarios))))
    )


def _scenario_archetype(item: AuthoredScenario) -> str | None:
    return infer_archetype(
        pattern_seed_key=item.pattern_seed_key,
        topic=item.topic,
        activity=item.activity,
        focus=item.issue_focus,
    )


def _catalog_plan_for(item: AuthoredScenario) -> str | None:
    key = _scenario_archetype(item)
    if key is None:
        return None
    authorized = ARCHETYPES[key].plans
    if item.plan_seed_key and item.plan_seed_key in authorized:
        return item.plan_seed_key
    if item.pattern_seed_key:
        candidate = PLAN_BY_PATTERN.get(item.pattern_seed_key)
        if candidate and candidate in authorized:
            return candidate
    topic_pattern = pattern_for(topic=item.topic, pole=item.pole) if item.topic else None
    if topic_pattern:
        candidate = PLAN_BY_PATTERN.get(topic_pattern)
        if candidate and candidate in authorized:
            return candidate
    if len(authorized) == 1:
        return next(iter(authorized))
    return None


def _with_oneshot_plan(item: AuthoredScenario) -> AuthoredScenario:
    focus = item.issue_focus.rstrip(".")
    unit = item.operational_unit.replace("_", " ")
    return replace(
        item,
        plan_seed_key=f"oneshot:{item.seed_key}",
        oneshot_title=focus,
        oneshot_tasks=(
            f"Vérifier {item.canonical_object} à {unit}",
            f"Traiter : {focus}",
            f"Confirmer le résultat avec le pôle {item.author_pole}",
        ),
        execution_seed_key=item.execution_seed_key or f"exec:signal:{item.seed_key}",
    )


def _attach_compatible_plan(item: AuthoredScenario) -> AuthoredScenario:
    if is_oneshot_plan(item.plan_seed_key) and item.oneshot_title and item.oneshot_tasks:
        return replace(
            item,
            execution_seed_key=item.execution_seed_key or f"exec:signal:{item.seed_key}",
        )
    catalog = _catalog_plan_for(item)
    if catalog:
        return replace(
            item,
            plan_seed_key=catalog,
            oneshot_title=None,
            oneshot_tasks=(),
            execution_seed_key=item.execution_seed_key or f"exec:signal:{item.seed_key}",
        )
    return _with_oneshot_plan(item)


def _repair_status_cycle(scenarios: list[AuthoredScenario]) -> list[AuthoredScenario]:
    assigned = list(scenarios)
    for index, item in enumerate(assigned):
        if item.status != "in_progress":
            continue
        assigned[index] = _attach_compatible_plan(item)
        if not assigned[index].plan_seed_key or not assigned[index].execution_seed_key:
            raise ValueError(f"{item.seed_key}: in_progress has no compatible plan")
    missing = SIGNAL_STATUS_COUNTS["in_progress"] - sum(
        1 for item in assigned if item.status == "in_progress"
    )
    if missing < 0:
        raise ValueError("too many in_progress Signals; refusing a silent demotion")
    if missing == 0:
        return assigned
    donors = [
        index
        for index, item in enumerate(assigned)
        if item.status == "open"
        and not item.routing_unassigned
        and item.seed_key != "signal:ci-clim-filtres"
        and item.narrative_family != "opportunity"
    ]
    for index in donors:
        if missing <= 0:
            break
        item = assigned[index]
        attached = _attach_compatible_plan(replace(item, status="in_progress"))
        if not attached.plan_seed_key:
            continue
        assigned[index] = attached
        missing -= 1
    if missing > 0:
        raise ValueError(
            f"cannot reach 23 in_progress without a pole default plan: short {missing}"
        )
    return assigned


def _select_cancel_indexes(drafts: list[dict], needed: int) -> set[int]:
    scored: list[tuple[int, int]] = []
    for index, draft in enumerate(drafts):
        folded = draft["focus"].casefold()
        score = 0
        if any(
            token in folded for token in ("groupe", "réservation", "privatisation", "séminaire")
        ):
            score += 3
        if any(token in folded for token in ("planning", "extra", "avis", "file")):
            score += 2
        if any(token in folded for token in ("clim", "wifi", "écran")):
            score += 1
        if score:
            scored.append((score, index))
    scored.sort(reverse=True)
    chosen = {index for _score, index in scored[:needed]}
    leftover = needed - len(chosen)
    if leftover:
        for index in range(len(drafts)):
            if leftover <= 0:
                break
            if index not in chosen:
                chosen.add(index)
                leftover -= 1
    return chosen


def _rebalance_families(scenarios: list[AuthoredScenario]) -> list[AuthoredScenario]:
    assigned = list(scenarios)
    for index, item in enumerate(assigned):
        if item.narrative_family == "continuous_improvement" and not item.pattern_seed_key:
            fallback = (
                "operational_incident"
                if item.topic in {"clim", "fuite", "borne", "eclairage"}
                else "guest_experience"
            )
            assigned[index] = replace(item, narrative_family=fallback)
    counts = Counter(item.narrative_family for item in assigned)
    ci_needed = NARRATIVE_FAMILY_COUNTS["continuous_improvement"] - counts["continuous_improvement"]
    if ci_needed > 0:
        donors = [
            index
            for index, item in enumerate(assigned)
            if item.pattern_seed_key
            and item.narrative_family != "continuous_improvement"
            and item.status != "interesting"
            and item.seed_key.split(":")[-1][:1].isdigit()
        ]
        for index in donors[:ci_needed]:
            source = assigned[index].narrative_family
            assigned[index] = _stamp_family(assigned[index], "continuous_improvement", index)
            counts[source] -= 1
            counts["continuous_improvement"] += 1
    for _ in range(len(NARRATIVE_FAMILIES)):
        if dict(counts) == NARRATIVE_FAMILY_COUNTS:
            break
        for family, expected in NARRATIVE_FAMILY_COUNTS.items():
            missing = expected - counts[family]
            if missing <= 0:
                continue
            extras = [
                index
                for index, item in enumerate(assigned)
                if counts[item.narrative_family] > NARRATIVE_FAMILY_COUNTS[item.narrative_family]
                and item.status != "interesting"
                and not item.seed_key.startswith("signal:golden")
                and item.seed_key.split(":")[-1][:1].isdigit()
                and (family != "continuous_improvement" or bool(item.pattern_seed_key))
            ]
            extras.sort(
                key=lambda index: (
                    0 if _family_compatible(assigned[index], family) else 1,
                    index,
                )
            )
            for index in extras[:missing]:
                source = assigned[index].narrative_family
                assigned[index] = _stamp_family(assigned[index], family, index)
                counts[source] -= 1
                counts[family] += 1
    if dict(counts) != NARRATIVE_FAMILY_COUNTS:
        raise ValueError(f"family rebalance failed: {dict(counts)}")
    return assigned


def _stamp_family(item: AuthoredScenario, family: str, index: int) -> AuthoredScenario:
    author = author_for(pole=item.pole, family=family, topic=item.topic, index=index)
    extra = justify_family(
        family=family,
        focus=item.issue_focus,
        unit=item.operational_unit,
        canonical=item.canonical_object,
        occurred_at=item.occurred_at,
        topic=item.topic,
        index=index,
    )
    observations = item.observations
    if extra and observations and extra not in observations[-1]:
        observations = (*observations[:-1], f"{observations[-1]} {extra}")
    pattern = item.pattern_seed_key
    plan = item.plan_seed_key
    execution = item.execution_seed_key
    if family == "continuous_improvement":
        pattern = pattern or pattern_for(topic=item.topic, pole=item.pole)
        if item.status in {"resolved", "in_progress"} and pattern:
            plan = PLAN_BY_PATTERN.get(pattern, plan)
            execution = execution or f"exec:signal:{item.seed_key}"
        if item.status == "open":
            plan = None
            execution = None
    if family == "opportunity":
        pattern = None
        plan = None
        execution = None
    return replace(
        item,
        narrative_family=family,
        author_pole=author,
        observations=observations,
        pattern_seed_key=pattern,
        plan_seed_key=plan,
        execution_seed_key=execution,
    )


def _family_compatible(item: AuthoredScenario, family: str) -> bool:
    if family == "opportunity":
        return item.status == "interesting" and item.interesting_kind == "opportunity"
    if family == "continuous_improvement":
        return pattern_for(topic=item.topic, pole=item.pole) is not None or bool(
            item.pattern_seed_key
        )
    if family == "cross_pole_coordination":
        return True
    if family == "prevention":
        return any(
            token in item.issue_focus.casefold()
            for token in ("contrôle", "avant", "prévent", "test")
        )
    if family == "process_inefficiency":
        return item.topic in {
            "linge",
            "chambre_prete",
            "caisse_hotel",
            "caisse_resto",
            "buffet",
            "effectif",
            "checkin",
        }
    if family == "service_quality":
        return item.topic in {
            "attente_resto",
            "erreur_service",
            "buffet",
            "proprete_pdj",
            "stock_bar",
        }
    if family == "guest_experience":
        return any(
            token in item.issue_focus.casefold()
            for token in ("client", "chambre", "lobby", "piscine")
        )
    return item.topic in {"clim", "fuite", "borne", "eclairage", "audiovisuel", "cafe"}


def _assign_matching_patterns(scenarios: list[AuthoredScenario]) -> list[AuthoredScenario]:
    remaining = Counter(PATTERN_QUOTA)
    assigned = list(scenarios)
    for index, item in enumerate(assigned):
        if item.status == "interesting":
            assigned[index] = replace(
                item, pattern_seed_key=None, plan_seed_key=None, execution_seed_key=None
            )
            continue
        pattern = item.pattern_seed_key or pattern_for(topic=item.topic, pole=item.pole)
        if pattern and remaining[pattern] > 0:
            remaining[pattern] -= 1
            assigned[index] = replace(
                item,
                pattern_seed_key=pattern,
                topic=item.topic or _topic_from_pattern(pattern),
            )
        elif item.pattern_seed_key:
            assigned[index] = replace(item, pattern_seed_key=None)
    for index, item in enumerate(assigned):
        if item.pattern_seed_key or item.status == "interesting":
            continue
        pattern = _best_remaining_pattern(item, remaining)
        if pattern is None:
            continue
        remaining[pattern] -= 1
        assigned[index] = replace(
            item,
            pattern_seed_key=pattern,
            topic=item.topic or _topic_from_pattern(pattern),
        )
    for pattern, count in list(remaining.items()):
        if count <= 0:
            continue
        topic = _topic_from_pattern(pattern)
        pole = PATTERN_POLE[pattern]
        donors = [
            index
            for index, item in enumerate(assigned)
            if item.pole == pole
            and not item.pattern_seed_key
            and item.status != "interesting"
            and item.activity not in EVENT_KEYWORDS
            and not item.seed_key.startswith("signal:golden")
            and ":" in item.seed_key
            and item.seed_key.split(":")[-1][:1].isdigit()
            and _can_rewrite_for_topic(item, topic)
        ]
        for index in donors[:count]:
            assigned[index] = _rewrite_for_pattern(assigned[index], pattern, topic)
            remaining[pattern] -= 1
    short = {key: count for key, count in remaining.items() if count > 0}
    if short:
        raise ValueError(f"pattern quotas short: {short}")
    return assigned


def _can_rewrite_for_topic(item: AuthoredScenario, topic: str | None) -> bool:
    return bool(topic) and item.pole == PATTERN_POLE[PATTERN_BY_TOPIC[topic]]


TOPIC_SUBJECT = {
    "clim": ("maintenance__cvc", "chambres"),
    "buffet": ("petit_dejeuner__stock", "restaurant_rdc"),
    "linge": ("hotel__linge", "chambres"),
    "attente_resto": ("restaurant__service_accueil", "restaurant_rdc"),
    "audiovisuel": ("evenements_privatisations__preparation_logistique", "atelier_1"),
    "signaletique": ("evenements_privatisations__communication", "atelier_2"),
}


def _rewrite_for_pattern(
    item: AuthoredScenario, pattern: str, topic: str | None
) -> AuthoredScenario:
    rewritten = rewrite_for_topic(topic=topic or "", index=sum(item.seed_key.encode()) % 32)
    if rewritten is None:
        raise ValueError(f"{item.seed_key}: cannot rewrite uniquely for {pattern}")
    focus, canonical, proof = rewritten
    subject, unit = TOPIC_SUBJECT.get(topic or "", (item.subject, item.operational_unit))
    observations = _observations_for(
        focus, proof, max(1, len(item.observations)), sum(item.seed_key.encode()) % 8
    )
    unit_hints = UNIT_HINTS.get(unit, ())
    if unit_hints and not any(_contains_any(text, unit_hints) for text in observations):
        observations = (f"{observations[0]} {unit_hints[0]}.", *observations[1:])
    return replace(
        item,
        subject=subject,
        operational_unit=unit,
        issue_focus=focus,
        canonical_object=canonical,
        observations=observations,
        pattern_seed_key=pattern,
        topic=topic,
        activity=infer_activity(pole=item.pole, unit=unit, focus=focus),
    )


def _finalize_relations(scenarios: list[AuthoredScenario]) -> list[AuthoredScenario]:
    assigned = list(scenarios)
    for index, item in enumerate(assigned):
        if item.status == "interesting":
            assigned[index] = replace(
                item, plan_seed_key=None, execution_seed_key=None, pattern_seed_key=None
            )
            continue
        if item.status == "open":
            assigned[index] = replace(item, plan_seed_key=None, execution_seed_key=None)
            continue
        if item.narrative_family == "continuous_improvement":
            pattern = item.pattern_seed_key
            if not pattern:
                raise ValueError(f"{item.seed_key}: continuous improvement without pattern")
            if item.status in {"resolved", "in_progress"}:
                assigned[index] = replace(
                    item,
                    plan_seed_key=PLAN_BY_PATTERN[pattern],
                    execution_seed_key=item.execution_seed_key or f"exec:signal:{item.seed_key}",
                )
            continue
        if item.status == "in_progress":
            if is_oneshot_plan(item.plan_seed_key):
                assigned[index] = replace(
                    item,
                    execution_seed_key=item.execution_seed_key or f"exec:signal:{item.seed_key}",
                )
                continue
            catalog = _catalog_plan_for(item)
            if not catalog:
                assigned[index] = replace(item, plan_seed_key=None, execution_seed_key=None)
                continue
            assigned[index] = replace(
                item,
                plan_seed_key=catalog,
                execution_seed_key=item.execution_seed_key or f"exec:signal:{item.seed_key}",
            )
            continue
        if item.plan_seed_key and PLAN_BY_PATTERN.get(item.pattern_seed_key) not in {
            item.plan_seed_key,
            None,
        }:
            if item.pattern_seed_key and PLAN_BY_PATTERN.get(
                item.pattern_seed_key
            ) != item.plan_seed_key:
                assigned[index] = replace(item, plan_seed_key=None, execution_seed_key=None)
    return assigned


def _topic_from_pattern(pattern: str) -> str | None:
    for topic, key in PATTERN_BY_TOPIC.items():
        if key == pattern:
            return topic
    return None


def _best_remaining_pattern(item: AuthoredScenario, remaining: Counter) -> str | None:
    if item.status == "interesting":
        return None
    folded = item.issue_focus.casefold()
    from houston.establishments.mama_nice_dataset_editorial import TOPIC_KEYWORDS

    scored: list[tuple[int, str]] = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        pattern = PATTERN_BY_TOPIC[topic]
        if remaining[pattern] <= 0 or PATTERN_POLE[pattern] != item.pole:
            continue
        hits = sum(1 for token in keywords if token in folded)
        if hits:
            scored.append((hits, pattern))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


def scenario_errors(scenarios: tuple[AuthoredScenario, ...]) -> list[str]:
    errors: list[str] = []
    if len(scenarios) != TOTAL_SIGNALS:
        errors.append(f"scenarios {len(scenarios)} != {TOTAL_SIGNALS}")
    poles = Counter(item.pole for item in scenarios)
    if dict(poles) != SIGNAL_COUNTS_BY_POLE:
        errors.append(f"scenario poles {dict(poles)}")
    statuses = Counter(item.status for item in scenarios)
    if dict(statuses) != SIGNAL_STATUS_COUNTS:
        errors.append(f"scenario statuses {dict(statuses)}")
    families = Counter(item.narrative_family for item in scenarios)
    if dict(families) != NARRATIVE_FAMILY_COUNTS:
        errors.append(f"scenario families {dict(families)}")
    if sum(1 for item in scenarios if item.routing_unassigned) != UNASSIGNED_OPEN_SIGNALS:
        errors.append("unassigned open signals must be 2")
    vanished = sum(1 for item in scenarios if item.interesting_kind == "vanished_technical")
    if vanished > INTERESTING_VANISHED_TECHNICAL_MAX:
        errors.append("too many vanished technical interesting signals")
    opportunities = sum(1 for item in scenarios if item.narrative_family == "opportunity")
    if opportunities != 8:
        errors.append("opportunity family must be 8")
    for item in scenarios:
        if item.status == "interesting" and (item.plan_seed_key or item.execution_seed_key):
            errors.append(f"{item.seed_key}: interesting cannot have a plan")
        if item.status == "canceled" and not item.cancel_reason:
            errors.append(f"{item.seed_key}: canceled signal needs a narrative reason")
        if item.activity in EVENT_KEYWORDS:
            if not _contains_any(item.issue_focus, EVENT_KEYWORDS[item.activity]):
                errors.append(f"{item.seed_key}: event activity without matching event")
        if item.pattern_seed_key and item.topic:
            expected = PATTERN_BY_TOPIC.get(item.topic)
            if expected and expected != item.pattern_seed_key:
                errors.append(f"{item.seed_key}: pattern does not match topic {item.topic}")
        if item.status == "open" and (item.plan_seed_key or item.execution_seed_key):
            errors.append(f"{item.seed_key}: open Signal cannot have a plan or execution")
        if item.status == "in_progress" and (not item.plan_seed_key or not item.execution_seed_key):
            errors.append(f"{item.seed_key}: in_progress Signal needs a plan and an execution")
        if (
            item.status == "in_progress"
            and item.plan_seed_key
            and not is_oneshot_plan(item.plan_seed_key)
        ):
            authorized = ARCHETYPES.get(_scenario_archetype(item) or "", None)
            if authorized is None or item.plan_seed_key not in authorized.plans:
                errors.append(f"{item.seed_key}: catalog plan is incompatible with the archetype")
        if item.status == "in_progress" and is_oneshot_plan(item.plan_seed_key):
            if not item.oneshot_title or not item.oneshot_tasks:
                errors.append(f"{item.seed_key}: oneshot plan is missing adapted title or tasks")
        if item.status == "in_progress":
            archetype_key = _scenario_archetype(item)
            if archetype_key is None:
                errors.append(f"{item.seed_key}: in_progress Signal has no archetype")
            else:
                errors.extend(
                    in_progress_relation_errors(
                        archetype_key=archetype_key,
                        plan_seed_key=item.plan_seed_key,
                        execution_seed_key=item.execution_seed_key,
                    )
                )
                if (
                    item.pattern_seed_key
                    and item.pattern_seed_key not in ARCHETYPES[archetype_key].patterns
                ):
                    errors.append(f"{item.seed_key}: Pattern is incompatible with the archetype")
        if item.status in {"open", "in_progress", "interesting"}:
            age = SNAPSHOT - item.occurred_at
            if age > timedelta(days=ACTIVE_SIGNAL_MAX_AGE_DAYS):
                errors.append(
                    f"{item.seed_key}: active Signal is older than "
                    f"{ACTIVE_SIGNAL_MAX_AGE_DAYS} days"
                )
            if item.occurred_at > SNAPSHOT:
                errors.append(f"{item.seed_key}: active Signal is after the snapshot")
        if item.narrative_family == "continuous_improvement":
            texts = (item.issue_focus, *item.observations, item.cancel_reason or "")
            if not continuous_improvement_justified(texts):
                errors.append(
                    f"{item.seed_key}: continuous improvement is not justified by the content"
                )
            if not item.pattern_seed_key:
                errors.append(f"{item.seed_key}: continuous improvement missing Pattern")
            if item.status in {"resolved", "in_progress"}:
                if not item.plan_seed_key or not item.execution_seed_key:
                    errors.append(f"{item.seed_key}: treated continuous improvement missing plan")
                elif is_oneshot_plan(item.plan_seed_key):
                    if not item.oneshot_title or not item.oneshot_tasks:
                        errors.append(
                            f"{item.seed_key}: treated continuous improvement oneshot is incomplete"
                        )
                elif PLAN_BY_PATTERN.get(item.pattern_seed_key) != item.plan_seed_key:
                    errors.append(f"{item.seed_key}: plan does not treat the pattern")
        for text in (item.issue_focus, *item.observations):
            folded = text.casefold()
            if any(clause in folded for clause in FORBIDDEN_GENERIC_CLAUSES):
                errors.append(f"{item.seed_key}: generic family suffix in visible text")
        if item.activity not in MAMA_NICE_ACTIVITIES:
            errors.append(f"{item.seed_key}: unknown activity")
        if item.narrative_family not in NARRATIVE_FAMILIES:
            errors.append(f"{item.seed_key}: unknown family")
        if not item.relations.observation_seed_keys:
            errors.append(f"{item.seed_key}: missing observation relations")
        if item.operational_unit not in POLE_UNITS.get(item.pole, frozenset()):
            errors.append(f"{item.seed_key}: unit not in pole")
        hints = SUBJECT_HINTS.get(item.subject, ())
        if hints and not _contains_any(item.issue_focus, hints):
            errors.append(f"{item.seed_key}: focus misses subject hint")
        unit_hints = UNIT_HINTS.get(item.operational_unit, ())
        if unit_hints and not any(_contains_any(text, unit_hints) for text in item.observations):
            errors.append(f"{item.seed_key}: observations miss place")
        for text in (item.issue_focus, *item.observations):
            folded = text.casefold()
            if any(fragment in folded for fragment in ESTABLISHMENT_NAME_FRAGMENTS):
                if "club sonore" not in folded and "bringue" not in folded:
                    errors.append(f"{item.seed_key}: establishment name in visible text")
        if item.pattern_seed_key and item.pole != PATTERN_POLE.get(item.pattern_seed_key):
            if item.seed_key != "signal:golden-clim-318":
                errors.append(f"{item.seed_key}: pattern pole mismatch")
    used_subjects = {item.subject for item in scenarios}
    unused = set(ROWS) - used_subjects
    if unused:
        errors.append(f"unused activity subjects: {sorted(unused)}")
    activities = {item.activity for item in scenarios}
    required = {
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
    if required - activities:
        errors.append(f"missing activities: {sorted(required - activities)}")
    if len(informational_texts()) != INFORMATIONAL_OBSERVATION_COUNT:
        errors.append("informational catalog diverges")
    overdue = overdue_execution_specs()
    if len(overdue) != OVERDUE_EXECUTION_COUNT:
        errors.append("overdue specs must be 6")
    days = {item.days_late for item in overdue}
    if days != set(range(OVERDUE_MIN_DAYS, OVERDUE_MAX_DAYS + 1)):
        errors.append("overdue days must be 2 through 7")
    for item in overdue:
        late = operational_now() - item.end_at
        if not (
            timedelta(days=OVERDUE_MIN_DAYS)
            <= late
            <= timedelta(days=OVERDUE_MAX_DAYS, hours=1)
        ):
            errors.append(f"{item.seed_key}: overdue window is off")
        if item.end_at == operational_now():
            errors.append(f"{item.seed_key}: overdue end_at must not equal reference_at")
    errors.extend(rooftop_closure_errors())
    return errors


def rooftop_closure_errors() -> list[str]:
    spec = next(
        item for item in proactive_project_specs() if item.seed_key == ROOFTOP_CLOSURE_IDENTITY
    )
    errors: list[str] = []
    if spec.plan_seed_key == "plan:ouverture-saison-rooftop-piscine":
        errors.append("rooftop closure cannot use the opening catalog plan")
    visible = (
        spec.title,
        spec.oneshot_title or "",
        spec.plan_seed_key,
        *spec.oneshot_tasks,
    )
    for text in visible:
        folded = text.casefold()
        if any(token in folded for token in ROOFTOP_OPENING_TOKENS):
            errors.append(f"rooftop closure still uses opening copy: {text}")
    if not spec.oneshot_tasks:
        errors.append("rooftop closure needs adapted closure tasks")
    return errors
