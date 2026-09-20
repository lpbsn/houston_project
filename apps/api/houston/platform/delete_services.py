from __future__ import annotations

from houston.accounts.models import User
from houston.analytics.models import OperationalPattern
from houston.establishments.models import Establishment, OnboardingSession
from houston.organizations.models import Organization
from houston.platform.exceptions import PlatformLifecycleDenied
from houston.platform.services import execute_platform_lifecycle


def establishment_delete_blocking_reasons(establishment: Establishment) -> list[str]:
    reasons: list[str] = []
    if establishment.status != Establishment.Status.DRAFT:
        reasons.append("establishment_not_draft")
    if OnboardingSession.objects.filter(
        establishment_id=establishment.id,
        status=OnboardingSession.Status.ACTIVATED,
    ).exists():
        reasons.append("onboarding_already_activated")
    if establishment.observations.exists():
        reasons.append("has_observations")
    if establishment.signals.exists():
        reasons.append("has_signals")
    if establishment.action_plans.exists():
        reasons.append("has_action_plans")
    if establishment.comments.exists():
        reasons.append("has_comments")
    if establishment.chat_conversations.exists():
        reasons.append("has_chat")
    return reasons


def organization_delete_blocking_reasons(organization: Organization) -> list[str]:
    reasons: list[str] = []
    if organization.has_been_operational:
        reasons.append("has_been_operational")
    if organization.establishments.exists():
        reasons.append("has_establishments")
    if OperationalPattern.objects.filter(organization_id=organization.id).exists():
        reasons.append("has_operational_patterns")
    return reasons


def delete_platform_establishment(
    *,
    operator: User,
    establishment: Establishment,
    justification: str,
) -> None:
    normalized = justification.strip()
    if not normalized:
        raise PlatformLifecycleDenied("justification_required")

    def mutate():
        locked = Establishment.objects.select_for_update().get(pk=establishment.pk)
        reasons = establishment_delete_blocking_reasons(locked)
        if reasons:
            raise PlatformLifecycleDenied("establishment_not_deletable")
        locked.delete()

    execute_platform_lifecycle(
        operator=operator,
        action="delete_establishment",
        resource_type="establishment",
        resource_id=establishment.id,
        mutate=mutate,
        justification=normalized,
    )


def delete_platform_organization(
    *,
    operator: User,
    organization: Organization,
    justification: str,
) -> None:
    normalized = justification.strip()
    if not normalized:
        raise PlatformLifecycleDenied("justification_required")

    def mutate():
        locked = Organization.objects.select_for_update().get(pk=organization.pk)
        reasons = organization_delete_blocking_reasons(locked)
        if reasons:
            raise PlatformLifecycleDenied("organization_not_deletable")
        locked.delete()

    execute_platform_lifecycle(
        operator=operator,
        action="delete_organization",
        resource_type="organization",
        resource_id=organization.id,
        mutate=mutate,
        justification=normalized,
    )
