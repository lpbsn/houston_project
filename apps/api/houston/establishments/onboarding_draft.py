from __future__ import annotations

import uuid
from typing import Any

from houston.accounts.models import User
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MAX_LENGTH,
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    CatalogActivitySubject,
    CatalogBusinessUnit,
    EstablishmentMembership,
)
from houston.establishments.taxonomy_normalization import slugify_label

DRAFT_VALIDATION_MODE_SOFT = "soft"
DRAFT_VALIDATION_MODE_FINAL = "final"

DRAFT_STEP_STRUCTURE = "structure"
DRAFT_STEP_TEAM = "team"
DRAFT_STEPS = frozenset({DRAFT_STEP_STRUCTURE, DRAFT_STEP_TEAM})

DRAFT_TOP_LEVEL_KEYS = frozenset(
    {
        "current_step",
        "establishment",
        "business_units",
        "activity_subjects",
        "team",
    }
)
DRAFT_ESTABLISHMENT_KEYS = frozenset({"name", "description"})
DRAFT_BUSINESS_UNIT_KEYS = frozenset(
    {
        "client_key",
        "catalog_key",
        "specific_name",
        "instance_description",
    }
)
DRAFT_ACTIVITY_SUBJECT_KEYS = frozenset(
    {
        "client_key",
        "business_unit_client_key",
        "catalog_key",
        "label",
        "description",
    }
)
DRAFT_TEAM_KEYS = frozenset({"director", "members"})
DRAFT_PERSON_KEYS = frozenset({"email", "first_name", "last_name"})
DRAFT_MEMBER_KEYS = frozenset(
    {"email", "first_name", "last_name", "role", "business_unit_client_keys"}
)
DRAFT_MEMBER_ROLES = frozenset(
    {
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    }
)


class OnboardingDraftValidationError(Exception):
    def __init__(self, errors: list[dict]):
        super().__init__("Onboarding draft payload is invalid.")
        self.errors = errors


def empty_onboarding_draft_payload() -> dict:
    return {
        "current_step": DRAFT_STEP_STRUCTURE,
        "establishment": {"name": "", "description": ""},
        "business_units": [],
        "activity_subjects": [],
        "team": {"director": None, "members": []},
    }


def draft_error(
    code: str,
    *,
    section: str | None = None,
    field: str | None = None,
    key: str | None = None,
) -> dict:
    error: dict[str, str] = {"code": code}
    if section is not None:
        error["section"] = section
    if field is not None:
        error["field"] = field
    if key is not None:
        error["key"] = key
    return error


def validate_onboarding_draft_payload(
    payload: Any,
    *,
    mode: str = DRAFT_VALIDATION_MODE_SOFT,
) -> tuple[dict, list[dict]]:
    """Validate draft payload.

    Returns ``(normalized_payload, soft_errors)``.

    Shape/type errors always raise ``OnboardingDraftValidationError`` (do not
    persist). Business-rule soft errors are returned for soft mode; final mode
    raises when any soft/final errors remain.
    """
    if mode not in {DRAFT_VALIDATION_MODE_SOFT, DRAFT_VALIDATION_MODE_FINAL}:
        raise OnboardingDraftValidationError([draft_error("invalid_validation_mode")])

    if not isinstance(payload, dict):
        raise OnboardingDraftValidationError([draft_error("invalid_payload_type")])

    shape_errors: list[dict] = []
    for key in payload:
        if key not in DRAFT_TOP_LEVEL_KEYS:
            shape_errors.append(draft_error("unknown_section", section=key))
    for key in DRAFT_TOP_LEVEL_KEYS:
        if key not in payload:
            shape_errors.append(draft_error("missing_required_section", section=key))
    if shape_errors:
        raise OnboardingDraftValidationError(shape_errors)

    errors: list[dict] = []
    current_step = payload.get("current_step")
    if current_step not in DRAFT_STEPS:
        raise OnboardingDraftValidationError(
            [
                draft_error(
                    "invalid_current_step",
                    section="current_step",
                    field="current_step",
                )
            ]
        )

    establishment = _normalize_establishment_section(
        payload.get("establishment"),
        errors=errors,
        shape_errors=shape_errors,
    )
    business_units, seen_client_keys = _normalize_business_units_section(
        payload.get("business_units"),
        errors=errors,
        shape_errors=shape_errors,
    )
    activity_subjects = _normalize_activity_subjects_section(
        payload.get("activity_subjects"),
        business_unit_client_keys={item["client_key"] for item in business_units},
        seen_client_keys=seen_client_keys,
        errors=errors,
        shape_errors=shape_errors,
    )
    team = _normalize_team_section(
        payload.get("team"),
        business_unit_client_keys={item["client_key"] for item in business_units},
        errors=errors,
        shape_errors=shape_errors,
    )
    if shape_errors:
        raise OnboardingDraftValidationError(shape_errors)

    _apply_catalog_and_final_rules(
        business_units=business_units,
        activity_subjects=activity_subjects,
        team=team,
        establishment=establishment,
        errors=errors,
        mode=mode,
    )

    normalized = {
        "current_step": current_step,
        "establishment": establishment,
        "business_units": business_units,
        "activity_subjects": activity_subjects,
        "team": team,
    }

    if mode == DRAFT_VALIDATION_MODE_FINAL and errors:
        raise OnboardingDraftValidationError(errors)

    return normalized, errors


def _normalize_establishment_section(
    value: Any,
    *,
    errors: list[dict],
    shape_errors: list[dict],
) -> dict:
    if not isinstance(value, dict):
        shape_errors.append(
            draft_error("invalid_section_type", section="establishment")
        )
        return {"name": "", "description": ""}

    for key in value:
        if key not in DRAFT_ESTABLISHMENT_KEYS:
            shape_errors.append(
                draft_error("unknown_field", section="establishment", field=key)
            )

    name = value.get("name", "")
    description = value.get("description", "")
    if not isinstance(name, str):
        shape_errors.append(
            draft_error("invalid_field_type", section="establishment", field="name")
        )
        name = ""
    if not isinstance(description, str):
        shape_errors.append(
            draft_error(
                "invalid_field_type",
                section="establishment",
                field="description",
            )
        )
        description = ""

    name = name.strip()
    description = description.strip()
    if not name:
        errors.append(
            draft_error("missing_establishment_name", section="establishment", field="name")
        )
    if len(description) < ACTIVITY_DESCRIPTION_MIN_LENGTH:
        errors.append(
            draft_error(
                "invalid_activity_description_length",
                section="establishment",
                field="description",
            )
        )
    elif len(description) > ACTIVITY_DESCRIPTION_MAX_LENGTH:
        errors.append(
            draft_error(
                "invalid_activity_description_length",
                section="establishment",
                field="description",
            )
        )

    return {"name": name, "description": description}


def _normalize_business_units_section(
    value: Any,
    *,
    errors: list[dict],
    shape_errors: list[dict],
) -> tuple[list[dict], set[str]]:
    if not isinstance(value, list):
        shape_errors.append(
            draft_error("invalid_section_type", section="business_units")
        )
        return [], set()

    items: list[dict] = []
    seen_client_keys: set[str] = set()
    seen_specific_names: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict):
            shape_errors.append(
                draft_error("invalid_item_type", section="business_units")
            )
            continue
        for key in raw:
            if key not in DRAFT_BUSINESS_UNIT_KEYS:
                shape_errors.append(
                    draft_error("unknown_field", section="business_units", field=key)
                )

        client_key = _parse_client_key(
            raw.get("client_key"),
            section="business_units",
            shape_errors=shape_errors,
        )
        catalog_key = raw.get("catalog_key", "")
        specific_name = raw.get("specific_name", "")
        instance_description = raw.get("instance_description", "")
        if not isinstance(catalog_key, str):
            shape_errors.append(
                draft_error(
                    "invalid_field_type",
                    section="business_units",
                    field="catalog_key",
                    key=client_key or None,
                )
            )
            catalog_key = ""
        if not isinstance(specific_name, str):
            shape_errors.append(
                draft_error(
                    "invalid_field_type",
                    section="business_units",
                    field="specific_name",
                    key=client_key or None,
                )
            )
            specific_name = ""
        if not isinstance(instance_description, str):
            shape_errors.append(
                draft_error(
                    "invalid_field_type",
                    section="business_units",
                    field="instance_description",
                    key=client_key or None,
                )
            )
            instance_description = ""

        catalog_key = catalog_key.strip()
        specific_name = specific_name.strip()
        instance_description = instance_description.strip()

        if client_key:
            if client_key in seen_client_keys:
                errors.append(
                    draft_error(
                        "duplicate_client_key",
                        section="business_units",
                        field="client_key",
                        key=client_key,
                    )
                )
            else:
                seen_client_keys.add(client_key)

        if not catalog_key:
            errors.append(
                draft_error(
                    "missing_catalog_key",
                    section="business_units",
                    field="catalog_key",
                    key=client_key or None,
                )
            )
        if not specific_name:
            errors.append(
                draft_error(
                    "missing_specific_name",
                    section="business_units",
                    field="specific_name",
                    key=client_key or None,
                )
            )
        else:
            normalized_specific_name = slugify_label(specific_name)
            if not normalized_specific_name:
                errors.append(
                    draft_error(
                        "invalid_specific_name",
                        section="business_units",
                        field="specific_name",
                        key=client_key or None,
                    )
                )
            elif normalized_specific_name in seen_specific_names:
                errors.append(
                    draft_error(
                        "duplicate_specific_name",
                        section="business_units",
                        field="specific_name",
                        key=client_key or None,
                    )
                )
            else:
                seen_specific_names.add(normalized_specific_name)

        if client_key:
            items.append(
                {
                    "client_key": client_key,
                    "catalog_key": catalog_key,
                    "specific_name": specific_name,
                    "instance_description": instance_description,
                }
            )

    if not items:
        errors.append(draft_error("insufficient_business_units", section="business_units"))

    return items, seen_client_keys


def _normalize_activity_subjects_section(
    value: Any,
    *,
    business_unit_client_keys: set[str],
    seen_client_keys: set[str],
    errors: list[dict],
    shape_errors: list[dict],
) -> list[dict]:
    if not isinstance(value, list):
        shape_errors.append(
            draft_error("invalid_section_type", section="activity_subjects")
        )
        return []

    items: list[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            shape_errors.append(
                draft_error("invalid_item_type", section="activity_subjects")
            )
            continue
        for key in raw:
            if key not in DRAFT_ACTIVITY_SUBJECT_KEYS:
                shape_errors.append(
                    draft_error("unknown_field", section="activity_subjects", field=key)
                )

        client_key = _parse_client_key(
            raw.get("client_key"),
            section="activity_subjects",
            shape_errors=shape_errors,
        )
        bu_client_key = _parse_client_key(
            raw.get("business_unit_client_key"),
            section="activity_subjects",
            field="business_unit_client_key",
            shape_errors=shape_errors,
        )
        catalog_key = raw.get("catalog_key", None)
        label = raw.get("label", "")
        description = raw.get("description", "")

        if catalog_key is not None and not isinstance(catalog_key, str):
            shape_errors.append(
                draft_error(
                    "invalid_field_type",
                    section="activity_subjects",
                    field="catalog_key",
                    key=client_key or None,
                )
            )
            catalog_key = None
        if catalog_key is not None:
            catalog_key = catalog_key.strip() or None

        if not isinstance(label, str):
            shape_errors.append(
                draft_error(
                    "invalid_field_type",
                    section="activity_subjects",
                    field="label",
                    key=client_key or None,
                )
            )
            label = ""
        if not isinstance(description, str):
            shape_errors.append(
                draft_error(
                    "invalid_field_type",
                    section="activity_subjects",
                    field="description",
                    key=client_key or None,
                )
            )
            description = ""

        label = label.strip()
        description = description.strip()

        has_catalog = catalog_key is not None
        has_label = bool(label)
        if has_catalog == has_label:
            errors.append(
                draft_error(
                    "invalid_subject_identity",
                    section="activity_subjects",
                    key=client_key or None,
                )
            )

        if client_key:
            if client_key in seen_client_keys:
                errors.append(
                    draft_error(
                        "duplicate_client_key",
                        section="activity_subjects",
                        field="client_key",
                        key=client_key,
                    )
                )
            else:
                seen_client_keys.add(client_key)

        if bu_client_key and bu_client_key not in business_unit_client_keys:
            errors.append(
                draft_error(
                    "orphan_activity_subject",
                    section="activity_subjects",
                    field="business_unit_client_key",
                    key=client_key or None,
                )
            )

        if client_key and bu_client_key:
            items.append(
                {
                    "client_key": client_key,
                    "business_unit_client_key": bu_client_key,
                    "catalog_key": catalog_key,
                    "label": label,
                    "description": description,
                }
            )

    return items


def _normalize_team_section(
    value: Any,
    *,
    business_unit_client_keys: set[str],
    errors: list[dict],
    shape_errors: list[dict],
) -> dict:
    if not isinstance(value, dict):
        shape_errors.append(draft_error("invalid_section_type", section="team"))
        return {"director": None, "members": []}

    for key in value:
        if key not in DRAFT_TEAM_KEYS:
            shape_errors.append(draft_error("unknown_field", section="team", field=key))

    director = value.get("director", None)
    members = value.get("members", [])
    normalized_director = None
    if director is not None:
        normalized_director = _normalize_person(
            director,
            section="team",
            field="director",
            errors=errors,
            shape_errors=shape_errors,
            required_identity=False,
        )

    if not isinstance(members, list):
        shape_errors.append(
            draft_error("invalid_field_type", section="team", field="members")
        )
        members = []

    normalized_members: list[dict] = []
    seen_emails: set[str] = set()
    if normalized_director is not None and normalized_director.get("email"):
        seen_emails.add(normalized_director["email"])

    for raw in members:
        member = _normalize_member(
            raw,
            business_unit_client_keys=business_unit_client_keys,
            errors=errors,
            shape_errors=shape_errors,
        )
        if member is None:
            continue
        email = member["email"]
        if email and email in seen_emails:
            errors.append(
                draft_error(
                    "duplicate_team_email",
                    section="team",
                    field="email",
                    key=email,
                )
            )
        elif email:
            seen_emails.add(email)
        normalized_members.append(member)

    if normalized_director is None or not normalized_director.get("email"):
        errors.append(draft_error("missing_director", section="team", field="director"))

    return {"director": normalized_director, "members": normalized_members}


def _normalize_person(
    value: Any,
    *,
    section: str,
    field: str,
    errors: list[dict],
    shape_errors: list[dict],
    required_identity: bool,
) -> dict | None:
    if not isinstance(value, dict):
        shape_errors.append(
            draft_error("invalid_field_type", section=section, field=field)
        )
        return None

    for key in value:
        if key not in DRAFT_PERSON_KEYS:
            shape_errors.append(
                draft_error("unknown_field", section=section, field=key)
            )

    email = value.get("email", "")
    first_name = value.get("first_name", "")
    last_name = value.get("last_name", "")
    if not isinstance(email, str):
        shape_errors.append(
            draft_error("invalid_field_type", section=section, field="email")
        )
        email = ""
    if not isinstance(first_name, str):
        shape_errors.append(
            draft_error("invalid_field_type", section=section, field="first_name")
        )
        first_name = ""
    if not isinstance(last_name, str):
        shape_errors.append(
            draft_error("invalid_field_type", section=section, field="last_name")
        )
        last_name = ""

    email = (User.normalize_email_value(email) or "").strip()
    first_name = first_name.strip()
    last_name = last_name.strip()

    if required_identity or email or first_name or last_name:
        if not email:
            errors.append(
                draft_error("missing_email", section=section, field="email")
            )
        if not first_name:
            errors.append(
                draft_error("missing_first_name", section=section, field="first_name")
            )
        if not last_name:
            errors.append(
                draft_error("missing_last_name", section=section, field="last_name")
            )

    return {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
    }


def _normalize_member(
    value: Any,
    *,
    business_unit_client_keys: set[str],
    errors: list[dict],
    shape_errors: list[dict],
) -> dict | None:
    if not isinstance(value, dict):
        shape_errors.append(
            draft_error("invalid_item_type", section="team", field="members")
        )
        return None

    for key in value:
        if key not in DRAFT_MEMBER_KEYS:
            shape_errors.append(
                draft_error("unknown_field", section="team", field=key)
            )

    person = _normalize_person(
        {
            "email": value.get("email", ""),
            "first_name": value.get("first_name", ""),
            "last_name": value.get("last_name", ""),
        },
        section="team",
        field="members",
        errors=errors,
        shape_errors=shape_errors,
        required_identity=True,
    )
    if person is None:
        return None

    role = value.get("role", "")
    if not isinstance(role, str):
        shape_errors.append(
            draft_error("invalid_field_type", section="team", field="role")
        )
        role = ""
    role = role.strip()
    if role not in DRAFT_MEMBER_ROLES:
        errors.append(draft_error("invalid_member_role", section="team", field="role"))

    raw_keys = value.get("business_unit_client_keys", [])
    if not isinstance(raw_keys, list):
        shape_errors.append(
            draft_error(
                "invalid_field_type",
                section="team",
                field="business_unit_client_keys",
            )
        )
        raw_keys = []

    bu_keys: list[str] = []
    seen: set[str] = set()
    for raw_key in raw_keys:
        parsed = _parse_client_key(
            raw_key,
            section="team",
            field="business_unit_client_keys",
            shape_errors=shape_errors,
        )
        if not parsed:
            continue
        if parsed in seen:
            continue
        seen.add(parsed)
        if parsed not in business_unit_client_keys:
            errors.append(
                draft_error(
                    "unknown_business_unit_client_key",
                    section="team",
                    field="business_unit_client_keys",
                    key=parsed,
                )
            )
        else:
            bu_keys.append(parsed)

    if not bu_keys:
        errors.append(
            draft_error(
                "missing_member_business_units",
                section="team",
                field="business_unit_client_keys",
            )
        )

    return {
        **person,
        "role": role,
        "business_unit_client_keys": bu_keys,
    }


def _parse_client_key(
    value: Any,
    *,
    section: str,
    shape_errors: list[dict],
    field: str = "client_key",
) -> str:
    if not isinstance(value, str) or not value.strip():
        shape_errors.append(
            draft_error("invalid_client_key", section=section, field=field)
        )
        return ""
    try:
        return str(uuid.UUID(value.strip()))
    except (ValueError, TypeError, AttributeError):
        shape_errors.append(
            draft_error("invalid_client_key", section=section, field=field)
        )
        return ""


def _apply_catalog_and_final_rules(
    *,
    business_units: list[dict],
    activity_subjects: list[dict],
    team: dict,
    establishment: dict,
    errors: list[dict],
    mode: str,
) -> None:
    catalog_bu_keys = set(
        CatalogBusinessUnit.objects.filter(active=True).values_list("key", flat=True)
    )
    catalog_unit_types = dict(
        CatalogBusinessUnit.objects.filter(active=True).values_list("key", "unit_type")
    )
    catalog_subject_keys = set(
        CatalogActivitySubject.objects.filter(active=True).values_list("key", flat=True)
    )
    subject_parent_by_key = dict(
        CatalogActivitySubject.objects.filter(active=True).values_list(
            "key",
            "catalog_business_unit__key",
        )
    )

    transversal_seen: set[str] = set()
    for item in business_units:
        catalog_key = item["catalog_key"]
        if catalog_key and catalog_key not in catalog_bu_keys:
            errors.append(
                draft_error(
                    "unknown_catalog_key",
                    section="business_units",
                    field="catalog_key",
                    key=item["client_key"],
                )
            )
            continue
        unit_type = catalog_unit_types.get(catalog_key)
        if unit_type == CatalogBusinessUnit.DefaultUnitType.TRANSVERSAL:
            if catalog_key in transversal_seen:
                errors.append(
                    draft_error(
                        "duplicate_transversal_business_unit",
                        section="business_units",
                        field="catalog_key",
                        key=item["client_key"],
                    )
                )
            transversal_seen.add(catalog_key)

    for subject in activity_subjects:
        catalog_key = subject["catalog_key"]
        if catalog_key is None:
            if mode == DRAFT_VALIDATION_MODE_FINAL and not subject["label"]:
                errors.append(
                    draft_error(
                        "missing_custom_subject_label",
                        section="activity_subjects",
                        field="label",
                        key=subject["client_key"],
                    )
                )
            continue
        if catalog_key not in catalog_subject_keys:
            errors.append(
                draft_error(
                    "unknown_catalog_key",
                    section="activity_subjects",
                    field="catalog_key",
                    key=subject["client_key"],
                )
            )
            continue
        parent_bu = next(
            (
                bu
                for bu in business_units
                if bu["client_key"] == subject["business_unit_client_key"]
            ),
            None,
        )
        if parent_bu is None:
            continue
        if subject_parent_by_key.get(catalog_key) != parent_bu["catalog_key"]:
            errors.append(
                draft_error(
                    "catalog_subject_business_unit_mismatch",
                    section="activity_subjects",
                    field="catalog_key",
                    key=subject["client_key"],
                )
            )

    if mode == DRAFT_VALIDATION_MODE_FINAL:
        subjects_by_bu: dict[str, int] = {}
        for subject in activity_subjects:
            key = subject["business_unit_client_key"]
            subjects_by_bu[key] = subjects_by_bu.get(key, 0) + 1
        for business_unit in business_units:
            if subjects_by_bu.get(business_unit["client_key"], 0) < 1:
                errors.append(
                    draft_error(
                        "business_unit_without_subjects",
                        section="business_units",
                        key=business_unit["client_key"],
                    )
                )

        # establishment name/description already collected; ensure final still lists them
        _ = establishment
        _ = team
