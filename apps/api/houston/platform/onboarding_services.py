from __future__ import annotations

from houston.accounts.models import User
from houston.establishments.models import OnboardingSession
from houston.establishments.services import (
    InvalidOnboardingActivationStateError,
    OnboardingReadinessError,
    build_activation_summary,
    complete_onboarding_session_core,
    create_establishment_for_organization,
    get_onboarding_draft,
    invite_director_during_onboarding_core,
    invite_organizational_owner_core,
    serialize_onboarding_draft,
    start_onboarding_session,
    upsert_onboarding_draft_core,
)
from houston.organizations.models import Organization
from houston.platform.exceptions import PlatformLifecycleDenied
from houston.platform.services import execute_platform_lifecycle


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
        except OnboardingReadinessError as exc:
            raise PlatformLifecycleDenied("activation_not_ready") from exc
        except InvalidOnboardingActivationStateError as exc:
            raise PlatformLifecycleDenied("invalid_onboarding_state") from exc

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
        return invite_director_during_onboarding_core(
            session=session,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

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
        return invite_organizational_owner_core(
            establishment=session.establishment,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

    return execute_platform_lifecycle(
        operator=operator,
        action="invite_owner",
        resource_type="onboarding_session",
        resource_id=session.id,
        mutate=mutate,
    )


def platform_activation_summary(*, session: OnboardingSession) -> dict:
    return build_activation_summary(session=session)
