from __future__ import annotations

import pytest

from houston.establishments.membership_scope import (
    membership_covers_business_unit_including_admins,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def test_owner_covers_business_unit_in_same_establishment():
    establishment = create_establishment()
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=establishment, key="restaurant")

    assert membership_covers_business_unit_including_admins(owner, business_unit) is True


def test_director_covers_business_unit_in_same_establishment():
    establishment = create_establishment()
    director = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    business_unit = create_business_unit(establishment=establishment, key="restaurant")

    assert membership_covers_business_unit_including_admins(director, business_unit) is True


def test_manager_in_scope_covers_business_unit():
    establishment = create_establishment()
    manager = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    business_unit = create_business_unit(establishment=establishment, key="restaurant")
    create_membership_with_business_unit_scope(membership=manager, business_unit=business_unit)
    manager = EstablishmentMembership.objects.prefetch_related("scope_links").get(pk=manager.pk)

    assert membership_covers_business_unit_including_admins(manager, business_unit) is True


def test_manager_out_of_scope_does_not_cover_business_unit():
    establishment = create_establishment()
    manager = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    restaurant = create_business_unit(establishment=establishment, key="restaurant")
    bar = create_business_unit(establishment=establishment, key="bar")
    create_membership_with_business_unit_scope(membership=manager, business_unit=restaurant)
    manager = EstablishmentMembership.objects.prefetch_related("scope_links").get(pk=manager.pk)

    assert membership_covers_business_unit_including_admins(manager, bar) is False


def test_staff_in_scope_covers_business_unit():
    establishment = create_establishment()
    staff = create_membership(establishment=establishment, role=EstablishmentMembership.Role.STAFF)
    business_unit = create_business_unit(establishment=establishment, key="restaurant")
    create_membership_with_business_unit_scope(membership=staff, business_unit=business_unit)
    staff = EstablishmentMembership.objects.prefetch_related("scope_links").get(pk=staff.pk)

    assert membership_covers_business_unit_including_admins(staff, business_unit) is True


def test_staff_without_scope_does_not_cover_business_unit():
    establishment = create_establishment()
    staff = create_membership(establishment=establishment, role=EstablishmentMembership.Role.STAFF)
    business_unit = create_business_unit(establishment=establishment, key="restaurant")

    assert membership_covers_business_unit_including_admins(staff, business_unit) is False


def test_inactive_business_unit_is_not_covered():
    establishment = create_establishment()
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=establishment, key="restaurant")
    business_unit.active = False
    business_unit.save(update_fields=["active", "updated_at"])

    assert membership_covers_business_unit_including_admins(owner, business_unit) is False


def test_inactive_membership_does_not_cover_business_unit():
    establishment = create_establishment()
    staff = create_membership(establishment=establishment, role=EstablishmentMembership.Role.STAFF)
    business_unit = create_business_unit(establishment=establishment, key="restaurant")
    create_membership_with_business_unit_scope(membership=staff, business_unit=business_unit)
    staff.status = EstablishmentMembership.Status.DEACTIVATED
    staff.save(update_fields=["status", "updated_at"])
    staff = EstablishmentMembership.objects.prefetch_related("scope_links").get(pk=staff.pk)

    assert membership_covers_business_unit_including_admins(staff, business_unit) is False


def test_cross_establishment_membership_does_not_cover_business_unit():
    establishment = create_establishment(name="Hotel A")
    other_establishment = create_establishment(name="Hotel B")
    staff = create_membership(establishment=establishment, role=EstablishmentMembership.Role.STAFF)
    business_unit = create_business_unit(establishment=other_establishment, key="restaurant")
    create_membership_with_business_unit_scope(membership=staff, business_unit=business_unit)
    staff = EstablishmentMembership.objects.prefetch_related("scope_links").get(pk=staff.pk)

    assert membership_covers_business_unit_including_admins(staff, business_unit) is False


def test_null_business_unit_is_not_covered():
    establishment = create_establishment()
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)

    assert membership_covers_business_unit_including_admins(owner, None) is False
