from __future__ import annotations

import unicodedata


def normalize_pattern_label(label: str) -> str:
    normalized = unicodedata.normalize("NFKC", label or "")
    return " ".join(normalized.casefold().split())
