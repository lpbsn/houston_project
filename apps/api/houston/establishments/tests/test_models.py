import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from houston.accounts.models import User
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    BusinessUnit,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    MembershipScope,
    OnboardingProposal,
    OnboardingSession,
)
from houston.establishments.services import (
    InvalidOnboardingSessionScopeError,
    UnsupportedOnboardingSessionSourceModeError,
    start_onboarding_session,
)
from houston.organizations.models import Organization
from houston.testing.taxonomy import create_activity_subject, create_business_unit

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(name="Mama Shelter")


@pytest.fixture
def establishment(organization):
    return Establishment.objects.create(name="Nice", organization=organization)


def test_establishment_defaults_to_europe_paris_timezone(organization):
    establishment = Establishment.objects.create(name="Paris Pilot", organization=organization)
    assert establishment.timezone == "Europe/Paris"


def test_establishment_rejects_invalid_timezone(establishment):
    establishment.timezone = "Not/A/Timezone"
    with pytest.raises(ValidationError):
        establishment.full_clean()


@pytest.fixture
def user():
    return User.objects.create_user(username="manager_01", password="secret")


def test_establishment_belongs_to_organization(establishment, organization):
    assert establishment.organization == organization


def test_establishment_status_default(organization):
    establishment = Establishment.objects.create(name="Nice", organization=organization)
    assert establishment.status == Establishment.Status.DRAFT


def test_membership_links_user_and_establishment(user, establishment):
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
    )
    assert membership.user == user
    assert membership.establishment == establishment


def test_membership_role_and_status_defaults(user, establishment):
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
    )
    assert membership.role == EstablishmentMembership.Role.STAFF
    assert membership.status == EstablishmentMembership.Status.INVITED


def test_business_unit_unique_normalized_specific_name_per_establishment(
    establishment,
    imported_catalog,
):
    import uuid

    from houston.establishments.business_unit_identity import (
        build_business_unit_routing_key,
        normalize_business_unit_specific_name,
    )
    from houston.establishments.models import CatalogBusinessUnit

    catalog = CatalogBusinessUnit.objects.get(key="maintenance")
    business_unit_id = uuid.uuid4()
    BusinessUnit.objects.create(
        id=business_unit_id,
        establishment=establishment,
        catalog_business_unit=catalog,
        specific_name="Maintenance",
        normalized_specific_name=normalize_business_unit_specific_name("Maintenance"),
        routing_key=build_business_unit_routing_key(
            business_unit_id=business_unit_id,
            catalog_key=catalog.key,
            specific_name="Maintenance",
        ),
        instance_description="",
        source=BusinessUnit.Source.MANUAL,
        active=True,
    )
    with pytest.raises(IntegrityError):
        duplicate_id = uuid.uuid4()
        BusinessUnit.objects.create(
            id=duplicate_id,
            establishment=establishment,
            catalog_business_unit=catalog,
            specific_name="Maintenance",
            normalized_specific_name=normalize_business_unit_specific_name("Maintenance"),
            routing_key=build_business_unit_routing_key(
                business_unit_id=duplicate_id,
                catalog_key=catalog.key,
                specific_name="Maintenance",
            ),
            instance_description="",
            source=BusinessUnit.Source.MANUAL,
            active=True,
        )


def test_business_unit_same_catalog_key_allowed_across_establishments(organization, establishment):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    first = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    second = create_business_unit(
        establishment=other_establishment,
        key="maintenance",
        label="Maintenance",
    )
    assert first.catalog_business_unit_id == second.catalog_business_unit_id


def test_activity_subject_unique_per_business_unit(establishment):
    bu = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=bu,
        label="Plomberie",
    )
    with pytest.raises(IntegrityError):
        create_activity_subject(
            establishment=establishment,
            business_unit=bu,
            label="Plomberie",
        )


def test_membership_unique_user_establishment_constraint(user, establishment):
    EstablishmentMembership.objects.create(user=user, establishment=establishment)
    with pytest.raises(IntegrityError):
        EstablishmentMembership.objects.create(user=user, establishment=establishment)


def test_auth_user_model_setting():
    from django.conf import settings

    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_membership_scope_unique_business_unit_per_membership(user, establishment):
    membership = EstablishmentMembership.objects.create(user=user, establishment=establishment)
    business_unit = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    MembershipScope.objects.create(membership=membership, business_unit=business_unit)
    with pytest.raises(IntegrityError):
        MembershipScope.objects.create(membership=membership, business_unit=business_unit)


def test_membership_delete_cascades_membership_scope(user, establishment):
    membership = EstablishmentMembership.objects.create(user=user, establishment=establishment)
    business_unit = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    MembershipScope.objects.create(membership=membership, business_unit=business_unit)
    membership.delete()
    assert MembershipScope.objects.count() == 0


def test_business_unit_delete_cascades_membership_scope(user, establishment):
    membership = EstablishmentMembership.objects.create(user=user, establishment=establishment)
    business_unit = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    MembershipScope.objects.create(membership=membership, business_unit=business_unit)
    business_unit.delete()
    assert MembershipScope.objects.count() == 0


def test_onboarding_session_defaults(organization, establishment, user):
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        started_by=user,
    )
    assert session.status == OnboardingSession.Status.STARTED
    assert session.source_mode == OnboardingSession.SourceMode.MANUAL
    assert session.current_step == ""
    assert session.ai_attempts == 0
    assert session.last_error_code == ""
    assert session.started_at is not None


def test_onboarding_session_status_helpers_classify_terminal_and_non_terminal_statuses():
    assert OnboardingSession.is_non_terminal_status(OnboardingSession.Status.STARTED) is True
    assert (
        OnboardingSession.is_non_terminal_status(OnboardingSession.Status.READY_FOR_ACTIVATION)
        is True
    )
    assert OnboardingSession.is_terminal_status(OnboardingSession.Status.ACTIVATED) is True
    assert OnboardingSession.is_terminal_status(OnboardingSession.Status.FAILED) is True
    assert OnboardingSession.is_terminal_status(OnboardingSession.Status.CANCELED) is True


def test_onboarding_session_unique_non_terminal_session_per_establishment(
    organization,
    establishment,
):
    OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
    )
    with pytest.raises(IntegrityError):
        OnboardingSession.objects.create(
            organization=organization,
            establishment=establishment,
            status=OnboardingSession.Status.CONFIGURING_RUNTIME,
        )


@pytest.mark.parametrize(
    "terminal_status",
    [
        OnboardingSession.Status.ACTIVATED,
        OnboardingSession.Status.FAILED,
        OnboardingSession.Status.CANCELED,
    ],
)
def test_onboarding_session_terminal_allows_later_non_terminal_session(
    organization,
    establishment,
    terminal_status,
):
    OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        status=terminal_status,
    )
    next_session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
    )
    assert next_session.status == OnboardingSession.Status.STARTED


def test_onboarding_session_allows_historical_terminal_sessions(
    organization,
    establishment,
):
    first = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        status=OnboardingSession.Status.ACTIVATED,
    )
    second = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        status=OnboardingSession.Status.CANCELED,
    )
    assert first.establishment == second.establishment


def test_onboarding_proposal_defaults(organization, establishment, user):
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        started_by=user,
    )
    proposal = OnboardingProposal.objects.create(
        onboarding_session=session,
        establishment=establishment,
        created_by=user,
    )
    assert proposal.source == OnboardingProposal.Source.MANUAL
    assert proposal.status == OnboardingProposal.Status.DRAFT
    assert proposal.payload == {}
    assert proposal.section_validation == {}
    assert proposal.validation_errors == []


def test_onboarding_proposal_validates_establishment_matches_session(
    organization,
    establishment,
):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
    )
    proposal = OnboardingProposal(
        onboarding_session=session,
        establishment=other_establishment,
    )
    with pytest.raises(ValidationError) as exc_info:
        proposal.full_clean()
    assert "establishment" in exc_info.value.message_dict


def test_onboarding_session_validates_organization_matches_establishment(establishment):
    other_organization = Organization.objects.create(name="Other Org")
    session = OnboardingSession(
        organization=other_organization,
        establishment=establishment,
    )
    with pytest.raises(ValidationError) as exc_info:
        session.full_clean()
    assert "organization" in exc_info.value.message_dict


def test_start_onboarding_session_creates_manual_session(organization, establishment, user):
    session = start_onboarding_session(
        organization=organization,
        establishment=establishment,
        started_by=user,
    )
    assert session.status == OnboardingSession.Status.STARTED
    assert session.source_mode == OnboardingSession.SourceMode.MANUAL
    assert session.started_by == user


def test_start_onboarding_session_allows_template_source_mode(
    organization,
    establishment,
):
    session = start_onboarding_session(
        organization=organization,
        establishment=establishment,
        source_mode=OnboardingSession.SourceMode.TEMPLATE,
    )
    assert session.source_mode == OnboardingSession.SourceMode.TEMPLATE


def test_start_onboarding_session_rejects_reserved_ai_source_mode(
    organization,
    establishment,
):
    with pytest.raises(UnsupportedOnboardingSessionSourceModeError):
        start_onboarding_session(
            organization=organization,
            establishment=establishment,
            source_mode=OnboardingSession.SourceMode.AI,
        )


def test_start_onboarding_session_rejects_mismatched_scope(establishment):
    other_organization = Organization.objects.create(name="Other Org")
    with pytest.raises(InvalidOnboardingSessionScopeError):
        start_onboarding_session(
            organization=other_organization,
            establishment=establishment,
        )


def test_activity_description_is_canonical_per_establishment(establishment):
    description = "A" * ACTIVITY_DESCRIPTION_MIN_LENGTH
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description=description,
    )
    with pytest.raises(IntegrityError):
        EstablishmentActivityDescription.objects.create(
            establishment=establishment,
            description=description,
        )
