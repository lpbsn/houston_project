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
from houston.core.exceptions import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from houston.establishments.access import get_onboarding_access_context
from houston.establishments.business_unit_domain_service import (
    create_onboarding_business_unit,
)
from houston.establishments.business_unit_domain_service import (
    create_runtime_activity_subject as create_runtime_activity_subject_domain,
)
from houston.establishments.business_unit_domain_service import (
    create_runtime_business_unit as create_runtime_business_unit_domain,
)
from houston.establishments.business_unit_domain_service import (
    reactivate_activity_subject as reactivate_activity_subject_domain,
)
from houston.establishments.business_unit_domain_service import (
    reactivate_business_unit as reactivate_business_unit_domain,
)
from houston.establishments.business_unit_domain_service import (
    update_business_unit as update_business_unit_domain,
)
from houston.establishments.business_unit_identity import (
    normalize_generic_activity_subject_name,
)
from houston.establishments.membership_scope import (
    InvalidMembershipScopeAssignmentError,
    MembershipScopeInput,
    assign_membership_scopes,
    membership_business_unit_scope_ids,
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
    MembershipScope,
    OnboardingProposal,
    OnboardingSession,
)
from houston.establishments.selectors import (
    business_unit_has_active_membership_scopes,
    get_membership_for_management,
    get_runtime_config_for_session,
    org_establishments_draft_active,
)
from houston.establishments.taxonomy_normalization import (
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


class MembershipRoleChangeForbiddenError(Exception):
    pass


class InvitedMembershipActivationError(Exception):
    pass


class InvalidMembershipInvitationInputError(Exception):
    pass


class MembershipInvitationRoleNotAllowedError(Exception):
    pass


class MembershipInvitationUserExistsError(Exception):
    """Invite refused because a Houston account already exists for this email."""

    def __init__(self, detail: str = "A Houston account with this email already exists."):
        self.detail = detail
        super().__init__(detail)


class MembershipInvitationOwnerConflictError(Exception):
    """Invite refused because a non-owner membership blocks owner fan-out."""

    def __init__(
        self,
        detail: str = "This invitation conflicts with an existing non-owner membership.",
    ):
        self.detail = detail
        super().__init__(detail)


class OrganizationalOwnerInvariantConflictError(Exception):
    """Organizational owner coverage or actor invariant is inconsistent."""

    def __init__(
        self,
        detail: str = "Organizational owner coverage is inconsistent.",
    ):
        self.detail = detail
        super().__init__(detail)


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


# Product: Onboarding manuel — schema onboarding_proposal_v4 (v3 rejected at runtime)
PROPOSAL_SCHEMA_VERSION_V3_BU = "onboarding_proposal_v3"
PROPOSAL_SCHEMA_VERSION_V4_BU = "onboarding_proposal_v4"
PROPOSAL_V4_BU_REQUIRED_SECTIONS = frozenset(
    {
        "business_units",
        "activity_subjects",
    }
)
PROPOSAL_V4_BU_SECTION_CAPS = {
    "business_units": 50,
    "activity_subjects": 500,
}
PROPOSAL_V4_BU_BUSINESS_UNIT_FIELDS = frozenset(
    {
        "client_key",
        "catalog_key",
        "specific_name",
        "instance_description",
    }
)
PROPOSAL_V4_BU_ACTIVITY_SUBJECT_FIELDS = frozenset(
    {
        "client_key",
        "business_unit_client_key",
        "catalog_key",
        "label",
        "description",
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
        raise OnboardingProposalValidationError(
            [_proposal_error("unsupported_schema_version", field="schema_version")]
        )
    if schema_version == PROPOSAL_SCHEMA_VERSION_V4_BU:
        return _validate_onboarding_proposal_payload_v4_bu(payload, mode=mode)

    raise OnboardingProposalValidationError(
        [_proposal_error("unsupported_schema_version", field="schema_version")]
    )


def _validate_onboarding_proposal_payload_v4_bu(payload: dict, *, mode: str) -> dict:
    errors: list[dict] = []

    for section in PROPOSAL_V4_BU_REQUIRED_SECTIONS:
        if section not in payload:
            errors.append(_proposal_error("missing_required_section", section=section))

    for section in payload:
        if section != "schema_version" and section not in PROPOSAL_V4_BU_REQUIRED_SECTIONS:
            errors.append(_proposal_error("unknown_section", section=section))

    raw_business_units = _section_items_v4_bu(payload, "business_units", errors)
    raw_activity_subjects = _section_items_v4_bu(payload, "activity_subjects", errors)
    catalog_keys = _active_business_unit_catalog_keys()
    catalog_unit_types = dict(
        CatalogBusinessUnit.objects.filter(active=True).values_list("key", "unit_type")
    )
    catalog_subject_labels = dict(
        CatalogActivitySubject.objects.filter(active=True).values_list("key", "label")
    )

    business_units, seen_client_keys = _validate_business_unit_section_v4(
        items=raw_business_units,
        catalog_keys=catalog_keys["business_units"],
        catalog_unit_types=catalog_unit_types,
        errors=errors,
    )
    business_unit_client_keys = {item["client_key"] for item in business_units}
    activity_subjects = _validate_activity_subject_section_v4(
        items=raw_activity_subjects,
        business_unit_client_keys=business_unit_client_keys,
        catalog_keys=catalog_keys["activity_subjects"],
        catalog_subject_labels=catalog_subject_labels,
        seen_client_keys=seen_client_keys,
        errors=errors,
    )
    business_unit_catalog_by_client_key = {
        item["client_key"]: item["catalog_key"] for item in business_units
    }
    subject_catalog_parent_by_key = dict(
        CatalogActivitySubject.objects.filter(
            key__in={
                item["catalog_key"]
                for item in activity_subjects
                if item["catalog_key"] is not None
            },
            active=True,
        ).values_list("key", "catalog_business_unit__key")
    )
    for subject in activity_subjects:
        catalog_key = subject["catalog_key"]
        if catalog_key is None:
            continue
        expected_parent_key = business_unit_catalog_by_client_key.get(
            subject["business_unit_client_key"]
        )
        if subject_catalog_parent_by_key.get(catalog_key) != expected_parent_key:
            errors.append(
                _proposal_error(
                    "catalog_subject_business_unit_mismatch",
                    section="activity_subjects",
                    key=subject["client_key"],
                    field="catalog_key",
                )
            )

    if not business_units:
        errors.append(_proposal_error("insufficient_business_units"))

    if mode == PROPOSAL_VALIDATION_MODE_FINAL:
        subjects_by_bu_client_key: dict[str, int] = {}
        for subject in activity_subjects:
            client_key = subject["business_unit_client_key"]
            subjects_by_bu_client_key[client_key] = (
                subjects_by_bu_client_key.get(client_key, 0) + 1
            )
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

    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION_V4_BU,
        "business_units": business_units,
        "activity_subjects": activity_subjects,
    }


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

    if payload.get("schema_version") != PROPOSAL_SCHEMA_VERSION_V4_BU:
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
    schema_version = payload["schema_version"]
    if schema_version != PROPOSAL_SCHEMA_VERSION_V4_BU:
        raise OnboardingProposalValidationError(
            [_proposal_error("unsupported_schema_version", field="schema_version")]
        )

    proposal.payload = payload
    proposal.section_validation = {
        section: PROPOSAL_SECTION_ACCEPTED for section in PROPOSAL_V4_BU_REQUIRED_SECTIONS
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

    schema_version = payload["schema_version"]
    if schema_version != PROPOSAL_SCHEMA_VERSION_V4_BU:
        raise OnboardingProposalValidationError(
            [_proposal_error("unsupported_schema_version", field="schema_version")]
        )
    bu_keys = apply_onboarding_proposal_v4(
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
        "schema_version": PROPOSAL_SCHEMA_VERSION_V4_BU,
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


def _section_items_v4_bu(payload: dict, section: str, errors: list[dict]) -> list:
    items = payload.get(section, [])
    if not isinstance(items, list):
        errors.append(_proposal_error("section_must_be_array", section=section))
        return []
    if len(items) > PROPOSAL_V4_BU_SECTION_CAPS[section]:
        errors.append(_proposal_error("section_cap_exceeded", section=section))
        return items[: PROPOSAL_V4_BU_SECTION_CAPS[section]]
    return items


def _validate_business_unit_section_v4(
    *,
    items: list,
    catalog_keys: set[str],
    catalog_unit_types: dict[str, str],
    errors: list[dict],
) -> tuple[list[dict], set[str]]:
    sanitized: list[dict] = []
    seen_client_keys: set[str] = set()
    seen_specific_names: set[str] = set()
    seen_transversal_catalog_keys: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            errors.append(_proposal_error("invalid_payload_type", section="business_units"))
            continue

        for field in item.keys() - PROPOSAL_V4_BU_BUSINESS_UNIT_FIELDS:
            errors.append(
                _proposal_error(
                    "unknown_field",
                    section="business_units",
                    field=field,
                )
            )

        client_key = _normalized_string(item.get("client_key"))
        catalog_key = _normalized_string(item.get("catalog_key"))
        specific_name = _normalized_string(item.get("specific_name"))
        instance_description = _normalized_string(item.get("instance_description"))

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
        seen_client_keys.add(client_key)

        if not catalog_key:
            errors.append(
                _proposal_error(
                    "missing_catalog_key",
                    section="business_units",
                    key=client_key,
                    field="catalog_key",
                )
            )
            continue
        if catalog_key not in catalog_keys:
            errors.append(
                _proposal_error(
                    "unknown_catalog_key",
                    section="business_units",
                    key=catalog_key,
                )
            )
            continue
        if (
            catalog_unit_types.get(catalog_key)
            == CatalogBusinessUnit.DefaultUnitType.TRANSVERSAL
        ):
            if catalog_key in seen_transversal_catalog_keys:
                errors.append(
                    _proposal_error(
                        "duplicate_transversal_catalog_instance",
                        section="business_units",
                        key=client_key,
                        field="catalog_key",
                    )
                )
                continue
            seen_transversal_catalog_keys.add(catalog_key)
        if not specific_name:
            errors.append(
                _proposal_error(
                    "missing_business_unit_specific_name",
                    section="business_units",
                    key=client_key,
                    field="specific_name",
                )
            )
            continue

        normalized_specific_name = slugify_label(specific_name)
        if not normalized_specific_name:
            errors.append(
                _proposal_error(
                    "invalid_normalized_name",
                    section="business_units",
                    key=client_key,
                    field="specific_name",
                )
            )
            continue
        if normalized_specific_name in seen_specific_names:
            errors.append(
                _proposal_error(
                    "duplicate_business_unit_key",
                    section="business_units",
                    key=client_key,
                )
            )
            continue
        seen_specific_names.add(normalized_specific_name)
        sanitized.append(
            {
                "client_key": client_key,
                "catalog_key": catalog_key,
                "specific_name": specific_name,
                "instance_description": instance_description,
            }
        )

    return sanitized, seen_client_keys


def _validate_activity_subject_section_v4(
    *,
    items: list,
    business_unit_client_keys: set[str],
    catalog_keys: set[str],
    catalog_subject_labels: dict[str, str],
    seen_client_keys: set[str],
    errors: list[dict],
) -> list[dict]:
    sanitized: list[dict] = []
    seen_normalized_names_by_bu: dict[str, set[str]] = {}

    for item in items:
        if not isinstance(item, dict):
            errors.append(_proposal_error("invalid_payload_type", section="activity_subjects"))
            continue

        for field in item.keys() - PROPOSAL_V4_BU_ACTIVITY_SUBJECT_FIELDS:
            errors.append(
                _proposal_error(
                    "unknown_field",
                    section="activity_subjects",
                    field=field,
                )
            )

        client_key = _normalized_string(item.get("client_key"))
        business_unit_client_key = _normalized_string(item.get("business_unit_client_key"))
        catalog_key = _nullable_normalized_string(item.get("catalog_key"))
        label = _nullable_normalized_string(item.get("label"))
        description = _normalized_string(item.get("description"))

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
        seen_client_keys.add(client_key)

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
        if (catalog_key is None) == (label is None):
            errors.append(
                _proposal_error(
                    "activity_subject_catalog_key_or_label_required",
                    section="activity_subjects",
                    key=client_key,
                )
            )
            continue
        if catalog_key is not None:
            if catalog_key not in catalog_keys:
                errors.append(
                    _proposal_error(
                        "unknown_catalog_key",
                        section="activity_subjects",
                        key=catalog_key,
                    )
                )
                continue
            catalog_label = catalog_subject_labels.get(catalog_key)
            if not catalog_label:
                errors.append(
                    _proposal_error(
                        "unknown_catalog_key",
                        section="activity_subjects",
                        key=catalog_key,
                    )
                )
                continue
            normalized_name = normalize_generic_activity_subject_name(catalog_label)
        else:
            normalized_name = slugify_label(label or "")
        if not normalized_name:
            errors.append(
                _proposal_error(
                    "invalid_free_activity_subject_label",
                    section="activity_subjects",
                    key=client_key,
                    field="label",
                )
            )
            continue
        seen_normalized_names = seen_normalized_names_by_bu.setdefault(
            business_unit_client_key,
            set(),
        )
        if normalized_name in seen_normalized_names:
            errors.append(
                _proposal_error(
                    "duplicate_activity_subject",
                    section="activity_subjects",
                    key=client_key,
                )
            )
            continue
        seen_normalized_names.add(normalized_name)

        sanitized_item = {
            "client_key": client_key,
            "business_unit_client_key": business_unit_client_key,
            "catalog_key": catalog_key,
        }
        if label is not None:
            sanitized_item["label"] = label
            sanitized_item["description"] = description
        sanitized.append(sanitized_item)

    return sanitized


def apply_onboarding_proposal_v4(
    *,
    establishment: Establishment,
    payload: dict,
    proposal: OnboardingProposal,
) -> set[str]:
    if payload.get("schema_version") != PROPOSAL_SCHEMA_VERSION_V4_BU:
        raise OnboardingProposalValidationError(
            [_proposal_error("unsupported_schema_version", field="schema_version")]
        )

    catalog_keys = {item["catalog_key"] for item in payload["business_units"]}
    catalog_business_units = {
        row.key: row
        for row in CatalogBusinessUnit.objects.filter(
            key__in=catalog_keys,
            active=True,
        )
    }
    subjects_by_business_unit: dict[str, list[dict]] = {}
    for subject in payload["activity_subjects"]:
        subjects_by_business_unit.setdefault(
            subject["business_unit_client_key"],
            [],
        ).append(subject)

    routing_keys: set[str] = set()
    for item in payload["business_units"]:
        catalog_business_unit = catalog_business_units.get(item["catalog_key"])
        if catalog_business_unit is None:
            raise OnboardingProposalValidationError(
                [
                    _proposal_error(
                        "unknown_catalog_key",
                        section="business_units",
                        key=item["catalog_key"],
                    )
                ]
            )

        selected_subjects = subjects_by_business_unit.get(item["client_key"], [])
        generic_activity_subject_keys = [
            subject["catalog_key"]
            for subject in selected_subjects
            if subject["catalog_key"] is not None
        ]
        free_activity_subjects = [
            {
                "label": subject["label"],
                "description": subject.get("description", ""),
            }
            for subject in selected_subjects
            if subject["catalog_key"] is None
        ]
        business_unit = create_onboarding_business_unit(
            establishment=establishment,
            catalog_business_unit=catalog_business_unit,
            specific_name=item["specific_name"],
            instance_description=item["instance_description"],
            generic_activity_subject_keys=generic_activity_subject_keys,
            free_activity_subjects=free_activity_subjects,
            managed_by_onboarding_proposal=proposal,
        )
        routing_keys.add(business_unit.routing_key)

    return routing_keys


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

    # 1) Owner email forbidden first.
    if User.objects.filter(id__in=owner_user_ids, email__iexact=normalized_email).exists():
        raise DirectorInvitationOwnerNotAllowedError

    existing_user = User.objects.filter(email__iexact=normalized_email).first()
    if existing_user is not None and existing_user.id in owner_user_ids:
        raise DirectorInvitationOwnerNotAllowedError

    # 2) Soft director slot occupied next (before User/Membership matrix).
    if (
        _count_non_owner_directors(
            establishment_id=establishment.id,
            owner_user_ids=owner_user_ids,
        )
        >= 1
    ):
        raise DirectorInvitationAlreadyExistsError

    existing_membership = None
    if existing_user is not None:
        existing_membership = EstablishmentMembership.objects.filter(
            user=existing_user,
            establishment=establishment,
        ).first()

    # 3) User/Membership matrix after owner + slot guards.
    from houston.establishments.invite_eligibility import (
        InviteTargetDecision,
        evaluate_invite_target,
    )

    decision = evaluate_invite_target(
        user=existing_user,
        membership=existing_membership,
        invited_role=EstablishmentMembership.Role.DIRECTOR,
    )
    if decision == InviteTargetDecision.USER_EXISTS:
        raise MembershipInvitationUserExistsError
    if decision == InviteTargetDecision.DUPLICATE:
        raise DirectorInvitationDuplicateError

    if decision == InviteTargetDecision.RESUME_DEACTIVATED:
        assert existing_membership is not None
        assert existing_user is not None
        existing_membership.status = EstablishmentMembership.Status.INVITED
        existing_membership.save(update_fields=["status", "updated_at"])
        existing_user.first_name = normalized_first_name
        existing_user.last_name = normalized_last_name
        existing_user.save(update_fields=["first_name", "last_name", "updated_at"])
        return _issue_director_invitation_for_membership(existing_membership)

    from houston.accounts.services import (
        PendingInviteUserAlreadyExistsError,
        create_pending_user_for_invite,
    )

    try:
        user = create_pending_user_for_invite(
            email=normalized_email,
            first_name=normalized_first_name,
            last_name=normalized_last_name,
        )
    except PendingInviteUserAlreadyExistsError as exc:
        raise MembershipInvitationUserExistsError from exc

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

    invitation = (
        EstablishmentInvitation.objects.select_related(
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

    if invitation.membership.role == EstablishmentMembership.Role.OWNER:
        return _accept_organizational_owner_invitation(
            request=request,
            raw_token=raw_token,
            password=password,
        )

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

    now = timezone.now()

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


@transaction.atomic
def _accept_organizational_owner_invitation(
    *,
    request: HttpRequest,
    raw_token: str,
    password: str,
) -> DirectorInvitationAcceptResult:
    token_digest = auth_tokens.digest_token(raw_token.strip())

    invitation = (
        EstablishmentInvitation.objects.select_related(
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

    membership = invitation.membership
    if membership.role != EstablishmentMembership.Role.OWNER:
        raise InvalidEstablishmentInvitationError

    organization_id = membership.establishment.organization_id
    anchor_membership_id = membership.id
    user_id = membership.user_id
    invitation_id = invitation.id

    establishment_ids = list(
        Establishment.objects.filter(
            organization_id=organization_id,
            status__in=[
                Establishment.Status.DRAFT,
                Establishment.Status.ACTIVE,
            ],
        )
        .order_by("id")
        .values_list("id", flat=True)
    )
    membership_ids = list(
        EstablishmentMembership.objects.filter(
            user_id=user_id,
            establishment_id__in=establishment_ids,
        ).values_list("id", flat=True)
    )
    pending_invitation_ids = list(
        EstablishmentInvitation.objects.filter(
            membership_id__in=membership_ids,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        ).values_list("id", flat=True)
    )

    organization = _lock_organization(organization_id=organization_id)
    other_membership_ids = [
        membership_id
        for membership_id in membership_ids
        if membership_id != anchor_membership_id
    ]
    locked = _lock_memberships_for_owner_workflow(
        actor_membership_id=None,
        anchor_membership_id=anchor_membership_id,
        other_membership_ids=other_membership_ids,
    )
    _lock_invitations_for_owner_workflow(invitation_ids=pending_invitation_ids)

    invitation = (
        EstablishmentInvitation.objects.select_related(
            "membership",
            "membership__user",
            "membership__establishment",
            "membership__establishment__organization",
        )
        .filter(id=invitation_id)
        .first()
    )
    if invitation is None:
        raise InvalidEstablishmentInvitationError

    membership = locked["anchor"]
    if membership is None:
        raise InvalidEstablishmentInvitationError

    user = membership.user
    now = timezone.now()

    if organization.status != Organization.Status.ACTIVE:
        raise InvalidEstablishmentInvitationError
    if membership.establishment.organization_id != organization_id:
        raise InvalidEstablishmentInvitationError
    if membership.establishment.status != Establishment.Status.ACTIVE:
        raise InvalidEstablishmentInvitationError
    if invitation.accepted_at is not None:
        raise EstablishmentInvitationAlreadyAcceptedError
    if invitation.revoked_at is not None:
        raise InvalidEstablishmentInvitationError
    if invitation.expires_at <= now:
        raise EstablishmentInvitationExpiredError
    if (
        membership.role != EstablishmentMembership.Role.OWNER
        or membership.status != EstablishmentMembership.Status.INVITED
    ):
        raise InvalidEstablishmentInvitationError
    if user.status != User.Status.PENDING:
        raise InvalidEstablishmentInvitationError

    establishments = org_establishments_draft_active(organization_id=organization_id)
    memberships_by_establishment_id = {
        row.establishment_id: row
        for row in EstablishmentMembership.objects.filter(
            user_id=user.id,
            establishment_id__in=[establishment.id for establishment in establishments],
        )
    }
    memberships_to_activate: list[EstablishmentMembership] = []
    for establishment in establishments:
        target = memberships_by_establishment_id.get(establishment.id)
        if target is None:
            raise OrganizationalOwnerInvariantConflictError
        if target.role != EstablishmentMembership.Role.OWNER:
            raise OrganizationalOwnerInvariantConflictError
        if target.status == EstablishmentMembership.Status.ACTIVE:
            raise OrganizationalOwnerInvariantConflictError
        if target.status != EstablishmentMembership.Status.INVITED:
            raise OrganizationalOwnerInvariantConflictError
        memberships_to_activate.append(target)

    user.set_password(password)
    user.status = User.Status.ACTIVE
    user.save(update_fields=["password", "status", "updated_at"])

    for target in memberships_to_activate:
        target.status = EstablishmentMembership.Status.ACTIVE
        target.save(update_fields=["status", "updated_at"])

    invitation.accepted_at = now
    invitation.save(update_fields=["accepted_at", "updated_at"])

    EstablishmentInvitation.objects.filter(
        membership_id__in=[target.id for target in memberships_to_activate],
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    ).exclude(id=invitation.id).update(revoked_at=now, updated_at=now)

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
        EstablishmentMembership.Role.OWNER,
    }:
        raise MembershipInvitationRoleNotAllowedError

    if not _can_actor_invite_role(actor_role=current_membership.role, invited_role=role):
        raise MembershipInvitationRoleNotAllowedError

    establishment = Establishment.objects.select_related("organization").get(id=establishment_id)

    normalized_email = User.normalize_email_value(email)
    if normalized_email is None:
        raise InvalidMembershipInvitationInputError("A valid email is required.")

    normalized_first_name = first_name.strip()
    normalized_last_name = last_name.strip()
    if not normalized_first_name or not normalized_last_name:
        raise InvalidMembershipInvitationInputError("First and last name are required.")

    scope_inputs = scopes or []
    if scopes_not_allowed_for_role(role):
        if scope_inputs:
            raise InvalidMembershipInvitationInputError(
                "Operational scopes cannot be assigned to owner or director invitations."
            )
    elif not scope_inputs:
        raise InvalidMembershipInvitationInputError(
            "At least one operational scope is required for staff and manager invitations."
        )

    if role == EstablishmentMembership.Role.OWNER:
        if establishment.status != Establishment.Status.ACTIVE:
            raise InvalidMembershipInvitationInputError(
                "Owner invitations are only allowed for active establishments."
            )
        return _invite_organizational_owner(
            current_membership=current_membership,
            establishment=establishment,
            email=normalized_email,
            first_name=normalized_first_name,
            last_name=normalized_last_name,
        )

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

    normalized_scopes = (
        normalize_membership_scope_inputs(
            establishment=establishment,
            scope_inputs=scope_inputs,
        )
        if scope_inputs
        else []
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

    from houston.establishments.invite_eligibility import (
        InviteTargetDecision,
        evaluate_invite_target,
    )

    decision = evaluate_invite_target(
        user=existing_user,
        membership=existing_membership,
        invited_role=role,
    )
    if decision == InviteTargetDecision.USER_EXISTS:
        raise MembershipInvitationUserExistsError
    if decision == InviteTargetDecision.DUPLICATE:
        raise DirectorInvitationDuplicateError

    if decision == InviteTargetDecision.RESUME_DEACTIVATED:
        assert existing_membership is not None
        assert existing_user is not None
        existing_membership.status = EstablishmentMembership.Status.INVITED
        existing_membership.save(update_fields=["status", "updated_at"])
        existing_user.first_name = normalized_first_name
        existing_user.last_name = normalized_last_name
        existing_user.save(update_fields=["first_name", "last_name", "updated_at"])
        if scope_inputs:
            assign_membership_scopes(
                membership=existing_membership,
                scope_inputs=scope_inputs,
            )
        return _issue_establishment_invitation_for_membership(existing_membership)

    from houston.accounts.services import (
        PendingInviteUserAlreadyExistsError,
        create_pending_user_for_invite,
    )

    try:
        user = create_pending_user_for_invite(
            email=normalized_email,
            first_name=normalized_first_name,
            last_name=normalized_last_name,
        )
    except PendingInviteUserAlreadyExistsError as exc:
        raise MembershipInvitationUserExistsError from exc

    membership = _create_invited_membership(
        user=user,
        establishment=establishment,
        role=role,
    )

    if scope_inputs:
        assign_membership_scopes(membership=membership, scope_inputs=scope_inputs)

    return _issue_establishment_invitation_for_membership(membership)


def _invite_organizational_owner(
    *,
    current_membership: EstablishmentMembership,
    establishment: Establishment,
    email: str,
    first_name: str,
    last_name: str,
) -> DirectorInvitationResult:
    organization_id = establishment.organization_id
    actor_membership_id = current_membership.id
    path_establishment_id = establishment.id
    actor_user_id = current_membership.user_id

    establishment_ids = list(
        Establishment.objects.filter(
            organization_id=organization_id,
            status__in=[
                Establishment.Status.DRAFT,
                Establishment.Status.ACTIVE,
            ],
        )
        .order_by("id")
        .values_list("id", flat=True)
    )

    existing_user = User.objects.filter(email__iexact=email).first()
    target_user_id = existing_user.id if existing_user is not None else None

    actor_membership_ids = list(
        EstablishmentMembership.objects.filter(
            user_id=actor_user_id,
            establishment_id__in=establishment_ids,
        ).values_list("id", flat=True)
    )
    target_membership_ids: list = []
    anchor_membership_id = None
    if target_user_id is not None:
        for membership_id, membership_establishment_id in EstablishmentMembership.objects.filter(
            user_id=target_user_id,
            establishment_id__in=establishment_ids,
        ).values_list("id", "establishment_id"):
            target_membership_ids.append(membership_id)
            if membership_establishment_id == path_establishment_id:
                anchor_membership_id = membership_id

    pending_invitation_ids: list = []
    if anchor_membership_id is not None:
        pending_invitation_ids = list(
            EstablishmentInvitation.objects.filter(
                membership_id=anchor_membership_id,
                accepted_at__isnull=True,
                revoked_at__isnull=True,
            ).values_list("id", flat=True)
        )

    _lock_organization(organization_id=organization_id)
    other_membership_ids = [
        membership_id
        for membership_id in {*actor_membership_ids, *target_membership_ids}
        if membership_id not in {actor_membership_id, anchor_membership_id}
    ]
    locked = _lock_memberships_for_owner_workflow(
        actor_membership_id=actor_membership_id,
        anchor_membership_id=anchor_membership_id,
        other_membership_ids=other_membership_ids,
    )
    _lock_invitations_for_owner_workflow(invitation_ids=pending_invitation_ids)

    actor = locked["actor"]
    if (
        actor is None
        or actor.role != EstablishmentMembership.Role.OWNER
        or actor.status != EstablishmentMembership.Status.ACTIVE
    ):
        raise OrganizationalOwnerInvariantConflictError

    establishments = org_establishments_draft_active(organization_id=organization_id)
    actor_memberships_by_establishment_id = _collect_org_memberships_for_user(
        user_id=actor.user_id,
        establishment_ids=[row.id for row in establishments],
    )
    if not _actor_has_full_coverage_active_org_owner(
        user_id=actor.user_id,
        establishments=establishments,
        memberships_by_establishment_id=actor_memberships_by_establishment_id,
    ):
        raise OrganizationalOwnerInvariantConflictError

    existing_user = User.objects.filter(email__iexact=email).first()
    path_membership = None
    if existing_user is not None:
        path_membership = EstablishmentMembership.objects.filter(
            user=existing_user,
            establishment_id=path_establishment_id,
        ).first()

    if path_membership is not None and path_membership.role != EstablishmentMembership.Role.OWNER:
        raise MembershipInvitationOwnerConflictError

    from houston.establishments.invite_eligibility import (
        InviteTargetDecision,
        evaluate_invite_target,
    )

    decision = evaluate_invite_target(
        user=existing_user,
        membership=path_membership,
        invited_role=EstablishmentMembership.Role.OWNER,
    )

    if (
        path_membership is not None
        and path_membership.role == EstablishmentMembership.Role.OWNER
        and path_membership.status == EstablishmentMembership.Status.ACTIVE
    ):
        raise DirectorInvitationDuplicateError

    if decision == InviteTargetDecision.USER_EXISTS:
        raise MembershipInvitationUserExistsError

    allow_reissue = (
        existing_user is not None
        and existing_user.status == User.Status.PENDING
        and path_membership is not None
        and path_membership.role == EstablishmentMembership.Role.OWNER
        and path_membership.status == EstablishmentMembership.Status.INVITED
    )
    # Owner/invited + User.pending: always revoke+reissue (including a live pending token).
    # Concurrent races still surface as a stable 409 after revalidation under the org lock.
    if decision == InviteTargetDecision.DUPLICATE and not allow_reissue:
        raise DirectorInvitationDuplicateError

    target_memberships_by_establishment_id: dict = {}
    if existing_user is not None:
        target_memberships_by_establishment_id = _collect_org_memberships_for_user(
            user_id=existing_user.id,
            establishment_ids=[row.id for row in establishments],
        )

    for establishment_row in establishments:
        target = target_memberships_by_establishment_id.get(establishment_row.id)
        if target is None:
            continue
        if target.role != EstablishmentMembership.Role.OWNER:
            raise MembershipInvitationOwnerConflictError
        if target.status == EstablishmentMembership.Status.ACTIVE:
            raise OrganizationalOwnerInvariantConflictError

    from houston.accounts.services import (
        PendingInviteUserAlreadyExistsError,
        create_pending_user_for_invite,
    )

    if decision == InviteTargetDecision.CREATE_PENDING_USER:
        try:
            user = create_pending_user_for_invite(
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
        except PendingInviteUserAlreadyExistsError as exc:
            raise MembershipInvitationUserExistsError from exc
    else:
        assert existing_user is not None
        user = existing_user
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=["first_name", "last_name", "updated_at"])

    anchor_membership = None
    for establishment_row in establishments:
        target = EstablishmentMembership.objects.filter(
            user=user,
            establishment=establishment_row,
        ).first()
        if target is None:
            target = _create_invited_membership(
                user=user,
                establishment=establishment_row,
                role=EstablishmentMembership.Role.OWNER,
            )
        elif target.role != EstablishmentMembership.Role.OWNER:
            raise MembershipInvitationOwnerConflictError
        elif target.status == EstablishmentMembership.Status.ACTIVE:
            raise OrganizationalOwnerInvariantConflictError
        elif target.status == EstablishmentMembership.Status.DEACTIVATED:
            target.status = EstablishmentMembership.Status.INVITED
            target.save(update_fields=["status", "updated_at"])

        if establishment_row.id == path_establishment_id:
            anchor_membership = target

    if anchor_membership is None:
        raise OrganizationalOwnerInvariantConflictError

    return _issue_establishment_invitation_for_membership(anchor_membership)


def _can_actor_manage_target_membership(
    *,
    actor_membership: EstablishmentMembership | None,
    target_membership: EstablishmentMembership,
) -> bool:
    return can_actor_manage_target_membership(
        actor_membership=actor_membership,
        target_membership=target_membership,
    )


def can_actor_manage_target_membership(
    *,
    actor_membership: EstablishmentMembership | None,
    target_membership: EstablishmentMembership,
) -> bool:
    if actor_membership is None:
        return False

    if actor_membership.establishment_id != target_membership.establishment_id:
        return False

    allowed_targets = _MANAGEABLE_TARGET_ROLES_BY_ACTOR.get(actor_membership.role)
    if allowed_targets is None:
        return False

    if target_membership.role not in allowed_targets:
        return False

    if actor_membership.role == EstablishmentMembership.Role.MANAGER:
        actor_scope_ids = membership_business_unit_scope_ids(actor_membership)
        if not actor_scope_ids:
            return False
        target_scope_ids = membership_business_unit_scope_ids(target_membership)
        return bool(actor_scope_ids & target_scope_ids)

    return True


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
    allowed_targets = _INVITABLE_TARGET_ROLES_BY_ACTOR.get(actor_role)
    if allowed_targets is None:
        return False

    return invited_role in allowed_targets


def _can_actor_invite_memberships(
    *,
    current_membership: EstablishmentMembership,
) -> bool:
    return current_membership.role in _INVITABLE_TARGET_ROLES_BY_ACTOR


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
        EstablishmentMembership.Role.MANAGER,
    },
    EstablishmentMembership.Role.STAFF: set(),
}

_INVITABLE_TARGET_ROLES_BY_ACTOR = {
    EstablishmentMembership.Role.OWNER: {
        EstablishmentMembership.Role.OWNER,
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
    from houston.establishments.invitation_email import schedule_establishment_invitation_email

    _revoke_pending_invitations(membership=membership)
    raw_token, invitation = _create_establishment_invitation(membership=membership)
    schedule_establishment_invitation_email(
        invitation=invitation,
        membership=membership,
        raw_token=raw_token,
    )
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
    role_changed = False
    scopes_changed = False

    if update_input.role is not None and membership.role != update_input.role:
        if _is_forbidden_membership_role_change(
            current_role=membership.role,
            next_role=update_input.role,
        ):
            raise MembershipRoleChangeForbiddenError

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
        role_changed = True

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
        previous_scope_ids = _membership_business_unit_scope_ids(membership.id)
        assign_membership_scopes(
            membership=membership,
            scope_inputs=update_input.scopes,
        )
        scopes_changed = previous_scope_ids != _membership_business_unit_scope_ids(membership.id)

    if role_changed or scopes_changed:
        from houston.realtime.broadcast import schedule_access_event

        schedule_access_event(
            reason="membership.updated",
            establishment_id=membership.establishment_id,
            membership_id=membership.id,
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

    if membership.role == EstablishmentMembership.Role.OWNER:
        assert current_membership is not None
        return _deactivate_organizational_owner(
            current_membership=current_membership,
            membership=membership,
        )

    if membership.status != EstablishmentMembership.Status.DEACTIVATED:
        membership.status = EstablishmentMembership.Status.DEACTIVATED
        membership.save(update_fields=["status", "updated_at"])

    from houston.chat.services import handle_membership_chat_deactivation

    handle_membership_chat_deactivation(membership=membership)

    from houston.realtime.broadcast import schedule_access_event

    schedule_access_event(
        reason="membership.deactivated",
        establishment_id=membership.establishment_id,
        membership_id=membership.id,
    )

    _clear_selected_establishment_for_membership(membership)

    membership.refresh_from_db()
    return _reload_membership_for_response(membership.id)


@transaction.atomic
def activate_membership_for_management(
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

    if membership.status == EstablishmentMembership.Status.INVITED:
        raise InvitedMembershipActivationError

    if membership.role == EstablishmentMembership.Role.OWNER:
        assert current_membership is not None
        return _reactivate_organizational_owner(
            current_membership=current_membership,
            membership=membership,
        )

    if membership.status != EstablishmentMembership.Status.ACTIVE:
        membership.status = EstablishmentMembership.Status.ACTIVE
        membership.save(update_fields=["status", "updated_at"])

        from houston.realtime.broadcast import schedule_access_event

        schedule_access_event(
            reason="membership.updated",
            establishment_id=membership.establishment_id,
            membership_id=membership.id,
        )

    membership.refresh_from_db()
    return _reload_membership_for_response(membership.id)


def _deactivate_organizational_owner(
    *,
    current_membership: EstablishmentMembership,
    membership: EstablishmentMembership,
) -> EstablishmentMembership:
    organization_id = membership.establishment.organization_id
    actor_membership_id = current_membership.id
    anchor_membership_id = membership.id
    actor_user_id = current_membership.user_id
    target_user_id = membership.user_id
    path_establishment_id = membership.establishment_id

    establishment_ids = list(
        Establishment.objects.filter(
            organization_id=organization_id,
            status__in=[
                Establishment.Status.DRAFT,
                Establishment.Status.ACTIVE,
            ],
        )
        .order_by("id")
        .values_list("id", flat=True)
    )
    actor_membership_ids = list(
        EstablishmentMembership.objects.filter(
            user_id=actor_user_id,
            establishment_id__in=establishment_ids,
        ).values_list("id", flat=True)
    )
    target_membership_ids = list(
        EstablishmentMembership.objects.filter(
            user_id=target_user_id,
            establishment_id__in=establishment_ids,
        ).values_list("id", flat=True)
    )

    organization = _lock_organization(organization_id=organization_id)
    other_membership_ids = [
        membership_id
        for membership_id in {*actor_membership_ids, *target_membership_ids}
        if membership_id not in {actor_membership_id, anchor_membership_id}
    ]
    locked = _lock_memberships_for_owner_workflow(
        actor_membership_id=actor_membership_id,
        anchor_membership_id=anchor_membership_id,
        other_membership_ids=other_membership_ids,
    )

    actor = locked["actor"]
    anchor = locked["anchor"]
    if actor is None or anchor is None:
        raise OrganizationalOwnerInvariantConflictError

    if organization.status != Organization.Status.ACTIVE:
        raise OrganizationalOwnerInvariantConflictError
    if anchor.establishment_id != path_establishment_id:
        raise OrganizationalOwnerInvariantConflictError
    if anchor.establishment.organization_id != organization_id:
        raise OrganizationalOwnerInvariantConflictError
    if anchor.establishment.status != Establishment.Status.ACTIVE:
        raise OrganizationalOwnerInvariantConflictError
    if anchor.role != EstablishmentMembership.Role.OWNER:
        raise OrganizationalOwnerInvariantConflictError
    if actor.user.status != User.Status.ACTIVE:
        raise OrganizationalOwnerInvariantConflictError
    if (
        actor.role != EstablishmentMembership.Role.OWNER
        or actor.status != EstablishmentMembership.Status.ACTIVE
    ):
        raise OrganizationalOwnerInvariantConflictError
    if anchor.user.status != User.Status.ACTIVE:
        raise OrganizationalOwnerInvariantConflictError

    establishments = org_establishments_draft_active(organization_id=organization_id)
    establishment_id_list = [row.id for row in establishments]
    actor_memberships_by_establishment_id = _collect_org_memberships_for_user(
        user_id=actor.user_id,
        establishment_ids=establishment_id_list,
    )
    if not _actor_has_full_coverage_active_org_owner(
        user_id=actor.user_id,
        establishments=establishments,
        memberships_by_establishment_id=actor_memberships_by_establishment_id,
    ):
        raise OrganizationalOwnerInvariantConflictError

    target_memberships_by_establishment_id = _collect_org_memberships_for_user(
        user_id=target_user_id,
        establishment_ids=establishment_id_list,
    )
    target_memberships: list[EstablishmentMembership] = []
    target_statuses: set[str] = set()
    for establishment in establishments:
        target = target_memberships_by_establishment_id.get(establishment.id)
        if target is None or target.role != EstablishmentMembership.Role.OWNER:
            raise OrganizationalOwnerInvariantConflictError
        target_statuses.add(target.status)
        target_memberships.append(target)

    if target_statuses == {EstablishmentMembership.Status.DEACTIVATED}:
        return _reload_membership_for_response(anchor.id)

    if target_statuses != {EstablishmentMembership.Status.ACTIVE}:
        raise OrganizationalOwnerInvariantConflictError

    if not _has_other_full_coverage_active_org_owner(
        exclude_user_id=target_user_id,
        establishments=establishments,
    ):
        raise CannotDeactivateLastActiveOwnerError

    from houston.chat.services import handle_membership_chat_deactivation
    from houston.realtime.broadcast import schedule_access_event

    for target in target_memberships:
        target.status = EstablishmentMembership.Status.DEACTIVATED
        target.save(update_fields=["status", "updated_at"])
        handle_membership_chat_deactivation(membership=target)
        schedule_access_event(
            reason="membership.deactivated",
            establishment_id=target.establishment_id,
            membership_id=target.id,
        )

    _clear_selected_establishments_for_org_owner(
        user_id=target_user_id,
        establishment_ids=establishment_id_list,
    )

    return _reload_membership_for_response(anchor.id)


def _reactivate_organizational_owner(
    *,
    current_membership: EstablishmentMembership,
    membership: EstablishmentMembership,
) -> EstablishmentMembership:
    organization_id = membership.establishment.organization_id
    actor_membership_id = current_membership.id
    anchor_membership_id = membership.id
    actor_user_id = current_membership.user_id
    target_user_id = membership.user_id
    path_establishment_id = membership.establishment_id

    establishment_ids = list(
        Establishment.objects.filter(
            organization_id=organization_id,
            status__in=[
                Establishment.Status.DRAFT,
                Establishment.Status.ACTIVE,
            ],
        )
        .order_by("id")
        .values_list("id", flat=True)
    )
    actor_membership_ids = list(
        EstablishmentMembership.objects.filter(
            user_id=actor_user_id,
            establishment_id__in=establishment_ids,
        ).values_list("id", flat=True)
    )
    target_membership_ids = list(
        EstablishmentMembership.objects.filter(
            user_id=target_user_id,
            establishment_id__in=establishment_ids,
        ).values_list("id", flat=True)
    )

    organization = _lock_organization(organization_id=organization_id)
    other_membership_ids = [
        membership_id
        for membership_id in {*actor_membership_ids, *target_membership_ids}
        if membership_id not in {actor_membership_id, anchor_membership_id}
    ]
    locked = _lock_memberships_for_owner_workflow(
        actor_membership_id=actor_membership_id,
        anchor_membership_id=anchor_membership_id,
        other_membership_ids=other_membership_ids,
    )

    actor = locked["actor"]
    anchor = locked["anchor"]
    if actor is None or anchor is None:
        raise OrganizationalOwnerInvariantConflictError

    if organization.status != Organization.Status.ACTIVE:
        raise OrganizationalOwnerInvariantConflictError
    if anchor.establishment_id != path_establishment_id:
        raise OrganizationalOwnerInvariantConflictError
    if anchor.establishment.organization_id != organization_id:
        raise OrganizationalOwnerInvariantConflictError
    if anchor.establishment.status != Establishment.Status.ACTIVE:
        raise OrganizationalOwnerInvariantConflictError
    if anchor.role != EstablishmentMembership.Role.OWNER:
        raise OrganizationalOwnerInvariantConflictError
    if actor.user.status != User.Status.ACTIVE:
        raise OrganizationalOwnerInvariantConflictError
    if (
        actor.role != EstablishmentMembership.Role.OWNER
        or actor.status != EstablishmentMembership.Status.ACTIVE
    ):
        raise OrganizationalOwnerInvariantConflictError
    if anchor.user.status != User.Status.ACTIVE:
        raise OrganizationalOwnerInvariantConflictError

    establishments = org_establishments_draft_active(organization_id=organization_id)
    establishment_id_list = [row.id for row in establishments]
    actor_memberships_by_establishment_id = _collect_org_memberships_for_user(
        user_id=actor.user_id,
        establishment_ids=establishment_id_list,
    )
    if not _actor_has_full_coverage_active_org_owner(
        user_id=actor.user_id,
        establishments=establishments,
        memberships_by_establishment_id=actor_memberships_by_establishment_id,
    ):
        raise OrganizationalOwnerInvariantConflictError

    target_memberships_by_establishment_id = _collect_org_memberships_for_user(
        user_id=target_user_id,
        establishment_ids=establishment_id_list,
    )
    target_memberships: list[EstablishmentMembership] = []
    target_statuses: set[str] = set()
    for establishment in establishments:
        target = target_memberships_by_establishment_id.get(establishment.id)
        if target is None or target.role != EstablishmentMembership.Role.OWNER:
            raise OrganizationalOwnerInvariantConflictError
        target_statuses.add(target.status)
        target_memberships.append(target)

    if target_statuses == {EstablishmentMembership.Status.ACTIVE}:
        return _reload_membership_for_response(anchor.id)

    if target_statuses != {EstablishmentMembership.Status.DEACTIVATED}:
        raise OrganizationalOwnerInvariantConflictError

    from houston.realtime.broadcast import schedule_access_event

    for target in target_memberships:
        target.status = EstablishmentMembership.Status.ACTIVE
        target.save(update_fields=["status", "updated_at"])
        schedule_access_event(
            reason="membership.updated",
            establishment_id=target.establishment_id,
            membership_id=target.id,
        )

    return _reload_membership_for_response(anchor.id)


def _actor_has_full_coverage_active_org_owner(
    *,
    user_id,
    establishments: list[Establishment],
    memberships_by_establishment_id: dict,
) -> bool:
    for establishment in establishments:
        membership = memberships_by_establishment_id.get(establishment.id)
        if (
            membership is None
            or membership.user_id != user_id
            or membership.role != EstablishmentMembership.Role.OWNER
            or membership.status != EstablishmentMembership.Status.ACTIVE
        ):
            return False
    return True


def _has_other_full_coverage_active_org_owner(
    *,
    exclude_user_id,
    establishments: list[Establishment],
) -> bool:
    if not establishments:
        return False

    establishment_ids = [establishment.id for establishment in establishments]
    candidate_user_ids = (
        EstablishmentMembership.objects.filter(
            establishment_id__in=establishment_ids,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
        )
        .exclude(user_id=exclude_user_id)
        .values_list("user_id", flat=True)
        .distinct()
    )
    for user_id in candidate_user_ids:
        memberships_by_establishment_id = _collect_org_memberships_for_user(
            user_id=user_id,
            establishment_ids=establishment_ids,
        )
        if _actor_has_full_coverage_active_org_owner(
            user_id=user_id,
            establishments=establishments,
            memberships_by_establishment_id=memberships_by_establishment_id,
        ):
            return True
    return False


def _collect_org_memberships_for_user(*, user_id, establishment_ids) -> dict:
    return {
        membership.establishment_id: membership
        for membership in EstablishmentMembership.objects.filter(
            user_id=user_id,
            establishment_id__in=establishment_ids,
        )
    }


def _clear_selected_establishments_for_org_owner(
    *,
    user_id,
    establishment_ids,
) -> None:
    if not establishment_ids:
        return
    UserSession.objects.filter(
        user_id=user_id,
        selected_establishment_id__in=establishment_ids,
    ).update(
        selected_establishment=None,
        updated_at=timezone.now(),
    )


def _lock_organization(*, organization_id) -> Organization:
    """Lock organization row — first step of organizational-owner workflows (§2.10)."""
    return Organization.objects.select_for_update().get(id=organization_id)


def _lock_memberships_for_owner_workflow(
    *,
    actor_membership_id=None,
    anchor_membership_id=None,
    other_membership_ids=(),
) -> dict:
    """Lock memberships in §2.10 order: actor → anchor → others by id ascending.

    Call only after ``_lock_organization``. Returns locked rows keyed by role in
    the workflow (``actor``, ``anchor``, ``others``). Missing ids are omitted.
    """
    ordered_ids: list = []
    for membership_id in (actor_membership_id, anchor_membership_id):
        if membership_id is not None and membership_id not in ordered_ids:
            ordered_ids.append(membership_id)

    others_sorted = sorted(
        {
            membership_id
            for membership_id in other_membership_ids
            if membership_id is not None and membership_id not in ordered_ids
        }
    )
    ordered_ids.extend(others_sorted)

    locked_by_id: dict = {}
    membership_qs = EstablishmentMembership.objects.select_for_update().select_related(
        "user",
        "establishment",
        "establishment__organization",
    )
    for membership_id in ordered_ids:
        membership = membership_qs.filter(id=membership_id).first()
        if membership is not None:
            locked_by_id[membership_id] = membership

    return {
        "actor": locked_by_id.get(actor_membership_id),
        "anchor": locked_by_id.get(anchor_membership_id),
        "others": [
            locked_by_id[membership_id]
            for membership_id in others_sorted
            if membership_id in locked_by_id
        ],
    }


def _lock_invitations_for_owner_workflow(*, invitation_ids=()) -> list[EstablishmentInvitation]:
    """Lock invitations after memberships, stable by id ascending (§2.10)."""
    ordered_ids = sorted({invitation_id for invitation_id in invitation_ids if invitation_id})
    locked: list[EstablishmentInvitation] = []
    invitation_qs = EstablishmentInvitation.objects.select_for_update()
    for invitation_id in ordered_ids:
        invitation = invitation_qs.filter(id=invitation_id).first()
        if invitation is not None:
            locked.append(invitation)
    return locked


def _is_forbidden_membership_role_change(*, current_role: str, next_role: str) -> bool:
    if next_role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return True
    if current_role == EstablishmentMembership.Role.OWNER:
        return True
    return False


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
            # Stable duplicate regardless of role after race on (user, establishment).
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


def _membership_business_unit_scope_ids(membership_id) -> set:
    return set(
        MembershipScope.objects.filter(membership_id=membership_id).values_list(
            "business_unit_id",
            flat=True,
        )
    )


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


def _map_runtime_domain_error(exc: Exception) -> None:
    if isinstance(exc, DomainNotFoundError):
        raise RuntimeConfigNotFoundError from exc
    if isinstance(exc, DomainValidationError):
        raise ValidationError({"detail": [exc.message]}) from exc
    if isinstance(exc, DomainConflictError):
        raise RuntimeConfigConflictError(code=exc.code, detail=exc.message) from exc
    raise exc


@transaction.atomic
def create_runtime_business_unit(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    catalog_key: str,
    specific_name: str,
    instance_description: str = "",
) -> BusinessUnit:
    establishment = _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )

    normalized_catalog_key = catalog_key.strip()
    if not normalized_catalog_key:
        raise ValidationError({"catalog_key": ["Catalog key is required."]})

    catalog_business_unit = CatalogBusinessUnit.objects.filter(
        key=normalized_catalog_key
    ).first()
    if catalog_business_unit is None:
        raise RuntimeConfigNotFoundError

    try:
        return create_runtime_business_unit_domain(
            establishment=establishment,
            catalog_business_unit=catalog_business_unit,
            specific_name=specific_name,
            instance_description=instance_description,
            source=BusinessUnit.Source.CATALOG_SUGGESTION,
        )
    except (DomainConflictError, DomainValidationError, DomainNotFoundError) as exc:
        _map_runtime_domain_error(exc)
        raise


@transaction.atomic
def update_runtime_business_unit(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    business_unit_id,
    specific_name: str | None = None,
    instance_description: str | None = None,
) -> BusinessUnit:
    _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )
    try:
        return update_business_unit_domain(
            establishment_id=establishment_id,
            business_unit_id=business_unit_id,
            specific_name=specific_name,
            instance_description=instance_description,
        )
    except (DomainConflictError, DomainValidationError, DomainNotFoundError) as exc:
        _map_runtime_domain_error(exc)
        raise


@transaction.atomic
def reactivate_runtime_business_unit(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    business_unit_id,
) -> BusinessUnit:
    _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )
    try:
        return reactivate_business_unit_domain(
            establishment_id=establishment_id,
            business_unit_id=business_unit_id,
        )
    except (DomainConflictError, DomainValidationError, DomainNotFoundError) as exc:
        _map_runtime_domain_error(exc)
        raise


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
    label: str | None = None,
    description: str = "",
    catalog_key: str | None = None,
) -> ActivitySubject:
    _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )
    try:
        return create_runtime_activity_subject_domain(
            establishment_id=establishment_id,
            business_unit_id=business_unit_id,
            label=label,
            description=description,
            catalog_key=catalog_key,
        )
    except (DomainConflictError, DomainValidationError, DomainNotFoundError) as exc:
        _map_runtime_domain_error(exc)
        raise


@transaction.atomic
def reactivate_runtime_activity_subject(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    activity_subject_id,
) -> ActivitySubject:
    _get_establishment_for_runtime_mutation(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )
    try:
        return reactivate_activity_subject_domain(
            establishment_id=establishment_id,
            activity_subject_id=activity_subject_id,
        )
    except (DomainConflictError, DomainValidationError, DomainNotFoundError) as exc:
        _map_runtime_domain_error(exc)
        raise


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
