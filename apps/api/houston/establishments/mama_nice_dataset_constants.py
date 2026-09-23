from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")
SCHEMA_VERSION = "mama_nice_dataset_v1"

SNAPSHOT = datetime(2026, 9, 22, 23, 59, 59, tzinfo=PARIS_TZ)
ACTIVE_SIGNAL_MAX_AGE_DAYS = 30
HISTORY_START = datetime(2025, 9, 23, 0, 0, 0, tzinfo=PARIS_TZ)
FUTURE_WINDOW_START = datetime(2026, 9, 23, 0, 0, 0, tzinfo=PARIS_TZ)
FUTURE_WINDOW_END = datetime(2027, 3, 31, 23, 59, 59, tzinfo=PARIS_TZ)
HORIZON_FROM = date(2026, 9, 22)
HORIZON_UNTIL = date(2026, 10, 6)

LOCAL_ORG_NAME = "[DEMO] SPORE"
LOCAL_ESTABLISHMENT_NAME = "Mama Shelter Nice"
LOCAL_TIMEZONE = "Europe/Paris"

PROD_ORGANIZATION_ID = "7a227b49-4019-46b0-854f-e8ed9fd02fba"
PROD_ESTABLISHMENT_ID = "fe29f398-4a6b-4f9b-a92f-00805435ddc2"
PROD_OWNER_REF = "ff1db0bc-45eb-4ff0-ac0c-a5bc164a5170"
PROD_DIRECTOR_REF = "730d4681-77d7-454f-9164-756db59c7f2a"

LOCAL_OWNER_EMAIL = "leonard.p.boisson@gmail.com"
LOCAL_GOVERNANCE_DIRECTOR_EMAIL = "director.mama.nice@example.com"

OWNER_PASSWORD_ENV = "HOUSTON_MAMA_NICE_OWNER_PASSWORD"
PERSONA_PASSWORD_ENV = "HOUSTON_MAMA_NICE_PERSONA_PASSWORD"

CATALOG_KEYS = (
    "hotel",
    "petit_dejeuner",
    "restaurant",
    "maintenance",
    "communication",
    "evenements_privatisations",
    "rh",
)

SIGNAL_COUNTS_BY_POLE = {
    "hotel": 105,
    "restaurant": 85,
    "petit_dejeuner": 50,
    "maintenance": 85,
    "communication": 30,
    "evenements_privatisations": 40,
    "rh": 25,
}

SIGNAL_STATUS_COUNTS = {
    "resolved": 350,
    "canceled": 15,
    "open": 22,
    "in_progress": 23,
    "interesting": 10,
}

OBSERVATION_SOURCE_LAYOUT = (
    (1, 294),
    (2, 105),
    (3, 7),
    (4, 7),
    (5, 7),
)
INFORMATIONAL_OBSERVATION_COUNT = 104
TOTAL_OBSERVATIONS = 692
TOTAL_SIGNALS = 420

HISTORICAL_EXECUTION_COUNT = 260
HISTORICAL_FROM_SIGNAL = 180
HISTORICAL_ROUTINE = 80
HISTORICAL_DONE = 218
HISTORICAL_CANCELED = 16
HISTORICAL_IN_PROGRESS_ON_TIME = 10
HISTORICAL_PENDING_VALIDATION_ON_TIME = 10
HISTORICAL_SCHEDULED_OR_OVERDUE = 6
SKIP_COUNT = 10
REOPEN_COUNT = 3
REVIEW_COUNT = 153
REVIEW_STARS = {5: 69, 4: 54, 3: 15, 2: 8, 1: 4, 0: 3}

FUTURE_EXECUTION_COUNT = 180
FUTURE_BY_MONTH = {
    (2026, 9): 60,
    (2026, 10): 50,
    (2026, 11): 14,
    (2026, 12): 14,
    (2027, 1): 14,
    (2027, 2): 13,
    (2027, 3): 15,
}

ACTIVE_PATTERN_COUNT = 22
MERGED_PATTERN_COUNT = 1
RETIRED_PATTERN_COUNT = 1
PATTERN_SIGNAL_COUNT = 170

REUSABLE_PLAN_COUNT = 21
ACTIVE_PLAN_COUNT = 18
INACTIVE_PLAN_COUNT = 3
MONO_PLAN_COUNT = 13
RUNTIME_RH_PLAN_SEED_KEY = "plan:runtime-rh-routines"
CROSS_PLAN_COUNT = 8
SCHEDULE_COUNT = 28
SHARED_SCHEDULE_COUNT = 23
INDIVIDUAL_SCHEDULE_COUNT = 5

ACTIVE_MEMBER_COUNT = 62
DEACTIVATED_MEMBER_COUNT = 4
INVITED_MEMBER_COUNT = 2
FICTIVE_ACTIVE_COUNT = 60
PERSONA_COUNT = 10
MULTI_SCOPE_COUNT = 5
BADGE_MEMBER_COUNT = 21

COMMENT_SIGNAL_COUNT = 19
COMMENT_EXECUTION_COUNT = 65
COMMENT_TOTAL = 148
COMMENT_THREAD_REPLIES = 12
COMMENT_MENTIONS = 10
COMMENT_BUCKETS = ((1, 42), (2, 25), (3, 12), (4, 5))

RR_APPROVED = 9
RR_REJECTED = 3
UNASSIGNED_OPEN_SIGNALS = 2

SEASON_MONTHS_CLOSED = (
    date(2026, 3, 1),
    date(2026, 4, 1),
    date(2026, 5, 1),
    date(2026, 6, 1),
    date(2026, 7, 1),
    date(2026, 8, 1),
)
SEASON_MONTH_ACTIVE = date(2026, 9, 1)

ESTABLISHMENT_DESCRIPTION = (
    "Mama Shelter Nice est un hôtel lifestyle de 102 chambres combinant hébergement, "
    "restaurant et bar, petit-déjeuner et brunch, rooftop avec piscine saisonnière, "
    "parking avec bornes électriques et espaces dédiés aux séminaires et événements. "
    "Son exploitation mobilise les équipes Hôtel, Petit déjeuner, Restaurant, "
    "Maintenance, Communication, Événements & privatisations et RH, avec une forte "
    "coordination interservices autour de l'expérience client, de la restauration, "
    "de la maintenance et de l'événementiel."
)

BU_DESCRIPTIONS = {
    "hotel": (
        "Le pôle Hôtel regroupe les opérations liées à l'accueil, à la réception, "
        "aux séjours, aux chambres, au ménage et au linge. Il assure le suivi de "
        "l'expérience client, des arrivées et départs, de la préparation des chambres "
        "et des incidents rencontrés pendant le séjour, en coordination avec la "
        "Maintenance et les autres pôles concernés."
    ),
    "petit_dejeuner": (
        "Le pôle Petit déjeuner est responsable du service matinal quotidien, ouvert "
        "de 7 h à 11 h, depuis la préparation et l'ouverture du buffet jusqu'au "
        "débarrassage et à la clôture. Il couvre la mise en place, le réassort, les "
        "produits dédiés, la propreté de l'espace et l'accueil des clients pendant ce "
        "service. Les déjeuners, dîners, brunchs, activités du bar et du rooftop "
        "relèvent du pôle Restaurant, avec lequel il coordonne les stocks, la cuisine "
        "et les transitions de service."
    ),
    "restaurant": (
        "Le pôle Restaurant est responsable des déjeuners, dîners et brunchs ainsi "
        "que des activités du bar, de la cuisine et du rooftop. Il couvre la "
        "préparation, la mise en place, le service, l'accueil client, les stocks, les "
        "équipements, les ouvertures, les fermetures et le suivi des caisses, en "
        "coordination avec Maintenance, Communication et Événements & privatisations."
    ),
    "maintenance": (
        "Le pôle Maintenance est un service transversal qui intervient auprès de "
        "l'ensemble des pôles et des espaces de l'établissement. Il assure le bon "
        "fonctionnement des bâtiments, installations et équipements, prend en charge "
        "les incidents techniques, organise la maintenance préventive et coordonne "
        "les contrôles de sécurité ainsi que les prestataires externes."
    ),
    "communication": (
        "Le pôle Communication est un service transversal chargé de l'image et de la "
        "visibilité de l'établissement. Il pilote les contenus, les réseaux sociaux, "
        "la communication commerciale et locale, l'e-réputation ainsi que la "
        "promotion des offres et événements, en coordination avec les pôles concernés."
    ),
    "evenements_privatisations": (
        "Le pôle Événements & privatisations organise les séminaires, réunions, "
        "célébrations et privatisations accueillis dans les Ateliers, Studios et "
        "autres espaces de l'établissement. Il coordonne la préparation, la "
        "logistique, les besoins techniques, l'accueil, la restauration et le suivi "
        "client avec les équipes concernées."
    ),
    "rh": (
        "Le pôle Ressources humaines est un service transversal chargé de "
        "l'accompagnement des équipes et du suivi des collaborateurs. Il couvre le "
        "recrutement, l'intégration, la formation, les plannings, l'administration "
        "du personnel et les besoins de staffing, en coordination avec les managers "
        "des différents pôles."
    ),
}

OBJECT_TYPE_MEMBERSHIP = "membership"
OBJECT_TYPE_OBSERVATION = "observation"
OBJECT_TYPE_SIGNAL = "signal"
OBJECT_TYPE_PATTERN = "pattern"
OBJECT_TYPE_PLAN = "plan"
OBJECT_TYPE_SCHEDULE = "schedule"
OBJECT_TYPE_EXECUTION = "execution"
OBJECT_TYPE_COMMENT = "comment"
OBJECT_TYPE_REVIEW = "review"
OBJECT_TYPE_SEASON = "season"
OBJECT_TYPE_OPERATIONAL_UNIT = "operational_unit"
OBJECT_TYPE_CLOCK = "clock"

ALLOWED_OBJECT_TYPES = frozenset(
    {
        OBJECT_TYPE_MEMBERSHIP,
        OBJECT_TYPE_OBSERVATION,
        OBJECT_TYPE_SIGNAL,
        OBJECT_TYPE_PATTERN,
        OBJECT_TYPE_PLAN,
        OBJECT_TYPE_SCHEDULE,
        OBJECT_TYPE_EXECUTION,
        OBJECT_TYPE_COMMENT,
        OBJECT_TYPE_REVIEW,
        OBJECT_TYPE_SEASON,
        OBJECT_TYPE_OPERATIONAL_UNIT,
        OBJECT_TYPE_CLOCK,
    }
)

NARRATIVE_FAMILIES = (
    "operational_incident",
    "guest_experience",
    "service_quality",
    "prevention",
    "process_inefficiency",
    "cross_pole_coordination",
    "continuous_improvement",
    "opportunity",
)

NARRATIVE_FAMILY_COUNTS = {
    "operational_incident": 74,
    "guest_experience": 52,
    "service_quality": 50,
    "prevention": 44,
    "process_inefficiency": 44,
    "cross_pole_coordination": 50,
    "continuous_improvement": 98,
    "opportunity": 8,
}

MAMA_NICE_ACTIVITIES = (
    "hebergement_chambres",
    "reception",
    "petit_dejeuner",
    "restaurant_cuisine_salle",
    "rooftop_piscine",
    "maintenance",
    "communication_avis",
    "ateliers_studios",
    "dj_sets",
    "super_sunday",
    "la_bringue",
    "mama_club_sonore",
    "seminaires",
    "privatisations",
    "staffing_rh",
)

OVERDUE_MIN_DAYS = 2
OVERDUE_MAX_DAYS = 7
OVERDUE_EXECUTION_COUNT = 6
INTERESTING_VANISHED_TECHNICAL_MAX = 2

ESTABLISHMENT_NAME_FRAGMENTS = ("mama shelter nice", "mama shelter")

CHAT_OBJECT_TYPES = frozenset(
    {
        "chat",
        "chat_conversation",
        "chat_message",
        "chat_mention",
        "chat_attachment",
    }
)

WEEKDAYS_ALL = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def paris_dt(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0):
    return datetime(year, month, day, hour, minute, second, tzinfo=PARIS_TZ)


def combine_paris(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=PARIS_TZ)
