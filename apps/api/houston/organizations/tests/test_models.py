import pytest

from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


def test_organization_creation():
    organization = Organization.objects.create(name="Mama Shelter")

    assert organization.name == "Mama Shelter"


def test_organization_status_default():
    organization = Organization.objects.create(name="Mama Shelter")

    assert organization.status == Organization.Status.ACTIVE
