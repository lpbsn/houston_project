from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.accounts.models import UserSession
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipDomain,
    OnboardingSession,
    OperationalDomain,
)
from houston.establishments.selectors import get_membership_for_management
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
