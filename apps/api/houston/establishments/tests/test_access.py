import pytest
from django.test import RequestFactory
from django.utils import timezone

from houston.accounts.authentication import AccessTokenAuthContext
from houston.accounts.models import AccessToken, User, UserSession
from houston.establishments.access import (
    ACCESS_STATE_INACTIVE_USER,
    ACCESS_STATE_READY,
    ACCESS_STATE_SELECTION_REQUIRED,
    get_api_access_context,
    resolve_api_access_context,
)
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def organization():
    return Organization.objects.create(name="Mama Shelter")


@pytest.fixture
def active_user():
    return User.objects.create_user(
        username="manager_01",
        password="secret",
        status=User.Status.ACTIVE,
    )


def build_api_request(request_factory, *, user, auth_context=None):
    request = request_factory.get("/api/v1/bootstrap/")
    request.user = user
    request.auth = auth_context
    return request


def create_auth_context(*, user, selected_establishment=None):
    session = UserSession.objects.create(
        user=user,
        selected_establishment=selected_establishment,
        refresh_token_family_id="00000000-0000-0000-0000-000000000001",
        refresh_expires_at=timezone.now(),
        absolute_expires_at=timezone.now(),
    )
    access_token = AccessToken(
        session=session,
        token_digest="token-digest",
        expires_at=timezone.now(),
    )
    return AccessTokenAuthContext(session=session, access_token=access_token)


def test_api_access_context_uses_auth_session_selected_establishment(
    request_factory,
    organization,
    active_user,
):
    first_establishment = Establishment.objects.create(
        name="Nice",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    second_establishment = Establishment.objects.create(
        name="Cannes",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    first_membership = EstablishmentMembership.objects.create(
        user=active_user,
        establishment=first_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    second_membership = EstablishmentMembership.objects.create(
        user=active_user,
        establishment=second_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    auth_context = create_auth_context(
        user=active_user,
        selected_establishment=second_establishment,
    )
    request = build_api_request(
        request_factory,
        user=active_user,
        auth_context=auth_context,
    )

    context = resolve_api_access_context(request)

    assert context.is_authenticated is True
    assert context.state == ACCESS_STATE_READY
    assert context.auth_session_id == str(auth_context.session.id)
    assert context.active_membership == second_membership
    assert context.selected_establishment == second_establishment
    assert context.active_memberships == (second_membership, first_membership)
    assert first_membership in context.active_memberships


def test_api_access_context_requires_explicit_selection_for_multiple_memberships(
    request_factory,
    organization,
    active_user,
):
    first_membership = EstablishmentMembership.objects.create(
        user=active_user,
        establishment=Establishment.objects.create(
            name="Nice",
            organization=organization,
            status=Establishment.Status.ACTIVE,
        ),
        status=EstablishmentMembership.Status.ACTIVE,
    )
    second_membership = EstablishmentMembership.objects.create(
        user=active_user,
        establishment=Establishment.objects.create(
            name="Cannes",
            organization=organization,
            status=Establishment.Status.ACTIVE,
        ),
        status=EstablishmentMembership.Status.ACTIVE,
    )
    auth_context = create_auth_context(user=active_user)
    request = build_api_request(
        request_factory,
        user=active_user,
        auth_context=auth_context,
    )

    context = resolve_api_access_context(request)

    assert context.state == ACCESS_STATE_SELECTION_REQUIRED
    assert context.active_membership is None
    assert context.selected_establishment is None
    assert context.active_memberships == (second_membership, first_membership)


def test_api_access_context_clears_stale_selected_establishment(
    request_factory,
    organization,
    active_user,
):
    active_establishment = Establishment.objects.create(
        name="Active",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    stale_establishment = Establishment.objects.create(
        name="Stale",
        organization=organization,
        status=Establishment.Status.DEACTIVATED,
    )
    active_membership = EstablishmentMembership.objects.create(
        user=active_user,
        establishment=active_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=active_user,
        establishment=stale_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    auth_context = create_auth_context(
        user=active_user,
        selected_establishment=stale_establishment,
    )
    request = build_api_request(
        request_factory,
        user=active_user,
        auth_context=auth_context,
    )

    context = resolve_api_access_context(request)
    auth_context.session.refresh_from_db()

    assert context.state == ACCESS_STATE_SELECTION_REQUIRED
    assert context.active_membership is None
    assert context.selected_establishment is None
    assert context.active_memberships == (active_membership,)
    assert auth_context.session.selected_establishment is None


def test_api_access_context_denies_inactive_user(
    request_factory,
    organization,
):
    inactive_user = User.objects.create_user(
        username="suspended_01",
        password="secret",
        status=User.Status.SUSPENDED,
    )
    establishment = Establishment.objects.create(
        name="Nice",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=inactive_user,
        establishment=establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    auth_context = create_auth_context(
        user=inactive_user,
        selected_establishment=establishment,
    )
    request = build_api_request(
        request_factory,
        user=inactive_user,
        auth_context=auth_context,
    )

    context = resolve_api_access_context(request)

    assert context.state == ACCESS_STATE_INACTIVE_USER
    assert context.active_memberships == ()
    assert context.active_membership is None


def test_api_access_context_is_cached_on_request(
    request_factory,
    organization,
    active_user,
):
    establishment = Establishment.objects.create(
        name="Nice",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=active_user,
        establishment=establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    auth_context = create_auth_context(
        user=active_user,
        selected_establishment=establishment,
    )
    request = build_api_request(
        request_factory,
        user=active_user,
        auth_context=auth_context,
    )

    first_context = get_api_access_context(request)
    second_context = get_api_access_context(request)

    assert first_context is second_context
