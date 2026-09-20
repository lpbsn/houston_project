from __future__ import annotations

from typing import NoReturn

from houston.accounts.models import User
from houston.core.exceptions import DomainConflictError, DomainNotFoundError, DomainValidationError
from houston.establishments.membership_scope import InvalidMembershipScopeAssignmentError
from houston.establishments.models import OnboardingSession
from houston.establishments.services import (
    DirectorInvitationAlreadyExistsError,
    DirectorInvitationDuplicateError,
    DirectorInvitationOwnerNotAllowedError,
    EstablishmentAlreadyActiveError,
    InvalidDirectorInvitationInputError,
    InvalidMembershipInvitationInputError,
    InvalidOnboardingActivationStateError,
    MembershipInvitationOwnerConflictError,
    MembershipInvitationRoleNotAllowedError,
    MembershipInvitationUserExistsError,
    OnboardingDraftNotFoundError,
    OnboardingDraftValidationError,
    OnboardingReadinessError,
    OnboardingRuntimeAlreadyMaterializedError,
    OnboardingSessionTerminalError,
    OrganizationalOwnerInvariantConflictError,
    build_activation_summary,
    complete_onboarding_session_core,
    create_establishment_for_organization,
    get_onboarding_draft,
    invite_director_during_onboarding_core,
    invite_organizational_owner_during_onboarding_core,
    serialize_onboarding_draft,
    start_onboarding_session,
    upsert_onboarding_draft_core,
)
from houston.organizations.models import Organization
from houston.platform.exceptions import PlatformLifecycleDenied
from houston.platform.services import execute_platform_lifecycle

_ONBOARDING_DOMAIN_ERROR_CODES: dict[type[BaseException], str] = {
    OnboardingDraftNotFoundError: "draft_not_found",
    InvalidOnboardingActivationStateError: "invalid_onboarding_state",
    OnboardingSessionTerminalError: "invalid_onboarding_state",
    OnboardingReadinessError: "activation_not_ready",
    EstablishmentAlreadyActiveError: "establishment_already_active",
    OnboardingRuntimeAlreadyMaterializedError: "runtime_already_materialized",
    DirectorInvitationAlreadyExistsError: "director_invitation_already_exists",
    DirectorInvitationDuplicateError: "membership_invitation_duplicate",
    MembershipInvitationUserExistsError: "membership_invitation_user_exists",
    DirectorInvitationOwnerNotAllowedError: "director_invitation_owner_not_allowed",
    InvalidDirectorInvitationInputError: "membership_invitation_invalid",
    InvalidMembershipInvitationInputError: "membership_invitation_invalid",
    InvalidMembershipScopeAssignmentError: "membership_invitation_invalid",
    MembershipInvitationOwnerConflictError: "membership_invitation_owner_conflict",
    OrganizationalOwnerInvariantConflictError: "organizational_owner_invariant_conflict",
    MembershipInvitationRoleNotAllowedError: "membership_invitation_role_not_allowed",
}


def map_onboarding_domain_error(exc: BaseException) -> PlatformLifecycleDenied | None:
    if isinstance(exc, OnboardingDraftValidationError):
        return PlatformLifecycleDenied(
            "onboarding_draft_invalid",
            str(exc) or "onboarding_draft_invalid",
            extra={"errors": exc.errors},
        )
    if isinstance(exc, (DomainValidationError, DomainConflictError, DomainNotFoundError)):
        return PlatformLifecycleDenied(exc.code, exc.message)
    for exc_type, code in _ONBOARDING_DOMAIN_ERROR_CODES.items():
        if isinstance(exc, exc_type):
            return PlatformLifecycleDenied(code, str(exc))
    return None


def _reraise_mapped_onboarding_error(exc: Exception) -> NoReturn:
    denied = map_onboarding_domain_error(exc)
    if denied is not None:
        raise denied from exc
    raise


def start_platform_onboarding(
    *,
    operator: User,
    organization_name: str,
    establishment_name: str | None = None,
) -> OnboardingSession:
    normalized_org = organization_name.strip()
    if not normalized_org:
        raise PlatformLifecycleDenied("invalid_organization_name")

    normalized_est = None
    if establishment_name is not None:
        normalized_est = establishment_name.strip() or None

    def mutate():
        organization = Organization.objects.create(
            name=normalized_org,
            status=Organization.Status.ACTIVE,
        )
        establishment = create_establishment_for_organization(
            organization_id=organization.id,
            name=normalized_est,
        )
        return start_onboarding_session(
            organization=organization,
            establishment=establishment,
            started_by=operator,
        )

    return execute_platform_lifecycle(
        operator=operator,
        action="start_onboarding",
        resource_type="onboarding_session",
        resource_id=None,
        mutate=mutate,
    )


def upsert_platform_onboarding_draft(*, operator: User, session: OnboardingSession, payload: dict):
    return upsert_onboarding_draft_core(session=session, actor=operator, payload=payload)


def get_platform_onboarding_draft(*, session: OnboardingSession) -> dict:
    draft = get_onboarding_draft(session=session)
    return serialize_onboarding_draft(draft=draft)


def complete_platform_onboarding(*, operator: User, session: OnboardingSession) -> dict:
    def mutate():
        try:
            return complete_onboarding_session_core(session=session, actor=operator)
        except Exception as exc:
            _reraise_mapped_onboarding_error(exc)

    return execute_platform_lifecycle(
        operator=operator,
        action="complete_onboarding",
        resource_type="onboarding_session",
        resource_id=session.id,
        mutate=mutate,
    )


def invite_platform_director(
    *,
    operator: User,
    session: OnboardingSession,
    email: str,
    first_name: str,
    last_name: str,
):
    def mutate():
        try:
            return invite_director_during_onboarding_core(
                session=session,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
        except Exception as exc:
            _reraise_mapped_onboarding_error(exc)

    return execute_platform_lifecycle(
        operator=operator,
        action="invite_director",
        resource_type="onboarding_session",
        resource_id=session.id,
        mutate=mutate,
    )


def invite_platform_owner(
    *,
    operator: User,
    session: OnboardingSession,
    email: str,
    first_name: str,
    last_name: str,
):
    def mutate():
        try:
            return invite_organizational_owner_during_onboarding_core(
                session=session,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
        except Exception as exc:
            _reraise_mapped_onboarding_error(exc)

    return execute_platform_lifecycle(
        operator=operator,
        action="invite_owner",
        resource_type="onboarding_session",
        resource_id=session.id,
        mutate=mutate,
    )


def platform_activation_summary(*, session: OnboardingSession) -> dict:
    return build_activation_summary(session=session)
