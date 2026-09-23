from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from houston.establishments.mama_nice_dataset_constants import SCHEMA_VERSION
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError

DATA_DIR = Path(__file__).resolve().parent / "data" / "mama_nice"

MANIFEST_FILES = (
    "catalog_lock.json",
    "operational_units.json",
    "schedules.json",
    "public_events.json",
    "oneshots.json",
    "patterns.json",
    "reusable_plans.json",
    "golden_paths.json",
)


def _load_json(name: str) -> dict[str, Any]:
    path = DATA_DIR / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise MamaNiceDatasetError(
            [f"{name}: schema_version must be {SCHEMA_VERSION}"]
        )
    return payload


@lru_cache(maxsize=1)
def load_mama_nice_manifest() -> dict[str, Any]:
    return {name.removesuffix(".json"): _load_json(name) for name in MANIFEST_FILES}
