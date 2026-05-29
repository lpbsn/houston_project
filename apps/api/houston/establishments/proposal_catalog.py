from __future__ import annotations

from houston.establishments.catalog import expand_module_keys, load_arborescence_rows
from houston.establishments.models import OnboardingCatalogDomain, OnboardingCatalogSubject


def build_expanded_proposal_sections(*, module_keys: list[str]) -> dict[str, list[dict]]:
    expanded = expand_module_keys(module_keys)
    modules = []
    seen_modules: set[str] = set()
    for row in load_arborescence_rows():
        if row.module_key not in module_keys or row.module_key in seen_modules:
            continue
        seen_modules.add(row.module_key)
        modules.append(
            {
                "key": row.module_key,
                "label": row.module_label,
                "reason": "Selected from activity description.",
                "confidence_score": None,
            }
        )

    domains = []
    for item in expanded["operational_domains"]:
        domains.append(
            {
                "key": item["key"],
                "label": item["label"],
                "module_key": item["module_key"],
                "reason": "Expanded from catalog for selected module.",
                "confidence_score": None,
            }
        )

    subjects = []
    for item in expanded["operational_subjects"]:
        subjects.append(
            {
                "key": item["key"],
                "label": item["label"],
                "domain_key": item["domain_key"],
                "module_key": item["module_key"],
                "reason": "Expanded from catalog for selected module.",
                "confidence_score": None,
            }
        )

    return {
        "operational_modules": modules,
        "operational_domains": domains,
        "operational_subjects": subjects,
    }


def merge_expanded_proposal(*, base_payload: dict, module_keys: list[str]) -> dict:
    expanded_sections = build_expanded_proposal_sections(module_keys=module_keys)
    merged = dict(base_payload)
    for section, items in expanded_sections.items():
        merged[section] = items
    return enforce_proposal_parent_child_coherence(merged)


def enforce_proposal_parent_child_coherence(payload: dict) -> dict:
    modules = {item["key"]: item for item in payload.get("operational_modules", []) if item.get("key")}
    domains_raw = payload.get("operational_domains", [])
    subjects_raw = payload.get("operational_subjects", [])

    domain_by_key: dict[str, dict] = {}
    for item in domains_raw:
        key = item.get("key")
        module_key = item.get("module_key") or _module_key_from_domain_key(key)
        if not key or module_key not in modules:
            continue
        domain_by_key[key] = {**item, "module_key": module_key}

    subject_by_key: dict[str, dict] = {}
    for item in subjects_raw:
        key = item.get("key")
        domain_key = item.get("domain_key") or _domain_key_from_subject_key(key)
        if not key or domain_key not in domain_by_key:
            continue
        module_key = domain_by_key[domain_key]["module_key"]
        subject_by_key[key] = {**item, "domain_key": domain_key, "module_key": module_key}

    for domain_key, domain_item in list(domain_by_key.items()):
        module_key = domain_item["module_key"]
        if module_key not in modules:
            del domain_by_key[domain_key]

    for subject_key, subject_item in list(subject_by_key.items()):
        if subject_item["domain_key"] not in domain_by_key:
            del subject_by_key[subject_key]

    for subject_item in subject_by_key.values():
        domain_by_key.setdefault(
            subject_item["domain_key"],
            _catalog_domain_item(subject_item["domain_key"]),
        )
        modules.setdefault(
            domain_by_key[subject_item["domain_key"]]["module_key"],
            _catalog_module_item(domain_by_key[subject_item["domain_key"]]["module_key"]),
        )

    for domain_item in domain_by_key.values():
        modules.setdefault(domain_item["module_key"], _catalog_module_item(domain_item["module_key"]))

    updated = dict(payload)
    updated["operational_modules"] = list(modules.values())
    updated["operational_domains"] = list(domain_by_key.values())
    updated["operational_subjects"] = list(subject_by_key.values())
    return updated


def apply_proposal_item_removal(*, payload: dict, section: str, key: str) -> dict:
    updated = dict(payload)
    if section == "operational_modules":
        updated["operational_modules"] = [
            item for item in updated.get("operational_modules", []) if item.get("key") != key
        ]
        updated["operational_domains"] = [
            item
            for item in updated.get("operational_domains", [])
            if item.get("module_key") != key and not item.get("key", "").startswith(f"{key}__")
        ]
        updated["operational_subjects"] = [
            item
            for item in updated.get("operational_subjects", [])
            if item.get("module_key") != key and not item.get("key", "").startswith(f"{key}__")
        ]
    elif section == "operational_domains":
        updated["operational_domains"] = [
            item for item in updated.get("operational_domains", []) if item.get("key") != key
        ]
        updated["operational_subjects"] = [
            item for item in updated.get("operational_subjects", []) if item.get("domain_key") != key
        ]
    elif section == "operational_subjects":
        updated["operational_subjects"] = [
            item for item in updated.get("operational_subjects", []) if item.get("key") != key
        ]
    else:
        raise ValueError(f"Unsupported proposal section for removal: {section}")
    return enforce_proposal_parent_child_coherence(updated)


def apply_proposal_item_addition(*, payload: dict, section: str, key: str) -> dict:
    updated = dict(payload)
    if section == "operational_modules":
        updated.setdefault("operational_modules", []).append(_catalog_module_item(key))
        expanded = build_expanded_proposal_sections(module_keys=[key])
        _merge_unique(updated, "operational_domains", expanded["operational_domains"])
        _merge_unique(updated, "operational_subjects", expanded["operational_subjects"])
    elif section == "operational_domains":
        updated.setdefault("operational_domains", []).append(_catalog_domain_item(key))
        module_key = _module_key_from_domain_key(key)
        updated.setdefault("operational_modules", []).append(_catalog_module_item(module_key))
        subjects = [
            _catalog_subject_item(row.subject_key)
            for row in load_arborescence_rows()
            if row.domain_key == key
        ]
        _merge_unique(updated, "operational_subjects", subjects)
    elif section == "operational_subjects":
        updated.setdefault("operational_subjects", []).append(_catalog_subject_item(key))
        domain_key = _domain_key_from_subject_key(key)
        module_key = _module_key_from_domain_key(domain_key)
        updated.setdefault("operational_domains", []).append(_catalog_domain_item(domain_key))
        updated.setdefault("operational_modules", []).append(_catalog_module_item(module_key))
    else:
        raise ValueError(f"Unsupported proposal section for addition: {section}")
    return enforce_proposal_parent_child_coherence(updated)


def _merge_unique(payload: dict, section: str, items: list[dict]) -> None:
    existing = {item["key"] for item in payload.get(section, []) if item.get("key")}
    payload.setdefault(section, [])
    for item in items:
        if item["key"] in existing:
            continue
        payload[section].append(item)
        existing.add(item["key"])


def _module_key_from_domain_key(domain_key: str) -> str:
    return domain_key.split("__", 1)[0]


def _domain_key_from_subject_key(subject_key: str) -> str:
    parts = subject_key.split("__")
    if len(parts) < 3:
        return subject_key
    return "__".join(parts[:2])


def _catalog_module_item(key: str) -> dict:
    for row in load_arborescence_rows():
        if row.module_key == key:
            return {
                "key": row.module_key,
                "label": row.module_label,
                "reason": "Added from catalog.",
                "confidence_score": None,
            }
    raise KeyError(key)


def _catalog_domain_item(key: str) -> dict:
    row = next((item for item in load_arborescence_rows() if item.domain_key == key), None)
    if row is None:
        catalog = OnboardingCatalogDomain.objects.select_related("catalog_module").filter(key=key).first()
        if catalog is None:
            raise KeyError(key)
        return {
            "key": catalog.key,
            "label": catalog.label,
            "module_key": catalog.catalog_module.key,
            "reason": "Added from catalog.",
            "confidence_score": None,
        }
    return {
        "key": row.domain_key,
        "label": row.domain_label,
        "module_key": row.module_key,
        "reason": "Added from catalog.",
        "confidence_score": None,
    }


def _catalog_subject_item(key: str) -> dict:
    row = next((item for item in load_arborescence_rows() if item.subject_key == key), None)
    if row is None:
        catalog = OnboardingCatalogSubject.objects.select_related(
            "catalog_domain",
            "catalog_domain__catalog_module",
        ).filter(key=key).first()
        if catalog is None:
            raise KeyError(key)
        return {
            "key": catalog.key,
            "label": catalog.label,
            "domain_key": catalog.catalog_domain.key,
            "module_key": catalog.catalog_domain.catalog_module.key,
            "reason": "Added from catalog.",
            "confidence_score": None,
        }
    return {
        "key": row.subject_key,
        "label": row.subject_label,
        "domain_key": row.domain_key,
        "module_key": row.module_key,
        "reason": "Added from catalog.",
        "confidence_score": None,
    }
