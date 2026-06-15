from __future__ import annotations

import uuid

import pytest

from houston.accounts.models import User
from houston.comments.constants import INVALID_MENTIONS_ERROR_DETAIL
from houston.comments.exceptions import CommentValidationError
from houston.comments.services import create_signal_comment, normalize_comment_body
from houston.comments.tests.conftest import build_api_membership
from houston.establishments.models import EstablishmentMembership
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _signal(owner):
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    return create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )


def test_normalize_comment_body_trims_and_validates():
    assert normalize_comment_body("  hello  ") == "hello"


def test_normalize_comment_body_rejects_empty():
    with pytest.raises(CommentValidationError, match="required"):
        normalize_comment_body("   ")


def test_create_signal_comment_dedupes_mentions():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    mentioned_user = User.objects.create_user(
        username=f"m_{uuid.uuid4().hex[:8]}",
        password="secret",
        status=User.Status.ACTIVE,
    )
    mentioned = EstablishmentMembership.objects.create(
        user=mentioned_user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    signal = _signal(owner)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="Regarde ceci",
        mentioned_membership_ids=[mentioned.id, mentioned.id],
    )

    assert comment.mention_links.count() == 1


def test_create_signal_comment_rejects_invalid_mention():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    with pytest.raises(CommentValidationError, match=INVALID_MENTIONS_ERROR_DETAIL):
        create_signal_comment(
            author_membership=owner,
            signal=signal,
            body="hello",
            mentioned_membership_ids=[uuid.uuid4()],
        )


def test_create_signal_comment_allows_self_mention():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="note",
        mentioned_membership_ids=[owner.id],
    )

    assert comment.mention_links.filter(mentioned_membership_id=owner.id).exists()
