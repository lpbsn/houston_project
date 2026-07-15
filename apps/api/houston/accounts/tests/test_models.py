import pytest
from django.db import IntegrityError

from houston.accounts.models import User


@pytest.mark.django_db
def test_user_email_is_normalized_on_save():
    user = User.objects.create_user(
        username="manager_01",
        email="  MANAGER@Example.COM ",
        password="secret",
    )

    assert user.email == "manager@example.com"


@pytest.mark.django_db
def test_user_email_is_unique_case_insensitively_when_present():
    User.objects.create_user(
        username="manager_01",
        email="manager@example.com",
        password="secret",
    )

    with pytest.raises(IntegrityError):
        User.objects.create_user(
            username="manager_02",
            email="MANAGER@example.com",
            password="secret",
        )
