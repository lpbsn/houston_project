from __future__ import annotations

import re
import unicodedata

LABEL_FIXES = {
    "Acceuil site": "Accueil site",
    "Communication/ commercialisation": "Communication / commercialisation",
    "Evenements": "Événements",
}


def slugify_label(text: str) -> str:
    text = text.strip()
    text = LABEL_FIXES.get(text, text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower())
    return text.strip("_") or "item"


def normalize_activity_subject_name(label: str) -> str:
    """Derive normalized_name for ActivitySubject uniqueness within a BusinessUnit."""
    return slugify_label(label)
