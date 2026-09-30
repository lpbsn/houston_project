"""Neutral invite-target eligibility decisions (User status × membership).

Does not import establishments.services — callers translate decisions to domain errors.
"""

from __future__ import annotations

from enum import Enum

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership


class InviteTargetDecision(str, Enum):
    CREATE_PENDING_USER = "create_pending_user"
    ATTACH_EXISTING_USER = "attach_existing_user"
    RESUME_DEACTIVATED = "resume_deactivated"
    DUPLICATE = "duplicate"
    USER_EXISTS = "user_exists"


def evaluate_invite_target(
    *,
    user: User | None,
    membership: EstablishmentMembership | None,
    invited_role: str,
) -> InviteTargetDecision:
    """Decide whether an invite may create, attach, resume, or must refuse.

    A pending or active user with no membership on the target establishment is
    attached. Resume stays limited to a pending user and a deactivated
    membership of the same role. An active user with a deactivated membership
    on this establishment is refused.
    """
    if user is None:
        return InviteTargetDecision.CREATE_PENDING_USER

    if user.status not in {User.Status.PENDING, User.Status.ACTIVE}:
        return InviteTargetDecision.USER_EXISTS

    if membership is None:
        return InviteTargetDecision.ATTACH_EXISTING_USER

    if membership.status in {
        EstablishmentMembership.Status.INVITED,
        EstablishmentMembership.Status.ACTIVE,
    }:
        return InviteTargetDecision.DUPLICATE

    if membership.status == EstablishmentMembership.Status.DEACTIVATED:
        if user.status == User.Status.PENDING and membership.role == invited_role:
            return InviteTargetDecision.RESUME_DEACTIVATED
        if user.status == User.Status.PENDING:
            return InviteTargetDecision.DUPLICATE
        return InviteTargetDecision.USER_EXISTS

    return InviteTargetDecision.DUPLICATE
