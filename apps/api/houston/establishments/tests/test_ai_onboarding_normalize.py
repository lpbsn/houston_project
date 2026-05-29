from __future__ import annotations

from houston.establishments.ai_onboarding import _normalize_provider_payload
from houston.establishments.tests.conftest import (
    HOTEL_HEBERGEMENT_DOMAIN_KEY,
    HOTEL_MODULE_KEY,
    valid_ai_modules_payload,
)


def test_normalize_strips_extra_module_fields():
    raw = valid_ai_modules_payload()
    raw["operational_modules"][0]["mapped_domain_key"] = None
    raw["operational_modules"][0]["suggested_domain_keys"] = [HOTEL_HEBERGEMENT_DOMAIN_KEY]
    raw["operational_domains"] = [{"key": HOTEL_HEBERGEMENT_DOMAIN_KEY}]
    raw["runtime_vocabulary"] = ["guest_check_in", {"term": "VRV", "meaning": "HVAC"}]

    normalized = _normalize_provider_payload(raw)

    assert "mapped_domain_key" not in normalized["operational_modules"][0]
    assert "operational_domains" not in normalized
    assert len(normalized["operational_modules"]) == 1
    assert normalized["operational_modules"][0]["key"] == HOTEL_MODULE_KEY


def test_normalize_strips_unknown_module_fields():
    raw = valid_ai_modules_payload()
    raw["operational_modules"][0]["related_domain_keys"] = ["housekeeping"]
    raw["operational_modules"][0]["extra_field"] = "drop-me"

    normalized = _normalize_provider_payload(raw)

    assert "related_domain_keys" not in normalized["operational_modules"][0]
    assert "extra_field" not in normalized["operational_modules"][0]
    assert normalized["operational_modules"][0]["key"] == HOTEL_MODULE_KEY
