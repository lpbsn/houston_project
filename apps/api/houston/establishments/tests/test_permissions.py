import uuid

import pytest
from django.test import RequestFactory
from django.utils import timezone

from houston.accounts.authentication import AccessTokenAuthContext
from houston.accounts.models import AccessToken, User, UserSession
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipDomain,
    OperationalDomain,
    RoutingHint,
    RoutingHintDomain,
    RuntimeTag,
    RuntimeTagDomain,
)
from houston.establishments.permissions import (
    CanManageMemberships,
    CanManageRuntimeContext,
    HasActiveMembership,
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


@pytest.fixture
def request_factory():
    return RequestFactory()


def build_membership(
    *,
    role=EstablishmentMembership.Role.STAFF,
    membership_status=EstablishmentMembership.Status.ACTIVE,
    user_status=User.Status.ACTIVE,
    organization_status=Organization.Status.ACTIVE,
    establishment_status=Establishment.Status.ACTIVE,
):
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:8]}",
        status=organization_status,
    )
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
    )
    return membership


def create_domain(
    establishment,
    *,
    key,
    label,
    active=True,
    source=OperationalDomain.Source.MANUAL,
):
    return OperationalDomain.objects.create(
        establishment=establishment,
        key=key,
        label=label,
        active=active,
        source=source,
    )


def link_membership_to_domain(membership, operational_domain):
    return MembershipDomain.objects.create(
        membership=membership,
        operational_domain=operational_domain,
    )


def build_permission_request(
    request_factory,
    *,
    user,
    selected_establishment=None,
):
    session = UserSession.objects.create(
        user=user,
        selected_establishment=selected_establishment,
        refresh_token_family_id=uuid.uuid4(),
        refresh_expires_at=timezone.now(),
        absolute_expires_at=timezone.now(),
    )
    access_token = AccessToken(
        session=session,
        token_digest=f"token-{uuid.uuid4().hex}",
        expires_at=timezone.now(),
    )
    request = request_factory.get("/api/v1/example/")
    request.user = user
    request.auth = AccessTokenAuthContext(session=session, access_token=access_token)
    return request


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


@pytest.mark.parametrize(
    "organization_status",
    [
        Organization.Status.SUSPENDED,
        Organization.Status.ARCHIVED,
    ],
)
def test_non_active_organization_denies_all_permissions(organization_status):
    membership = build_membership(organization_status=organization_status)

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
    create_domain(
        owner_membership.establishment,
        key="housekeeping",
        label="Housekeeping",
    )
    create_domain(
        director_membership.establishment,
        key="maintenance",
        label="Maintenance",
    )

    assert can_access_domain(owner_membership, " housekeeping ") is True
    assert can_access_domain(director_membership, "maintenance") is True


@pytest.mark.parametrize(
    "role",
    [EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF],
)
def test_manager_and_staff_can_access_matching_linked_domain(role):
    membership = build_membership(role=role)
    domain = create_domain(
        membership.establishment,
        key="housekeeping",
        label="Housekeeping",
    )
    link_membership_to_domain(membership, domain)

    assert can_access_domain(membership, "housekeeping") is True


@pytest.mark.parametrize(
    "role",
    [EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF],
)
def test_manager_and_staff_cannot_access_without_linked_domain(role):
    membership = build_membership(role=role)
    create_domain(
        membership.establishment,
        key="security",
        label="Security",
    )

    assert can_access_domain(membership, "security") is False


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
    membership = build_membership(role=role)
    domain = create_domain(
        membership.establishment,
        key="housekeeping",
        label="Housekeeping",
    )
    if role in {EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF}:
        link_membership_to_domain(membership, domain)

    assert can_access_domain(membership, "   ") is False
    assert can_access_domain(membership, None) is False


@pytest.mark.parametrize(
    "role",
    [
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    ],
)
def test_unknown_domain_key_is_denied_for_every_role(role):
    membership = build_membership(role=role)
    domain = create_domain(
        membership.establishment,
        key="housekeeping",
        label="Housekeeping",
    )
    if role in {EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF}:
        link_membership_to_domain(membership, domain)

    assert can_access_domain(membership, "unknown") is False


@pytest.mark.parametrize(
    "role",
    [
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    ],
)
def test_inactive_domain_is_denied_for_every_role(role):
    membership = build_membership(role=role)
    inactive_domain = create_domain(
        membership.establishment,
        key="housekeeping",
        label="Housekeeping",
        active=False,
    )
    if role in {EstablishmentMembership.Role.MANAGER, EstablishmentMembership.Role.STAFF}:
        link_membership_to_domain(membership, inactive_domain)

    assert can_access_domain(membership, "housekeeping") is False


def test_domain_from_another_establishment_is_denied():
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    other_membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    foreign_domain = create_domain(
        other_membership.establishment,
        key="maintenance",
        label="Maintenance",
    )
    link_membership_to_domain(membership, foreign_domain)

    assert can_access_domain(membership, "maintenance") is False


def test_owner_and_director_domain_access_requires_existing_active_domain():
    owner_membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    director_membership = build_membership(role=EstablishmentMembership.Role.DIRECTOR)

    assert can_access_domain(owner_membership, "housekeeping") is False
    assert can_access_domain(director_membership, "maintenance") is False


def test_runtime_tag_domain_link_does_not_grant_domain_access():
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    domain = create_domain(
        membership.establishment,
        key="maintenance",
        label="Maintenance",
    )
    runtime_tag = RuntimeTag.objects.create(
        establishment=membership.establishment,
        key="hvac",
        label="HVAC",
    )
    RuntimeTagDomain.objects.create(
        runtime_tag=runtime_tag,
        operational_domain=domain,
    )

    assert can_access_domain(membership, "maintenance") is False


def test_routing_hint_domain_link_does_not_grant_domain_access():
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    domain = create_domain(
        membership.establishment,
        key="maintenance",
        label="Maintenance",
    )
    routing_hint = RoutingHint.objects.create(
        establishment=membership.establishment,
        pattern="VRV",
    )
    RoutingHintDomain.objects.create(
        routing_hint=routing_hint,
        operational_domain=domain,
    )

    assert can_access_domain(membership, "maintenance") is False


def test_has_active_membership_allows_ready_and_selection_required_contexts(request_factory):
    owner_membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    EstablishmentMembership.objects.create(
        user=owner_membership.user,
        establishment=Establishment.objects.create(
            name="Second Site",
            organization=owner_membership.establishment.organization,
            status=Establishment.Status.ACTIVE,
        ),
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    permission = HasActiveMembership()

    ready_request = build_permission_request(
        request_factory,
        user=owner_membership.user,
        selected_establishment=owner_membership.establishment,
    )
    selection_required_request = build_permission_request(
        request_factory,
        user=owner_membership.user,
        selected_establishment=None,
    )

    assert permission.has_permission(ready_request, None) is True
    assert permission.has_permission(selection_required_request, None) is True


def test_has_active_membership_denies_when_no_active_memberships(request_factory):
    user = User.objects.create_user(
        username=f"user_{uuid.uuid4().hex[:8]}",
        password="secret",
        status=User.Status.ACTIVE,
    )
    permission = HasActiveMembership()
    request = build_permission_request(
        request_factory,
        user=user,
        selected_establishment=None,
    )

    assert permission.has_permission(request, None) is False


@pytest.mark.parametrize(
    ("role", "expected_allowed"),
    [
        (EstablishmentMembership.Role.OWNER, True),
        (EstablishmentMembership.Role.DIRECTOR, True),
        (EstablishmentMembership.Role.MANAGER, False),
        (EstablishmentMembership.Role.STAFF, False),
    ],
)
def test_manage_membership_permissions_follow_rbac_helpers(
    request_factory,
    role,
    expected_allowed,
):
    membership = build_membership(role=role)
    request = build_permission_request(
        request_factory,
        user=membership.user,
        selected_establishment=membership.establishment,
    )

    assert CanManageMemberships().has_permission(request, None) is expected_allowed
    assert CanManageRuntimeContext().has_permission(request, None) is expected_allowed


def test_manage_permissions_fail_closed_without_selected_membership(request_factory):
    owner_membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    EstablishmentMembership.objects.create(
        user=owner_membership.user,
        establishment=Establishment.objects.create(
            name="Second Site",
            organization=owner_membership.establishment.organization,
            status=Establishment.Status.ACTIVE,
        ),
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    request = build_permission_request(
        request_factory,
        user=owner_membership.user,
        selected_establishment=None,
    )

    assert CanManageMemberships().has_permission(request, None) is False
    assert CanManageRuntimeContext().has_permission(request, None) is False
