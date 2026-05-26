import pytest

from houston.accounts.models import User
from houston.establishments.access import CURRENT_ESTABLISHMENT_SESSION_KEY
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


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


def test_anonymous_user_visiting_app_is_redirected_to_login(client):
    response = client.get("/app/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login/?next=/app/"


def test_active_authenticated_user_with_one_active_membership_can_access_app(
    client,
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
    client.force_login(active_user)

    response = client.get("/app/")

    assert response.status_code == 200
    assert b"Access context resolved successfully." in response.content
    assert b"Nice" in response.content


def test_single_active_establishment_is_auto_selected_and_visible_in_template(
    client,
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
    client.force_login(active_user)

    response = client.get("/app/")

    assert response.status_code == 200
    assert client.session[CURRENT_ESTABLISHMENT_SESSION_KEY] == str(establishment.id)
    assert b"Current establishment: Nice" in response.content


def test_active_authenticated_user_with_no_active_membership_gets_blocked_cleanly(
    client,
    active_user,
):
    client.force_login(active_user)

    response = client.get("/app/")

    assert response.status_code == 403
    assert b"No active establishment access is available for this account." in response.content


def test_suspended_non_active_user_cannot_access_app(client):
    user = User.objects.create_user(
        username="suspended_01",
        password="secret",
        status=User.Status.SUSPENDED,
    )
    client.force_login(user)
    session = client.session
    session[CURRENT_ESTABLISHMENT_SESSION_KEY] = "stale-id"
    session.save()

    response = client.get("/app/")

    assert response.status_code == 403
    assert b"This account is not active in Houston." in response.content
    assert CURRENT_ESTABLISHMENT_SESSION_KEY not in client.session


def test_multiple_active_memberships_require_explicit_selection(
    client,
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
    client.force_login(active_user)

    response = client.get("/app/")

    assert response.status_code == 200
    assert (
        b"Multiple active establishments are available. Selection is required before continuing."
        in response.content
    )
    assert CURRENT_ESTABLISHMENT_SESSION_KEY not in client.session
