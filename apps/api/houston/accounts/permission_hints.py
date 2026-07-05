from __future__ import annotations

from houston.establishments.models import EstablishmentMembership


def build_bootstrap_permission_hints(
    active_membership: EstablishmentMembership | None,
) -> dict:
    from houston.action_plans.permissions import (
        can_create_action_plan,
        can_create_catalog_action_plan,
    )
    from houston.chat.permissions import can_access_chat
    from houston.establishments.permissions import (
        can_invite_memberships,
        can_manage_runtime_context,
    )

    can_create_action_plan_hint = False
    if active_membership is not None:
        can_create_action_plan_hint = can_create_action_plan(
            active_membership,
            establishment_id=active_membership.establishment_id,
        )

    return {
        "chat_available": can_access_chat(active_membership),
        "can_create_action_plan": can_create_action_plan_hint,
        "can_create_catalog_action_plan": can_create_catalog_action_plan(active_membership),
        "can_invite": can_invite_memberships(active_membership),
        "can_manage_runtime_config": can_manage_runtime_context(active_membership),
    }
