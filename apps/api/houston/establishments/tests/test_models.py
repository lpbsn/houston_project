import pytest
from django.db import IntegrityError

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipDomain,
    OperationalDomain,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(name="Mama Shelter")


@pytest.fixture
def establishment(organization):
    return Establishment.objects.create(name="Nice", organization=organization)


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


def test_membership_role_and_status_choices():
    role_field = EstablishmentMembership._meta.get_field("role")
    status_field = EstablishmentMembership._meta.get_field("status")

    assert role_field.choices == EstablishmentMembership.Role.choices
    assert status_field.choices == EstablishmentMembership.Status.choices


def test_operational_domain_defaults(establishment):
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )

    assert domain.active is True
    assert domain.source == OperationalDomain.Source.MANUAL


def test_operational_domain_unique_key_per_establishment(establishment):
    OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )

    with pytest.raises(IntegrityError):
        OperationalDomain.objects.create(
            establishment=establishment,
            key="maintenance",
            label="Maintenance Duplicate",
        )


def test_operational_domain_same_key_allowed_across_establishments(organization, establishment):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    first_domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    second_domain = OperationalDomain.objects.create(
        establishment=other_establishment,
        key="maintenance",
        label="Maintenance",
    )

    assert first_domain.key == second_domain.key


def test_membership_unique_user_establishment_constraint(user, establishment):
    EstablishmentMembership.objects.create(user=user, establishment=establishment)

    with pytest.raises(IntegrityError):
        EstablishmentMembership.objects.create(user=user, establishment=establishment)


def test_auth_user_model_setting():
    from django.conf import settings

    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_membership_domain_unique_membership_and_domain(user, establishment):
    membership = EstablishmentMembership.objects.create(user=user, establishment=establishment)
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    MembershipDomain.objects.create(membership=membership, operational_domain=domain)

    with pytest.raises(IntegrityError):
        MembershipDomain.objects.create(membership=membership, operational_domain=domain)


def test_membership_delete_cascades_membership_domain(user, establishment):
    membership = EstablishmentMembership.objects.create(user=user, establishment=establishment)
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    MembershipDomain.objects.create(membership=membership, operational_domain=domain)

    membership.delete()

    assert MembershipDomain.objects.count() == 0


def test_operational_domain_delete_cascades_membership_domain(user, establishment):
    membership = EstablishmentMembership.objects.create(user=user, establishment=establishment)
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    MembershipDomain.objects.create(membership=membership, operational_domain=domain)

    domain.delete()

    assert MembershipDomain.objects.count() == 0
