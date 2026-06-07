import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    MembershipScope,
    OnboardingSession,
    OperationalUnit,
)
from houston.establishments.selectors import (
    get_active_onboarding_session_for_establishment,
    get_onboarding_session_for_actor,
    get_runtime_config_for_session,
    list_onboarding_sessions_for_actor,
)
from houston.establishments.services import build_activation_summary
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(name="Mama Shelter")


@pytest.fixture
def actor():
    return User.objects.create_user(
        username="owner_selector",
        password="secret",
        status=User.Status.ACTIVE,
    )


def create_session_with_membership(
    *,
    organization,
    actor,
    role=EstablishmentMembership.Role.OWNER,
    status=Establishment.Status.DRAFT,
):
    establishment = Establishment.objects.create(
        name=f"Site {Establishment.objects.count()}",
        organization=organization,
        status=status,
    )
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        started_by=actor,
    )
    EstablishmentMembership.objects.create(
        user=actor,
        establishment=establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    return session


def test_actor_can_retrieve_own_accessible_onboarding_session(organization, actor):
    session = create_session_with_membership(organization=organization, actor=actor)

    result = get_onboarding_session_for_actor(actor=actor, session_id=session.id)

    assert result == session
    assert result.establishment == session.establishment
    assert result.organization == organization


def test_actor_cannot_retrieve_foreign_onboarding_session(organization, actor):
    foreign_user = User.objects.create_user(
        username="foreign_owner",
        password="secret",
        status=User.Status.ACTIVE,
    )
    foreign_session = create_session_with_membership(
        organization=organization,
        actor=foreign_user,
    )

    result = get_onboarding_session_for_actor(actor=actor, session_id=foreign_session.id)

    assert result is None


def test_list_onboarding_sessions_returns_only_accessible_sessions(organization, actor):
    accessible_session = create_session_with_membership(
        organization=organization,
        actor=actor,
    )
    foreign_user = User.objects.create_user(
        username="foreign_list_owner",
        password="secret",
        status=User.Status.ACTIVE,
    )
    create_session_with_membership(organization=organization, actor=foreign_user)

    result = list_onboarding_sessions_for_actor(actor=actor)

    assert result == [accessible_session]


def test_active_session_selector_returns_non_terminal_same_establishment_only(
    organization,
    actor,
):
    session = create_session_with_membership(organization=organization, actor=actor)
    foreign_establishment = Establishment.objects.create(
        name="Foreign",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )

    result = get_active_onboarding_session_for_establishment(
        actor=actor,
        establishment_id=session.establishment_id,
    )
    foreign_result = get_active_onboarding_session_for_establishment(
        actor=actor,
        establishment_id=foreign_establishment.id,
    )

    assert result == session
    assert foreign_result is None


def test_runtime_config_selector_returns_only_same_establishment_data(
    organization,
    actor,
):
    session = create_session_with_membership(organization=organization, actor=actor)
    establishment = session.establishment
    foreign_establishment = Establishment.objects.create(
        name="Foreign",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    business_unit = BusinessUnit.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    foreign_business_unit = BusinessUnit.objects.create(
        establishment=foreign_establishment,
        key="restaurant",
        label="Restaurant",
    )
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name="proprete",
        label="Proprete",
    )
    ActivitySubject.objects.create(
        establishment=foreign_establishment,
        business_unit=foreign_business_unit,
        normalized_name="foreign",
        label="Foreign",
    )
    OperationalUnit.objects.create(
        establishment=establishment,
        key="lobby",
        label="Lobby",
    )

    config = get_runtime_config_for_session(session=session)

    assert [item["key"] for item in config["active_business_units"]] == ["hotel"]
    assert [item.key for item in config["optional_units"]] == ["lobby"]


def test_activation_summary_selector_exposes_active_business_units(
    organization,
    actor,
):
    session = create_session_with_membership(organization=organization, actor=actor)
    establishment = session.establishment
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description="A" * 50,
        submitted_by=actor,
        validated_at=timezone.now(),
    )
    business_unit = BusinessUnit.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name="proprete",
        label="Proprete",
    )
    manager = User.objects.create_user(
        username="manager_selector",
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
        business_unit=business_unit,
    )

    summary = build_activation_summary(session=session)

    assert "active_business_units" in summary
    assert summary["active_business_units"][0]["key"] == "hotel"
