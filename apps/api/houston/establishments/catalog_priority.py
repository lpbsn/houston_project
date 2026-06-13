"""Priority catalogue keys enriched for LLM routing (pipeline IA Lot 2).

Generic scope descriptions only — no observation-specific patches.
"""

from __future__ import annotations

# Transversal and high-traffic dedicated BUs used in ambiguous routing.
PRIORITY_BUSINESS_UNIT_KEYS: frozenset[str] = frozenset(
    {
        "hotel",
        "maintenance",
        "restaurant",
        "petit_dejeuner",
    }
)

# ~30 ActivitySubjects covering stock, propreté, ménage, plomberie/eau, équipements, sécurité.
PRIORITY_ACTIVITY_SUBJECT_KEYS: frozenset[str] = frozenset(
    {
        "hotel__menage",
        "hotel__maintenance",
        "maintenance__plomberie_eau",
        "maintenance__electricite",
        "maintenance__equipements_dexploitation",
        "maintenance__cvc",
        "maintenance__securite_conformite",
        "petit_dejeuner__proprete",
        "restaurant__proprete",
        "commerce__proprete",
        "coworking__proprete",
        "salles_de_reunion__proprete",
        "salle_de_sport__proprete",
        "loisirs__proprete",
        "spa_piscine__proprete",
        "petit_dejeuner__stock",
        "restaurant__stock",
        "commerce__stock",
        "livraison_uber_eats_deliveroo__stocks_dedies_livraison",
        "commerce__securite",
        "salle_de_sport__securite",
        "loisirs__securite",
        "spa_piscine__securite",
        "restaurant__maintenance",
        "petit_dejeuner__maintenance",
        "spa_piscine__maintenance",
    }
)

MIN_PRIORITY_DESCRIPTION_LENGTH = 40
