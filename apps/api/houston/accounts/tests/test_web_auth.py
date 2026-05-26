import pytest

from houston.accounts.models import User

pytestmark = pytest.mark.django_db


def test_login_page_renders(client):
    response = client.get("/login/")

    assert response.status_code == 200
    assert b"Log in to Houston" in response.content


def test_login_with_valid_username_and_password_creates_session_and_redirects_to_app(client):
    user = User.objects.create_user(
        username="manager_01",
        password="secret",
        status=User.Status.ACTIVE,
    )

    response = client.post("/login/", {"username": user.username, "password": "secret"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/app/"
    assert client.session.get("_auth_user_id") == str(user.pk)


def test_login_rejects_user_with_non_active_business_status(client):
    user = User.objects.create_user(
        username="suspended_01",
        password="secret",
        status=User.Status.SUSPENDED,
    )

    response = client.post("/login/", {"username": user.username, "password": "secret"})

    assert response.status_code == 200
    assert b"This account does not have access to the Houston app." in response.content
    assert client.session.get("_auth_user_id") is None


def test_logout_post_clears_session_and_redirects_to_login(client):
    user = User.objects.create_user(
        username="manager_01",
        password="secret",
        status=User.Status.ACTIVE,
    )
    client.force_login(user)

    response = client.post("/logout/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login/"
    assert client.session.get("_auth_user_id") is None
