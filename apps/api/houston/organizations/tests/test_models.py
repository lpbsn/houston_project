import pytest

from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


def test_organization_creation():
    organization = Organization.objects.create(name="Mama Shelter")

    assert organization.name == "Mama Shelter"


def test_organization_status_default():
    organization = Organization.objects.create(name="Mama Shelter")

    assert organization.status == Organization.Status.ACTIVE
    assert organization.has_been_operational is False


def test_mark_organization_has_been_operational_is_sticky():
    from houston.organizations.services import mark_organization_has_been_operational

    organization = Organization.objects.create(name="Draft Only Org")
    mark_organization_has_been_operational(organization)
    first_updated = organization.updated_at
    mark_organization_has_been_operational(organization)
    organization.refresh_from_db()
    assert organization.has_been_operational is True
    assert organization.updated_at == first_updated
