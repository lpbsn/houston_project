from __future__ import annotations

import pytest

from houston.accounts.models import User
from houston.establishments.invite_eligibility import (
    InviteTargetDecision,
    evaluate_invite_target,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.factories import create_establishment, create_membership, create_user

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("user_status", "expected"),
    [
        (User.Status.ACTIVE, InviteTargetDecision.USER_EXISTS),
        (User.Status.SUSPENDED, InviteTargetDecision.USER_EXISTS),
        (User.Status.ANONYMIZED, InviteTargetDecision.USER_EXISTS),
    ],
)
def test_evaluate_invite_target_non_pending_user_exists(user_status, expected):
    user = create_user(username=f"invite_elig_{user_status}", status=user_status)
    assert (
        evaluate_invite_target(
            user=user,
            membership=None,
            invited_role=EstablishmentMembership.Role.STAFF,
        )
        == expected
    )


def test_evaluate_invite_target_no_user_creates_pending():
    assert (
        evaluate_invite_target(
            user=None,
            membership=None,
            invited_role=EstablishmentMembership.Role.STAFF,
        )
        == InviteTargetDecision.CREATE_PENDING_USER
    )


def test_evaluate_invite_target_pending_without_membership_user_exists():
    user = create_user(username="pending_no_membership", status=User.Status.PENDING)
    assert (
        evaluate_invite_target(
            user=user,
            membership=None,
            invited_role=EstablishmentMembership.Role.STAFF,
        )
        == InviteTargetDecision.USER_EXISTS
    )


@pytest.mark.parametrize(
    "membership_status",
    [
        EstablishmentMembership.Status.INVITED,
        EstablishmentMembership.Status.ACTIVE,
    ],
)
def test_evaluate_invite_target_pending_invited_or_active_is_duplicate(membership_status):
    establishment = create_establishment(name="Elig Est")
    user = create_user(username=f"pending_{membership_status}", status=User.Status.PENDING)
    membership = create_membership(
        establishment=establishment,
        user=user,
        role=EstablishmentMembership.Role.STAFF,
        status=membership_status,
    )
    assert (
        evaluate_invite_target(
            user=user,
            membership=membership,
            invited_role=EstablishmentMembership.Role.STAFF,
        )
        == InviteTargetDecision.DUPLICATE
    )


def test_evaluate_invite_target_pending_deactivated_same_role_resumes():
    establishment = create_establishment(name="Elig Resume")
    user = create_user(username="pending_deactivated_same", status=User.Status.PENDING)
    membership = create_membership(
        establishment=establishment,
        user=user,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.DEACTIVATED,
    )
    assert (
        evaluate_invite_target(
            user=user,
            membership=membership,
            invited_role=EstablishmentMembership.Role.STAFF,
        )
        == InviteTargetDecision.RESUME_DEACTIVATED
    )


def test_evaluate_invite_target_pending_deactivated_different_role_duplicate():
    establishment = create_establishment(name="Elig Diff Role")
    user = create_user(username="pending_deactivated_diff", status=User.Status.PENDING)
    membership = create_membership(
        establishment=establishment,
        user=user,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.DEACTIVATED,
    )
    assert (
        evaluate_invite_target(
            user=user,
            membership=membership,
            invited_role=EstablishmentMembership.Role.STAFF,
        )
        == InviteTargetDecision.DUPLICATE
    )
