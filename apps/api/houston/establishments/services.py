from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from houston.accounts.models import UserSession
from houston.establishments.access import get_onboarding_access_context
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    MembershipDomain,
    OnboardingSession,
    OperationalDomain,
)
from houston.establishments.selectors import (
    get_membership_for_management,
    get_runtime_config_for_session,
)
from houston.organizations.models import Organization


class MembershipManagementNotFoundError(Exception):
    pass


class InvalidMembershipDomainAssignmentError(Exception):
    pass


class CannotDeactivateLastActiveOwnerError(Exception):
    pass


class CannotDemoteLastActiveOwnerError(Exception):
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


class InvalidActivityDescriptionError(Exception):
    pass


class OnboardingReadinessError(Exception):
    def __init__(self, readiness: dict):
        super().__init__("Onboarding session is not ready for activation.")
        self.readiness = readiness


@dataclass(frozen=True)
class MembershipUpdateInput:
    role: str | None = None
    operational_domains: list[str] | None = None


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

    session = OnboardingSession(
        organization=organization,
        establishment=establishment,
        started_by=started_by,
        source_mode=source_mode,
        current_step=current_step,
    )
    session.full_clean(validate_unique=False, validate_constraints=False)

    try:
        session.save()
    except IntegrityError as exc:
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
            "Activity description must be at least "
            f"{ACTIVITY_DESCRIPTION_MIN_LENGTH} characters."
        )

    activity_description, _created = (
        EstablishmentActivityDescription.objects.update_or_create(
            establishment=session.establishment,
            defaults={
                "description": normalized_description,
                "source": EstablishmentActivityDescription.Source.MANUAL,
                "submitted_by": actor,
                "validated_at": timezone.now(),
            },
        )
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
    config = get_runtime_config_for_session(session=session)
    description = config["activity_description"]

    counts = _activation_counts(session)
    sections = {
        "description": {
            "is_ready": _is_valid_activity_description(description),
            "required": True,
            "is_skippable": False,
        },
        "modules": {
            "is_ready": counts["active_modules_count"] >= 1,
            "required": True,
            "is_skippable": False,
        },
        "domains": {
            "is_ready": counts["active_domains_count"] >= 3,
            "required": True,
            "is_skippable": False,
        },
        "units": {
            "is_ready": True,
            "required": False,
            "is_skippable": True,
        },
        "vocabulary": {
            "is_ready": True,
            "required": False,
            "is_skippable": True,
        },
        "runtime_tags": {
            "is_ready": True,
            "required": False,
            "is_skippable": True,
        },
        "routing_hints": {
            "is_ready": True,
            "required": False,
            "is_skippable": True,
        },
        "managers": {
            "is_ready": (
                counts["active_or_invited_manager_count"] >= 1
                and counts["managers_with_domains_count"]
                == counts["active_or_invited_manager_count"]
            ),
            "required": True,
            "is_skippable": False,
        },
    }
    blockers = _activation_blockers(
        session=session,
        description=description,
        counts=counts,
    )

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
        "active_modules": [
            _serialize_keyed_runtime_item(item) for item in config["active_modules"]
        ],
        "active_domains": [
            _serialize_keyed_runtime_item(item) for item in config["active_domains"]
        ],
        "optional_units": [
            _serialize_keyed_runtime_item(item) for item in config["optional_units"]
        ],
        "optional_vocabulary": [
            _serialize_vocabulary_item(item) for item in config["optional_vocabulary"]
        ],
        "optional_runtime_tags": [
            _serialize_runtime_tag(item) for item in config["optional_runtime_tags"]
        ],
        "optional_routing_hints": [
            _serialize_routing_hint(item) for item in config["optional_routing_hints"]
        ],
        "initial_owner_director_count": counts["active_owner_or_director_count"],
        "initial_manager_count": counts["active_or_invited_manager_count"],
        "managers_with_domains_count": counts["managers_with_domains_count"],
        "readiness": readiness,
        "blockers": readiness["blockers"],
    }


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

    update_fields: list[str] = []

    if update_input.role is not None and membership.role != update_input.role:
        if _would_demote_last_active_owner(
            membership=membership,
            next_role=update_input.role,
        ):
            raise CannotDemoteLastActiveOwnerError

        membership.role = update_input.role
        update_fields.append("role")

    if update_fields:
        membership.save(update_fields=[*update_fields, "updated_at"])

    if update_input.operational_domains is not None:
        _replace_membership_domains(
            membership=membership,
            operational_domain_keys=update_input.operational_domains,
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

    if (
        membership.status == EstablishmentMembership.Status.ACTIVE
        and membership.role == EstablishmentMembership.Role.OWNER
        and _is_last_active_owner(membership)
    ):
        raise CannotDeactivateLastActiveOwnerError

    if membership.status != EstablishmentMembership.Status.DEACTIVATED:
        membership.status = EstablishmentMembership.Status.DEACTIVATED
        membership.save(update_fields=["status", "updated_at"])

    _clear_selected_establishment_for_membership(membership)

    membership.refresh_from_db()
    return _reload_membership_for_response(membership.id)


def _lock_onboarding_session(session: OnboardingSession) -> OnboardingSession:
    return (
        OnboardingSession.objects.select_for_update()
        .select_related("organization", "establishment", "establishment__organization")
        .get(id=session.id)
    )


def _reload_onboarding_session(session: OnboardingSession) -> OnboardingSession:
    return (
        OnboardingSession.objects.select_related(
            "organization",
            "establishment",
            "establishment__organization",
        )
        .get(id=session.id)
    )


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
    managers = EstablishmentMembership.objects.filter(
        establishment_id=establishment_id,
        role=EstablishmentMembership.Role.MANAGER,
        status__in=[
            EstablishmentMembership.Status.ACTIVE,
            EstablishmentMembership.Status.INVITED,
        ],
    )
    managers_with_domains_count = (
        managers.annotate(
            active_domains_count=Count(
                "domain_links",
                filter=Q(
                    domain_links__operational_domain__active=True,
                    domain_links__operational_domain__establishment_id=establishment_id,
                ),
                distinct=True,
            )
        )
        .filter(active_domains_count__gte=1)
        .count()
    )

    return {
        "active_modules_count": session.establishment.operational_modules.filter(
            active=True,
        ).count(),
        "active_domains_count": session.establishment.operational_domains.filter(
            active=True,
        ).count(),
        "active_owner_or_director_count": EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
            role__in=[
                EstablishmentMembership.Role.OWNER,
                EstablishmentMembership.Role.DIRECTOR,
            ],
        ).count(),
        "active_or_invited_manager_count": managers.count(),
        "managers_with_domains_count": managers_with_domains_count,
    }


def _activation_blockers(
    *,
    session: OnboardingSession,
    description: EstablishmentActivityDescription | None,
    counts: dict,
) -> list[dict]:
    blockers: list[dict] = []

    if OnboardingSession.is_terminal_status(session.status):
        blockers.append(_blocker("session_terminal"))

    if session.organization.status != Organization.Status.ACTIVE:
        blockers.append(_blocker("organization_not_active"))

    if session.establishment.status != Establishment.Status.DRAFT:
        blockers.append(_blocker("establishment_not_draft"))

    if description is None or description.validated_at is None:
        blockers.append(_blocker("missing_validated_description"))
    elif len((description.description or "").strip()) < ACTIVITY_DESCRIPTION_MIN_LENGTH:
        blockers.append(_blocker("description_too_short"))

    if counts["active_modules_count"] < 1:
        blockers.append(_blocker("missing_active_module"))

    if counts["active_domains_count"] < 3:
        blockers.append(_blocker("insufficient_active_domains"))

    if counts["active_owner_or_director_count"] < 1:
        blockers.append(_blocker("missing_active_owner_or_director"))

    if counts["active_or_invited_manager_count"] < 1:
        blockers.append(_blocker("missing_active_or_invited_manager"))
    elif (
        counts["managers_with_domains_count"]
        != counts["active_or_invited_manager_count"]
    ):
        blockers.append(_blocker("manager_domains_missing"))

    return blockers


def _blocker(code: str) -> dict:
    return {"code": code, "message": code.replace("_", " ")}


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
            None
            if description.submitted_by_id is None
            else str(description.submitted_by_id)
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


def _serialize_vocabulary_item(item) -> dict:
    return {
        "id": str(item.id),
        "term": item.term,
        "meaning": item.meaning,
        "mapped_domain_key": (
            None if item.mapped_domain_id is None else item.mapped_domain.key
        ),
        "mapped_unit_key": None if item.mapped_unit_id is None else item.mapped_unit.key,
        "source": item.source,
        "active": item.active,
    }


def _serialize_runtime_tag(runtime_tag) -> dict:
    return {
        "id": str(runtime_tag.id),
        "key": runtime_tag.key,
        "label": runtime_tag.label,
        "source": runtime_tag.source,
        "active": runtime_tag.active,
        "domain_keys": [
            link.operational_domain.key for link in runtime_tag.domain_links.all()
        ],
    }


def _serialize_routing_hint(routing_hint) -> dict:
    return {
        "id": str(routing_hint.id),
        "pattern": routing_hint.pattern,
        "suggested_unit_key": (
            None
            if routing_hint.suggested_unit_id is None
            else routing_hint.suggested_unit.key
        ),
        "source": routing_hint.source,
        "active": routing_hint.active,
        "domain_keys": [
            link.operational_domain.key for link in routing_hint.domain_links.all()
        ],
    }


def _replace_membership_domains(
    *,
    membership: EstablishmentMembership,
    operational_domain_keys: list[str],
) -> None:
    normalized_keys = _normalize_domain_keys(operational_domain_keys)
    domains_by_key = {
        domain.key: domain
        for domain in OperationalDomain.objects.filter(
            establishment=membership.establishment,
            active=True,
            key__in=normalized_keys,
        ).only("id", "key")
    }

    if len(domains_by_key) != len(normalized_keys):
        raise InvalidMembershipDomainAssignmentError(
            "Operational domains must be active and belong to the same establishment."
        )

    requested_domain_ids = {domains_by_key[key].id for key in normalized_keys}

    MembershipDomain.objects.filter(membership=membership).exclude(
        operational_domain_id__in=requested_domain_ids
    ).delete()

    existing_domain_ids = set(
        MembershipDomain.objects.filter(membership=membership).values_list(
            "operational_domain_id",
            flat=True,
        )
    )
    missing_links = [
        MembershipDomain(
            membership=membership,
            operational_domain=domains_by_key[key],
        )
        for key in normalized_keys
        if domains_by_key[key].id not in existing_domain_ids
    ]
    if missing_links:
        MembershipDomain.objects.bulk_create(missing_links)


def _normalize_domain_keys(domain_keys: list[str]) -> list[str]:
    normalized_keys: list[str] = []
    seen_keys: set[str] = set()

    for domain_key in domain_keys:
        if not isinstance(domain_key, str):
            raise InvalidMembershipDomainAssignmentError(
                "Operational domain keys must be non-empty strings."
            )

        normalized_key = domain_key.strip()
        if not normalized_key:
            raise InvalidMembershipDomainAssignmentError(
                "Operational domain keys must be non-empty strings."
            )

        if normalized_key in seen_keys:
            continue

        seen_keys.add(normalized_key)
        normalized_keys.append(normalized_key)

    return normalized_keys


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


def _reload_membership_for_response(membership_id) -> EstablishmentMembership:
    return (
        EstablishmentMembership.objects.select_related(
            "user",
            "establishment",
            "establishment__organization",
        )
        .prefetch_related("domain_links__operational_domain")
        .get(id=membership_id)
    )
