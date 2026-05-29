from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings

LABEL_FIXES = {
    "Acceuil site": "Accueil site",
    "Communication/ commercialisation": "Communication / commercialisation",
    "Evenements": "Événements",
}

MODULE_SLUGS = {
    "Hôtel": "hotel",
    "Restaurant": "restaurant",
    "Retail / Commerce": "retail_commerce",
    "Coworking / Bureau": "coworking_bureau",
    "Salle de sport": "salle_de_sport",
    "Loisirs": "loisirs",
}


@dataclass(frozen=True)
class CatalogSubjectRow:
    module_label: str
    module_key: str
    domain_label: str
    domain_key: str
    subject_label: str
    subject_key: str


def slugify_label(text: str) -> str:
    text = text.strip()
    text = LABEL_FIXES.get(text, text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower())
    return text.strip("_") or "item"


def arborescence_csv_path() -> Path:
    repo_root = Path(settings.BASE_DIR).parent.parent
    return repo_root / "docs" / "catalogue" / "arborescence.csv"


@lru_cache(maxsize=1)
def load_arborescence_rows() -> tuple[CatalogSubjectRow, ...]:
    path = arborescence_csv_path()
    rows: list[CatalogSubjectRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows.append(
                CatalogSubjectRow(
                    module_label=raw["module_label"],
                    module_key=raw["module_key"],
                    domain_label=raw["domain_label"],
                    domain_key=raw["domain_key"],
                    subject_label=raw["subject_label"],
                    subject_key=raw["subject_key"],
                )
            )
    return tuple(rows)


def catalog_module_rows() -> list[dict[str, str]]:
    seen: dict[str, str] = {}
    for row in load_arborescence_rows():
        seen.setdefault(row.module_key, row.module_label)
    return [{"key": key, "label": label} for key, label in seen.items()]


def catalog_domain_rows() -> list[dict[str, str]]:
    seen: dict[str, dict[str, str]] = {}
    for row in load_arborescence_rows():
        seen.setdefault(
            row.domain_key,
            {
                "key": row.domain_key,
                "label": row.domain_label,
                "module_key": row.module_key,
            },
        )
    return list(seen.values())


def catalog_subject_rows() -> list[dict[str, str]]:
    return [
        {
            "key": row.subject_key,
            "label": row.subject_label,
            "domain_key": row.domain_key,
        }
        for row in load_arborescence_rows()
    ]


def expand_module_keys(module_keys: list[str]) -> dict[str, list[dict[str, str]]]:
    """Return domains and subjects for selected catalog module keys."""
    module_set = set(module_keys)
    domains: dict[str, dict[str, str]] = {}
    subjects: list[dict[str, str]] = []
    for row in load_arborescence_rows():
        if row.module_key not in module_set:
            continue
        domains.setdefault(
            row.domain_key,
            {
                "key": row.domain_key,
                "label": row.domain_label,
                "module_key": row.module_key,
            },
        )
        subjects.append(
            {
                "key": row.subject_key,
                "label": row.subject_label,
                "domain_key": row.domain_key,
                "module_key": row.module_key,
            }
        )
    return {
        "operational_domains": list(domains.values()),
        "operational_subjects": subjects,
    }
