import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.ai.models import AIUsageLog
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    MembershipDomain,
    OnboardingSession,
    OperationalDomain,
    OperationalModule,
)
from houston.establishments.services import (
    InvalidActivityDescriptionError,
    InvalidOnboardingActivationStateError,
    OnboardingAccessDeniedError,
    OnboardingReadinessError,
    OnboardingSessionTerminalError,
    activate_onboarding_session,
    build_activation_summary,
    compute_activation_readiness,
    mark_onboarding_ready_for_activation,
    submit_activity_description,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(name="Mama Shelter")


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="owner_services",
        password="secret",
        status=User.Status.ACTIVE,
    )


@pytest.fixture
def onboarding_session(organization, owner):
    establishment = Establishment.objects.create(
        name="Draft",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        started_by=owner,
    )
    EstablishmentMembership.objects.create(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    return session


def blocker_codes(readiness):
    return {blocker["code"] for blocker in readiness["blockers"]}


def create_ready_runtime(session, owner):
    establishment = session.establishment
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description="A" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        submitted_by=owner,
        validated_at=timezone.now(),
    )
    OperationalModule.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    domains = [
        OperationalDomain.objects.create(
            establishment=establishment,
            key=key,
            label=label,
        )
        for key, label in [
            ("maintenance", "Maintenance"),
            ("housekeeping", "Housekeeping"),
            ("security", "Security"),
        ]
    ]
    manager = User.objects.create_user(
        username="manager_ready_runtime",
        password="secret",
        status=User.Status.ACTIVE,
    )
    manager_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.INVITED,
    )
    MembershipDomain.objects.create(
        membership=manager_membership,
        operational_domain=domains[0],
    )
    return domains


def test_submit_valid_activity_description_updates_canonical_description_and_status(
    onboarding_session,
    owner,
):
    description = f" {'A' * ACTIVITY_DESCRIPTION_MIN_LENGTH} "

    activity_description = submit_activity_description(
        session=onboarding_session,
        actor=owner,
        description=description,
    )
    onboarding_session.refresh_from_db()

    assert activity_description.description == "A" * ACTIVITY_DESCRIPTION_MIN_LENGTH
    assert activity_description.submitted_by == owner
    assert activity_description.validated_at is not None
    assert onboarding_session.status == OnboardingSession.Status.DESCRIPTION_SUBMITTED


def test_submit_too_short_activity_description_is_rejected(onboarding_session, owner):
    with pytest.raises(InvalidActivityDescriptionError):
        submit_activity_description(
            session=onboarding_session,
            actor=owner,
            description="A" * (ACTIVITY_DESCRIPTION_MIN_LENGTH - 1),
        )

    assert not EstablishmentActivityDescription.objects.filter(
        establishment=onboarding_session.establishment,
    ).exists()


def test_submit_activity_description_rejects_terminal_session(onboarding_session, owner):
    onboarding_session.status = OnboardingSession.Status.CANCELED
    onboarding_session.save(update_fields=["status", "updated_at"])

    with pytest.raises(OnboardingSessionTerminalError):
        submit_activity_description(
            session=onboarding_session,
            actor=owner,
            description="A" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        )


def test_submit_activity_description_reopens_ready_session_to_validation(
    onboarding_session,
    owner,
):
    onboarding_session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    onboarding_session.ready_for_activation_at = timezone.now()
    onboarding_session.save(
        update_fields=["status", "ready_for_activation_at", "updated_at"],
    )

    submit_activity_description(
        session=onboarding_session,
        actor=owner,
        description="B" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
    )
    onboarding_session.refresh_from_db()

    assert onboarding_session.status == OnboardingSession.Status.VALIDATING_SECTIONS
    assert onboarding_session.ready_for_activation_at is None


def test_activation_readiness_returns_blockers_when_setup_is_empty(onboarding_session):
    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert blocker_codes(readiness) == {
        "missing_validated_description",
        "missing_active_module",
        "insufficient_active_domains",
        "missing_active_or_invited_manager",
    }
    assert "required_sections_not_validated" not in blocker_codes(readiness)


def test_activation_readiness_passes_when_minimum_criteria_are_met(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is True
    assert readiness["blockers"] == []
    assert readiness["counts"]["active_modules_count"] == 1
    assert readiness["counts"]["active_domains_count"] == 3
    assert readiness["counts"]["active_owner_or_director_count"] == 1
    assert readiness["counts"]["active_or_invited_manager_count"] == 1
    assert readiness["counts"]["managers_with_domains_count"] == 1
    assert all(section["is_ready"] for section in readiness["sections"].values())


def test_manager_without_domains_blocks_readiness(onboarding_session, owner):
    establishment = onboarding_session.establishment
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description="A" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        submitted_by=owner,
        validated_at=timezone.now(),
    )
    OperationalModule.objects.create(establishment=establishment, key="hotel", label="Hotel")
    for key in ["maintenance", "housekeeping", "security"]:
        OperationalDomain.objects.create(establishment=establishment, key=key, label=key.title())
    manager = User.objects.create_user(
        username="manager_without_domains",
        password="secret",
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert "manager_domains_missing" in blocker_codes(readiness)


def test_optional_sections_do_not_block_readiness(onboarding_session, owner):
    create_ready_runtime(onboarding_session, owner)

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["sections"]["units"]["is_skippable"] is True
    assert readiness["sections"]["vocabulary"]["is_skippable"] is True
    assert readiness["sections"]["runtime_tags"]["is_skippable"] is True
    assert readiness["sections"]["routing_hints"]["is_skippable"] is True
    assert readiness["is_ready"] is True


def test_mark_ready_sets_ready_status_only_when_effectively_allowed(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)

    result = mark_onboarding_ready_for_activation(
        session=onboarding_session,
        actor=owner,
    )
    onboarding_session.refresh_from_db()

    assert result["readiness"]["is_ready"] is True
    assert result["access"].can_activate is True
    assert result["effective_can_activate"] is True
    assert onboarding_session.status == OnboardingSession.Status.READY_FOR_ACTIVATION
    assert onboarding_session.activated_at is None
    assert onboarding_session.establishment.status == Establishment.Status.DRAFT


def test_mark_ready_does_not_change_status_when_readiness_fails(
    onboarding_session,
    owner,
):
    with pytest.raises(OnboardingReadinessError) as exc_info:
        mark_onboarding_ready_for_activation(
            session=onboarding_session,
            actor=owner,
        )
    onboarding_session.refresh_from_db()

    assert exc_info.value.readiness["is_ready"] is False
    assert onboarding_session.status == OnboardingSession.Status.STARTED
    assert onboarding_session.ready_for_activation_at is None


def test_mark_ready_denies_manager_even_when_readiness_passes(onboarding_session, owner):
    domains = create_ready_runtime(onboarding_session, owner)
    manager = User.objects.create_user(
        username="manager_denied_ready",
        password="secret",
        status=User.Status.ACTIVE,
    )
    manager_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    MembershipDomain.objects.create(
        membership=manager_membership,
        operational_domain=domains[0],
    )

    readiness = compute_activation_readiness(session=onboarding_session)
    assert readiness["is_ready"] is True

    with pytest.raises(OnboardingAccessDeniedError):
        mark_onboarding_ready_for_activation(
            session=onboarding_session,
            actor=manager,
        )


def test_activate_onboarding_session_success_for_owner(onboarding_session, owner):
    create_ready_runtime(onboarding_session, owner)
    mark_onboarding_ready_for_activation(session=onboarding_session, actor=owner)
    onboarding_session.refresh_from_db()
    ready_at = onboarding_session.ready_for_activation_at

    result = activate_onboarding_session(session=onboarding_session, actor=owner)
    onboarding_session.refresh_from_db()
    onboarding_session.establishment.refresh_from_db()

    assert result["activated"] is True
    assert result["effective_can_activate"] is True
    assert onboarding_session.status == OnboardingSession.Status.ACTIVATED
    assert onboarding_session.activated_at is not None
    assert onboarding_session.ready_for_activation_at == ready_at
    assert onboarding_session.establishment.status == Establishment.Status.ACTIVE
    assert AIUsageLog.objects.count() == 0


def test_activate_onboarding_session_success_for_director(onboarding_session, owner):
    create_ready_runtime(onboarding_session, owner)
    director = User.objects.create_user(
        username="director_activate",
        password="secret",
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=director,
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    mark_onboarding_ready_for_activation(session=onboarding_session, actor=director)

    activate_onboarding_session(session=onboarding_session, actor=director)
    onboarding_session.refresh_from_db()
    onboarding_session.establishment.refresh_from_db()

    assert onboarding_session.status == OnboardingSession.Status.ACTIVATED
    assert onboarding_session.establishment.status == Establishment.Status.ACTIVE


def test_activate_onboarding_session_is_idempotent_for_same_activated_session(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)
    mark_onboarding_ready_for_activation(session=onboarding_session, actor=owner)
    activate_onboarding_session(session=onboarding_session, actor=owner)
    onboarding_session.refresh_from_db()
    activated_at = onboarding_session.activated_at

    result = activate_onboarding_session(session=onboarding_session, actor=owner)
    onboarding_session.refresh_from_db()

    assert result["activated"] is False
    assert onboarding_session.status == OnboardingSession.Status.ACTIVATED
    assert onboarding_session.activated_at == activated_at


def test_activate_onboarding_session_requires_mark_ready_status(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)

    with pytest.raises(InvalidOnboardingActivationStateError):
        activate_onboarding_session(session=onboarding_session, actor=owner)

    onboarding_session.refresh_from_db()
    onboarding_session.establishment.refresh_from_db()
    assert onboarding_session.status == OnboardingSession.Status.STARTED
    assert onboarding_session.establishment.status == Establishment.Status.DRAFT


def test_activate_onboarding_session_requires_ready_timestamp(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)
    onboarding_session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    onboarding_session.ready_for_activation_at = None
    onboarding_session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    with pytest.raises(InvalidOnboardingActivationStateError):
        activate_onboarding_session(session=onboarding_session, actor=owner)

    onboarding_session.refresh_from_db()
    onboarding_session.establishment.refresh_from_db()
    assert onboarding_session.status == OnboardingSession.Status.READY_FOR_ACTIVATION
    assert onboarding_session.establishment.status == Establishment.Status.DRAFT


def test_activate_onboarding_session_rejects_active_establishment_before_activation(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)
    onboarding_session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    onboarding_session.ready_for_activation_at = timezone.now()
    onboarding_session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])
    onboarding_session.establishment.status = Establishment.Status.ACTIVE
    onboarding_session.establishment.save(update_fields=["status", "updated_at"])

    with pytest.raises(InvalidOnboardingActivationStateError):
        activate_onboarding_session(session=onboarding_session, actor=owner)

    onboarding_session.refresh_from_db()
    assert onboarding_session.status == OnboardingSession.Status.READY_FOR_ACTIVATION
    assert onboarding_session.activated_at is None


def test_activate_onboarding_session_recomputes_readiness_before_transition(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)
    mark_onboarding_ready_for_activation(session=onboarding_session, actor=owner)
    OperationalModule.objects.filter(establishment=onboarding_session.establishment).update(
        active=False,
    )

    with pytest.raises(OnboardingReadinessError) as exc_info:
        activate_onboarding_session(session=onboarding_session, actor=owner)

    onboarding_session.refresh_from_db()
    onboarding_session.establishment.refresh_from_db()
    assert "missing_active_module" in blocker_codes(exc_info.value.readiness)
    assert onboarding_session.status == OnboardingSession.Status.READY_FOR_ACTIVATION
    assert onboarding_session.establishment.status == Establishment.Status.DRAFT


def test_activate_onboarding_session_denies_manager_even_when_ready(
    onboarding_session,
    owner,
):
    domains = create_ready_runtime(onboarding_session, owner)
    manager = User.objects.create_user(
        username="manager_denied_activation",
        password="secret",
        status=User.Status.ACTIVE,
    )
    manager_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    MembershipDomain.objects.create(
        membership=manager_membership,
        operational_domain=domains[0],
    )
    mark_onboarding_ready_for_activation(session=onboarding_session, actor=owner)

    with pytest.raises(OnboardingAccessDeniedError):
        activate_onboarding_session(session=onboarding_session, actor=manager)


def test_activate_onboarding_session_rejects_terminal_nonactivated_session(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)
    onboarding_session.status = OnboardingSession.Status.CANCELED
    onboarding_session.save(update_fields=["status", "updated_at"])

    with pytest.raises(InvalidOnboardingActivationStateError):
        activate_onboarding_session(session=onboarding_session, actor=owner)


def test_build_activation_summary_uses_active_module_and_domain_names(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)

    summary = build_activation_summary(session=onboarding_session)

    assert "active_modules" in summary
    assert "active_domains" in summary
    assert "validated_modules" not in summary
    assert "validated_domains" not in summary
    assert summary["active_modules"][0]["key"] == "hotel"
    assert len(summary["active_domains"]) == 3
    assert summary["readiness"]["is_ready"] is True
    assert summary["blockers"] == []
