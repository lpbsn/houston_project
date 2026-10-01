from __future__ import annotations

import uuid

import pytest
from django.core.signing import SignatureExpired
from houston.uploads.preview_tokens import (
    sign_upload_preview_token,
    unsign_upload_preview_token,
    with_preview_token,
)

SALT = "houston.test-preview"


def test_preview_token_round_trips_and_differs_by_membership():
    establishment_id = uuid.uuid4()
    attachment_id = uuid.uuid4()
    first_membership_id = uuid.uuid4()
    second_membership_id = uuid.uuid4()
    first = sign_upload_preview_token(
        salt=SALT,
        establishment_id=establishment_id,
        attachment_id=attachment_id,
        membership_id=first_membership_id,
    )
    second = sign_upload_preview_token(
        salt=SALT,
        establishment_id=establishment_id,
        attachment_id=attachment_id,
        membership_id=second_membership_id,
    )
    assert first != second
    assert unsign_upload_preview_token(salt=SALT, token=first) == (
        establishment_id,
        attachment_id,
        first_membership_id,
    )


def test_preview_token_rejects_a_bad_signature_and_expiry(settings, monkeypatch):
    settings.HOUSTON_UPLOAD_PREVIEW_TOKEN_TTL_SECONDS = 3600
    token = sign_upload_preview_token(
        salt=SALT,
        establishment_id=uuid.uuid4(),
        attachment_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )
    assert unsign_upload_preview_token(salt=SALT, token=f"{token}x") is None

    def expired(*_args, **_kwargs):
        raise SignatureExpired("expired")

    monkeypatch.setattr(
        "houston.uploads.preview_tokens.TimestampSigner.unsign",
        lambda self, value, max_age=None: expired(),
    )
    assert unsign_upload_preview_token(salt=SALT, token=token) is None


def test_with_preview_token_keeps_a_relative_url():
    token = "abc:def"
    assert with_preview_token("/preview/", token) == "/preview/?token=abc%3Adef"
    assert with_preview_token("/preview/?variant=thumbnail", None) == (
        "/preview/?variant=thumbnail"
    )
    assert "token=" not in with_preview_token("/preview/", None)


@pytest.mark.parametrize("token", ["", "   "])
def test_blank_preview_token_does_not_unsign(token):
    assert unsign_upload_preview_token(salt=SALT, token=token.strip()) is None
