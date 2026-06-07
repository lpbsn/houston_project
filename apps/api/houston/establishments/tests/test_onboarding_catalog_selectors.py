from __future__ import annotations

import pytest

from houston.establishments.models import (
    OnboardingCatalogDomain,
    OnboardingCatalogModule,
    OnboardingCatalogSubject,
)
from houston.establishments.onboarding_catalog_selectors import expand_module_keys

pytestmark = pytest.mark.django_db


def test_onboarding_catalog_seed_counts():
    assert OnboardingCatalogModule.objects.filter(active=True).count() == 6
    assert OnboardingCatalogDomain.objects.filter(active=True).count() == 31
    assert OnboardingCatalogSubject.objects.filter(active=True).count() == 154


def test_expand_module_keys_for_hotel():
    expanded = expand_module_keys(["hotel"])

    assert len(expanded["operational_domains"]) == 6
    assert len(expanded["operational_subjects"]) == 29
    assert all(item["module_key"] == "hotel" for item in expanded["operational_domains"])
    assert all(item["module_key"] == "hotel" for item in expanded["operational_subjects"])
    assert all(
        item["domain_key"].startswith("hotel__") for item in expanded["operational_subjects"]
    )
