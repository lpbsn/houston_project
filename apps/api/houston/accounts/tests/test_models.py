import uuid

import pytest
from django.db import IntegrityError

from houston.accounts.models import AccessToken, SessionRefreshToken, User, UserSession


def test_user_uuid_primary_key_configuration():
    field = User._meta.get_field("id")

    assert field.primary_key is True
    assert field.default is uuid.uuid4
    assert field.editable is False


def test_user_identity_type_choices_and_default():
    field = User._meta.get_field("identity_type")

    assert field.default == User.IdentityType.EMAIL
    assert field.choices == User.IdentityType.choices


def test_user_status_choices_and_default():
    field = User._meta.get_field("status")

    assert field.default == User.Status.PENDING
    assert field.choices == User.Status.choices


def test_user_email_is_nullable_and_blankable():
    field = User._meta.get_field("email")

    assert field.null is True
    assert field.blank is True


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


def test_user_session_status_choices():
    field = UserSession._meta.get_field("status")

    assert field.default == UserSession.Status.ACTIVE
    assert field.choices == UserSession.Status.choices


def test_access_token_digest_field_is_unique_and_indexed():
    field = AccessToken._meta.get_field("token_digest")

    assert field.unique is True
    assert field.db_index is True


def test_session_refresh_token_digest_field_is_unique_and_indexed():
    field = SessionRefreshToken._meta.get_field("token_digest")

    assert field.unique is True
    assert field.db_index is True


def test_refresh_token_family_fields_are_indexed():
    session_field = UserSession._meta.get_field("refresh_token_family_id")
    refresh_field = SessionRefreshToken._meta.get_field("family_id")

    assert session_field.db_index is True
    assert refresh_field.db_index is True
