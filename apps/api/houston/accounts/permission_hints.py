from __future__ import annotations

from houston.establishments.models import EstablishmentMembership


def build_bootstrap_permission_hints(
    active_membership: EstablishmentMembership | None,
) -> dict:
    from houston.action_plans.permissions import (
        can_create_action_plan,
        can_create_catalog_action_plan,
        can_view_action_plan_catalog,
    )
    from houston.chat.permissions import can_access_chat
    from houston.establishments.permissions import (
        can_create_action as establishment_can_create_action,
    )
    from houston.establishments.permissions import (
        can_invite_memberships,
        can_manage_runtime_context,
        can_view_team_memberships,
    )

    can_create_action_plan_hint = False
    if active_membership is not None:
        can_create_action_plan_hint = can_create_action_plan(
            active_membership,
            establishment_id=active_membership.establishment_id,
        )
        if (
            not can_create_action_plan_hint
            and active_membership.role == EstablishmentMembership.Role.STAFF
        ):
            can_create_action_plan_hint = establishment_can_create_action(active_membership)

    return {
        "chat_available": can_access_chat(active_membership),
        "can_create_action_plan": can_create_action_plan_hint,
        "can_create_catalog_action_plan": can_create_catalog_action_plan(active_membership),
        "can_view_action_plan_catalog": can_view_action_plan_catalog(active_membership),
        "can_invite": can_invite_memberships(active_membership),
        "can_manage_runtime_config": can_manage_runtime_context(active_membership),
        "can_view_team": can_view_team_memberships(active_membership),
    }
