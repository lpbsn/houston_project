"""Neutral invite-target eligibility decisions (User status × membership).

Does not import establishments.services — callers translate decisions to domain errors.
"""

from __future__ import annotations

from enum import Enum

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership


class InviteTargetDecision(str, Enum):
    CREATE_PENDING_USER = "create_pending_user"
    RESUME_DEACTIVATED = "resume_deactivated"
    DUPLICATE = "duplicate"
    USER_EXISTS = "user_exists"


def evaluate_invite_target(
    *,
    user: User | None,
    membership: EstablishmentMembership | None,
    invited_role: str,
) -> InviteTargetDecision:
    """Decide whether an invite may create, resume, or must refuse.

    Resume is allowed only for User.pending + deactivated membership of the same role.
    """
    if user is None:
        return InviteTargetDecision.CREATE_PENDING_USER

    if user.status != User.Status.PENDING:
        return InviteTargetDecision.USER_EXISTS

    if membership is None:
        return InviteTargetDecision.USER_EXISTS

    if membership.status in {
        EstablishmentMembership.Status.INVITED,
        EstablishmentMembership.Status.ACTIVE,
    }:
        return InviteTargetDecision.DUPLICATE

    if membership.status == EstablishmentMembership.Status.DEACTIVATED:
        if membership.role == invited_role:
            return InviteTargetDecision.RESUME_DEACTIVATED
        return InviteTargetDecision.DUPLICATE

    return InviteTargetDecision.DUPLICATE
