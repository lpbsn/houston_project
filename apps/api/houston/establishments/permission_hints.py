from __future__ import annotations

from houston.establishments.models import EstablishmentMembership


def build_membership_permission_hints(
    *,
    actor_membership: EstablishmentMembership | None,
    target_membership: EstablishmentMembership,
) -> dict[str, bool]:
    from houston.establishments.services import (
        ReinviteTargetDecision,
        actor_can_reinvite_target_membership,
        can_actor_manage_target_membership,
    )

    can_edit_personal_info = (
        actor_membership is not None and actor_membership.user_id == target_membership.user_id
    )
    can_manage = can_actor_manage_target_membership(
        actor_membership=actor_membership,
        target_membership=target_membership,
    )
    can_edit_scopes = can_manage and target_membership.role in {
        EstablishmentMembership.Role.STAFF,
        EstablishmentMembership.Role.MANAGER,
    }
    can_edit_status = (
        can_manage and target_membership.status != EstablishmentMembership.Status.INVITED
    )
    can_reinvite = (
        actor_can_reinvite_target_membership(
            actor_membership=actor_membership,
            target_membership=target_membership,
        )
        == ReinviteTargetDecision.ALLOWED
    )

    return {
        "can_edit_role": can_manage,
        "can_edit_scopes": can_edit_scopes,
        "can_edit_status": can_edit_status,
        "can_edit_personal_info": can_edit_personal_info,
        "can_reinvite": can_reinvite,
    }
