"""Unique family and Pattern justifications. No generic suffixes."""

from __future__ import annotations

from datetime import datetime

from houston.establishments.mama_nice_dataset_constants import PARIS_TZ

_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)

CI_PROCESSES: dict[str, tuple[str, ...]] = {
    "clim": (
        "le filtre n'est jamais changé au départ",
        "la consigne CVC n'est pas dans le briefing ménage",
        "le thermostat est remis à fond sans contrôle après le client",
        "personne ne note la température à la remise de clé",
        "le prestataire CVC n'est relancé qu'après trois chambres",
        "le filtre de palier est partagé sans suivi d'étage",
        "la purge est oubliée entre deux séjours d'été",
        "le relevé de 18 h n'est jamais comparé à l'arrivée",
    ),
    "buffet": (
        "le réassort n'est pas calé avant 7 h 30",
        "l'économat n'ouvre le stock qu'après la première rupture",
        "la substitution n'est pas prévue dans le brief",
        "le comptage de la veille n'est pas transmis à la cuisine",
        "le chariot de secours reste en plonge",
        "la commande fournisseur part trop tard le mercredi",
    ),
    "linge": (
        "l'écart blanchisserie n'est pas confronté le jour même",
        "le réassort d'étage n'a pas de seuil d'alerte",
        "les sacs d'enlèvement partent sans bordereau",
        "le reliquat du 2e n'est pas redistribué avant 16 h",
    ),
    "chambre_prete": (
        "le check ménage n'est pas croisé avec l'heure d'arrivée",
        "la chambre prioritaire n'est pas marquée au chariot",
        "la passation 14 h ne liste plus les départs tardifs",
        "le late check-out n'est pas poussé au planning ménage",
    ),
    "attente_resto": (
        "la mise en place des tables de huit n'est pas anticipée",
        "le runner n'est pas appelé avant que la file atteigne le lobby",
        "l'ouverture de la deuxième rangée dépend d'un seul manager",
        "le brief 19 h n'inclut pas la jauge réelle",
    ),
    "audiovisuel": (
        "le test HDMI n'est pas fait la veille du brief",
        "le ClickShare n'a pas de fiche de statut en salle",
        "le câble de rechange reste au local technique",
        "personne ne consigne le dernier redémarrage",
    ),
    "avis": (
        "les thèmes d'attente ne sont pas remontés au restaurant",
        "la réponse publique part sans vérifier le service cité",
        "le fil e-réputation n'est pas croisé avec les files du pdj",
    ),
    "fuite": (
        "le siphon n'est contrôlé qu'après la deuxième flaque",
        "le joint de lavabo n'est pas dans la ronde hebdo",
    ),
    "eclairage": (
        "les circulations ne sont pas relevées après 22 h",
        "le stock d'ampoules n'est pas tenu par palier",
    ),
    "borne": (
        "le badge rouge n'est pas tracé avant l'arrivée client",
        "le redémarrage n'est pas consigné pour le prestataire",
    ),
    "effectif": (
        "les Super Sunday ne sont pas figés avant le jeudi",
        "les extras voient le trou trop tard au breakroom",
    ),
    "signaletique": (
        "les fichiers de fléchage ne sont pas validés avant impression",
        "le parcours Atelier n'est pas relu par Communication",
    ),
    "default": (
        "le geste de clôture n'est pas tenu dans le brief",
        "la cause n'est pas écrite avant de relancer le prestataire",
        "le même écart revient faute de consigne d'étage",
        "personne n'a calé le contrôle après l'opération",
    ),
}

CI_FRAMES = (
    (
        "Depuis {month}, {obj} à {place} revient : {process}. "
        "C'est une faiblesse de processus à améliorer."
    ),
    "{obj} au {place} : cause commune, {process}. La récurrence date de {month}.",
    "À chaque arrivée depuis {month}, {obj} au {place} retombe sur {process}.",
    "On cherche à améliorer le processus : {process}. Vu au {place} depuis {month} sur {obj}.",
    "Récurrence depuis {month} au {place} : {obj} à cause de {process}.",
)

FAMILY_FRAMES: dict[str, tuple[str, ...]] = {
    "prevention": (
        "Contrôle fait au {place} avant le service, {obj} était déjà signalé.",
        "Ronde de {month} au {place} : {obj} relevé avant qu'un client le voie.",
        "Check-list du matin au {place}, {obj} noté pour passage préventif.",
    ),
    "process_inefficiency": (
        "Au {place}, {obj} bloque encore la passation de {month}.",
        "Le geste prévu pour {obj} n'a pas été tenu au {place}.",
        "{obj} au {place} : le seuil d'alerte n'a pas déclenché le réassort.",
    ),
    "cross_pole_coordination": (
        "Le pôle auteur et le responsable ne sont pas alignés sur {obj} au {place}.",
        "{obj} au {place} demande encore un arbitrage entre les deux pôles.",
        "Chacun a une partie de {obj} au {place}, personne n'a clôturé.",
    ),
    "service_quality": (
        "L'écart sur {obj} se voit encore au service du {place}.",
        "Prestation {obj} au {place} : le standard du brief n'est pas tenu.",
        "Au {place}, {obj} allonge le service plus que la jauge prévue.",
    ),
    "guest_experience": (
        "Le client le vit au {place} autour de {obj}.",
        "Séjour impacté au {place} : {obj} reste le point d'irritation.",
        "À l'accueil on entend encore {obj} pour le {place}.",
    ),
    "operational_incident": (
        "Écart ponctuel sur {obj} au {place}, traité pour cette occurrence.",
        "{obj} au {place} : une occurrence isolée, pas une série ouverte.",
        "Intervention unique sur {obj} au {place} ce {month}.",
    ),
}

PATTERN_REWRITES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "clim": (
        (
            "La clim de la 207 ne descend plus sous 24 °C",
            "la climatisation",
            "en 207 l'air reste à 24 °C près de la fenêtre",
        ),
        (
            "La clim de la 119 souffle fort et ne refroidit pas",
            "la climatisation",
            "en 119 le flux est fort, l'air reste tiède",
        ),
        (
            "Le thermostat de la 331 reste bloqué sur chaud",
            "le thermostat",
            "en 331 le bouton tourne dans le vide",
        ),
        (
            "La clim de la 415 s'arrête dès que la porte se ferme",
            "la climatisation",
            "en 415 l'unité coupe en porte close",
        ),
        (
            "La clim de la 508 fait du givre sur la façade",
            "la climatisation",
            "en 508 le bac déborde sur le parquet",
        ),
        (
            "La clim de la 222 n'a plus de télécommande qui réponde",
            "la climatisation",
            "en 222 aucune commande ne change le souffle",
        ),
        (
            "La clim de la 104 reste en mode chauffage en septembre",
            "la climatisation",
            "en 104 l'air sort brûlant à 11 h",
        ),
        (
            "La clim de la 617 vibre et coupe toutes les vingt minutes",
            "la climatisation",
            "en 617 le cycle s'interrompt sans consigne",
        ),
    ),
    "buffet": (
        (
            "Les yaourts nature manquent au buffet dès 7 h 40",
            "les yaourts",
            "au buffet le bac nature est vide avant 8 h",
        ),
        (
            "Le pain complet n'est plus sur le buffet après 8 h 10",
            "le pain complet",
            "au buffet il reste seulement le blanc",
        ),
        (
            "Les fruits coupés du buffet brunissent avant 9 h",
            "les fruits coupés",
            "au buffet le bac fruits n'a pas été renouvelé",
        ),
        (
            "Le lait d'avoine du buffet est en rupture le jeudi",
            "le lait d'avoine",
            "au buffet plus de brique côté boissons",
        ),
        (
            "Les œufs brouillés manquent au buffet dès le premier service",
            "les œufs",
            "au buffet le bac œufs est froid et vide",
        ),
        (
            "Le granola du buffet n'a plus de bac propre à 8 h",
            "le granola",
            "au buffet le bac est taché et presque vide",
        ),
    ),
    "linge": (
        (
            "Il manque 18 taies après le passage blanchisserie",
            "les taies",
            "au local linge le bac taies est à sec",
        ),
        (
            "Les peignoirs du 4e ne sont pas redescendus",
            "les peignoirs",
            "au 4e plus de peignoir dans le chariot",
        ),
        (
            "Les draps king du 5e arrivent avec un jour de retard",
            "les draps king",
            "au 5e le reliquat king n'est pas là",
        ),
        (
            "Les serviettes piscine ne sont pas distinguées du stock chambres",
            "les serviettes piscine",
            "au local linge tout est mélangé",
        ),
    ),
    "attente_resto": (
        (
            "La file du samedi soir bloque encore l'entrée côté bar",
            "la file",
            "à l'entrée restaurant la file touche le bar",
        ),
        (
            "L'attente à la table 4 dépasse vingt minutes sans eau",
            "l'attente table 4",
            "en salle table 4 n'a toujours pas d'eau",
        ),
        (
            "La file du déjeuner déborde vers le lobby à 12 h 40",
            "la file du déjeuner",
            "au lobby les clients du restaurant attendent",
        ),
        (
            "Deux tables de six attendent encore un runner à 21 h",
            "l'attente runner",
            "en salle plus de runner visible",
        ),
    ),
    "audiovisuel": (
        (
            "Le ClickShare du Studio 1 n'a plus de dongle",
            "le ClickShare",
            "en Studio 1 le dongle n'est pas dans le tiroir",
        ),
        (
            "L'écran de l'Atelier 2 reste en HDMI 2 vide",
            "l'écran",
            "en Atelier 2 HDMI 2 n'a pas de source",
        ),
        (
            "La sono de l'Atelier 1 sature dès le micro main",
            "la sono",
            "en Atelier 1 le micro larsen dès le brief",
        ),
        (
            "Le réseau invité de l'Atelier 2 coupe le Share",
            "le réseau",
            "en Atelier 2 le Share perd le wifi salle",
        ),
        (
            "Le projecteur du Studio 2 affiche une dalle rose",
            "le projecteur",
            "en Studio 2 l'image reste rose",
        ),
        (
            "Le boîtier ClickShare de l'Atelier 1 clignote orange fixe",
            "le ClickShare",
            "en Atelier 1 orange fixe depuis le test",
        ),
    ),
    "signaletique": (
        (
            "La flèche Atelier 1 envoie encore vers le Studio 2",
            "la signalétique",
            "au palier Atelier 1 le pictogramme pointe Studio 2",
        ),
        (
            "Le chevalet Super Sunday manque le nom de salle",
            "la signalétique",
            "à l'entrée Studio 1 le chevalet n'a plus de nom",
        ),
        (
            "Le fléchage Bringue de l'Atelier 2 s'arrête au vestiaire",
            "la signalétique",
            "en Atelier 2 plus de flèche après le vestiaire",
        ),
        (
            "La plaque Studio 2 est encore celle du brief de mai",
            "la signalétique",
            "sur la porte Studio 2 le titre de mai est resté",
        ),
        (
            "Le panneau lobby oriente La Bringue vers l'Atelier 1",
            "la signalétique",
            "au lobby la flèche Bringue pointe Atelier 1",
        ),
        (
            "Le totem DJ de l'Atelier 1 n'a plus l'horaire du 26",
            "la signalétique",
            "en Atelier 1 le totem affiche encore 22 h",
        ),
        (
            "Les pictogrammes sanitaires de l'Atelier 2 sont inversés",
            "la signalétique",
            "en Atelier 2 hommes et femmes sont permutés",
        ),
        (
            "Le plan de salle Horizon Azur n'est pas affiché à l'Atelier 1",
            "la signalétique",
            "à l'Atelier 1 le plan 80 places manque",
        ),
    ),
}


def month_label(instant: datetime) -> str:
    local = instant.astimezone(PARIS_TZ)
    return _MONTHS[local.month - 1]


def _place(unit: str) -> str:
    return unit.replace("_", " ")


def justify_family(
    *,
    family: str,
    focus: str,
    unit: str,
    canonical: str,
    occurred_at: datetime,
    topic: str | None,
    index: int,
) -> str:
    place = _place(unit)
    month = month_label(occurred_at)
    obj = canonical or "l'écart"
    if family == "continuous_improvement":
        processes = CI_PROCESSES.get(topic or "", ()) + CI_PROCESSES["default"]
        process = processes[index % len(processes)]
        frame = CI_FRAMES[index % len(CI_FRAMES)]
        return frame.format(month=month, obj=obj, place=place, process=process)
    frames = FAMILY_FRAMES.get(family)
    if not frames:
        return ""
    return frames[index % len(frames)].format(month=month, obj=obj, place=place, process=focus)
    # process unused in family frames except CI; keep signature stable.


def rewrite_for_topic(*, topic: str, index: int) -> tuple[str, str, str] | None:
    rows = PATTERN_REWRITES.get(topic)
    if not rows:
        return None
    return rows[index % len(rows)]


def unique_cancel_reason(focus: str, generic: str) -> str:
    return f"{generic} Sujet : {focus}."
