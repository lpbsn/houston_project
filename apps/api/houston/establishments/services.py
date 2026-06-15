from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpRequest
from django.utils import timezone

from houston.accounts import tokens as auth_tokens
from houston.accounts.models import User, UserSession
from houston.establishments.access import get_onboarding_access_context
from houston.establishments.membership_scope import (
    InvalidMembershipScopeAssignmentError,
    MembershipScopeInput,
    assign_membership_scopes,
    membership_scope_covers_business_unit,
    normalize_membership_scope_inputs,
    scopes_not_allowed_for_role,
)
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    ActivitySubject,
    BusinessUnit,
    CatalogActivitySubject,
    CatalogBusinessUnit,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentInvitation,
    EstablishmentMembership,
    OnboardingProposal,
    OnboardingSession,
)
from houston.establishments.selectors import (
    business_unit_has_active_membership_scopes,
    get_membership_for_management,
    get_runtime_config_for_session,
)
from houston.establishments.taxonomy_normalization import (
    normalize_activity_subject_name,
    slugify_label,
)
from houston.organizations.models import Organization


class MembershipManagementNotFoundError(Exception):
    pass


class CannotDeactivateLastActiveOwnerError(Exception):
    pass


class CannotDemoteLastActiveOwnerError(Exception):
    pass


class MembershipManagementForbiddenError(Exception):
    pass


class InvalidMembershipInvitationInputError(Exception):
    pass


class MembershipInvitationRoleNotAllowedError(Exception):
    pass


class ActiveOnboardingSessionExistsError(Exception):
    pass


class InvalidOnboardingSessionScopeError(Exception):
    pass


class UnsupportedOnboardingSessionSourceModeError(Exception):
    pass


class OnboardingAccessDeniedError(Exception):
    pass


class OnboardingSessionTerminalError(Exception):
    pass


class InvalidOnboardingActivationStateError(Exception):
    pass


class InvalidActivityDescriptionError(Exception):
    pass


class OnboardingReadinessError(Exception):
    def __init__(self, readiness: dict):
        super().__init__("Onboarding session is not ready for activation.")
        self.readiness = readiness


class ActiveOnboardingProposalExistsError(Exception):
    pass


class OnboardingProposalValidationError(Exception):
    def __init__(self, errors: list[dict]):
        super().__init__("Onboarding proposal payload is invalid.")
        self.errors = errors


class OnboardingProposalStateError(Exception):
    pass


class DirectorInvitationDuplicateError(Exception):
    pass


class DirectorInvitationAlreadyExistsError(Exception):
    pass


class DirectorInvitationOwnerNotAllowedError(Exception):
    pass


class InvalidDirectorInvitationInputError(Exception):
    pass


class InvalidEstablishmentInvitationError(Exception):
    pass


class RuntimeConfigNotFoundError(Exception):
    pass


class RuntimeConfigConflictError(Exception):
    def __init__(self, *, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


class EstablishmentInvitationExpiredError(Exception):
    pass


class EstablishmentInvitationAlreadyAcceptedError(Exception):
    pass


@dataclass(frozen=True)
class DirectorInvitationResult:
    membership: EstablishmentMembership
    invitation_token: str
    invitation_expires_at: datetime


@dataclass(frozen=True)
class DirectorInvitationAcceptResult:
    auth: object
    payload: dict


@dataclass(frozen=True)
class MembershipUpdateInput:
    role: str | None = None
    scopes: list[MembershipScopeInput] | None = None


# Product: Onboarding manuel V2 (Lot 4)
# Technical schema: onboarding_proposal_v3 — BusinessUnit / ActivitySubject payload
PROPOSAL_SCHEMA_VERSION_V3_BU = "onboarding_proposal_v3"
PROPOSAL_V3_BU_REQUIRED_SECTIONS = frozenset(
    {
        "business_units",
        "activity_subjects",
    }
)
PROPOSAL_V3_BU_OPTIONAL_SECTIONS = frozenset(
    {
        "excluded_catalog_subject_keys",
    }
)
PROPOSAL_V3_BU_SECTIONS = PROPOSAL_V3_BU_REQUIRED_SECTIONS | PROPOSAL_V3_BU_OPTIONAL_SECTIONS
PROPOSAL_V3_BU_SECTION_CAPS = {
    "business_units": 50,
    "activity_subjects": 500,
}
PROPOSAL_V3_BU_EXCLUDED_SECTIONS = frozenset(
    {
        "roles",
        "memberships",
        "billing",
        "subscription",
        "checklists",
        "checklist_templates",
        "signal_examples",
        "observations",
        "signals",
        "actions",
        "comments",
        "permissions",
    }
)
PROPOSAL_SECTION_ACCEPTED = "accepted"
PROPOSAL_VALIDATION_MODE_DRAFT = "draft"
PROPOSAL_VALIDATION_MODE_FINAL = "final"


def validate_onboarding_proposal_payload(
    payload: dict,
    *,
    mode: str = PROPOSAL_VALIDATION_MODE_FINAL,
) -> dict:
    if not isinstance(payload, dict):
        raise OnboardingProposalValidationError([_proposal_error("invalid_payload_type")])

    if mode not in {PROPOSAL_VALIDATION_MODE_DRAFT, PROPOSAL_VALIDATION_MODE_FINAL}:
        raise OnboardingProposalValidationError([_proposal_error("invalid_payload_type")])

    schema_version = payload.get("schema_version")
    if schema_version == PROPOSAL_SCHEMA_VERSION_V3_BU:
        return _validate_onboarding_proposal_payload_v3_bu(payload, mode=mode)

    raise OnboardingProposalValidationError(
        [_proposal_error("unsupported_schema_version", field="schema_version")]
    )


def _validate_onboarding_proposal_payload_v3_bu(payload: dict, *, mode: str) -> dict:
    errors: list[dict] = []

    if payload.get("schema_version") != PROPOSAL_SCHEMA_VERSION_V3_BU:
        errors.append(_proposal_error("unsupported_schema_version", field="schema_version"))

    for section in PROPOSAL_V3_BU_REQUIRED_SECTIONS:
        if section not in payload:
            errors.append(_proposal_error("missing_required_section", section=section))

    for section in payload:
        if section == "schema_version":
            continue
        if section in PROPOSAL_V3_BU_EXCLUDED_SECTIONS:
            errors.append(_proposal_error("excluded_section", section=section))
        elif section not in PROPOSAL_V3_BU_SECTIONS:
            errors.append(_proposal_error("unknown_section", section=section))

    raw_business_units = _section_items_v3_bu(payload, "business_units", errors)
    raw_activity_subjects = _section_items_v3_bu(payload, "activity_subjects", errors)
    catalog_keys = _active_business_unit_catalog_keys()

    require_unit_type = mode == PROPOSAL_VALIDATION_MODE_FINAL
    business_units = _validate_business_unit_section(
        items=raw_business_units,
        catalog_keys=catalog_keys["business_units"],
        errors=errors,
        require_unit_type=require_unit_type,
    )
    business_unit_client_keys = {item["client_key"] for item in business_units}

    activity_subjects = _validate_activity_subject_section(
        items=raw_activity_subjects,
        business_unit_client_keys=business_unit_client_keys,
        catalog_keys=catalog_keys["activity_subjects"],
        errors=errors,
    )

    if len(business_units) < 1:
        errors.append(_proposal_error("insufficient_business_units"))

    subjects_by_bu_client_key: dict[str, int] = {}
    for subject in activity_subjects:
        subjects_by_bu_client_key[subject["business_unit_client_key"]] = (
            subjects_by_bu_client_key.get(subject["business_unit_client_key"], 0) + 1
        )
    if mode == PROPOSAL_VALIDATION_MODE_FINAL:
        for business_unit in business_units:
            if subjects_by_bu_client_key.get(business_unit["client_key"], 0) < 1:
                errors.append(
                    _proposal_error(
                        "business_unit_without_subjects",
                        key=business_unit["client_key"],
                    )
                )

    if errors:
        raise OnboardingProposalValidationError(errors)

    result = {
        "schema_version": PROPOSAL_SCHEMA_VERSION_V3_BU,
        "business_units": business_units,
        "activity_subjects": activity_subjects,
    }
    excluded_catalog_subject_keys = _validate_excluded_catalog_subject_keys(
        payload.get("excluded_catalog_subject_keys"),
        business_unit_client_keys=business_unit_client_keys,
        errors=errors,
    )
    if errors:
        raise OnboardingProposalValidationError(errors)
    if excluded_catalog_subject_keys:
        result["excluded_catalog_subject_keys"] = excluded_catalog_subject_keys
    return result


@transaction.atomic
def create_manual_onboarding_proposal(
    *,
    session: OnboardingSession,
    actor,
    payload: dict,
) -> OnboardingProposal:
    return _create_onboarding_proposal(
        session=session,
        actor=actor,
        payload=payload,
        source=OnboardingProposal.Source.MANUAL,
    )


@transaction.atomic
def update_onboarding_proposal_payload(
    *,
    proposal: OnboardingProposal,
    actor,
    payload: dict,
) -> OnboardingProposal:
    proposal = _lock_onboarding_proposal(proposal)
    _ensure_proposal_editable(proposal)
    _ensure_can_manage_onboarding_proposal(proposal=proposal, actor=actor)

    if payload.get("schema_version") != PROPOSAL_SCHEMA_VERSION_V3_BU:
        raise OnboardingProposalValidationError(
            [_proposal_error("unsupported_schema_version", field="schema_version")]
        )

    sanitized_payload = validate_onboarding_proposal_payload(
        payload,
        mode=PROPOSAL_VALIDATION_MODE_DRAFT,
    )
    proposal.payload = sanitized_payload
    proposal.section_validation = {}
    proposal.validation_errors = []
    proposal.status = OnboardingProposal.Status.READY
    proposal.save(
        update_fields=[
            "payload",
            "section_validation",
            "validation_errors",
            "status",
            "updated_at",
        ]
    )
    return proposal


@transaction.atomic
def submit_manual_onboarding_proposal(
    *,
    proposal: OnboardingProposal,
    actor,
) -> OnboardingProposal:
    proposal = _lock_onboarding_proposal(proposal)
    _ensure_proposal_reviewable(proposal)
    _ensure_can_manage_onboarding_proposal(proposal=proposal, actor=actor)

    payload = validate_onboarding_proposal_payload(
        proposal.payload,
        mode=PROPOSAL_VALIDATION_MODE_FINAL,
    )
    if payload["schema_version"] != PROPOSAL_SCHEMA_VERSION_V3_BU:
        raise OnboardingProposalValidationError(
            [_proposal_error("unsupported_schema_version", field="schema_version")]
        )

    proposal.payload = payload
    proposal.section_validation = {
        section: PROPOSAL_SECTION_ACCEPTED for section in PROPOSAL_V3_BU_REQUIRED_SECTIONS
    }
    proposal.validation_errors = []
    proposal.status = OnboardingProposal.Status.VALIDATED
    proposal.validated_by = actor
    proposal.validated_at = timezone.now()
    proposal.save(
        update_fields=[
            "payload",
            "section_validation",
            "validation_errors",
            "status",
            "validated_by",
            "validated_at",
            "updated_at",
        ]
    )
    _set_session_status_after_proposal_validation(proposal.onboarding_session)
    return proposal


@transaction.atomic
def reject_onboarding_proposal(*, proposal: OnboardingProposal, actor) -> OnboardingProposal:
    proposal = _lock_onboarding_proposal(proposal)
    _ensure_proposal_reviewable(proposal)
    _ensure_can_manage_onboarding_proposal(proposal=proposal, actor=actor)

    proposal.status = OnboardingProposal.Status.REJECTED
    proposal.save(update_fields=["status", "updated_at"])
    return proposal


@transaction.atomic
def apply_onboarding_proposal(*, proposal: OnboardingProposal, actor) -> OnboardingProposal:
    proposal = _lock_onboarding_proposal(proposal)
    session = _lock_onboarding_session(proposal.onboarding_session)
    establishment = (
        Establishment.objects.select_for_update()
        .select_related("organization")
        .get(id=proposal.establishment_id)
    )
    _ensure_non_terminal_onboarding_session(session)
    _ensure_can_manage_onboarding_proposal(proposal=proposal, actor=actor)

    if establishment.status != Establishment.Status.DRAFT:
        raise OnboardingProposalStateError("Only draft establishments can apply proposals.")
    if proposal.status != OnboardingProposal.Status.VALIDATED:
        raise OnboardingProposalStateError("Only validated proposals can be applied.")

    payload = validate_onboarding_proposal_payload(
        proposal.payload,
        mode=PROPOSAL_VALIDATION_MODE_FINAL,
    )

    bu_keys, _subject_pairs = _apply_business_unit_sections(
        establishment=establishment,
        payload=payload,
        proposal=proposal,
    )
    assert bu_keys

    proposal.payload = payload
    proposal.status = OnboardingProposal.Status.APPLIED
    proposal.applied_by = actor
    proposal.applied_at = timezone.now()
    proposal.validation_errors = []
    proposal.save(
        update_fields=[
            "payload",
            "status",
            "applied_by",
            "applied_at",
            "validation_errors",
            "updated_at",
        ]
    )

    session.status = OnboardingSession.Status.CONFIGURING_RUNTIME
    session.ready_for_activation_at = None
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    return proposal


def _create_onboarding_proposal(
    *,
    session: OnboardingSession,
    actor,
    payload: dict,
    source: str,
) -> OnboardingProposal:
    session = _lock_onboarding_session(session)
    _ensure_non_terminal_onboarding_session(session)

    access = get_onboarding_access_context(actor=actor, session=session)
    if not access.can_configure_runtime:
        raise OnboardingAccessDeniedError

    existing_proposal = (
        OnboardingProposal.objects.filter(onboarding_session=session)
        .filter(
            Q(status__in=OnboardingProposal.NON_TERMINAL_STATUSES)
            | Q(
                status=OnboardingProposal.Status.APPLIED,
                establishment__status=Establishment.Status.DRAFT,
            )
        )
        .order_by("-created_at", "-id")
        .first()
    )
    if existing_proposal is not None:
        raise ActiveOnboardingProposalExistsError(
            "A non-terminal onboarding proposal already exists for this session."
        )

    sanitized_payload = validate_onboarding_proposal_payload(
        payload,
        mode=PROPOSAL_VALIDATION_MODE_DRAFT,
    )
    proposal = OnboardingProposal(
        onboarding_session=session,
        establishment=session.establishment,
        source=source,
        status=OnboardingProposal.Status.READY,
        payload=sanitized_payload,
        validation_errors=[],
        created_by=actor,
    )
    proposal.full_clean(validate_unique=False, validate_constraints=False)

    try:
        with transaction.atomic():
            proposal.save()
    except IntegrityError as exc:
        raise ActiveOnboardingProposalExistsError(
            "A non-terminal onboarding proposal already exists for this session."
        ) from exc

    session.status = OnboardingSession.Status.PROPOSAL_READY
    session.ready_for_activation_at = None
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])
    return proposal


def _empty_proposal_payload() -> dict:
    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION_V3_BU,
        "business_units": [],
        "activity_subjects": [],
    }


def _active_business_unit_catalog_keys() -> dict[str, set[str]]:
    return {
        "business_units": set(
            CatalogBusinessUnit.objects.filter(active=True).values_list("key", flat=True)
        ),
        "activity_subjects": set(
            CatalogActivitySubject.objects.filter(active=True).values_list("key", flat=True)
        ),
    }


def _section_items_v3_bu(payload: dict, section: str, errors: list[dict]) -> list:
    items = payload.get(section, [])
    if not isinstance(items, list):
        errors.append(_proposal_error("section_must_be_array", section=section))
        return []
    if len(items) > PROPOSAL_V3_BU_SECTION_CAPS[section]:
        errors.append(_proposal_error("section_cap_exceeded", section=section))
        return items[: PROPOSAL_V3_BU_SECTION_CAPS[section]]
    return items


def _validate_business_unit_section(
    *,
    items: list,
    catalog_keys: set[str],
    errors: list[dict],
    require_unit_type: bool = True,
) -> list[dict]:
    sanitized: list[dict] = []
    seen_client_keys: set[str] = set()
    seen_runtime_keys: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            errors.append(_proposal_error("invalid_payload_type", section="business_units"))
            continue

        client_key = _normalized_string(item.get("client_key"))
        label = _normalized_string(item.get("label"))
        unit_type = _normalized_string(item.get("unit_type"))
        description = _normalized_string(item.get("description"))
        catalog_key = _nullable_normalized_string(item.get("catalog_key"))

        if not client_key:
            errors.append(
                _proposal_error("missing_client_key", section="business_units", field="client_key")
            )
            continue
        if client_key in seen_client_keys:
            errors.append(
                _proposal_error(
                    "duplicate_client_key",
                    section="business_units",
                    key=client_key,
                )
            )
            continue
        if not label:
            errors.append(
                _proposal_error(
                    "missing_business_unit_label",
                    section="business_units",
                    key=client_key,
                )
            )
            continue
        if require_unit_type:
            if unit_type not in {
                BusinessUnit.UnitType.DEDICATED,
                BusinessUnit.UnitType.TRANSVERSAL,
            }:
                errors.append(
                    _proposal_error(
                        "invalid_unit_type",
                        section="business_units",
                        key=client_key,
                        field="unit_type",
                    )
                )
                continue
        elif unit_type and unit_type not in {
            BusinessUnit.UnitType.DEDICATED,
            BusinessUnit.UnitType.TRANSVERSAL,
        }:
            errors.append(
                _proposal_error(
                    "invalid_unit_type",
                    section="business_units",
                    key=client_key,
                    field="unit_type",
                )
            )
            continue

        runtime_key = slugify_label(label)
        if runtime_key in seen_runtime_keys:
            errors.append(
                _proposal_error(
                    "duplicate_business_unit_key",
                    section="business_units",
                    key=client_key,
                )
            )
            continue
        if catalog_key is not None and catalog_key not in catalog_keys:
            errors.append(
                _proposal_error(
                    "unknown_catalog_key",
                    section="business_units",
                    key=catalog_key,
                )
            )
            continue

        seen_client_keys.add(client_key)
        seen_runtime_keys.add(runtime_key)
        sanitized_item = {
            "client_key": client_key,
            "label": label,
            "description": description,
            "catalog_key": catalog_key,
        }
        if unit_type in {
            BusinessUnit.UnitType.DEDICATED,
            BusinessUnit.UnitType.TRANSVERSAL,
        }:
            sanitized_item["unit_type"] = unit_type
        sanitized.append(sanitized_item)

    return sanitized


def _validate_activity_subject_section(
    *,
    items: list,
    business_unit_client_keys: set[str],
    catalog_keys: set[str],
    errors: list[dict],
) -> list[dict]:
    sanitized: list[dict] = []
    seen_client_keys: set[str] = set()
    seen_normalized_by_bu: dict[str, set[str]] = {}

    for item in items:
        if not isinstance(item, dict):
            errors.append(_proposal_error("invalid_payload_type", section="activity_subjects"))
            continue

        client_key = _normalized_string(item.get("client_key"))
        label = _normalized_string(item.get("label"))
        description = _normalized_string(item.get("description"))
        business_unit_client_key = _normalized_string(item.get("business_unit_client_key"))
        catalog_key = _nullable_normalized_string(item.get("catalog_key"))

        if not client_key:
            errors.append(
                _proposal_error(
                    "missing_client_key",
                    section="activity_subjects",
                    field="client_key",
                )
            )
            continue
        if client_key in seen_client_keys:
            errors.append(
                _proposal_error(
                    "duplicate_client_key",
                    section="activity_subjects",
                    key=client_key,
                )
            )
            continue
        if not label:
            errors.append(
                _proposal_error(
                    "missing_activity_subject_label",
                    section="activity_subjects",
                    key=client_key,
                )
            )
            continue
        if business_unit_client_key not in business_unit_client_keys:
            errors.append(
                _proposal_error(
                    "orphan_activity_subject",
                    section="activity_subjects",
                    key=client_key,
                    field="business_unit_client_key",
                )
            )
            continue
        if catalog_key is not None and catalog_key not in catalog_keys:
            errors.append(
                _proposal_error(
                    "unknown_catalog_key",
                    section="activity_subjects",
                    key=catalog_key,
                )
            )
            continue

        normalized_name = normalize_activity_subject_name(label)
        bu_names = seen_normalized_by_bu.setdefault(business_unit_client_key, set())
        if normalized_name in bu_names:
            errors.append(
                _proposal_error(
                    "duplicate_activity_subject",
                    section="activity_subjects",
                    key=client_key,
                )
            )
            continue

        seen_client_keys.add(client_key)
        bu_names.add(normalized_name)
        sanitized.append(
            {
                "client_key": client_key,
                "label": label,
                "description": description,
                "business_unit_client_key": business_unit_client_key,
                "catalog_key": catalog_key,
            }
        )

    return sanitized


def _validate_excluded_catalog_subject_keys(
    raw_value,
    *,
    business_unit_client_keys: set[str],
    errors: list[dict],
) -> dict[str, list[str]]:
    if raw_value is None:
        return {}

    if not isinstance(raw_value, dict):
        errors.append(
            _proposal_error(
                "invalid_payload_type",
                section="excluded_catalog_subject_keys",
            )
        )
        return {}

    sanitized: dict[str, list[str]] = {}
    for business_unit_client_key, catalog_keys in raw_value.items():
        normalized_bu_key = _normalized_string(business_unit_client_key)
        if not normalized_bu_key:
            errors.append(
                _proposal_error(
                    "missing_client_key",
                    section="excluded_catalog_subject_keys",
                    field="business_unit_client_key",
                )
            )
            continue
        if normalized_bu_key not in business_unit_client_keys:
            errors.append(
                _proposal_error(
                    "orphan_excluded_catalog_subject",
                    section="excluded_catalog_subject_keys",
                    key=normalized_bu_key,
                )
            )
            continue

        normalized_catalog_keys = _normalized_string_list(catalog_keys)
        if normalized_catalog_keys:
            sanitized[normalized_bu_key] = normalized_catalog_keys

    return sanitized


def _apply_business_unit_sections(
    *,
    establishment: Establishment,
    payload: dict,
    proposal: OnboardingProposal,
) -> tuple[set[str], set[tuple[int, str]]]:
    catalog_bus = {row.key: row for row in CatalogBusinessUnit.objects.filter(active=True)}
    catalog_ass = {row.key: row for row in CatalogActivitySubject.objects.filter(active=True)}

    business_units_by_client_key: dict[str, BusinessUnit] = {}
    bu_runtime_keys: set[str] = set()
    kept_business_unit_ids: set = set()
    kept_activity_subject_ids: set = set()
    subject_pairs: set[tuple[int, str]] = set()

    for item in payload["business_units"]:
        runtime_key = slugify_label(item["label"])
        catalog_key = item.get("catalog_key")
        catalog_bu = catalog_bus.get(catalog_key) if catalog_key else None
        bu_source = (
            BusinessUnit.Source.CATALOG_SUGGESTION if catalog_key else BusinessUnit.Source.MANUAL
        )

        business_unit, _created = BusinessUnit.objects.update_or_create(
            establishment=establishment,
            key=runtime_key,
            defaults={
                "label": item["label"],
                "description": item.get("description", ""),
                "unit_type": item["unit_type"],
                "catalog_business_unit": catalog_bu,
                "source": bu_source,
                "active": True,
                "managed_by_onboarding_proposal": proposal,
            },
        )
        business_units_by_client_key[item["client_key"]] = business_unit
        bu_runtime_keys.add(runtime_key)
        kept_business_unit_ids.add(business_unit.id)

    BusinessUnit.objects.filter(
        establishment=establishment,
        active=True,
        managed_by_onboarding_proposal=proposal,
    ).exclude(id__in=kept_business_unit_ids).update(
        active=False,
        updated_at=timezone.now(),
    )

    for item in payload["activity_subjects"]:
        business_unit = business_units_by_client_key[item["business_unit_client_key"]]
        normalized_name = normalize_activity_subject_name(item["label"])
        catalog_key = item.get("catalog_key")
        catalog_as = catalog_ass.get(catalog_key) if catalog_key else None
        subject_source = (
            ActivitySubject.Source.CATALOG_SUGGESTION
            if catalog_key
            else ActivitySubject.Source.MANUAL
        )

        activity_subject, _created = ActivitySubject.objects.update_or_create(
            establishment=establishment,
            business_unit=business_unit,
            normalized_name=normalized_name,
            defaults={
                "label": item["label"],
                "description": item.get("description", ""),
                "catalog_activity_subject": catalog_as,
                "source": subject_source,
                "active": True,
                "managed_by_onboarding_proposal": proposal,
            },
        )
        kept_activity_subject_ids.add(activity_subject.id)
        subject_pairs.add((business_unit.id, normalized_name))

    ActivitySubject.objects.filter(
        establishment=establishment,
        active=True,
        managed_by_onboarding_proposal=proposal,
    ).exclude(id__in=kept_activity_subject_ids).update(
        active=False,
        updated_at=timezone.now(),
    )

    return bu_runtime_keys, subject_pairs


def _proposal_error(
    code: str,
    *,
    section: str | None = None,
    field: str | None = None,
    key: str | None = None,
) -> dict:
    error = {"code": code}
    if section is not None:
        error["section"] = section
    if field is not None:
        error["field"] = field
    if key is not None:
        error["key"] = key
    return error


def _normalized_string(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _nullable_normalized_string(value) -> str | None:
    if value is None:
        return None
    normalized = _normalized_string(value)
    return normalized or None


def _normalized_string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        normalized_item = _normalized_string(item)
        if not normalized_item or normalized_item in seen:
            continue
        seen.add(normalized_item)
        normalized.append(normalized_item)
    return normalized


def _ensure_proposal_reviewable(proposal: OnboardingProposal) -> None:
    if proposal.status not in {
        OnboardingProposal.Status.READY,
        OnboardingProposal.Status.PARTIALLY_VALIDATED,
        OnboardingProposal.Status.VALIDATED,
    }:
        raise OnboardingProposalStateError("Proposal cannot be reviewed.")


def _ensure_proposal_editable(proposal: OnboardingProposal) -> None:
    establishment = proposal.establishment
    if (
        proposal.status == OnboardingProposal.Status.APPLIED
        and establishment.status == Establishment.Status.DRAFT
    ):
        return

    if proposal.status not in {
        OnboardingProposal.Status.READY,
        OnboardingProposal.Status.PARTIALLY_VALIDATED,
    }:
        raise OnboardingProposalStateError("Only draft proposals can be updated.")


def _ensure_can_manage_onboarding_proposal(*, proposal: OnboardingProposal, actor) -> None:
    access = get_onboarding_access_context(
        actor=actor,
        session=proposal.onboarding_session,
    )
    if not access.can_manage:
        raise OnboardingAccessDeniedError


def _set_session_status_after_proposal_validation(session: OnboardingSession) -> None:
    session = _lock_onboarding_session(session)
    if session.status != OnboardingSession.Status.VALIDATING_SECTIONS:
        session.status = OnboardingSession.Status.VALIDATING_SECTIONS
        session.ready_for_activation_at = None
        session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])


@transaction.atomic
def start_onboarding_session(
    *,
    organization: Organization,
    establishment: Establishment,
    started_by=None,
    source_mode: str = OnboardingSession.SourceMode.MANUAL,
    current_step: str = "",
) -> OnboardingSession:
    if source_mode not in {
        OnboardingSession.SourceMode.MANUAL,
        OnboardingSession.SourceMode.TEMPLATE,
    }:
        raise UnsupportedOnboardingSessionSourceModeError(
            "Only manual and template onboarding sessions are supported."
        )

    if establishment.organization_id != organization.id:
        raise InvalidOnboardingSessionScopeError(
            "Organization must match the establishment organization."
        )

    existing_session = (
        OnboardingSession.objects.filter(
            establishment=establishment,
            status__in=OnboardingSession.NON_TERMINAL_STATUSES,
        )
        .order_by("-created_at", "-id")
        .first()
    )
    if existing_session is not None:
        return existing_session

    session = OnboardingSession(
        organization=organization,
        establishment=establishment,
        started_by=started_by,
        source_mode=source_mode,
        current_step=current_step,
    )
    session.full_clean(validate_unique=False, validate_constraints=False)

    try:
        with transaction.atomic():
            session.save()
    except IntegrityError as exc:
        existing_session = (
            OnboardingSession.objects.filter(
                establishment=establishment,
                status__in=OnboardingSession.NON_TERMINAL_STATUSES,
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if existing_session is not None:
            return existing_session
        raise ActiveOnboardingSessionExistsError(
            "A non-terminal onboarding session already exists for this establishment."
        ) from exc

    return session


@transaction.atomic
def submit_activity_description(
    *,
    session: OnboardingSession,
    actor,
    description: str,
) -> EstablishmentActivityDescription:
    session = _lock_onboarding_session(session)
    _ensure_non_terminal_onboarding_session(session)

    access = get_onboarding_access_context(actor=actor, session=session)
    if not access.can_configure_runtime:
        raise OnboardingAccessDeniedError

    normalized_description = _normalize_activity_description(description)
    if len(normalized_description) < ACTIVITY_DESCRIPTION_MIN_LENGTH:
        raise InvalidActivityDescriptionError(
            f"Activity description must be at least {ACTIVITY_DESCRIPTION_MIN_LENGTH} characters."
        )

    activity_description, _created = EstablishmentActivityDescription.objects.update_or_create(
        establishment=session.establishment,
        defaults={
            "description": normalized_description,
            "source": EstablishmentActivityDescription.Source.MANUAL,
            "submitted_by": actor,
            "validated_at": timezone.now(),
        },
    )
    try:
        activity_description.full_clean()
    except ValidationError as exc:
        raise InvalidActivityDescriptionError(str(exc)) from exc

    activity_description.save(
        update_fields=[
            "description",
            "source",
            "submitted_by",
            "validated_at",
            "updated_at",
        ],
    )

    _set_status_after_description_submit(session)
    return activity_description


def compute_activation_readiness(*, session: OnboardingSession) -> dict:
    session = _reload_onboarding_session(session)
    counts = _activation_counts(session)
    sections = {
        "business_units": {
            "is_ready": counts["active_business_units_count"] >= 1,
            "required": True,
            "is_skippable": False,
        },
        "activity_subjects": {
            "is_ready": (
                counts["active_activity_subjects_count"] >= 1
                and counts["active_business_units_without_subjects_count"] == 0
            ),
            "required": True,
            "is_skippable": False,
        },
        "director": {
            "is_ready": counts["active_or_invited_director_count"] >= 1,
            "required": True,
            "is_skippable": False,
        },
    }
    blockers = _activation_blockers(session=session, counts=counts)

    return {
        "is_ready": not blockers,
        "blockers": blockers,
        "counts": counts,
        "sections": sections,
        "establishment_status": session.establishment.status,
        "session_status": session.status,
    }


def build_activation_summary(*, session: OnboardingSession) -> dict:
    session = _reload_onboarding_session(session)
    config = get_runtime_config_for_session(session=session)
    readiness = compute_activation_readiness(session=session)
    counts = readiness["counts"]

    return {
        "organization": _serialize_organization(session.organization),
        "establishment": _serialize_establishment(session.establishment),
        "activity_description": _serialize_activity_description(
            config["activity_description"],
        ),
        "active_business_units": config["active_business_units"],
        "optional_units": [
            _serialize_keyed_runtime_item(item) for item in config["optional_units"]
        ],
        "initial_owner_director_count": counts["active_owner_or_director_count"],
        "initial_director_count": counts["active_or_invited_director_count"],
        "readiness": readiness,
        "blockers": readiness["blockers"],
    }


@transaction.atomic
def invite_director_during_onboarding(
    *,
    session: OnboardingSession,
    actor,
    email: str,
    first_name: str,
    last_name: str,
) -> DirectorInvitationResult:
    session = _lock_onboarding_session(session)
    _ensure_non_terminal_onboarding_session(session)

    access = get_onboarding_access_context(actor=actor, session=session)
    if not access.can_manage:
        raise OnboardingAccessDeniedError

    if session.establishment.status != Establishment.Status.DRAFT:
        raise InvalidOnboardingActivationStateError(
            "Director invitations are only allowed for draft establishments."
        )

    normalized_email = User.normalize_email_value(email)
    if normalized_email is None:
        raise InvalidDirectorInvitationInputError("A valid email is required.")

    normalized_first_name = first_name.strip()
    normalized_last_name = last_name.strip()
    if not normalized_first_name or not normalized_last_name:
        raise InvalidDirectorInvitationInputError("First and last name are required.")

    establishment = session.establishment
    owner_user_ids = _active_owner_user_ids(establishment_id=establishment.id)

    if User.objects.filter(id__in=owner_user_ids, email__iexact=normalized_email).exists():
        raise DirectorInvitationOwnerNotAllowedError

    existing_user = User.objects.filter(email__iexact=normalized_email).first()
    if existing_user is not None and existing_user.id in owner_user_ids:
        raise DirectorInvitationOwnerNotAllowedError

    existing_membership = None
    if existing_user is not None:
        existing_membership = EstablishmentMembership.objects.filter(
            user=existing_user,
            establishment=establishment,
        ).first()

    if existing_membership is not None:
        if existing_membership.status in {
            EstablishmentMembership.Status.INVITED,
            EstablishmentMembership.Status.ACTIVE,
        }:
            raise DirectorInvitationDuplicateError

        if (
            existing_membership.status == EstablishmentMembership.Status.DEACTIVATED
            and existing_membership.role == EstablishmentMembership.Role.DIRECTOR
        ):
            if (
                _count_non_owner_directors(
                    establishment_id=establishment.id,
                    owner_user_ids=owner_user_ids,
                )
                >= 1
            ):
                raise DirectorInvitationAlreadyExistsError

            existing_membership.status = EstablishmentMembership.Status.INVITED
            existing_membership.save(update_fields=["status", "updated_at"])
            existing_user.first_name = normalized_first_name
            existing_user.last_name = normalized_last_name
            existing_user.save(update_fields=["first_name", "last_name", "updated_at"])
            return _issue_director_invitation_for_membership(existing_membership)

        raise DirectorInvitationDuplicateError

    if (
        _count_non_owner_directors(
            establishment_id=establishment.id,
            owner_user_ids=owner_user_ids,
        )
        >= 1
    ):
        raise DirectorInvitationAlreadyExistsError

    from houston.accounts.services import resolve_or_create_pending_user_for_invite

    user = resolve_or_create_pending_user_for_invite(
        email=normalized_email,
        first_name=normalized_first_name,
        last_name=normalized_last_name,
        existing_user=existing_user,
    )

    if user.id in owner_user_ids:
        raise DirectorInvitationOwnerNotAllowedError

    membership = _create_invited_membership(
        user=user,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        owner_user_ids=owner_user_ids,
    )
    return _issue_director_invitation_for_membership(membership)


@transaction.atomic
def accept_director_invitation(
    *,
    request: HttpRequest,
    raw_token: str,
    password: str,
) -> DirectorInvitationAcceptResult:
    token_digest = auth_tokens.digest_token(raw_token.strip())
    now = timezone.now()

    invitation = (
        EstablishmentInvitation.objects.select_for_update()
        .select_related(
            "membership",
            "membership__user",
            "membership__establishment",
            "membership__establishment__organization",
        )
        .filter(token_digest=token_digest)
        .first()
    )

    if invitation is None:
        raise InvalidEstablishmentInvitationError

    if invitation.accepted_at is not None:
        raise EstablishmentInvitationAlreadyAcceptedError

    if invitation.revoked_at is not None:
        raise InvalidEstablishmentInvitationError

    if invitation.expires_at <= now:
        raise EstablishmentInvitationExpiredError

    membership = invitation.membership
    user = membership.user

    if membership.role != EstablishmentMembership.Role.DIRECTOR:
        raise InvalidEstablishmentInvitationError

    if membership.status != EstablishmentMembership.Status.INVITED:
        raise InvalidEstablishmentInvitationError

    if user.status != User.Status.PENDING:
        raise InvalidEstablishmentInvitationError

    return _finalize_establishment_invitation_accept(
        request=request,
        invitation=invitation,
        membership=membership,
        user=user,
        password=password,
    )


_INVITATION_ACCEPT_ROLES = frozenset(
    {
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    }
)


@transaction.atomic
def accept_establishment_invitation(
    *,
    request: HttpRequest,
    raw_token: str,
    password: str,
) -> DirectorInvitationAcceptResult:
    token_digest = auth_tokens.digest_token(raw_token.strip())
    now = timezone.now()

    invitation = (
        EstablishmentInvitation.objects.select_for_update()
        .select_related(
            "membership",
            "membership__user",
            "membership__establishment",
            "membership__establishment__organization",
        )
        .filter(token_digest=token_digest)
        .first()
    )

    if invitation is None:
        raise InvalidEstablishmentInvitationError

    if invitation.accepted_at is not None:
        raise EstablishmentInvitationAlreadyAcceptedError

    if invitation.revoked_at is not None:
        raise InvalidEstablishmentInvitationError

    if invitation.expires_at <= now:
        raise EstablishmentInvitationExpiredError

    membership = invitation.membership
    user = membership.user

    if membership.role not in _INVITATION_ACCEPT_ROLES:
        raise InvalidEstablishmentInvitationError

    if membership.status != EstablishmentMembership.Status.INVITED:
        raise InvalidEstablishmentInvitationError

    if user.status != User.Status.PENDING:
        raise InvalidEstablishmentInvitationError

    return _finalize_establishment_invitation_accept(
        request=request,
        invitation=invitation,
        membership=membership,
        user=user,
        password=password,
    )


def _finalize_establishment_invitation_accept(
    *,
    request: HttpRequest,
    invitation: EstablishmentInvitation,
    membership: EstablishmentMembership,
    user: User,
    password: str,
) -> DirectorInvitationAcceptResult:
    now = timezone.now()

    user.set_password(password)
    user.status = User.Status.ACTIVE
    user.save(update_fields=["password", "status", "updated_at"])

    membership.status = EstablishmentMembership.Status.ACTIVE
    membership.save(update_fields=["status", "updated_at"])

    invitation.accepted_at = now
    invitation.save(update_fields=["accepted_at", "updated_at"])

    from houston.accounts.services import (
        build_auth_response_payload,
        create_login_session,
    )

    auth_bundle = create_login_session(request=request, user=user)
    auth_session = auth_bundle.session
    auth_session.selected_establishment = membership.establishment
    auth_session.save(update_fields=["selected_establishment", "updated_at"])

    payload = build_auth_response_payload(
        session=auth_session,
        access_token=auth_bundle.access_token,
    )
    payload["establishment_id"] = membership.establishment_id

    onboarding_session = (
        OnboardingSession.objects.filter(
            establishment_id=membership.establishment_id,
        )
        .exclude(
            status__in=[
                OnboardingSession.Status.ACTIVATED,
                OnboardingSession.Status.FAILED,
                OnboardingSession.Status.CANCELED,
            ],
        )
        .order_by("-created_at")
        .first()
    )
    if onboarding_session is not None:
        payload["onboarding_session_id"] = onboarding_session.id

    return DirectorInvitationAcceptResult(
        auth=auth_bundle,
        payload=payload,
    )


@transaction.atomic
def invite_membership_for_establishment(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    scopes: list[MembershipScopeInput] | None = None,
) -> DirectorInvitationResult:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        raise MembershipManagementNotFoundError

    if not _can_actor_invite_memberships(current_membership=current_membership):
        raise MembershipManagementForbiddenError

    if role not in {
        EstablishmentMembership.Role.STAFF,
        EstablishmentMembership.Role.MANAGER,
    }:
        raise MembershipInvitationRoleNotAllowedError

    if not _can_actor_invite_role(actor_role=current_membership.role, invited_role=role):
        raise MembershipInvitationRoleNotAllowedError

    establishment = Establishment.objects.select_related("organization").get(id=establishment_id)
    if establishment.status == Establishment.Status.DRAFT:
        if current_membership.role not in {
            EstablishmentMembership.Role.OWNER,
            EstablishmentMembership.Role.DIRECTOR,
        }:
            raise InvalidMembershipInvitationInputError(
                "Membership invitations on draft establishments require owner or director "
                "authority."
            )
    elif establishment.status != Establishment.Status.ACTIVE:
        raise InvalidMembershipInvitationInputError(
            "Membership invitations are only allowed for active establishments."
        )

    normalized_email = User.normalize_email_value(email)
    if normalized_email is None:
        raise InvalidMembershipInvitationInputError("A valid email is required.")

    normalized_first_name = first_name.strip()
    normalized_last_name = last_name.strip()
    if not normalized_first_name or not normalized_last_name:
        raise InvalidMembershipInvitationInputError("First and last name are required.")

    if not scopes:
        raise InvalidMembershipInvitationInputError(
            "At least one operational scope is required for staff and manager invitations."
        )

    normalized_scopes = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=scopes,
    )
    if (
        current_membership.role == EstablishmentMembership.Role.MANAGER
        and role == EstablishmentMembership.Role.STAFF
    ):
        _ensure_manager_scope_covers_invited_scopes(
            manager_membership=current_membership,
            resolved_invited_scopes=normalized_scopes,
        )

    existing_user = User.objects.filter(email__iexact=normalized_email).first()
    existing_membership = None
    if existing_user is not None:
        existing_membership = EstablishmentMembership.objects.filter(
            user=existing_user,
            establishment=establishment,
        ).first()

    if existing_membership is not None:
        if existing_membership.status in {
            EstablishmentMembership.Status.INVITED,
            EstablishmentMembership.Status.ACTIVE,
        }:
            raise DirectorInvitationDuplicateError

        if existing_membership.status == EstablishmentMembership.Status.DEACTIVATED:
            existing_membership.role = role
            existing_membership.status = EstablishmentMembership.Status.INVITED
            existing_membership.save(update_fields=["role", "status", "updated_at"])
            existing_user.first_name = normalized_first_name
            existing_user.last_name = normalized_last_name
            existing_user.save(update_fields=["first_name", "last_name", "updated_at"])
            assign_membership_scopes(
                membership=existing_membership,
                scope_inputs=scopes,
            )
            return _issue_establishment_invitation_for_membership(existing_membership)

        raise DirectorInvitationDuplicateError

    from houston.accounts.services import resolve_or_create_pending_user_for_invite

    user = resolve_or_create_pending_user_for_invite(
        email=normalized_email,
        first_name=normalized_first_name,
        last_name=normalized_last_name,
        existing_user=existing_user,
    )

    membership = _create_invited_membership(
        user=user,
        establishment=establishment,
        role=role,
    )

    assign_membership_scopes(membership=membership, scope_inputs=scopes)

    return _issue_establishment_invitation_for_membership(membership)


def _can_actor_manage_target_membership(
    *,
    actor_membership: EstablishmentMembership | None,
    target_membership: EstablishmentMembership,
) -> bool:
    if actor_membership is None:
        return False

    allowed_targets = _MANAGEABLE_TARGET_ROLES_BY_ACTOR.get(actor_membership.role)
    if allowed_targets is None:
        return False

    return target_membership.role in allowed_targets


def _can_actor_manage_target_role(
    *,
    actor_membership: EstablishmentMembership | None,
    target_role: str,
) -> bool:
    if actor_membership is None:
        return False

    allowed_targets = _MANAGEABLE_TARGET_ROLES_BY_ACTOR.get(actor_membership.role)
    if allowed_targets is None:
        return False

    return target_role in allowed_targets


def _can_actor_invite_role(*, actor_role: str, invited_role: str) -> bool:
    if invited_role not in {
        EstablishmentMembership.Role.STAFF,
        EstablishmentMembership.Role.MANAGER,
    }:
        return False

    allowed_targets = _MANAGEABLE_TARGET_ROLES_BY_ACTOR.get(actor_role)
    if allowed_targets is None:
        return False

    return invited_role in allowed_targets


def _can_actor_invite_memberships(
    *,
    current_membership: EstablishmentMembership,
) -> bool:
    return current_membership.role in _MANAGEABLE_TARGET_ROLES_BY_ACTOR


def _ensure_manager_scope_covers_invited_scopes(
    *,
    manager_membership: EstablishmentMembership,
    resolved_invited_scopes,
) -> None:
    for resolved_scope in resolved_invited_scopes:
        if not membership_scope_covers_business_unit(
            manager_membership,
            resolved_scope.business_unit,
        ):
            raise MembershipManagementForbiddenError


_MANAGEABLE_TARGET_ROLES_BY_ACTOR = {
    EstablishmentMembership.Role.OWNER: {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    },
    EstablishmentMembership.Role.DIRECTOR: {
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    },
    EstablishmentMembership.Role.MANAGER: {
        EstablishmentMembership.Role.STAFF,
    },
    EstablishmentMembership.Role.STAFF: set(),
}


def _issue_establishment_invitation_for_membership(
    membership: EstablishmentMembership,
) -> DirectorInvitationResult:
    _revoke_pending_invitations(membership=membership)
    raw_token, invitation = _create_establishment_invitation(membership=membership)
    return DirectorInvitationResult(
        membership=_reload_membership_for_response(membership.id),
        invitation_token=raw_token,
        invitation_expires_at=invitation.expires_at,
    )


def _revoke_pending_invitations(*, membership: EstablishmentMembership) -> None:
    now = timezone.now()
    EstablishmentInvitation.objects.filter(
        membership=membership,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=now, updated_at=now)


@transaction.atomic
def mark_onboarding_ready_for_activation(
    *,
    session: OnboardingSession,
    actor,
) -> dict:
    session = _lock_onboarding_session(session)
    _ensure_non_terminal_onboarding_session(session)

    access = get_onboarding_access_context(actor=actor, session=session)
    if not access.can_activate:
        raise OnboardingAccessDeniedError

    readiness = compute_activation_readiness(session=session)
    effective_can_activate = readiness["is_ready"] and access.can_activate
    if not effective_can_activate:
        raise OnboardingReadinessError(readiness)

    if session.status != OnboardingSession.Status.READY_FOR_ACTIVATION:
        session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = timezone.now()
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    return {
        "session": session,
        "readiness": readiness,
        "access": access,
        "effective_can_activate": effective_can_activate,
    }


@transaction.atomic
def activate_onboarding_session(
    *,
    session: OnboardingSession,
    actor,
) -> dict:
    session = _lock_onboarding_session(session)
    establishment = (
        Establishment.objects.select_for_update()
        .select_related("organization")
        .get(id=session.establishment_id)
    )
    session.establishment = establishment
    session.organization = establishment.organization

    if (
        session.status == OnboardingSession.Status.ACTIVATED
        and session.activated_at is not None
        and establishment.status == Establishment.Status.ACTIVE
    ):
        access = get_onboarding_access_context(actor=actor, session=session)
        if not access.can_manage:
            raise OnboardingAccessDeniedError

        readiness = compute_activation_readiness(session=session)
        return {
            "session": session,
            "readiness": readiness,
            "access": access,
            "effective_can_activate": False,
            "activated": False,
        }

    if OnboardingSession.is_terminal_status(session.status):
        raise InvalidOnboardingActivationStateError(
            "Terminal onboarding sessions cannot be activated."
        )

    access = get_onboarding_access_context(actor=actor, session=session)
    if not access.can_manage:
        raise OnboardingAccessDeniedError

    if establishment.status != Establishment.Status.DRAFT:
        raise InvalidOnboardingActivationStateError("Only draft establishments can be activated.")

    if session.status != OnboardingSession.Status.READY_FOR_ACTIVATION:
        raise InvalidOnboardingActivationStateError(
            "Onboarding session must be marked ready before activation."
        )

    if session.ready_for_activation_at is None:
        raise InvalidOnboardingActivationStateError(
            "Onboarding session must have a ready timestamp before activation."
        )

    readiness = compute_activation_readiness(session=session)
    effective_can_activate = readiness["is_ready"] and access.can_activate
    if not effective_can_activate:
        raise OnboardingReadinessError(readiness)

    now = timezone.now()
    establishment.status = Establishment.Status.ACTIVE
    establishment.chat_enabled = True
    establishment.save(update_fields=["status", "chat_enabled", "updated_at"])

    session.status = OnboardingSession.Status.ACTIVATED
    session.activated_at = now
    session.save(update_fields=["status", "activated_at", "updated_at"])

    return {
        "session": session,
        "readiness": readiness,
        "access": access,
        "effective_can_activate": True,
        "activated": True,
    }


@transaction.atomic
def update_membership_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    membership_id,
    update_input: MembershipUpdateInput,
) -> EstablishmentMembership:
    membership = get_membership_for_management(
        current_membership=current_membership,
        establishment_id=establishment_id,
        membership_id=membership_id,
    )
    if membership is None:
        raise MembershipManagementNotFoundError

    if not _can_actor_manage_target_membership(
        actor_membership=current_membership,
        target_membership=membership,
    ):
        raise MembershipManagementForbiddenError

    update_fields: list[str] = []

    if update_input.role is not None and membership.role != update_input.role:
        if not _can_actor_manage_target_role(
            actor_membership=current_membership,
            target_role=update_input.role,
        ):
            raise MembershipManagementForbiddenError

        if _would_demote_last_active_owner(
            membership=membership,
            next_role=update_input.role,
        ):
            raise CannotDemoteLastActiveOwnerError

        membership.role = update_input.role
        update_fields.append("role")

    if update_fields:
        membership.save(update_fields=[*update_fields, "updated_at"])

    effective_role = update_input.role if update_input.role is not None else membership.role

    if update_input.scopes is not None:
        if scopes_not_allowed_for_role(effective_role):
            raise InvalidMembershipScopeAssignmentError(
                "Operational scopes cannot be assigned to owner or director memberships."
            )
        if not update_input.scopes:
            raise InvalidMembershipScopeAssignmentError(
                "At least one operational scope is required for staff and manager memberships."
            )
        assign_membership_scopes(
            membership=membership,
            scope_inputs=update_input.scopes,
        )

    membership.refresh_from_db()
    return _reload_membership_for_response(membership.id)


@transaction.atomic
def deactivate_membership_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    membership_id,
) -> EstablishmentMembership:
    membership = get_membership_for_management(
        current_membership=current_membership,
        establishment_id=establishment_id,
        membership_id=membership_id,
    )
    if membership is None:
        raise MembershipManagementNotFoundError

    if not _can_actor_manage_target_membership(
        actor_membership=current_membership,
        target_membership=membership,
    ):
        raise MembershipManagementForbiddenError

    if (
        membership.status == EstablishmentMembership.Status.ACTIVE
        and membership.role == EstablishmentMembership.Role.OWNER
        and _is_last_active_owner(membership)
    ):
        raise CannotDeactivateLastActiveOwnerError

    if membership.status != EstablishmentMembership.Status.DEACTIVATED:
        membership.status = EstablishmentMembership.Status.DEACTIVATED
        membership.save(update_fields=["status", "updated_at"])

    from houston.chat.services import handle_membership_chat_deactivation

    handle_membership_chat_deactivation(membership=membership)

    _clear_selected_establishment_for_membership(membership)

    membership.refresh_from_db()
    return _reload_membership_for_response(membership.id)


def _lock_onboarding_session(session: OnboardingSession) -> OnboardingSession:
    return (
        OnboardingSession.objects.select_for_update()
        .select_related("organization", "establishment", "establishment__organization")
        .get(id=session.id)
    )


def _lock_onboarding_proposal(proposal: OnboardingProposal) -> OnboardingProposal:
    return (
        OnboardingProposal.objects.select_for_update()
        .select_related(
            "establishment",
            "establishment__organization",
            "onboarding_session",
            "onboarding_session__organization",
            "onboarding_session__establishment",
            "onboarding_session__establishment__organization",
        )
        .get(id=proposal.id)
    )


def _reload_onboarding_session(session: OnboardingSession) -> OnboardingSession:
    return OnboardingSession.objects.select_related(
        "organization",
        "establishment",
        "establishment__organization",
    ).get(id=session.id)


def _ensure_non_terminal_onboarding_session(session: OnboardingSession) -> None:
    if OnboardingSession.is_terminal_status(session.status):
        raise OnboardingSessionTerminalError


def _normalize_activity_description(description: str) -> str:
    if not isinstance(description, str):
        raise InvalidActivityDescriptionError("Activity description must be a string.")

    return description.strip()


def _set_status_after_description_submit(session: OnboardingSession) -> None:
    if session.status in {
        OnboardingSession.Status.STARTED,
        OnboardingSession.Status.DESCRIPTION_SUBMITTED,
    }:
        next_status = OnboardingSession.Status.DESCRIPTION_SUBMITTED
    elif session.status == OnboardingSession.Status.READY_FOR_ACTIVATION:
        next_status = OnboardingSession.Status.VALIDATING_SECTIONS
    else:
        next_status = OnboardingSession.Status.CONFIGURING_RUNTIME

    session.status = next_status
    if next_status != OnboardingSession.Status.READY_FOR_ACTIVATION:
        session.ready_for_activation_at = None
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])


def _activation_counts(session: OnboardingSession) -> dict:
    establishment_id = session.establishment_id
    owner_user_ids = _active_owner_user_ids(establishment_id=establishment_id)

    active_business_units_without_subjects_count = (
        BusinessUnit.objects.filter(
            establishment_id=establishment_id,
            active=True,
        )
        .annotate(
            active_subject_count=Count(
                "activity_subjects",
                filter=Q(activity_subjects__active=True),
            )
        )
        .filter(active_subject_count=0)
        .count()
    )

    return {
        "active_business_units_count": session.establishment.business_units.filter(
            active=True,
        ).count(),
        "active_activity_subjects_count": session.establishment.activity_subjects.filter(
            active=True,
        ).count(),
        "active_business_units_without_subjects_count": (
            active_business_units_without_subjects_count
        ),
        "active_owner_or_director_count": EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
            role__in=[
                EstablishmentMembership.Role.OWNER,
                EstablishmentMembership.Role.DIRECTOR,
            ],
        ).count(),
        "active_or_invited_director_count": EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            role=EstablishmentMembership.Role.DIRECTOR,
            status__in=[
                EstablishmentMembership.Status.ACTIVE,
                EstablishmentMembership.Status.INVITED,
            ],
        )
        .exclude(user_id__in=owner_user_ids)
        .count(),
    }


def _activation_blockers(
    *,
    session: OnboardingSession,
    counts: dict,
) -> list[dict]:
    blockers: list[dict] = []

    if OnboardingSession.is_terminal_status(session.status):
        blockers.append(_blocker("session_terminal"))

    if session.organization.status != Organization.Status.ACTIVE:
        blockers.append(_blocker("organization_not_active"))

    if session.establishment.status != Establishment.Status.DRAFT:
        blockers.append(_blocker("establishment_not_draft"))

    if counts["active_business_units_count"] < 1:
        blockers.append(_blocker("missing_active_business_unit"))

    business_units_without_subjects = counts["active_business_units_without_subjects_count"]
    if counts["active_business_units_count"] > 0 and business_units_without_subjects > 0:
        blockers.append(
            _blocker(
                "business_units_without_active_subjects",
                message=(
                    f"{business_units_without_subjects} active business unit(s) "
                    "have no active activity subjects"
                ),
            )
        )

    if counts["active_owner_or_director_count"] < 1:
        blockers.append(_blocker("missing_active_owner_or_director"))

    if counts["active_or_invited_director_count"] < 1:
        blockers.append(_blocker("missing_active_or_invited_director"))

    return blockers


def _blocker(code: str, *, message: str | None = None) -> dict:
    return {"code": code, "message": message or code.replace("_", " ")}


def _is_valid_activity_description(
    description: EstablishmentActivityDescription | None,
) -> bool:
    return (
        description is not None
        and description.validated_at is not None
        and len((description.description or "").strip()) >= ACTIVITY_DESCRIPTION_MIN_LENGTH
    )


def _serialize_organization(organization: Organization) -> dict:
    return {
        "id": str(organization.id),
        "name": organization.name,
        "status": organization.status,
    }


def _serialize_establishment(establishment: Establishment) -> dict:
    return {
        "id": str(establishment.id),
        "name": establishment.name,
        "status": establishment.status,
    }


def _serialize_activity_description(
    description: EstablishmentActivityDescription | None,
) -> dict | None:
    if description is None:
        return None

    return {
        "id": str(description.id),
        "description": description.description,
        "source": description.source,
        "submitted_by_id": (
            None if description.submitted_by_id is None else str(description.submitted_by_id)
        ),
        "validated_at": description.validated_at,
    }


def _serialize_keyed_runtime_item(item) -> dict:
    return {
        "id": str(item.id),
        "key": item.key,
        "label": item.label,
        "source": item.source,
        "active": item.active,
    }


def _is_last_active_owner(membership: EstablishmentMembership) -> bool:
    return (
        EstablishmentMembership.objects.filter(
            establishment=membership.establishment,
            status=EstablishmentMembership.Status.ACTIVE,
            role=EstablishmentMembership.Role.OWNER,
        )
        .exclude(id=membership.id)
        .count()
        == 0
    )


def _would_demote_last_active_owner(
    *,
    membership: EstablishmentMembership,
    next_role: str,
) -> bool:
    return (
        membership.status == EstablishmentMembership.Status.ACTIVE
        and membership.role == EstablishmentMembership.Role.OWNER
        and next_role != EstablishmentMembership.Role.OWNER
        and _is_last_active_owner(membership)
    )


def _clear_selected_establishment_for_membership(
    membership: EstablishmentMembership,
) -> None:
    UserSession.objects.filter(
        user=membership.user,
        selected_establishment=membership.establishment,
    ).update(
        selected_establishment=None,
        updated_at=timezone.now(),
    )


def _active_owner_user_ids(*, establishment_id) -> set:
    return set(
        EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
        ).values_list("user_id", flat=True)
    )


def _count_non_owner_directors(
    *,
    establishment_id,
    owner_user_ids: set | None = None,
) -> int:
    if owner_user_ids is None:
        owner_user_ids = _active_owner_user_ids(establishment_id=establishment_id)

    return (
        EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            role=EstablishmentMembership.Role.DIRECTOR,
            status__in=[
                EstablishmentMembership.Status.INVITED,
                EstablishmentMembership.Status.ACTIVE,
            ],
        )
        .exclude(user_id__in=owner_user_ids)
        .count()
    )


def _create_invited_membership(
    *,
    user: User,
    establishment: Establishment,
    role: str,
    owner_user_ids: set | None = None,
) -> EstablishmentMembership:
    try:
        with transaction.atomic():
            return EstablishmentMembership.objects.create(
                user=user,
                establishment=establishment,
                role=role,
                status=EstablishmentMembership.Status.INVITED,
            )
    except IntegrityError as exc:
        existing_membership = EstablishmentMembership.objects.filter(
            user=user,
            establishment=establishment,
        ).first()
        if existing_membership is not None:
            if existing_membership.status in {
                EstablishmentMembership.Status.INVITED,
                EstablishmentMembership.Status.ACTIVE,
            }:
                raise DirectorInvitationDuplicateError from exc

        if role == EstablishmentMembership.Role.DIRECTOR:
            if (
                _count_non_owner_directors(
                    establishment_id=establishment.id,
                    owner_user_ids=owner_user_ids,
                )
                >= 1
            ):
                raise DirectorInvitationAlreadyExistsError from exc

        raise


def _reload_membership_for_response(membership_id) -> EstablishmentMembership:
    return (
        EstablishmentMembership.objects.select_related(
            "user",
            "establishment",
            "establishment__organization",
        )
        .prefetch_related("scope_links__business_unit")
        .get(id=membership_id)
    )


def _issue_director_invitation_for_membership(
    membership: EstablishmentMembership,
) -> DirectorInvitationResult:
    return _issue_establishment_invitation_for_membership(membership)


def _revoke_pending_director_invitations(*, membership: EstablishmentMembership) -> None:
    _revoke_pending_invitations(membership=membership)


def _create_establishment_invitation(
    *,
    membership: EstablishmentMembership,
) -> tuple[str, EstablishmentInvitation]:
    expires_at = timezone.now() + settings.HOUSTON_DIRECTOR_INVITATION_TTL

    for _ in range(settings.HOUSTON_AUTH_TOKEN_GENERATION_MAX_ATTEMPTS):
        raw_token = auth_tokens.generate_raw_token()
        token_digest = auth_tokens.digest_token(raw_token)

        try:
            with transaction.atomic():
                invitation = EstablishmentInvitation.objects.create(
                    membership=membership,
                    token_digest=token_digest,
                    expires_at=expires_at,
                )
                return raw_token, invitation
        except IntegrityError:
            continue

    raise RuntimeError("Unable to generate a unique establishment invitation token digest.")


def _get_establishment_for_runtime_mutation(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
) -> Establishment:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        raise RuntimeConfigNotFoundError

    establishment = current_membership.establishment
    if establishment.status != Establishment.Status.ACTIVE:
        raise RuntimeConfigNotFoundError

    return establishment


@transaction.atomic
def create_runtime_business_unit(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    label: str,
    description: str = "",
    unit_type: str = BusinessUnit.UnitType.DEDICATED,
    catalog_key: str | None = None,
) -> BusinessUnit:
    establishment = _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )

    normalized_label = label.strip()
    if not normalized_label:
        raise ValidationError({"label": ["Label is required."]})

    runtime_key = slugify_label(normalized_label)
    if not runtime_key:
        raise ValidationError({"label": ["Label must produce a valid runtime key."]})

    catalog_bu = None
    if catalog_key:
        catalog_bu = CatalogBusinessUnit.objects.filter(key=catalog_key, active=True).first()

    source = BusinessUnit.Source.CATALOG_SUGGESTION if catalog_key else BusinessUnit.Source.MANUAL

    business_unit, _created = BusinessUnit.objects.update_or_create(
        establishment=establishment,
        key=runtime_key,
        defaults={
            "label": normalized_label,
            "description": description.strip(),
            "unit_type": unit_type,
            "catalog_business_unit": catalog_bu,
            "source": source,
            "active": True,
            "managed_by_onboarding_proposal": None,
        },
    )
    return business_unit


@transaction.atomic
def update_runtime_business_unit(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    business_unit_id,
    label: str | None = None,
    description: str | None = None,
    unit_type: str | None = None,
) -> BusinessUnit:
    establishment = _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )

    business_unit = (
        BusinessUnit.objects.select_for_update()
        .filter(
            id=business_unit_id,
            establishment_id=establishment.id,
            active=True,
        )
        .first()
    )
    if business_unit is None:
        raise RuntimeConfigNotFoundError

    update_fields: list[str] = []

    if label is not None:
        normalized_label = label.strip()
        if not normalized_label:
            raise ValidationError({"label": ["Label is required."]})

        runtime_key = slugify_label(normalized_label)
        if not runtime_key:
            raise ValidationError({"label": ["Label must produce a valid runtime key."]})

        if runtime_key != business_unit.key:
            if (
                BusinessUnit.objects.filter(
                    establishment=establishment,
                    key=runtime_key,
                )
                .exclude(id=business_unit.id)
                .exists()
            ):
                raise RuntimeConfigConflictError(
                    code="duplicate_business_unit_key",
                    detail="A business unit with this label already exists.",
                )
            business_unit.key = runtime_key

        business_unit.label = normalized_label
        update_fields.extend(["label", "key"])

    if description is not None:
        business_unit.description = description.strip()
        update_fields.append("description")

    if unit_type is not None:
        business_unit.unit_type = unit_type
        update_fields.append("unit_type")

    if update_fields:
        business_unit.save(update_fields=[*update_fields, "updated_at"])

    return business_unit


@transaction.atomic
def deactivate_runtime_business_unit(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    business_unit_id,
) -> BusinessUnit:
    establishment = _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )

    business_unit = (
        BusinessUnit.objects.select_for_update()
        .filter(
            id=business_unit_id,
            establishment_id=establishment.id,
            active=True,
        )
        .first()
    )
    if business_unit is None:
        raise RuntimeConfigNotFoundError

    active_business_unit_count = BusinessUnit.objects.filter(
        establishment=establishment,
        active=True,
    ).count()
    if active_business_unit_count <= 1:
        raise RuntimeConfigConflictError(
            code="last_active_business_unit",
            detail="At least one active business unit must remain.",
        )

    if business_unit_has_active_membership_scopes(business_unit=business_unit):
        raise RuntimeConfigConflictError(
            code="business_unit_has_membership_scopes",
            detail="Remove active membership scopes before deactivating this business unit.",
        )

    now = timezone.now()
    business_unit.active = False
    business_unit.save(update_fields=["active", "updated_at"])
    ActivitySubject.objects.filter(
        establishment=establishment,
        business_unit=business_unit,
        active=True,
    ).update(active=False, updated_at=now)
    return business_unit


@transaction.atomic
def create_runtime_activity_subject(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    business_unit_id,
    label: str,
    description: str = "",
    catalog_key: str | None = None,
) -> ActivitySubject:
    establishment = _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )

    business_unit = BusinessUnit.objects.filter(
        id=business_unit_id,
        establishment_id=establishment.id,
        active=True,
    ).first()
    if business_unit is None:
        raise RuntimeConfigNotFoundError

    normalized_label = label.strip()
    if not normalized_label:
        raise ValidationError({"label": ["Label is required."]})

    normalized_name = normalize_activity_subject_name(normalized_label)
    if not normalized_name:
        raise ValidationError({"label": ["Label must produce a valid subject name."]})

    catalog_as = None
    if catalog_key:
        catalog_as = CatalogActivitySubject.objects.filter(key=catalog_key, active=True).first()

    source = (
        ActivitySubject.Source.CATALOG_SUGGESTION if catalog_key else ActivitySubject.Source.MANUAL
    )

    activity_subject, _created = ActivitySubject.objects.update_or_create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name=normalized_name,
        defaults={
            "label": normalized_label,
            "description": description.strip(),
            "catalog_activity_subject": catalog_as,
            "source": source,
            "active": True,
            "managed_by_onboarding_proposal": None,
        },
    )
    return activity_subject


@transaction.atomic
def deactivate_runtime_activity_subject(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    activity_subject_id,
) -> ActivitySubject:
    establishment = _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )

    activity_subject = (
        ActivitySubject.objects.select_for_update()
        .filter(
            id=activity_subject_id,
            establishment_id=establishment.id,
            active=True,
        )
        .select_related("business_unit")
        .first()
    )
    if activity_subject is None:
        raise RuntimeConfigNotFoundError

    active_subject_count = ActivitySubject.objects.filter(
        business_unit=activity_subject.business_unit,
        active=True,
    ).count()
    if active_subject_count <= 1:
        raise RuntimeConfigConflictError(
            code="last_active_activity_subject",
            detail="Each active business unit must keep at least one active activity subject.",
        )

    activity_subject.active = False
    activity_subject.save(update_fields=["active", "updated_at"])
    return activity_subject
