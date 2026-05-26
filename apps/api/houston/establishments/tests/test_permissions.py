import uuid

import pytest

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.permissions import (
    can_access_app,
    can_access_domain,
    can_create_action,
    can_create_observation,
    can_manage_establishment_settings,
    can_manage_memberships,
    can_manage_runtime_context,
    can_validate_action,
    can_view_signal_feed,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


def build_membership(
    *,
    role=EstablishmentMembership.Role.STAFF,
    membership_status=EstablishmentMembership.Status.ACTIVE,
    user_status=User.Status.ACTIVE,
    establishment_status=Establishment.Status.ACTIVE,
    operational_domains=None,
):
    organization = Organization.objects.create(name=f"Org {uuid.uuid4().hex[:8]}")
    user = User.objects.create_user(
        username=f"user_{uuid.uuid4().hex[:8]}",
        password="secret",
        status=user_status,
    )
    establishment = Establishment.objects.create(
        name=f"Establishment {uuid.uuid4().hex[:8]}",
        organization=organization,
        status=establishment_status,
    )
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=membership_status,
        operational_domains=[] if operational_domains is None else operational_domains,
    )
    return membership


def assert_all_permissions_denied(membership):
    assert can_access_app(membership) is False
    assert can_manage_establishment_settings(membership) is False
    assert can_manage_memberships(membership) is False
    assert can_manage_runtime_context(membership) is False
    assert can_view_signal_feed(membership) is False
    assert can_create_observation(membership) is False
    assert can_create_action(membership) is False
    assert can_validate_action(membership) is False
    assert can_access_domain(membership, "housekeeping") is False


def test_owner_permissions():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)

    assert can_access_app(membership) is True
    assert can_manage_establishment_settings(membership) is True
    assert can_manage_memberships(membership) is True
    assert can_manage_runtime_context(membership) is True
    assert can_view_signal_feed(membership) is True
    assert can_create_observation(membership) is True
    assert can_create_action(membership) is True
    assert can_validate_action(membership) is True


def test_director_permissions():
    membership = build_membership(role=EstablishmentMembership.Role.DIRECTOR)

    assert can_access_app(membership) is True
    assert can_manage_establishment_settings(membership) is True
    assert can_manage_memberships(membership) is True
    assert can_manage_runtime_context(membership) is True
    assert can_view_signal_feed(membership) is True
    assert can_create_observation(membership) is True
    assert can_create_action(membership) is True
    assert can_validate_action(membership) is True


def test_manager_permissions():
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)

    assert can_access_app(membership) is True
    assert can_manage_establishment_settings(membership) is False
    assert can_manage_memberships(membership) is False
    assert can_manage_runtime_context(membership) is False
    assert can_view_signal_feed(membership) is True
    assert can_create_observation(membership) is True
    assert can_create_action(membership) is True
    assert can_validate_action(membership) is True


def test_staff_permissions():
    membership = build_membership(role=EstablishmentMembership.Role.STAFF)

    assert can_access_app(membership) is True
    assert can_manage_establishment_settings(membership) is False
    assert can_manage_memberships(membership) is False
    assert can_manage_runtime_context(membership) is False
    assert can_view_signal_feed(membership) is True
    assert can_create_observation(membership) is True
    assert can_create_action(membership) is False
    assert can_validate_action(membership) is False


def test_missing_membership_denies_all_permissions():
    assert_all_permissions_denied(None)


def test_inactive_membership_denies_all_permissions():
    membership = build_membership(membership_status=EstablishmentMembership.Status.DEACTIVATED)

    assert_all_permissions_denied(membership)


@pytest.mark.parametrize(
    "user_status",
    [
        User.Status.PENDING,
        User.Status.SUSPENDED,
        User.Status.ANONYMIZED,
    ],
)
def test_non_active_user_denies_all_permissions(user_status):
    membership = build_membership(user_status=user_status)

    assert_all_permissions_denied(membership)


@pytest.mark.parametrize(
    "establishment_status",
    [
        Establishment.Status.DRAFT,
        Establishment.Status.DEACTIVATED,
    ],
)
def test_non_active_establishment_denies_all_permissions(establishment_status):
    membership = build_membership(establishment_status=establishment_status)

    assert_all_permissions_denied(membership)


def test_unknown_role_fails_closed():
    membership = build_membership()
    membership.role = "unknown-role"

    assert_all_permissions_denied(membership)


@pytest.mark.parametrize(
    ("attribute_name", "attribute_value"),
    [
        ("status", "unknown-membership-status"),
        ("user.status", "unknown-user-status"),
    ],
)
def test_unknown_status_fails_closed(attribute_name, attribute_value):
    membership = build_membership()

    if attribute_name == "status":
        membership.status = attribute_value
    else:
        membership.user.status = attribute_value

    assert_all_permissions_denied(membership)


def test_owner_and_director_can_access_any_nonblank_domain():
    owner_membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    director_membership = build_membership(role=EstablishmentMembership.Role.DIRECTOR)

    assert can_access_domain(owner_membership, " housekeeping ") is True
    assert can_access_domain(director_membership, "maintenance") is True


@pytest.mark.parametrize(
    "role",
    [EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF],
)
def test_manager_and_staff_can_access_matching_domain(role):
    membership = build_membership(role=role, operational_domains=[" housekeeping ", "security"])
    original_domains = list(membership.operational_domains)

    assert can_access_domain(membership, "housekeeping") is True
    assert membership.operational_domains == original_domains


@pytest.mark.parametrize(
    "role",
    [EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF],
)
def test_manager_and_staff_cannot_access_non_matching_domain(role):
    membership = build_membership(role=role, operational_domains=["housekeeping"])

    assert can_access_domain(membership, "security") is False


@pytest.mark.parametrize(
    "role",
    [EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF],
)
def test_manager_and_staff_empty_operational_domains_deny_domain_access(role):
    membership = build_membership(role=role, operational_domains=[])

    assert can_access_domain(membership, "housekeeping") is False


@pytest.mark.parametrize(
    "role",
    [
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    ],
)
def test_blank_domain_is_denied_for_every_role(role):
    membership = build_membership(role=role, operational_domains=["housekeeping"])

    assert can_access_domain(membership, "   ") is False


@pytest.mark.parametrize(
    "role",
    [EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF],
)
def test_malformed_operational_domains_deny_domain_access(role):
    membership = build_membership(role=role, operational_domains=["housekeeping"])
    membership.operational_domains = {"domain": "housekeeping"}

    assert can_access_domain(membership, "housekeeping") is False
