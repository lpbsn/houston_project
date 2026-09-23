"""Semantic Mama Nice archetypes. Volumes are not applied here."""

from __future__ import annotations

from dataclasses import dataclass

FORBIDDEN_GENERIC_CLAUSES = (
    "contrôle fait avant que ça casse",
    "le geste de passation n'est pas calé",
    "un second pôle a le même constat",
    "l'écart se voit au service",
    "le client le dit à l'accueil",
    "incident ponctuel, pas encore une série",
    "même écart déjà vu, on capitalise le plan",
    "motif d'annulation :",
)

CI_CONTENT_MARKERS = (
    "récurrence",
    "récurrent",
    "à chaque arrivée",
    "à chaque séjour",
    "chaque été",
    "cause commune",
    "faiblesse de processus",
    "processus à améliorer",
    "améliorer le processus",
    "entre deux séjours",
)

CONTINUOUS_IMPROVEMENT_CONTRACT = (
    "Un incident isolé conserve sa famille métier naturelle. "
    "`continuous_improvement` exige que le titre et les observations décrivent "
    "explicitement une récurrence, une cause commune, une faiblesse de processus "
    "ou une amélioration concrète recherchée. Appartenir à un Pattern ne suffit pas. "
    "Aucun suffixe générique ne justifie cette famille."
)


def continuous_improvement_justified(texts: tuple[str, ...]) -> bool:
    folded = " ".join(texts).casefold()
    if any(clause in folded for clause in FORBIDDEN_GENERIC_CLAUSES):
        return False
    return any(marker in folded for marker in CI_CONTENT_MARKERS)


@dataclass(frozen=True)
class Archetype:
    key: str
    label: str
    families: frozenset[str]
    observer_poles: frozenset[str]
    responsible_poles: frozenset[str]
    activities: frozenset[str]
    patterns: frozenset[str]
    plans: frozenset[str]
    statuses: frozenset[str]
    allows_unassigned: bool = False
    allows_no_pattern: bool = True
    allows_no_plan: bool = True
    allows_no_signal: bool = False


ARCHETYPES: dict[str, Archetype] = {
    "clim_chambre": Archetype(
        key="clim_chambre",
        label="Clim d'une chambre",
        families=frozenset({"operational_incident", "continuous_improvement"}),
        observer_poles=frozenset({"hotel", "maintenance"}),
        responsible_poles=frozenset({"maintenance"}),
        activities=frozenset({"hebergement_chambres"}),
        patterns=frozenset({"pattern:clim-chambres"}),
        plans=frozenset({"plan:diagnostic-clim"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled", "interesting"}),
    ),
    "chambre_non_prete": Archetype(
        key="chambre_non_prete",
        label="Chambre non prête à l'arrivée",
        families=frozenset({"process_inefficiency", "guest_experience", "continuous_improvement"}),
        observer_poles=frozenset({"hotel"}),
        responsible_poles=frozenset({"hotel"}),
        activities=frozenset({"hebergement_chambres", "reception"}),
        patterns=frozenset({"pattern:chambres-non-pretes"}),
        plans=frozenset({"plan:rattrapage-chambre"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled"}),
    ),
    "linge": Archetype(
        key="linge",
        label="Rupture ou écart de linge",
        families=frozenset({"process_inefficiency", "continuous_improvement"}),
        observer_poles=frozenset({"hotel"}),
        responsible_poles=frozenset({"hotel"}),
        activities=frozenset({"hebergement_chambres"}),
        patterns=frozenset({"pattern:linge"}),
        plans=frozenset({"plan:rupture-linge"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled", "pending_validation"}),
    ),
    "accueil_lobby": Archetype(
        key="accueil_lobby",
        label="Accueil et attente au lobby",
        families=frozenset({"guest_experience", "service_quality", "opportunity"}),
        observer_poles=frozenset({"hotel"}),
        responsible_poles=frozenset({"hotel"}),
        activities=frozenset({"reception", "hebergement_chambres"}),
        patterns=frozenset({"pattern:attente-checkin"}),
        plans=frozenset(),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled", "interesting"}),
        allows_unassigned=True,
    ),
    "buffet_pdj": Archetype(
        key="buffet_pdj",
        label="Buffet petit-déjeuner",
        families=frozenset(
            {
                "service_quality",
                "process_inefficiency",
                "continuous_improvement",
                "cross_pole_coordination",
                "opportunity",
            }
        ),
        observer_poles=frozenset({"petit_dejeuner", "restaurant"}),
        responsible_poles=frozenset({"petit_dejeuner"}),
        activities=frozenset({"petit_dejeuner"}),
        patterns=frozenset(
            {
                "pattern:ruptures-buffet",
                "pattern:proprete-buffet",
                "pattern:equipements-cafe",
            }
        ),
        plans=frozenset({"plan:reassort-buffet-pdj", "plan:remise-conformite-buffet"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled", "interesting"}),
    ),
    "service_restaurant": Archetype(
        key="service_restaurant",
        label="Service restaurant ou file",
        families=frozenset(
            {"service_quality", "guest_experience", "opportunity", "continuous_improvement"}
        ),
        observer_poles=frozenset({"restaurant", "hotel"}),
        responsible_poles=frozenset({"restaurant"}),
        activities=frozenset({"restaurant_cuisine_salle"}),
        patterns=frozenset({"pattern:attente-restaurant", "pattern:erreurs-service"}),
        plans=frozenset({"plan:incident-service-resto"}),
        statuses=frozenset({"open", "in_progress", "resolved", "interesting", "canceled"}),
    ),
    "caisse": Archetype(
        key="caisse",
        label="Écart de caisse",
        families=frozenset({"process_inefficiency"}),
        observer_poles=frozenset({"restaurant", "hotel"}),
        responsible_poles=frozenset({"restaurant", "hotel"}),
        activities=frozenset({"restaurant_cuisine_salle", "reception"}),
        patterns=frozenset({"pattern:cloture-caisse", "pattern:facturation-caisse"}),
        plans=frozenset({"plan:anomalie-caisse"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled", "pending_validation"}),
    ),
    "fuite_sanitaire": Archetype(
        key="fuite_sanitaire",
        label="Fuite sanitaire en chambre",
        families=frozenset({"operational_incident", "continuous_improvement"}),
        observer_poles=frozenset({"hotel", "maintenance"}),
        responsible_poles=frozenset({"maintenance"}),
        activities=frozenset({"hebergement_chambres"}),
        patterns=frozenset({"pattern:fuites"}),
        plans=frozenset({"plan:fuite-sanitaire"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled"}),
    ),
    "borne_parking": Archetype(
        key="borne_parking",
        label="Borne électrique du parking",
        families=frozenset({"operational_incident", "continuous_improvement"}),
        observer_poles=frozenset({"maintenance", "hotel"}),
        responsible_poles=frozenset({"maintenance"}),
        activities=frozenset({"maintenance"}),
        patterns=frozenset({"pattern:bornes"}),
        plans=frozenset({"plan:borne-electrique"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled"}),
    ),
    "eclairage": Archetype(
        key="eclairage",
        label="Éclairage des circulations",
        families=frozenset({"prevention", "operational_incident", "continuous_improvement"}),
        observer_poles=frozenset({"maintenance", "hotel"}),
        responsible_poles=frozenset({"maintenance"}),
        activities=frozenset({"maintenance"}),
        patterns=frozenset({"pattern:eclairage"}),
        plans=frozenset({"plan:defaut-eclairage"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled", "pending_validation"}),
    ),
    "avis_client": Archetype(
        key="avis_client",
        label="Avis clients sur un irritant déjà vu",
        families=frozenset({"guest_experience", "opportunity", "continuous_improvement"}),
        observer_poles=frozenset({"communication"}),
        responsible_poles=frozenset({"communication"}),
        activities=frozenset({"communication_avis"}),
        patterns=frozenset({"pattern:avis-negatifs"}),
        plans=frozenset({"plan:avis-client-negatif"}),
        statuses=frozenset({"open", "in_progress", "resolved", "interesting", "canceled"}),
    ),
    "staffing": Archetype(
        key="staffing",
        label="Staffing et extras",
        families=frozenset({"process_inefficiency", "opportunity", "prevention"}),
        observer_poles=frozenset({"rh", "hotel", "evenements_privatisations"}),
        responsible_poles=frozenset({"rh"}),
        activities=frozenset({"staffing_rh", "super_sunday", "reception"}),
        patterns=frozenset({"pattern:sous-effectif"}),
        plans=frozenset({"plan:runtime-rh-routines"}),
        statuses=frozenset(
            {"open", "in_progress", "resolved", "interesting", "canceled", "pending_validation"}
        ),
    ),
    "audiovisuel_salle": Archetype(
        key="audiovisuel_salle",
        label="Audiovisuel Atelier ou Studio",
        families=frozenset(
            {"operational_incident", "cross_pole_coordination", "continuous_improvement"}
        ),
        observer_poles=frozenset({"evenements_privatisations", "maintenance"}),
        responsible_poles=frozenset({"evenements_privatisations", "maintenance"}),
        activities=frozenset({"ateliers_studios", "seminaires", "dj_sets"}),
        patterns=frozenset({"pattern:audiovisuel-ateliers"}),
        plans=frozenset({"plan:verification-clickshare"}),
        statuses=frozenset({"open", "in_progress", "resolved", "interesting", "canceled"}),
    ),
    "evenement_public": Archetype(
        key="evenement_public",
        label="Événement public figé",
        families=frozenset({"cross_pole_coordination", "prevention"}),
        observer_poles=frozenset(
            {"evenements_privatisations", "communication", "maintenance", "rh"}
        ),
        responsible_poles=frozenset({"evenements_privatisations"}),
        activities=frozenset({"dj_sets", "super_sunday", "la_bringue", "mama_club_sonore"}),
        patterns=frozenset({"pattern:signaletique-event", "pattern:audiovisuel-ateliers"}),
        plans=frozenset({"plan:preparation-evenement-dj"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled"}),
        allows_no_signal=True,
    ),
    "seminaire_privatisation": Archetype(
        key="seminaire_privatisation",
        label="Séminaire ou privatisation",
        families=frozenset({"cross_pole_coordination", "opportunity", "guest_experience"}),
        observer_poles=frozenset({"evenements_privatisations", "hotel", "restaurant"}),
        responsible_poles=frozenset({"evenements_privatisations"}),
        activities=frozenset({"seminaires", "privatisations", "ateliers_studios"}),
        patterns=frozenset(),
        plans=frozenset({"plan:preparation-seminaire", "plan:preparation-privatisation"}),
        statuses=frozenset({"open", "in_progress", "resolved", "canceled", "interesting"}),
        allows_no_signal=True,
    ),
    "saison_rooftop": Archetype(
        key="saison_rooftop",
        label="Saison rooftop et piscine",
        families=frozenset({"prevention", "opportunity", "guest_experience"}),
        observer_poles=frozenset(
            {"restaurant", "hotel", "evenements_privatisations", "maintenance"}
        ),
        responsible_poles=frozenset({"evenements_privatisations", "restaurant", "hotel"}),
        activities=frozenset({"rooftop_piscine"}),
        patterns=frozenset({"pattern:piscine", "pattern:equipements-rooftop"}),
        plans=frozenset({"plan:ouverture-saison-rooftop-piscine"}),
        statuses=frozenset({"resolved", "interesting", "canceled"}),
        allows_no_signal=True,
    ),
    "wifi_reseau": Archetype(
        key="wifi_reseau",
        label="Wifi ou réseau chambre",
        families=frozenset({"operational_incident"}),
        observer_poles=frozenset({"hotel", "maintenance"}),
        responsible_poles=frozenset({"maintenance"}),
        activities=frozenset({"maintenance", "hebergement_chambres"}),
        patterns=frozenset(),
        plans=frozenset(),
        statuses=frozenset({"interesting", "canceled", "resolved"}),
    ),
    "bruit_chambre": Archetype(
        key="bruit_chambre",
        label="Bruit en chambre ou circulation",
        families=frozenset({"opportunity", "guest_experience"}),
        observer_poles=frozenset({"hotel"}),
        responsible_poles=frozenset({"hotel"}),
        activities=frozenset({"hebergement_chambres"}),
        patterns=frozenset(),
        plans=frozenset(),
        statuses=frozenset({"interesting", "open", "canceled"}),
    ),
}


TOPIC_ARCHETYPE = {
    "clim": "clim_chambre",
    "chambre_prete": "chambre_non_prete",
    "linge": "linge",
    "checkin": "accueil_lobby",
    "caisse_hotel": "caisse",
    "caisse_resto": "caisse",
    "piscine": "saison_rooftop",
    "buffet": "buffet_pdj",
    "cafe": "buffet_pdj",
    "proprete_pdj": "buffet_pdj",
    "attente_resto": "service_restaurant",
    "erreur_service": "service_restaurant",
    "stock_bar": "service_restaurant",
    "plonge": "service_restaurant",
    "rooftop": "saison_rooftop",
    "audiovisuel": "audiovisuel_salle",
    "eclairage": "eclairage",
    "fuite": "fuite_sanitaire",
    "borne": "borne_parking",
    "signaletique": "evenement_public",
    "avis": "avis_client",
    "effectif": "staffing",
}

ACTIVITY_ARCHETYPE = {
    "dj_sets": "evenement_public",
    "super_sunday": "evenement_public",
    "la_bringue": "evenement_public",
    "mama_club_sonore": "evenement_public",
    "seminaires": "seminaire_privatisation",
    "privatisations": "seminaire_privatisation",
    "ateliers_studios": "audiovisuel_salle",
    "rooftop_piscine": "saison_rooftop",
    "communication_avis": "avis_client",
    "staffing_rh": "staffing",
}

PATTERN_ARCHETYPE = {
    pattern: key for key, archetype in ARCHETYPES.items() for pattern in archetype.patterns
}


def is_oneshot_plan(plan_seed_key: str | None) -> bool:
    return bool(plan_seed_key) and plan_seed_key.startswith("oneshot:")


def infer_archetype(
    *,
    pattern_seed_key: str | None,
    topic: str | None,
    activity: str,
    focus: str,
) -> str | None:
    if pattern_seed_key and pattern_seed_key in PATTERN_ARCHETYPE:
        return PATTERN_ARCHETYPE[pattern_seed_key]
    if topic and topic in TOPIC_ARCHETYPE:
        return TOPIC_ARCHETYPE[topic]
    if activity in ACTIVITY_ARCHETYPE:
        return ACTIVITY_ARCHETYPE[activity]
    folded = focus.casefold()
    if "bruit" in folded:
        return "bruit_chambre"
    if "wifi" in folded:
        return "wifi_reseau"
    return None


def archetype_errors(
    *,
    archetype_key: str,
    family: str,
    author_pole: str,
    responsible_pole: str,
    activity: str,
    status: str,
    pattern_seed_key: str | None,
    plan_seed_key: str | None,
    texts: tuple[str, ...],
    routing_unassigned: bool = False,
    has_signal: bool = True,
    execution_seed_key: str | None = None,
) -> list[str]:
    archetype = ARCHETYPES[archetype_key]
    errors: list[str] = []
    if family not in archetype.families:
        errors.append(f"{archetype_key}: family {family} is outside the archetype")
    if author_pole not in archetype.observer_poles:
        errors.append(f"{archetype_key}: {author_pole} cannot observe this")
    if responsible_pole not in archetype.responsible_poles:
        errors.append(f"{archetype_key}: {responsible_pole} is not the responsible pole")
    if activity not in archetype.activities:
        errors.append(f"{archetype_key}: activity {activity} is outside the archetype")
    if status not in archetype.statuses:
        errors.append(f"{archetype_key}: status {status} is incoherent")
    if pattern_seed_key and pattern_seed_key not in archetype.patterns:
        errors.append(f"{archetype_key}: pattern {pattern_seed_key} is incompatible")
    if (
        plan_seed_key
        and not is_oneshot_plan(plan_seed_key)
        and plan_seed_key not in archetype.plans
    ):
        errors.append(f"{archetype_key}: plan {plan_seed_key} is incompatible")
    if status == "in_progress":
        errors.extend(
            in_progress_relation_errors(
                archetype_key=archetype_key,
                plan_seed_key=plan_seed_key,
                execution_seed_key=execution_seed_key,
            )
        )
    if routing_unassigned and not archetype.allows_unassigned:
        errors.append(f"{archetype_key}: cannot be unassigned")
    if not has_signal and not archetype.allows_no_signal:
        errors.append(f"{archetype_key}: cannot exist without a Signal")
    if family == "continuous_improvement" and not continuous_improvement_justified(texts):
        errors.append(f"{archetype_key}: continuous improvement is not justified by the content")
    if family == "opportunity" and (pattern_seed_key or plan_seed_key):
        errors.append(f"{archetype_key}: opportunity cannot carry a plan or Pattern")
    if status == "interesting" and plan_seed_key:
        errors.append(f"{archetype_key}: interesting cannot have a plan")
    if family == "cross_pole_coordination" and author_pole == responsible_pole:
        errors.append(f"{archetype_key}: cross-pole needs a distinct observer")
    for text in texts:
        folded = text.casefold()
        if any(clause in folded for clause in FORBIDDEN_GENERIC_CLAUSES):
            errors.append(f"{archetype_key}: generic family suffix in visible text")
        if "mama shelter" in folded and "club sonore" not in folded and "bringue" not in folded:
            errors.append(f"{archetype_key}: establishment name in visible text")
    return errors


def in_progress_relation_errors(
    *,
    archetype_key: str,
    plan_seed_key: str | None,
    execution_seed_key: str | None,
) -> list[str]:
    archetype = ARCHETYPES[archetype_key]
    errors: list[str] = []
    if not plan_seed_key or not execution_seed_key:
        errors.append(f"{archetype_key}: in_progress needs a plan and an execution")
    elif not is_oneshot_plan(plan_seed_key) and plan_seed_key not in archetype.plans:
        errors.append(f"{archetype_key}: in_progress plan is not authorized")
    return errors
