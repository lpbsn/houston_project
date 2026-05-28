import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    MembershipDomain,
    OnboardingSession,
    OperationalDomain,
    OperationalModule,
    OperationalUnit,
    RoutingHint,
    RoutingHintDomain,
    RuntimeTag,
    RuntimeTagDomain,
    RuntimeVocabulary,
)
from houston.establishments.selectors import (
    get_activation_summary_for_session,
    get_active_onboarding_session_for_establishment,
    get_onboarding_session_for_actor,
    get_runtime_config_for_session,
    list_onboarding_sessions_for_actor,
)
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
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    foreign_domain = OperationalDomain.objects.create(
        establishment=foreign_establishment,
        key="maintenance",
        label="Maintenance",
    )
    OperationalModule.objects.create(establishment=establishment, key="hotel", label="Hotel")
    OperationalModule.objects.create(
        establishment=foreign_establishment,
        key="restaurant",
        label="Restaurant",
    )
    unit = OperationalUnit.objects.create(
        establishment=establishment,
        key="lobby",
        label="Lobby",
    )
    RuntimeVocabulary.objects.create(
        establishment=establishment,
        term="VRV",
        meaning="HVAC",
        mapped_domain=domain,
        mapped_unit=unit,
    )
    RuntimeVocabulary.objects.create(
        establishment=foreign_establishment,
        term="foreign",
        meaning="Foreign",
        mapped_domain=foreign_domain,
    )
    tag = RuntimeTag.objects.create(
        establishment=establishment,
        key="hvac",
        label="HVAC",
    )
    RuntimeTagDomain.objects.create(runtime_tag=tag, operational_domain=domain)
    hint = RoutingHint.objects.create(
        establishment=establishment,
        pattern="VRV",
        suggested_unit=unit,
    )
    RoutingHintDomain.objects.create(routing_hint=hint, operational_domain=domain)

    config = get_runtime_config_for_session(session=session)

    assert [item.key for item in config["active_modules"]] == ["hotel"]
    assert [item.key for item in config["active_domains"]] == ["maintenance"]
    assert [item.key for item in config["optional_units"]] == ["lobby"]
    assert [item.term for item in config["optional_vocabulary"]] == ["VRV"]
    assert [item.key for item in config["optional_runtime_tags"]] == ["hvac"]
    assert [item.pattern for item in config["optional_routing_hints"]] == ["VRV"]


def test_activation_summary_selector_uses_active_module_and_domain_names(
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
    OperationalModule.objects.create(establishment=establishment, key="hotel", label="Hotel")
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
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
    MembershipDomain.objects.create(
        membership=manager_membership,
        operational_domain=domain,
    )

    summary = get_activation_summary_for_session(session=session)

    assert "active_modules" in summary
    assert "active_domains" in summary
    assert "validated_modules" not in summary
    assert "validated_domains" not in summary
    assert summary["active_modules"][0]["key"] == "hotel"
    assert summary["active_domains"][0]["key"] == "maintenance"
