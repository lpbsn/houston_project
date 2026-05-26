import uuid

from django.db import models

from houston.core.models import BaseModel, TimestampedModel, UUIDModel


def test_uuid_model_is_abstract():
    assert UUIDModel._meta.abstract is True


def test_timestamped_model_is_abstract():
    assert TimestampedModel._meta.abstract is True


def test_base_model_is_abstract():
    assert BaseModel._meta.abstract is True


def test_uuid_model_id_field_configuration():
    field = UUIDModel._meta.get_field("id")

    assert isinstance(field, models.UUIDField)
    assert field.primary_key is True
    assert field.editable is False
    assert field.default is uuid.uuid4


def test_timestamped_model_field_configuration():
    created_at = TimestampedModel._meta.get_field("created_at")
    updated_at = TimestampedModel._meta.get_field("updated_at")

    assert isinstance(created_at, models.DateTimeField)
    assert created_at.auto_now_add is True
    assert isinstance(updated_at, models.DateTimeField)
    assert updated_at.auto_now is True
