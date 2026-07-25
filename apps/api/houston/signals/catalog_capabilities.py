"""Versioned catalog activity-subject capabilities for the observation pipeline."""

from __future__ import annotations

CATALOG_CAPABILITIES_VERSION = "catalog_capabilities_v1"

# Minimal seed for Lot 3 — keys match CatalogActivitySubject.key values.
_CATALOG_CAPABILITIES: dict[str, list[str]] = {
    "hotel__menage": ["cleaning", "spill_cleanup", "temporary_securing"],
    "maintenance__plomberie_eau": ["leak_response", "plumbing_repair"],
    "maintenance__equipements_dexploitation": ["equipment_repair", "equipment_inspect"],
}


def capabilities_for_catalog_key(catalog_key: str | None) -> list[str]:
    """Return versioned capabilities for a catalog subject key; unknown → []."""
    if not catalog_key:
        return []
    capabilities = _CATALOG_CAPABILITIES.get(catalog_key)
    if capabilities is None:
        return []
    return list(capabilities)
