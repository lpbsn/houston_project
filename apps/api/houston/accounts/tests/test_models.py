import uuid

from houston.accounts.models import User


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
