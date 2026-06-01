from __future__ import annotations

from django.db import models
from django.db.models import Prefetch, Q

from houston.accounts.models import User
from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import (
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    OnboardingProposal,
    OnboardingSession,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
    OperationalUnit,
    RoutingHint,
    RoutingHintDomain,
    RuntimeTag,
    RuntimeTagDomain,
    RuntimeVocabulary,
)
from houston.organizations.models import Organization

_ONBOARDING_MANAGEMENT_ROLES = (
    EstablishmentMembership.Role.OWNER,
    EstablishmentMembership.Role.DIRECTOR,
)
_ONBOARDING_ESTABLISHMENT_STATUSES = (
    Establishment.Status.DRAFT,
    Establishment.Status.ACTIVE,
)


def list_memberships_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
) -> list[EstablishmentMembership] | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    return list(_management_membership_queryset(establishment_id=establishment_id))


def get_membership_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    membership_id,
) -> EstablishmentMembership | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    return (
        _management_membership_queryset(establishment_id=establishment_id)
        .filter(id=membership_id)
        .first()
    )


def get_workspace_summary_for_establishment(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
) -> dict | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    establishment = current_membership.establishment

    owner_membership = (
        EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
        )
        .select_related("user")
        .order_by("created_at", "id")
        .first()
    )

    director_membership = (
        EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            role=EstablishmentMembership.Role.DIRECTOR,
            status__in=[
                EstablishmentMembership.Status.ACTIVE,
                EstablishmentMembership.Status.INVITED,
            ],
        )
        .select_related("user")
        .order_by(
            models.Case(
                models.When(status=EstablishmentMembership.Status.ACTIVE, then=0),
                default=1,
            ),
            "created_at",
            "id",
        )
        .first()
    )

    active_membership_count = EstablishmentMembership.objects.filter(
        establishment_id=establishment_id,
        status=EstablishmentMembership.Status.ACTIVE,
    ).count()

    return {
        "establishment": {
            "id": establishment.id,
            "name": establishment.name,
        },
        "owner": _serialize_workspace_person(owner_membership),
        "director": _serialize_workspace_director(director_membership),
        "active_membership_count": active_membership_count,
    }


def _serialize_workspace_person(membership: EstablishmentMembership | None) -> dict | None:
    if membership is None:
        return None

    return {"display_name": _membership_display_name(membership.user)}


def _serialize_workspace_director(membership: EstablishmentMembership | None) -> dict | None:
    if membership is None:
        return None

    return {
        "display_name": _membership_display_name(membership.user),
        "status": membership.status,
    }


def _membership_display_name(user: User) -> str:
    full_name = user.get_full_name().strip()
    if full_name:
        return full_name

    if user.username:
        return user.username

    if user.email:
        return user.email

    return str(user.id)


def search_users_for_establishment(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    query: str,
) -> list[EstablishmentMembership] | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    normalized_query = query.strip()
    if not normalized_query:
        return []

    return list(
        _management_membership_queryset(establishment_id=establishment_id)
        .filter(
            user__status=User.Status.ACTIVE,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .filter(
            Q(user__first_name__icontains=normalized_query)
            | Q(user__last_name__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(user__email__icontains=normalized_query)
        )
    )


def get_onboarding_session_for_actor(
    *,
    actor: User,
    session_id,
) -> OnboardingSession | None:
    if actor.status != User.Status.ACTIVE:
        return None

    return _onboarding_session_queryset_for_actor(actor).filter(id=session_id).first()


def list_onboarding_sessions_for_actor(*, actor: User) -> list[OnboardingSession]:
    if actor.status != User.Status.ACTIVE:
        return []

    return list(_onboarding_session_queryset_for_actor(actor))


def get_active_onboarding_session_for_establishment(
    *,
    actor: User,
    establishment_id,
) -> OnboardingSession | None:
    if actor.status != User.Status.ACTIVE:
        return None

    return (
        _onboarding_session_queryset_for_actor(actor)
        .filter(
            establishment_id=establishment_id,
            status__in=OnboardingSession.NON_TERMINAL_STATUSES,
        )
        .first()
    )


def list_onboarding_proposals_for_actor(
    *,
    actor: User,
    session_id,
) -> list[OnboardingProposal] | None:
    session = get_onboarding_session_for_actor(actor=actor, session_id=session_id)
    if session is None:
        return None

    return list(_onboarding_proposal_queryset(session_id=session.id))


def get_onboarding_proposal_for_actor(
    *,
    actor: User,
    session_id,
    proposal_id,
) -> OnboardingProposal | None:
    session = get_onboarding_session_for_actor(actor=actor, session_id=session_id)
    if session is None:
        return None

    return _onboarding_proposal_queryset(session_id=session.id).filter(id=proposal_id).first()


def get_runtime_config_for_session(*, session: OnboardingSession) -> dict:
    establishment_id = session.establishment_id

    return {
        "activity_description": _get_activity_description(establishment_id),
        "active_modules": list(
            OperationalModule.objects.filter(
                establishment_id=establishment_id,
                active=True,
            ).order_by("key", "id")
        ),
        "active_domains": list(
            OperationalDomain.objects.filter(
                establishment_id=establishment_id,
                active=True,
            )
            .select_related("operational_module")
            .order_by("key", "id")
        ),
        "active_subjects": list(
            OperationalSubject.objects.filter(
                establishment_id=establishment_id,
                active=True,
            )
            .select_related("operational_domain", "operational_domain__operational_module")
            .order_by("key", "id")
        ),
        "optional_units": list(
            OperationalUnit.objects.filter(
                establishment_id=establishment_id,
                active=True,
            ).order_by("key", "id")
        ),
        "optional_vocabulary": list(
            RuntimeVocabulary.objects.filter(
                establishment_id=establishment_id,
                active=True,
            )
            .select_related("mapped_domain", "mapped_unit")
            .order_by("term", "id")
        ),
        "optional_runtime_tags": list(
            RuntimeTag.objects.filter(
                establishment_id=establishment_id,
                active=True,
            )
            .prefetch_related(
                Prefetch(
                    "domain_links",
                    queryset=RuntimeTagDomain.objects.select_related(
                        "operational_domain",
                    )
                    .filter(operational_domain__active=True)
                    .order_by("operational_domain__key"),
                )
            )
            .order_by("key", "id")
        ),
        "optional_routing_hints": list(
            RoutingHint.objects.filter(
                establishment_id=establishment_id,
                active=True,
            )
            .select_related("suggested_unit")
            .prefetch_related(
                Prefetch(
                    "domain_links",
                    queryset=RoutingHintDomain.objects.select_related(
                        "operational_domain",
                    )
                    .filter(operational_domain__active=True)
                    .order_by("operational_domain__key"),
                )
            )
            .order_by("pattern", "id")
        ),
    }


def _onboarding_session_queryset_for_actor(actor: User):
    accessible_establishment_ids = EstablishmentMembership.objects.filter(
        user=actor,
        status=EstablishmentMembership.Status.ACTIVE,
        role__in=_ONBOARDING_MANAGEMENT_ROLES,
        establishment__status__in=_ONBOARDING_ESTABLISHMENT_STATUSES,
        establishment__organization__status=Organization.Status.ACTIVE,
    ).values("establishment_id")

    return (
        OnboardingSession.objects.filter(
            establishment_id__in=accessible_establishment_ids,
            organization_id=models.F("establishment__organization_id"),
            establishment__status__in=_ONBOARDING_ESTABLISHMENT_STATUSES,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related(
            "organization",
            "establishment",
            "establishment__organization",
            "started_by",
        )
        .order_by("-updated_at", "-created_at", "id")
    )


def _onboarding_proposal_queryset(*, session_id):
    return (
        OnboardingProposal.objects.filter(onboarding_session_id=session_id)
        .select_related(
            "onboarding_session",
            "onboarding_session__organization",
            "onboarding_session__establishment",
            "establishment",
            "created_by",
            "validated_by",
            "applied_by",
        )
        .order_by("-updated_at", "-created_at", "id")
    )


def _get_activity_description(establishment_id):
    return (
        EstablishmentActivityDescription.objects.filter(establishment_id=establishment_id)
        .select_related("submitted_by")
        .first()
    )


def _management_membership_queryset(*, establishment_id):
    return (
        EstablishmentMembership.objects.filter(establishment_id=establishment_id)
        .select_related("user", "establishment", "establishment__organization")
        .prefetch_related(membership_scope_prefetch())
        .order_by("user__username", "user__email", "id")
    )

def get_operational_taxonomy_for_establishment(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
) -> dict | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    if current_membership.status != EstablishmentMembership.Status.ACTIVE:
        return None

    modules = list(
        OperationalModule.objects.filter(
            establishment_id=establishment_id,
            active=True,
        ).order_by("label", "key", "id")
    )
    domains = list(
        OperationalDomain.objects.filter(
            establishment_id=establishment_id,
            active=True,
        ).order_by("label", "key", "id")
    )
    subjects = list(
        OperationalSubject.objects.filter(
            establishment_id=establishment_id,
            active=True,
        ).order_by("label", "key", "id")
    )

    domains_by_module: dict = {}
    for domain in domains:
        domains_by_module.setdefault(domain.operational_module_id, []).append(domain)

    subjects_by_domain: dict = {}
    for subject in subjects:
        subjects_by_domain.setdefault(subject.operational_domain_id, []).append(subject)

    module_payload = []
    for module in modules:
        domain_payload = []
        for domain in domains_by_module.get(module.id, []):
            domain_payload.append(
                {
                    "id": domain.id,
                    "key": domain.key,
                    "label": domain.label,
                    "subjects": [
                        {
                            "id": subject.id,
                            "key": subject.key,
                            "label": subject.label,
                        }
                        for subject in subjects_by_domain.get(domain.id, [])
                    ],
                }
            )
        module_payload.append(
            {
                "id": module.id,
                "key": module.key,
                "label": module.label,
                "domains": domain_payload,
            }
        )

    unassigned_domains = []
    for domain in domains_by_module.get(None, []):
        unassigned_domains.append(
            {
                "id": domain.id,
                "key": domain.key,
                "label": domain.label,
                "subjects": [
                    {
                        "id": subject.id,
                        "key": subject.key,
                        "label": subject.label,
                    }
                    for subject in subjects_by_domain.get(domain.id, [])
                ],
            }
        )

    return {
        "modules": module_payload,
        "unassigned_domains": unassigned_domains,
    }

