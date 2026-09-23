"""Editorial classification for authored Mama Nice scenarios."""

from __future__ import annotations

from collections import Counter

from houston.establishments.mama_nice_dataset_copy import (
    PATTERN_BY_TOPIC,
    PATTERN_POLE,
    PATTERN_QUOTA,
)

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "clim": ("clim", "climatisation", "thermostat"),
    "linge": ("linge", "drap", "serviette", "peignoir", "taie", "housse", "plaid"),
    "chambre_prete": ("pas prête", "n'est pas prête", "chambre prête", "ménage"),
    "checkin": ("check-in", "check-out", "file au lobby", "file au check"),
    "caisse_hotel": ("caisse de la réception", "note à la réception", "facture", "taxe de séjour"),
    "piscine": ("piscine", "bassin", "pédiluve", "transat"),
    "buffet": ("buffet", "jus", "viennoiser", "yaourt", "pain"),
    "cafe": ("café", "machine à café", "toaster", "presse"),
    "proprete_pdj": ("buffet", "miette", "plateau sale", "nappe"),
    "attente_resto": ("file du", "attente", "vingt minutes"),
    "erreur_service": ("commande", "mauvais plat", "table 12", "note de la table"),
    "stock_bar": ("bar", "stock", "plus de ", "rupture"),
    "caisse_resto": ("caisse", "clôture", "écart"),
    "plonge": ("plonge", "évacuation", "vaisselle"),
    "rooftop": ("rooftop",),
    "audiovisuel": ("clickshare", "écran", "sono", "hdmi", "vidéo"),
    "eclairage": ("éclairage", "ampoule", "luminaire", "interrupteur"),
    "fuite": ("fuite", "siphon", "chasse", "robinet"),
    "borne": ("borne",),
    "signaletique": ("signalétique", "flèche", "panneau", "plaque", "pictogramme"),
    "avis": ("avis",),
    "effectif": ("planning", "extra", "sous-effectif", "effectif"),
}

EVENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dj_sets": ("lienders", "dj set", "dj "),
    "super_sunday": ("super sunday",),
    "la_bringue": ("bringue",),
    "mama_club_sonore": ("club sonore",),
    "seminaires": ("horizon azur", "séminaire", "seminaire"),
    "privatisations": ("privatisation",),
}

CROSS_AUTHOR: dict[str, str] = {
    "clim": "hotel",
    "fuite": "hotel",
    "eclairage": "hotel",
    "borne": "hotel",
    "buffet": "restaurant",
    "cafe": "maintenance",
    "avis": "restaurant",
    "audiovisuel": "maintenance",
    "signaletique": "communication",
    "effectif": "hotel",
    "linge": "maintenance",
    "chambre_prete": "restaurant",
    "attente_resto": "hotel",
    "rooftop": "maintenance",
}

CANCEL_REASON_BY_HINT: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("groupe", "réservation", "contrat"),
        "Le client a déplacé la date, la préparation n'a plus lieu.",
    ),
    (
        ("privatisation", "séminaire", "atelier"),
        "La réservation a été annulée, la salle est libérée.",
    ),
    (("doublon", "déjà"), "Doublon d'un Signal déjà ouvert le même matin."),
    (("avis",), "L'avis a été retiré par le client avant la réponse."),
    (("planning", "extra"), "L'extra s'est présenté, le trou de staffing n'a plus lieu."),
    (("clim", "wifi", "clickshare"), "L'écart a disparu avant le passage, rien à traiter."),
    (("file", "attente"), "Le pic s'est résorbé tout seul, plus rien à traiter."),
)

FALLBACK_CANCEL_REASON = "Le besoin a été retiré avant intervention, le Signal n'a plus d'objet."


def infer_topic(*, focus: str, topic: str | None, subject: str) -> str | None:
    if topic and topic in PATTERN_BY_TOPIC:
        return topic
    folded = focus.casefold()
    subject_topics = {
        "hotel__linge": "linge",
        "hotel__menage": "chambre_prete",
        "hotel__check_in_out": "checkin",
        "hotel__facturation_caisse": "caisse_hotel",
        "maintenance__cvc": "clim",
        "maintenance__plomberie_eau": "fuite",
        "maintenance__electricite": "eclairage",
        "communication__e_reputation": "avis",
        "rh__planning": "effectif",
        "petit_dejeuner__stock": "buffet",
        "petit_dejeuner__proprete": "proprete_pdj",
        "evenements_privatisations__preparation_logistique": "audiovisuel",
        "evenements_privatisations__communication": "signaletique",
    }
    hinted = subject_topics.get(subject)
    if hinted:
        keywords = TOPIC_KEYWORDS[hinted]
        if any(token in folded for token in keywords):
            return hinted
    ranked: list[tuple[int, str]] = []
    for name, keywords in TOPIC_KEYWORDS.items():
        hits = sum(1 for token in keywords if token in folded)
        if hits:
            ranked.append((hits, name))
    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][1]


def infer_activity(*, pole: str, unit: str, focus: str) -> str:
    folded = focus.casefold()
    for activity, keywords in EVENT_KEYWORDS.items():
        if any(token in folded for token in keywords):
            return activity
    if unit in {"atelier_1", "atelier_2", "studio_1", "studio_2"}:
        return "ateliers_studios"
    if unit in {"rooftop", "piscine"}:
        return "rooftop_piscine"
    if pole == "petit_dejeuner":
        return "petit_dejeuner"
    if pole == "restaurant":
        return "restaurant_cuisine_salle"
    if pole == "rh":
        return "staffing_rh"
    if pole == "communication":
        return "communication_avis"
    if pole == "maintenance":
        return "maintenance"
    if pole == "evenements_privatisations":
        return "ateliers_studios"
    if unit == "reception_lobby":
        return "reception"
    return "hebergement_chambres"


def infer_family(
    *,
    focus: str,
    topic: str | None,
    author_pole: str,
    pole: str,
    status: str,
    interesting_kind: str | None,
    observation_count: int,
) -> str:
    if interesting_kind == "opportunity" or (
        status == "interesting" and interesting_kind != "vanished_technical"
    ):
        return "opportunity"
    if interesting_kind == "vanished_technical":
        return "operational_incident"
    folded = focus.casefold()
    if any(
        token in folded
        for token in ("contrôle", "préventif", "ronde", "avant l'ouverture", "check-list")
    ):
        return "prevention"
    if author_pole != pole:
        return "cross_pole_coordination"
    if any(
        token in folded
        for token in ("planning", "passation", "pas prête", "réassort", "clôture", "linge")
    ):
        if topic in {
            "linge",
            "chambre_prete",
            "caisse_hotel",
            "caisse_resto",
            "buffet",
            "effectif",
        }:
            return "process_inefficiency"
    if any(
        token in folded
        for token in ("file", "commande", "buffet", "plat", "service", "attente")
    ):
        if topic in {"attente_resto", "erreur_service", "buffet", "proprete_pdj", "checkin"}:
            return "service_quality"
    if any(
        token in folded
        for token in ("client", "chambre", "lobby", "bruit", "minibar", "accueil", "séjour")
    ):
        if topic in {"piscine", None} or "chambre" in folded or "lobby" in folded:
            return "guest_experience"
    if any(
        token in folded
        for token in (
            "récurrence",
            "récurrent",
            "à chaque arrivée",
            "cause commune",
            "faiblesse de processus",
            "améliorer le processus",
            "entre deux séjours",
        )
    ):
        return "continuous_improvement"
    if observation_count == 1 and topic in {
        "clim",
        "fuite",
        "borne",
        "eclairage",
        "cafe",
        "audiovisuel",
    }:
        return "operational_incident"
    return "operational_incident"


def cancel_reason_for(focus: str) -> str:
    folded = focus.casefold()
    for hints, reason in CANCEL_REASON_BY_HINT:
        if any(token in folded for token in hints):
            return f"{reason} Sujet : {focus}."
    return f"{FALLBACK_CANCEL_REASON} Sujet : {focus}."


def author_for(*, pole: str, family: str, topic: str | None, index: int) -> str:
    if family != "cross_pole_coordination":
        return pole
    mapped = CROSS_AUTHOR.get(topic or "")
    if mapped and mapped != pole:
        return mapped
    others = [key for key in ("hotel", "restaurant", "maintenance", "communication") if key != pole]
    return others[index % len(others)]


def pattern_for(*, topic: str | None, pole: str) -> str | None:
    if not topic:
        return None
    pattern = PATTERN_BY_TOPIC.get(topic)
    if pattern and PATTERN_POLE[pattern] == pole:
        return pattern
    return None


def remaining_pattern_quota(used: Counter) -> Counter:
    leftover = Counter(PATTERN_QUOTA)
    leftover.subtract(used)
    return leftover
