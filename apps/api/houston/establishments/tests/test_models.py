import pytest
from django.db import IntegrityError

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
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


def test_operational_domains_default_is_empty_list(user, establishment):
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
    )

    assert membership.operational_domains == []


def test_operational_domains_default_is_not_shared(user, establishment, organization):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    first_membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
    )
    second_user = User.objects.create_user(username="staff_02", password="secret")
    second_membership = EstablishmentMembership.objects.create(
        user=second_user,
        establishment=other_establishment,
    )

    first_membership.operational_domains.append("maintenance")

    assert second_membership.operational_domains == []


def test_membership_unique_user_establishment_constraint(user, establishment):
    EstablishmentMembership.objects.create(user=user, establishment=establishment)

    with pytest.raises(IntegrityError):
        EstablishmentMembership.objects.create(user=user, establishment=establishment)


def test_auth_user_model_setting():
    from django.conf import settings

    assert settings.AUTH_USER_MODEL == "accounts.User"
