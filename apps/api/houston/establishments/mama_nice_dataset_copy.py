"""Deterministic French copy for the Mama Nice demo corpus.

Seed keys stay internal. Everything this module emits can appear in the
product: signal titles, observations, comments, execution labels.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta

from houston.establishments.mama_nice_dataset_situations import ROWS

_MAX_CROSS_PREFIX = 42
_TECHNICAL = re.compile(
    r"incident\s+\d+|signal\s*:\s*\d+|obs\s*:\s*\d+|point d'info service\s+\d+|"
    r"\b(?:todo|lorem|placeholder|xxx)\b",
    re.IGNORECASE,
)
_SLUGS = (
    "evenements_privatisations",
    "petit_dejeuner",
    "back_office_administratif",
    "reception_lobby",
    "circulations_chambres",
    "restaurant_rdc",
    "bar_central",
    "plonge_economat",
    "atelier_1",
    "atelier_2",
    "studio_1",
    "studio_2",
    "bornes_electriques",
    "locaux_techniques",
    "operational_unit",
    "issue_focus",
    "seed_key",
)
POLE_UNITS: dict[str, frozenset[str]] = {
    "hotel": frozenset(
        {
            "reception_lobby",
            "chambres",
            "circulations_chambres",
            "piscine",
            "breakroom",
        }
    ),
    "petit_dejeuner": frozenset({"restaurant_rdc"}),
    "restaurant": frozenset(
        {
            "restaurant_rdc",
            "bar_central",
            "cuisine",
            "plonge_economat",
            "rooftop",
        }
    ),
    "maintenance": frozenset(
        {
            "chambres",
            "circulations_chambres",
            "parking",
            "locaux_techniques",
            "bornes_electriques",
            "piscine",
            "rooftop",
            "reception_lobby",
            "bar_central",
            "back_office_administratif",
        }
    ),
    "communication": frozenset(
        {
            "back_office_administratif",
            "reception_lobby",
            "rooftop",
            "bar_central",
        }
    ),
    "evenements_privatisations": frozenset(
        {
            "atelier_1",
            "atelier_2",
            "studio_1",
            "studio_2",
            "rooftop",
            "reception_lobby",
            "breakroom",
        }
    ),
    "rh": frozenset({"breakroom", "back_office_administratif"}),
}

UNIT_HINTS: dict[str, tuple[str, ...]] = {
    "reception_lobby": ("réception", "lobby", "check-in", "check-out"),
    "chambres": ("chambre", "suite"),
    "circulations_chambres": ("couloir", "palier", "escalier"),
    "restaurant_rdc": ("restaurant", "buffet", "salle"),
    "bar_central": ("bar",),
    "cuisine": ("cuisine",),
    "plonge_economat": ("plonge", "économat"),
    "rooftop": ("rooftop",),
    "piscine": ("piscine",),
    "atelier_1": ("atelier 1",),
    "atelier_2": ("atelier 2",),
    "breakroom": ("breakroom",),
    "studio_1": ("studio 1",),
    "studio_2": ("studio 2",),
    "parking": ("parking",),
    "bornes_electriques": ("borne",),
    "locaux_techniques": ("local technique",),
    "back_office_administratif": ("back-office", "bureau"),
}

SUBJECT_HINTS: dict[str, tuple[str, ...]] = {
    "hotel__experience_client": ("piscine", "chambre", "lobby", "minibar", "coffre"),
    "hotel__menage": ("chambre", "ménage", "douche", "lit", "balcon"),
    "hotel__maintenance": ("chambre", "serrure", "ampoule", "thermostat"),
    "hotel__linge": ("serviette", "drap", "peignoir", "linge", "housse", "taie", "plaid"),
    "hotel__check_in_out": ("check-in", "check-out", "lobby", "réception", "file"),
    "hotel__communication": ("lobby", "affichage", "affiche", "livret", "écran", "wifi"),
    "hotel__commercialisation": ("réservation", "site", "tarif", "offre", "promo", "forfait"),
    "hotel__rh": ("planning", "breakroom", "formation", "extra", "congé"),
    "hotel__signaletique": ("lobby", "chambre", "flèche", "panneau", "plaque", "plan"),
    "hotel__facturation_caisse": ("caisse", "réception", "note", "facture", "paiement"),
    "petit_dejeuner__experience_client": ("buffet",),
    "petit_dejeuner__proprete": ("buffet",),
    "petit_dejeuner__mise_en_place": ("buffet",),
    "petit_dejeuner__rh": ("buffet", "planning"),
    "petit_dejeuner__maintenance": ("buffet", "machine", "toaster", "presse"),
    "petit_dejeuner__menu": ("buffet",),
    "petit_dejeuner__stock": ("buffet",),
    "petit_dejeuner__commercialisation": ("buffet", "petit-déjeuner"),
    "restaurant__experience_client": ("restaurant", "table"),
    "restaurant__proprete": ("restaurant",),
    "restaurant__mise_en_place": ("restaurant", "plonge", "économat"),
    "restaurant__service_accueil": ("restaurant", "bar", "file"),
    "restaurant__maintenance": ("rooftop", "cuisine", "bar"),
    "restaurant__communication": ("restaurant", "ardoise", "menu", "bar"),
    "restaurant__rh": ("restaurant", "planning", "serveur", "extra"),
    "restaurant__menu": ("restaurant", "menu", "ardoise", "carte", "bar"),
    "restaurant__stock": ("bar", "restaurant"),
    "restaurant__commercialisation": ("restaurant", "rooftop", "bar", "site"),
    "restaurant__admin": ("caisse", "restaurant", "bar"),
    "maintenance__cvc": ("clim", "chambre"),
    "maintenance__electricite": ("chambre", "couloir", "parking", "local technique", "escalier"),
    "maintenance__plomberie_eau": ("chambre", "fuite", "siphon", "chasse", "robinet"),
    "maintenance__maintenance_batiment_second_uvre": (
        "chambre",
        "couloir",
        "local technique",
        "parking",
        "palier",
    ),
    "maintenance__equipements_dexploitation": ("clim", "chambre", "borne"),
    "maintenance__reseau_informatique": ("wifi", "réseau", "chambre", "local technique"),
    "maintenance__securite_conformite": (
        "parking",
        "couloir",
        "chambre",
        "local technique",
        "lobby",
        "rooftop",
    ),
    "maintenance__logistique_consommables_techniques": ("borne", "local technique"),
    "maintenance__ouverture_fermeture_technique": (
        "local technique",
        "parking",
        "piscine",
        "rooftop",
        "borne",
    ),
    "maintenance__prestataires_sous_traitance": (
        "prestataire",
        "chambre",
        "lobby",
        "piscine",
        "rooftop",
        "borne",
    ),
    "communication__reseaux_sociaux": ("avis",),
    "communication__image_de_marque": ("avis", "photo", "réponse"),
    "communication__acquisition_visibilite": ("campagne", "story", "réservation"),
    "communication__animation_communaute": ("story", "message", "communauté"),
    "communication__communication_commerciale": ("newsletter", "offre", "post"),
    "communication__crm_relation_client": ("avis", "code", "questionnaire"),
    "communication__contenu_production": ("vidéo",),
    "communication__e_reputation": ("avis",),
    "communication__partenariats_influence": ("partenaire", "collaboration"),
    "communication__site_web_plateformes": ("site", "réservation"),
    "communication__communication_locale": ("fiche", "article", "guide"),
    "communication__data_performance_marketing": ("avis", "réservation", "clic"),
    "evenements_privatisations__preparation_logistique": ("atelier", "studio", "clickshare"),
    "evenements_privatisations__experience_client": ("atelier", "studio"),
    "evenements_privatisations__communication": ("atelier", "studio", "lobby", "signalétique"),
    "evenements_privatisations__commercialisation": ("atelier", "studio", "rooftop", "devis"),
    "evenements_privatisations__rh_planning": ("planning", "atelier", "studio", "rooftop"),
    "evenements_privatisations__facturation": (
        "atelier",
        "studio",
        "rooftop",
        "facture",
        "acompte",
    ),
    "rh__recrutement": ("poste", "candidat", "vivier"),
    "rh__planning": ("planning",),
    "rh__formation": ("formation", "breakroom", "module"),
    "rh__culture_engagement": ("breakroom", "brief"),
    "rh__paie": ("paie", "bulletin", "avenant"),
    "rh__bien_etre": ("breakroom", "planning", "coupure"),
    "rh__discipline_conflits": ("brief", "tenue", "breakroom"),
    "rh__securite_conformite_sociale": ("breakroom", "bureau", "visite"),
    "rh__interim_prestataires": ("intérim", "breakroom", "agence"),
}

PATTERN_BY_TOPIC: dict[str, str] = {
    "clim": "pattern:clim-chambres",
    "linge": "pattern:linge",
    "chambre_prete": "pattern:chambres-non-pretes",
    "checkin": "pattern:attente-checkin",
    "caisse_hotel": "pattern:facturation-caisse",
    "piscine": "pattern:piscine",
    "buffet": "pattern:ruptures-buffet",
    "cafe": "pattern:equipements-cafe",
    "proprete_pdj": "pattern:proprete-buffet",
    "attente_resto": "pattern:attente-restaurant",
    "erreur_service": "pattern:erreurs-service",
    "stock_bar": "pattern:ruptures-bar",
    "caisse_resto": "pattern:cloture-caisse",
    "plonge": "pattern:evacuations-cuisine",
    "rooftop": "pattern:equipements-rooftop",
    "audiovisuel": "pattern:audiovisuel-ateliers",
    "eclairage": "pattern:eclairage",
    "fuite": "pattern:fuites",
    "borne": "pattern:bornes",
    "signaletique": "pattern:signaletique-event",
    "avis": "pattern:avis-negatifs",
    "effectif": "pattern:sous-effectif",
}

PATTERN_POLE: dict[str, str] = {
    "pattern:clim-chambres": "maintenance",
    "pattern:linge": "hotel",
    "pattern:chambres-non-pretes": "hotel",
    "pattern:attente-checkin": "hotel",
    "pattern:facturation-caisse": "hotel",
    "pattern:piscine": "hotel",
    "pattern:ruptures-buffet": "petit_dejeuner",
    "pattern:equipements-cafe": "petit_dejeuner",
    "pattern:proprete-buffet": "petit_dejeuner",
    "pattern:attente-restaurant": "restaurant",
    "pattern:erreurs-service": "restaurant",
    "pattern:ruptures-bar": "restaurant",
    "pattern:cloture-caisse": "restaurant",
    "pattern:evacuations-cuisine": "restaurant",
    "pattern:equipements-rooftop": "restaurant",
    "pattern:audiovisuel-ateliers": "evenements_privatisations",
    "pattern:eclairage": "maintenance",
    "pattern:fuites": "maintenance",
    "pattern:bornes": "maintenance",
    "pattern:signaletique-event": "evenements_privatisations",
    "pattern:avis-negatifs": "communication",
    "pattern:sous-effectif": "rh",
}

PATTERN_QUOTA: dict[str, int] = {
    "pattern:clim-chambres": 16,
    "pattern:linge": 8,
    "pattern:chambres-non-pretes": 8,
    "pattern:attente-checkin": 8,
    "pattern:facturation-caisse": 6,
    "pattern:piscine": 6,
    "pattern:ruptures-buffet": 12,
    "pattern:equipements-cafe": 6,
    "pattern:proprete-buffet": 6,
    "pattern:attente-restaurant": 10,
    "pattern:erreurs-service": 8,
    "pattern:ruptures-bar": 6,
    "pattern:cloture-caisse": 6,
    "pattern:evacuations-cuisine": 6,
    "pattern:equipements-rooftop": 6,
    "pattern:audiovisuel-ateliers": 12,
    "pattern:eclairage": 8,
    "pattern:fuites": 6,
    "pattern:bornes": 6,
    "pattern:signaletique-event": 8,
    "pattern:avis-negatifs": 6,
    "pattern:sous-effectif": 6,
}

_SECOND = (
    "Je confirme sur place",
    "Le client vient de le redire",
    "Vu à l'instant avec l'équipe",
    "Je repasse avant le prochain service",
    "Contrôle fait, c'est net",
    "On a la même info au poste",
    "Le responsable de zone confirme",
    "Ça n'a pas bougé depuis tout à l'heure",
    "Je viens de revérifier",
    "Retour du client, identique",
    "L'équipe suivante voit la même chose",
    "Toujours le cas au moment du passage",
)
_LATER = (
    (
        "Troisième passage, rien n'a changé",
        "On me le signale encore une fois",
        "J'ai revu la zone avec un collègue",
        "Le constat tient toujours",
        "Même situation au contrôle suivant",
        "Je laisse une trace de plus",
        "Personne n'a pu corriger entre-temps",
    ),
    (
        "Quatrième regard, c'est inchangé",
        "Le sujet est toujours ouvert sur le terrain",
        "Je revérifie avant la passation",
        "L'info est la même en fin de vacation",
        "On tourne en rond, le constat reste",
        "Dernier état avant de transmettre",
        "Je note encore une fois le même écart",
    ),
    (
        "Cinquième passage, toujours identique",
        "Je clôture la trace terrain sur ce constat",
        "Ultime vérification, rien n'a bougé",
        "Le dernier contrôle dit la même chose",
        "On a assez de retours concordants",
        "Je confirme une dernière fois avant relais",
        "La situation n'a pas évolué du tout",
    ),
)


@dataclass(frozen=True)
class Situation:
    unit: str
    focus: str
    canonical: str
    proof: str
    topic: str | None = None


@dataclass(frozen=True)
class GoldenSignal:
    focus: str
    canonical: str
    unit: str
    subject: str
    observations: tuple[str, ...]


GOLDEN_BY_INDEX: dict[int, GoldenSignal] = {
    0: GoldenSignal(
        focus="La clim de la chambre 318 ne refroidit plus",
        canonical="la climatisation",
        unit="chambres",
        subject="hotel__maintenance",
        observations=(
            "La clim de la 318 souffle mais ne refroidit plus, le client revient vers 18 h.",
            "Je confirme à l'étage : air tiède en chambre 318, le client l'a redit à la réception.",
        ),
    ),
    1: GoldenSignal(
        focus="La clim de la chambre 214 souffle tiède",
        canonical="la climatisation",
        unit="chambres",
        subject="hotel__maintenance",
        observations=(
            "En chambre 214 la clim tourne et l'air reste tiède, le client l'a signalé hier soir.",
        ),
    ),
    2: GoldenSignal(
        focus="La clim de la chambre 426 s'est coupée",
        canonical="la climatisation",
        unit="chambres",
        subject="hotel__maintenance",
        observations=(
            "La clim de la 426 s'est arrêtée dans la nuit, le client a appelé la réception à 6 h.",
        ),
    ),
}


def _s(
    unit: str,
    focus: str,
    canonical: str,
    proof: str,
    topic: str | None = None,
) -> Situation:
    return Situation(unit=unit, focus=focus, canonical=canonical, proof=proof, topic=topic)


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(hint.casefold() in folded for hint in hints)


def observation_lines(situation: Situation, count: int, slot: int) -> list[str]:
    lines = [f"{situation.focus}, {situation.proof}."]
    openers: list[str] = []
    if count >= 2:
        openers.append(_SECOND[slot % len(_SECOND)])
    for offset, pool in enumerate(_LATER, start=2):
        if len(openers) >= count - 1:
            break
        openers.append(pool[(slot + offset) % len(pool)])
    for opener in openers:
        lowered = opener[0].lower() + opener[1:]
        lines.append(f"{situation.focus} : {lowered}, {situation.proof}.")
    if len(lines) < count:
        raise ValueError(f"not enough observation lines for {situation.focus}")
    return lines[:count]


def execution_title(focus: str) -> str:
    return focus.strip()


def execution_tasks(canonical: str) -> tuple[str, str, str]:
    return (
        f"Constater {canonical} sur place",
        f"Corriger {canonical}",
        f"Confirmer que {canonical} est rétabli",
    )


def signal_comment_body(focus: str, index: int) -> str:
    frames = (
        "Je peux passer après le service. Le sujet : {focus}.",
        "On le reprend au brief de fin de shift. {focus}.",
        "Je reste disponible si quelqu'un monte. {focus}.",
        "Vu de mon côté, il faut un passage. {focus}.",
        "Je note pour ne pas le perdre au changement d'équipe. {focus}.",
        "On en parle au prochain point terrain. {focus}.",
        "Je garde un œil, dites-moi si c'est pris. {focus}.",
        "Pas urgentissime, mais il ne faut pas l'oublier. {focus}.",
    )
    return frames[index % len(frames)].format(focus=focus)


def execution_comment_body(title: str, index: int) -> str:
    frames = (
        "J'ai commencé le premier passage. On est sur : {title}.",
        "Point d'avancement : la première vérif est faite. {title}.",
        "Je repasse en fin de service pour boucler. {title}.",
        "Le terrain confirme, je poursuis. {title}.",
        "J'ai prévenu l'équipe en place. {title}.",
        "Rien de bloquant de plus pour l'instant. {title}.",
        "Je laisse l'état avant la passation. {title}.",
        "Deuxième regard fait, je mets à jour. {title}.",
    )
    return frames[index % len(frames)].format(title=title)


def reply_body(title: str, index: int) -> str:
    frames = (
        "Bien reçu. On cale le prochain passage pour : {title}.",
        "OK, garde la trace et préviens-moi si ça bouge. {title}.",
        "Merci, je valide le créneau suivant. {title}.",
        "Noté. On ne clôture pas tant que ce n'est pas revu. {title}.",
    )
    return frames[index % len(frames)].format(title=title)


def _technical_errors(text: str, label: str) -> list[str]:
    errors: list[str] = []
    if "_" in text:
        errors.append(f"{label}: underscore in visible text")
    lowered = text.casefold()
    for slug in _SLUGS:
        if slug in lowered:
            errors.append(f"{label}: technical slug {slug}")
    if _TECHNICAL.search(text):
        errors.append(f"{label}: generic or technical placeholder")
    return errors


def _shared_prefix(left: str, right: str) -> int:
    count = 0
    for char_a, char_b in zip(left, right, strict=False):
        if char_a != char_b:
            break
        count += 1
    return count


def informational_texts() -> tuple[str, ...]:
    return _INFO


def situation_for(subject: str, slot: int) -> Situation:
    bank = BANKS[subject]
    if slot >= len(bank):
        raise KeyError(f"{subject} has no situation for slot {slot} ({len(bank)} available)")
    return bank[slot]


def bank_errors() -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    if sum(PATTERN_QUOTA.values()) != 170:
        errors.append(f"pattern quotas sum to {sum(PATTERN_QUOTA.values())}")
    for subject, rows in BANKS.items():
        hints = SUBJECT_HINTS.get(subject)
        if not hints:
            errors.append(f"{subject}: missing subject hints")
            continue
        for slot, row in enumerate(rows):
            label = f"{subject}[{slot}]"
            if len(row.focus) > 80:
                errors.append(f"{label}: focus length {len(row.focus)}")
            if row.topic and row.topic not in PATTERN_BY_TOPIC:
                errors.append(f"{label}: unknown topic {row.topic}")
            unit_hints = UNIT_HINTS.get(row.unit)
            if unit_hints is None:
                errors.append(f"{label}: unknown unit {row.unit}")
            elif not _contains_any(row.proof, unit_hints):
                errors.append(f"{label}: proof does not mention the place")
            pole = subject.split("__", 1)[0]
            if row.unit not in POLE_UNITS.get(pole, frozenset()):
                errors.append(f"{label}: unit {row.unit} is not coherent with {pole}")
            if not _contains_any(row.focus, hints):
                errors.append(f"{label}: focus does not match subject")
            for piece, name in (
                (row.focus, "focus"),
                (row.proof, "proof"),
                (row.canonical, "canonical"),
            ):
                errors.extend(_technical_errors(piece, f"{label} {name}"))
            key = " ".join(row.focus.casefold().split())
            if key in seen:
                errors.append(f"{label}: duplicate focus with {seen[key]}")
            seen[key] = label
    for index, golden in GOLDEN_BY_INDEX.items():
        label = f"golden[{index}]"
        if len(golden.focus) > 80:
            errors.append(f"{label}: focus length {len(golden.focus)}")
        key = " ".join(golden.focus.casefold().split())
        if key in seen:
            errors.append(f"{label}: duplicate focus with {seen[key]}")
        seen[key] = label
        errors.extend(_technical_errors(golden.focus, label))
        for obs_index, text in enumerate(golden.observations):
            errors.extend(_technical_errors(text, f"{label} obs {obs_index}"))
            if not _contains_any(text, ("318", "214", "426")):
                errors.append(f"{label} obs {obs_index}: missing room")
    if len(_INFO) != 104:
        errors.append(f"informational notes {len(_INFO)} != 104")
    info_seen: set[str] = set()
    for index, text in enumerate(_INFO):
        errors.extend(_technical_errors(text, f"info[{index}]"))
        if text in info_seen:
            errors.append(f"info[{index}]: duplicate")
        info_seen.add(text)
        if " ".join(text.casefold().split()) in seen:
            errors.append(f"info[{index}]: collides with a signal focus")
    return errors


def assign_pattern_keys(signals: list[dict]) -> list[str]:
    remaining = Counter(PATTERN_QUOTA)
    for signal in signals:
        if signal.get("pattern_seed_key"):
            pattern = signal["pattern_seed_key"]
            if remaining[pattern] <= 0:
                return [f"{signal['seed_key']}: pattern {pattern} over quota"]
            remaining[pattern] -= 1
    errors: list[str] = []
    for signal in signals:
        if signal.get("pattern_seed_key"):
            continue
        # Authored scenarios already carry their Pattern relation. Do not invent one.
    short = {key: count for key, count in remaining.items() if count}
    if short:
        errors.append(f"pattern quotas short: {short}")
    patterned = sum(1 for signal in signals if signal.get("pattern_seed_key"))
    if patterned != 170:
        errors.append(f"patterned signals {patterned} != 170")
    return errors


def copy_quality_errors(
    *,
    signals: list[dict],
    observations: list[dict],
    extra_visible: list[str],
) -> list[str]:
    errors = bank_errors()
    focuses = [" ".join(signal["issue_focus"].casefold().split()) for signal in signals]
    if len(focuses) != len(set(focuses)):
        errors.append("signal issue focuses are not unique after normalization")
    by_signal: dict[str, list[dict]] = {}
    for obs in observations:
        by_signal.setdefault(obs.get("signal_seed_key") or "", []).append(obs)
        errors.extend(_technical_errors(obs["raw_text"], obs["seed_key"]))
    texts = [obs["raw_text"] for obs in observations]
    if len(texts) != len(set(texts)):
        errors.append("observation texts must be unique")
    grouped = [obs for obs in observations if obs.get("signal_seed_key")]
    for left_index, left in enumerate(grouped):
        for right in grouped[left_index + 1 :]:
            if left["signal_seed_key"] == right["signal_seed_key"]:
                continue
            if _shared_prefix(left["raw_text"], right["raw_text"]) > _MAX_CROSS_PREFIX:
                errors.append(
                    "observation texts share a long prefix across incidents: "
                    f"{left['seed_key']} / {right['seed_key']}"
                )
                return errors
    for signal in signals:
        group = by_signal.get(signal["seed_key"], [])
        errors.extend(_technical_errors(signal["issue_focus"], signal["seed_key"]))
        errors.extend(_technical_errors(signal["title"], f"{signal['seed_key']} title"))
        errors.extend(
            _technical_errors(signal["canonical_object"], f"{signal['seed_key']} object")
        )
        if len(group) != signal["observation_count"]:
            errors.append(
                f"{signal['seed_key']}: {len(group)} observations, "
                f"expected {signal['observation_count']}"
            )
        if signal["routing_unassigned"] and len(group) != 1:
            errors.append(f"{signal['seed_key']}: unassigned signal must have one observation")
        if any(obs["informational"] for obs in group):
            errors.append(f"{signal['seed_key']}: informational observation linked to a signal")
        times = [obs["occurred_at"] for obs in group]
        if times and max(times) - min(times) > timedelta(hours=2):
            errors.append(f"{signal['seed_key']}: observations are too far apart")
        subject_hints = SUBJECT_HINTS.get(signal["subject"], ())
        if subject_hints and not _contains_any(signal["issue_focus"], subject_hints):
            errors.append(f"{signal['seed_key']}: title does not match its subject")
        allowed_units = POLE_UNITS.get(signal["pole"], frozenset())
        if signal["operational_unit"] not in allowed_units:
            errors.append(
                f"{signal['seed_key']}: place {signal['operational_unit']} "
                f"does not belong to {signal['pole']}"
            )
        pattern = signal.get("pattern_seed_key")
        if pattern and signal["pole"] != PATTERN_POLE.get(pattern):
            allowed = signal["seed_key"] == "signal:golden-clim-318" or signal["issue_focus"] in {
                golden.focus for golden in GOLDEN_BY_INDEX.values()
            }
            if not allowed:
                errors.append(f"{signal['seed_key']}: pattern {pattern} is another pole")
    info = [obs for obs in observations if obs["informational"]]
    if any(obs["signal_seed_key"] for obs in info):
        errors.append("informational observations must not point at a signal")
    for text in extra_visible:
        errors.extend(_technical_errors(text, "visible catalogue"))
    active = [
        signal
        for signal in signals
        if signal["status"] in {"open", "in_progress", "interesting"}
    ][:19]
    comments = [
        signal_comment_body(signal["issue_focus"], index)
        for index, signal in enumerate(active)
    ]
    if len(comments) != len(set(comments)):
        errors.append("signal comments are duplicated")
    for index, comment in enumerate(comments):
        errors.extend(_technical_errors(comment, f"signal comment {index}"))
    return errors


_INFO: tuple[str, ...] = (
    "Les plannings de la semaine sont affichés au breakroom.",
    "La piscine ferme à 20 h ce soir pour l'entretien du bassin, c'est affiché.",
    "Le petit-déjeuner ouvre à 7 h demain, l'info est passée aux équipes.",
    "Le rooftop est privatisé jeudi soir, la salle du restaurant reste ouverte.",
    "Les clés maître sont de retour au coffre de la réception.",
    "Le prestataire linge passe à 6 h, les sacs sont prêts pour l'enlèvement.",
    "Rappel affiché au lobby : check-out à 11 h, late check-out selon les chambres libres.",
    "Le poisson est le plat du jour au restaurant, le brief salle est fait.",
    "L'atelier 1 est dressé pour 9 h, le café d'accueil est commandé.",
    "Les bornes du parking sont toutes en service ce matin.",
    "Du vent est annoncé, les parasols du rooftop sont fermés par précaution.",
    "Le groupe du matin est attendu à 9 h à la réception, le welcome est prêt.",
    "Les plannings extras du week-end sont publiés au breakroom.",
    "Le buffet a assez de jus et de pain pour le service, rien à relancer.",
    "La ronde de nuit n'a rien remonté, les issues étaient condamnées.",
    "Le mot de passe wifi invité a été renouvelé, il est noté au poste.",
    "Les tenues propres sont arrivées, le vestiaire du breakroom est à jour.",
    "Un compliment sur l'accueil d'hier est affiché au breakroom.",
    "La caisse de la réception a été contrôlée, les montants collent.",
    "Le studio 2 est libre cet après-midi, aucun montage en cours.",
    "L'atelier 2 est réservé demain toute la journée, le plan de salle est posé.",
    "Le menu enfant du restaurant est reconduit cette semaine, l'ardoise est à jour.",
    "Les horaires d'ouverture de la piscine sont à jour sur le chevalet du lobby.",
    "La livraison pain du matin est passée, les corbeilles du buffet sont pleines.",
    "Aucun départ de groupe aujourd'hui, la réception reste sur le rythme habituel.",
    "Le stock de peignoirs couvre les arrivées du jour.",
    "Les chambres du 3e sont toutes libérées pour le ménage de l'après-midi.",
    "Le bar ouvre à 17 h, la mise en place est déjà calée.",
    "La sono du studio 1 a été testée à vide, le son passe.",
    "Les badges du séminaire de demain sont imprimés et rangés à la réception.",
    "Le planning du restaurant de ce soir est complet, personne à remplacer.",
    "Une table de huit est confirmée à 20 h 30, la salle est prévenue.",
    "Le late check-out de la suite est accordé, la gouvernante est au courant.",
    "Les transats de la piscine sont sortis, le bassin est ouvert.",
    "Le café du lobby est en route, les tasses sont dressées.",
    "Rien à signaler sur les chambres parties ce matin, les clés sont rentrées.",
    "Le brief sécurité de la semaine a eu lieu au breakroom.",
    "Les allergies du groupe de midi sont notées en cuisine.",
    "Le rooftop rouvre à 18 h, les lampes sont vérifiées.",
    "La borne 2 a redémarré hier, elle accepte à nouveau les badges.",
    "Les draps du jour sont montés aux étages, les chariots sont pleins.",
    "Le check-in de l'après-midi est fluide, pas de file au lobby.",
    "L'écran d'accueil de l'atelier 1 affiche le bon nom de société.",
    "Le petit-déjeuner de demain est calé pour 86 couverts, le chef est prévenu.",
    "Les pauses de l'équipe étages sont posées sur le planning.",
    "Un client fidèle arrive ce soir, la réception a son préféré en note.",
    "Le menu déjeuner est affiché à l'entrée du restaurant.",
    "Les serviettes de la piscine sont en place au local ouvert.",
    "La caisse du bar a été ouverte avec le fond habituel.",
    "Aucun travaux dans les couloirs aujourd'hui, les étages sont calmes.",
    "Le studio 1 reçoit une répétition à 16 h, les chaises sont en U.",
    "Les horaires du room service sont rappelés en bas des livrets de chambre.",
    "La météo est bonne, le rooftop reste en configuration été.",
    "Les jus du buffet ont été réassortis avant le rush de 8 h 30.",
    "Le planning communication de la semaine est affiché au bureau.",
    "Une visite mystère n'est pas annoncée, on reste sur le standard.",
    "Les clés des ateliers sont au tableau de la réception.",
    "Le vestiaire client du rooftop est ouvert pour ce soir.",
    "Les fiches techniques du plat du jour sont au passe.",
    "Le bus du groupe part à 10 h, les bagages sont déjà au lobby.",
    "La fermeture piscine de dimanche est rappelée aux équipes.",
    "Les nappes du petit-déjeuner sont propres, les tables sont nappées.",
    "Un anniversaire est noté en chambre 150, le mot est prêt à la réception.",
    "Le stock de dosettes café couvre le week-end du buffet.",
    "Les issues de secours ont été contrôlées à l'ouverture, tout ferme bien.",
    "Le brief salle de 10 h 45 a eu lieu, les réservations sont lues.",
    "Aucune rupture annoncée sur la carte du soir.",
    "Les chambres communicantes demandées sont bien côte à côte.",
    "Le tapis d'entrée a été changé ce matin, il est sec.",
    "L'équipe de nuit a laissé le lobby en ordre.",
    "Les prix du jour sont ceux du PMS, l'ardoise réception est alignée.",
    "Le créneau ménage des suites est avancé, les arrivées sont à 14 h.",
    "Un journaliste passe au bar à 18 h, l'accueil est briefé.",
    "Les goodies du séminaire sont en cartons à l'atelier 2.",
    "La température du hall est confortable, la clim générale est stable.",
    "Les réservations restaurant du midi sont à 42, la cuisine est calée.",
    "Le planning RH de la semaine prochaine sort cet après-midi au breakroom.",
    "Les lampes du couloir des chambres sont toutes allumées ce matin.",
    "Un upgrade est offert sur une chambre calme, le client est prévenu.",
    "Le livre d'or du lobby a été remis en place.",
    "Les portions enfant sont prévues pour trois tables ce midi.",
    "La ligne directe des étages fonctionne, le test d'ouverture est bon.",
    "Les plantes du lobby ont été arrosées.",
    "Le service bagagerie est renforcé de 15 h à 17 h pour un car.",
    "Les sets de table du buffet sont renouvelés.",
    "Aucun colis en souffrance à la réception.",
    "Le code parking invité du jour est noté au poste.",
    "Les chambres non-fumeurs demandées sont bien affectées.",
    "Le thé du lobby est prêt pour l'accueil de 16 h.",
    "La répétition micro de l'atelier 2 est prévue à 8 h 30, avant les clients.",
    "Les effectifs du soir collent au prévisionnel, pas de renfort à appeler.",
    "Le dessert du jour est la tarte citron, c'est dit en brief.",
    "Les rideaux des chambres côté rue sont briefés pour le calme.",
    "Un early breakfast est prévu pour un départ avion, la cuisine est au courant.",
    "Les transats cassés d'hier sont retirés, la piscine est présentable.",
    "La signalétique des ascenseurs est complète ce matin.",
    "Les badges staff oubliés ont été rendus au breakroom.",
    "Le fond de caisse du restaurant est préparé pour le service.",
    "Les chambres PM sont les seules encore en recouche, le reste est libre.",
    "Un bouquet est en chambre 240 pour une demande, la réception le sait.",
    "Le wifi du back-office est stable depuis le redémarrage d'hier.",
    "Les minutes du brief d'hier sont affichées au breakroom.",
    "Aucune alarme technique cette nuit, la ronde l'a noté.",
    "Les arrivées du jour ne changent pas le rythme, la réception est calée.",
)

BANKS: dict[str, tuple[Situation, ...]] = {
    subject: tuple(_s(*row) for row in rows) for subject, rows in ROWS.items()
}
