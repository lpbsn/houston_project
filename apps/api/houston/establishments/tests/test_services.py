import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.ai.models import AIUsageLog
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    MembershipScope,
    OnboardingSession,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
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
from houston.establishments.tests.conftest import (
    HOTEL_HEBERGEMENT_DOMAIN_KEY,
    READINESS_DOMAIN_KEYS,
    first_catalog_subject_for_domain,
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
            (HOTEL_HEBERGEMENT_DOMAIN_KEY, "Hébergement"),
            ("hotel__reception_hall", "Réception / Hall"),
            ("hotel__parties_communes", "Parties communes"),
        ]
    ]
    director = User.objects.create_user(
        username="director_ready_runtime",
        password="secret",
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.INVITED,
    )
    domains_by_key = {domain.key: domain for domain in domains}
    for domain_key in READINESS_DOMAIN_KEYS:
        subject_key, subject_label = first_catalog_subject_for_domain(domain_key)
        OperationalSubject.objects.create(
            establishment=establishment,
            operational_domain=domains_by_key[domain_key],
            key=subject_key,
            label=subject_label,
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
        "insufficient_active_subjects",
        "missing_active_or_invited_director",
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
    assert readiness["counts"]["active_or_invited_director_count"] == 1
    assert all(section["is_ready"] for section in readiness["sections"].values())


def test_activation_readiness_blocks_when_active_domains_lack_subjects(
    onboarding_session,
    owner,
):
    establishment = onboarding_session.establishment
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description="A" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        submitted_by=owner,
        validated_at=timezone.now(),
    )
    OperationalModule.objects.create(establishment=establishment, key="hotel", label="Hotel")
    for key in READINESS_DOMAIN_KEYS:
        OperationalDomain.objects.create(
            establishment=establishment,
            key=key,
            label=key.replace("__", " ").replace("_", " ").title(),
        )
    manager = User.objects.create_user(
        username="manager_domains_without_subjects",
        password="secret",
        status=User.Status.ACTIVE,
    )
    manager_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.INVITED,
    )
    MembershipScope.objects.create(
        membership=manager_membership,
        operational_domain=OperationalDomain.objects.get(
            establishment=establishment,
            key=HOTEL_HEBERGEMENT_DOMAIN_KEY,
        ),
    )

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert "insufficient_active_subjects" in blocker_codes(readiness)
    assert "domains_without_active_subjects" in blocker_codes(readiness)
    assert readiness["counts"]["active_domains_without_subjects_count"] == 3


def test_activation_readiness_blocks_when_one_active_domain_lacks_subjects(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)
    establishment = onboarding_session.establishment
    OperationalSubject.objects.filter(establishment=establishment).filter(
        operational_domain__key="hotel__reception_hall",
    ).delete()

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert "domains_without_active_subjects" in blocker_codes(readiness)
    assert readiness["counts"]["active_subjects_count"] >= 1
    assert readiness["counts"]["active_domains_without_subjects_count"] == 1


def test_manager_invited_does_not_satisfy_readiness(onboarding_session, owner):
    establishment = onboarding_session.establishment
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description="A" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        submitted_by=owner,
        validated_at=timezone.now(),
    )
    OperationalModule.objects.create(establishment=establishment, key="hotel", label="Hotel")
    for key in READINESS_DOMAIN_KEYS:
        OperationalDomain.objects.create(
            establishment=establishment,
            key=key,
            label=key.replace("__", " ").replace("_", " ").title(),
        )
    manager = User.objects.create_user(
        username="manager_only_readiness",
        password="secret",
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=manager,
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.INVITED,
    )

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert "missing_active_or_invited_director" in blocker_codes(readiness)
    assert readiness["counts"]["active_or_invited_director_count"] == 0


def test_owner_alone_does_not_satisfy_director_readiness(onboarding_session, owner):
    establishment = onboarding_session.establishment
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description="A" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        submitted_by=owner,
        validated_at=timezone.now(),
    )
    OperationalModule.objects.create(establishment=establishment, key="hotel", label="Hotel")
    domains = [
        OperationalDomain.objects.create(
            establishment=establishment,
            key=key,
            label=key.replace("__", " ").replace("_", " ").title(),
        )
        for key in READINESS_DOMAIN_KEYS
    ]
    domains_by_key = {domain.key: domain for domain in domains}
    for domain_key in READINESS_DOMAIN_KEYS:
        subject_key, subject_label = first_catalog_subject_for_domain(domain_key)
        OperationalSubject.objects.create(
            establishment=establishment,
            operational_domain=domains_by_key[domain_key],
            key=subject_key,
            label=subject_label,
        )

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert "missing_active_or_invited_director" in blocker_codes(readiness)
    assert readiness["counts"]["active_owner_or_director_count"] == 1
    assert readiness["counts"]["active_or_invited_director_count"] == 0


def test_deactivated_director_does_not_satisfy_activation_readiness(onboarding_session, owner):
    create_ready_runtime(onboarding_session, owner)
    director_membership = EstablishmentMembership.objects.get(
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    director_membership.status = EstablishmentMembership.Status.DEACTIVATED
    director_membership.save(update_fields=["status", "updated_at"])

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert "missing_active_or_invited_director" in blocker_codes(readiness)
    assert readiness["counts"]["active_or_invited_director_count"] == 0


def test_active_director_satisfies_readiness(onboarding_session, owner):
    create_ready_runtime(onboarding_session, owner)
    director_membership = EstablishmentMembership.objects.get(
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    director_membership.status = EstablishmentMembership.Status.ACTIVE
    director_membership.save(update_fields=["status", "updated_at"])

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is True
    assert readiness["counts"]["active_or_invited_director_count"] == 1


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
    MembershipScope.objects.create(
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
    director_membership = EstablishmentMembership.objects.get(
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    director_membership.status = EstablishmentMembership.Status.ACTIVE
    director_membership.save(update_fields=["status", "updated_at"])
    director = director_membership.user
    director.status = User.Status.ACTIVE
    director.save(update_fields=["status", "updated_at"])
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
    MembershipScope.objects.create(
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
