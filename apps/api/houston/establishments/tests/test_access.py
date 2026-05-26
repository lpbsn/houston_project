import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from houston.accounts.models import User
from houston.establishments.access import (
    ACCESS_STATE_INACTIVE_USER,
    ACCESS_STATE_NO_MEMBERSHIPS,
    ACCESS_STATE_READY,
    ACCESS_STATE_SELECTION_REQUIRED,
    CURRENT_ESTABLISHMENT_SESSION_KEY,
    resolve_current_access_context,
)
from houston.establishments.models import Establishment, EstablishmentMembership
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


def build_request(request_factory, user, session_value=None):
    request = request_factory.get("/app/")
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    request.user = user

    if session_value is not None:
        request.session[CURRENT_ESTABLISHMENT_SESSION_KEY] = session_value

    return request


def test_invalid_current_establishment_id_is_cleared_safely(
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
    EstablishmentMembership.objects.create(
        user=active_user,
        establishment=first_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=active_user,
        establishment=second_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    request = build_request(request_factory, active_user, session_value="not-a-valid-id")

    context = resolve_current_access_context(request)

    assert context.state == ACCESS_STATE_SELECTION_REQUIRED
    assert CURRENT_ESTABLISHMENT_SESSION_KEY not in request.session


def test_multiple_active_memberships_with_valid_session_selection_reuse_that_selection(
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
    EstablishmentMembership.objects.create(
        user=active_user,
        establishment=first_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    second_membership = EstablishmentMembership.objects.create(
        user=active_user,
        establishment=second_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    request = build_request(
        request_factory,
        active_user,
        session_value=str(second_establishment.id),
    )

    context = resolve_current_access_context(request)

    assert context.state == ACCESS_STATE_READY
    assert context.selected_membership == second_membership
    assert context.selected_establishment == second_establishment
    assert request.session[CURRENT_ESTABLISHMENT_SESSION_KEY] == str(second_establishment.id)


def test_active_membership_resolution_ignores_deactivated_memberships_and_non_active_establishments(
    request_factory,
    organization,
    active_user,
):
    valid_establishment = Establishment.objects.create(
        name="Nice",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    deactivated_establishment = Establishment.objects.create(
        name="Closed",
        organization=organization,
        status=Establishment.Status.DEACTIVATED,
    )
    invited_establishment = Establishment.objects.create(
        name="Invited",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    valid_membership = EstablishmentMembership.objects.create(
        user=active_user,
        establishment=valid_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=active_user,
        establishment=deactivated_establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=active_user,
        establishment=invited_establishment,
        status=EstablishmentMembership.Status.INVITED,
    )
    request = build_request(request_factory, active_user)

    context = resolve_current_access_context(request)

    assert context.state == ACCESS_STATE_READY
    assert context.active_memberships == (valid_membership,)
    assert context.selected_establishment == valid_establishment
    assert request.session[CURRENT_ESTABLISHMENT_SESSION_KEY] == str(valid_establishment.id)


def test_anonymized_user_is_denied_access_and_stale_selection_is_cleared(request_factory):
    user = User.objects.create_user(
        username="anonymized_01",
        password="secret",
        status=User.Status.ANONYMIZED,
    )
    request = build_request(request_factory, user, session_value="stale-id")

    context = resolve_current_access_context(request)

    assert context.state == ACCESS_STATE_INACTIVE_USER
    assert context.has_app_access is False
    assert CURRENT_ESTABLISHMENT_SESSION_KEY not in request.session

def test_active_membership_resolution_ignores_establishments_under_non_active_organization(
    request_factory,
    active_user,
):
    suspended_organization = Organization.objects.create(
        name="Suspended Org",
        status=Organization.Status.SUSPENDED,
    )
    establishment = Establishment.objects.create(
        name="Nice",
        organization=suspended_organization,
        status=Establishment.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=active_user,
        establishment=establishment,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    request = build_request(
        request_factory,
        active_user,
        session_value=str(establishment.id),
    )

    context = resolve_current_access_context(request)

    assert context.state == ACCESS_STATE_NO_MEMBERSHIPS
    assert context.has_app_access is False
    assert context.active_memberships == ()
    assert CURRENT_ESTABLISHMENT_SESSION_KEY not in request.session