import pytest

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.establishments.services import (
    build_activation_summary,
    compute_activation_readiness,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.organizations.models import Organization
from houston.testing.onboarding import create_ready_runtime

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


def test_activation_readiness_returns_blockers_when_setup_is_empty(onboarding_session):
    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert blocker_codes(readiness) == {
        "missing_or_invalid_activity_description",
        "missing_active_business_unit",
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
    assert readiness["counts"]["active_business_units_count"] == 1
    assert readiness["counts"]["active_activity_subjects_count"] == 1
    assert readiness["counts"]["active_owner_or_director_count"] == 1
    assert readiness["counts"]["active_or_invited_director_count"] == 1
    assert all(section["is_ready"] for section in readiness["sections"].values())


def test_activation_readiness_blocks_when_active_business_units_lack_subjects(
    onboarding_session,
    owner,
):
    establishment = onboarding_session.establishment
    create_business_unit(establishment=establishment, key="coworking", label="Coworking")
    create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    director = User.objects.create_user(
        username="director_bu_without_subjects",
        password="secret",
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.INVITED,
    )

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert "business_units_without_active_subjects" in blocker_codes(readiness)
    assert readiness["counts"]["active_business_units_without_subjects_count"] == 2


def test_activation_readiness_blocks_when_one_active_business_unit_lacks_subjects(
    onboarding_session,
    owner,
):
    establishment = onboarding_session.establishment
    staffed_business_unit = create_business_unit(
        establishment=establishment,
        key="coworking",
        label="Coworking",
    )
    create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    create_activity_subject(
        establishment=establishment,
        business_unit=staffed_business_unit,
        label="Propreté",
    )
    director = User.objects.create_user(
        username="director_one_bu_without_subjects",
        password="secret",
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.INVITED,
    )

    readiness = compute_activation_readiness(session=onboarding_session)

    assert readiness["is_ready"] is False
    assert "business_units_without_active_subjects" in blocker_codes(readiness)
    assert readiness["counts"]["active_activity_subjects_count"] == 1
    assert readiness["counts"]["active_business_units_without_subjects_count"] == 1


def test_manager_invited_does_not_satisfy_readiness(onboarding_session, owner):
    establishment = onboarding_session.establishment
    business_unit = create_business_unit(
        establishment=establishment,
        key="coworking",
        label="Coworking",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=business_unit,
        label="Propreté",
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
    business_unit = create_business_unit(
        establishment=establishment,
        key="coworking",
        label="Coworking",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=business_unit,
        label="Propreté",
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


def test_activity_description_blocks_readiness_when_missing(onboarding_session, owner):
    create_ready_runtime(onboarding_session, owner)
    EstablishmentActivityDescription.objects.filter(
        establishment=onboarding_session.establishment,
    ).delete()

    readiness = compute_activation_readiness(session=onboarding_session)

    assert "activity_description" in readiness["sections"]
    assert readiness["sections"]["activity_description"]["is_ready"] is False
    assert readiness["is_ready"] is False
    assert "missing_or_invalid_activity_description" in blocker_codes(readiness)

def test_build_activation_summary_includes_business_units_and_readiness(
    onboarding_session,
    owner,
):
    create_ready_runtime(onboarding_session, owner)

    summary = build_activation_summary(session=onboarding_session)

    assert summary["active_business_units"][0]["generic"]["key"] == "coworking"
    assert summary["readiness"]["is_ready"] is True
    assert summary["blockers"] == []
