from __future__ import annotations

from houston.establishments.models import (
    OnboardingCatalogDomain,
    OnboardingCatalogModule,
    OnboardingCatalogSubject,
)


def expand_module_keys(module_keys: list[str]) -> dict[str, list[dict[str, str]]]:
    """Return domains and subjects for selected OnboardingCatalog module keys."""
    module_set = set(module_keys)
    domains: dict[str, dict[str, str]] = {}
    subjects: list[dict[str, str]] = []

    domain_qs = (
        OnboardingCatalogDomain.objects.select_related("catalog_module")
        .filter(active=True, catalog_module__key__in=module_set, catalog_module__active=True)
        .order_by("sort_order", "key")
    )
    for domain in domain_qs:
        module_key = domain.catalog_module.key
        domains.setdefault(
            domain.key,
            {
                "key": domain.key,
                "label": domain.label,
                "module_key": module_key,
            },
        )

    subject_qs = (
        OnboardingCatalogSubject.objects.select_related(
            "catalog_domain",
            "catalog_domain__catalog_module",
        )
        .filter(
            active=True,
            catalog_domain__active=True,
            catalog_domain__catalog_module__key__in=module_set,
            catalog_domain__catalog_module__active=True,
        )
        .order_by("sort_order", "key")
    )
    for subject in subject_qs:
        domain = subject.catalog_domain
        module_key = domain.catalog_module.key
        domains.setdefault(
            domain.key,
            {
                "key": domain.key,
                "label": domain.label,
                "module_key": module_key,
            },
        )
        subjects.append(
            {
                "key": subject.key,
                "label": subject.label,
                "domain_key": domain.key,
                "module_key": module_key,
            }
        )

    return {
        "operational_domains": list(domains.values()),
        "operational_subjects": subjects,
    }


def get_onboarding_catalog_module_item(key: str) -> dict:
    module = OnboardingCatalogModule.objects.filter(active=True, key=key).first()
    if module is None:
        raise KeyError(key)
    return {
        "key": module.key,
        "label": module.label,
        "reason": "Added from catalog.",
        "confidence_score": None,
    }


def get_onboarding_catalog_domain_item(key: str) -> dict:
    domain = (
        OnboardingCatalogDomain.objects.select_related("catalog_module")
        .filter(active=True, key=key, catalog_module__active=True)
        .first()
    )
    if domain is None:
        raise KeyError(key)
    return {
        "key": domain.key,
        "label": domain.label,
        "module_key": domain.catalog_module.key,
        "reason": "Added from catalog.",
        "confidence_score": None,
    }


def get_onboarding_catalog_subject_item(key: str) -> dict:
    subject = (
        OnboardingCatalogSubject.objects.select_related(
            "catalog_domain",
            "catalog_domain__catalog_module",
        )
        .filter(
            active=True,
            key=key,
            catalog_domain__active=True,
            catalog_domain__catalog_module__active=True,
        )
        .first()
    )
    if subject is None:
        raise KeyError(key)
    return {
        "key": subject.key,
        "label": subject.label,
        "domain_key": subject.catalog_domain.key,
        "module_key": subject.catalog_domain.catalog_module.key,
        "reason": "Added from catalog.",
        "confidence_score": None,
    }


def list_onboarding_catalog_subject_items_for_domain(*, domain_key: str) -> list[dict]:
    subjects = (
        OnboardingCatalogSubject.objects.select_related(
            "catalog_domain",
            "catalog_domain__catalog_module",
        )
        .filter(
            active=True,
            catalog_domain__key=domain_key,
            catalog_domain__active=True,
            catalog_domain__catalog_module__active=True,
        )
        .order_by("sort_order", "key")
    )
    return [get_onboarding_catalog_subject_item(subject.key) for subject in subjects]


def list_onboarding_catalog_module_items(*, module_keys: list[str]) -> list[dict]:
    modules = (
        OnboardingCatalogModule.objects.filter(active=True, key__in=module_keys)
        .order_by("sort_order", "key")
    )
    return [
        {
            "key": module.key,
            "label": module.label,
            "reason": "Selected from activity description.",
            "confidence_score": None,
        }
        for module in modules
    ]
