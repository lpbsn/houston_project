from __future__ import annotations

from houston.establishments.models import EstablishmentMembership


def build_bootstrap_permission_hints(
    active_membership: EstablishmentMembership | None,
) -> dict:
    from houston.chat.permissions import can_access_chat
    from houston.establishments.permissions import (
        can_invite_memberships,
        can_manage_runtime_context,
    )

    return {
        "chat_available": can_access_chat(active_membership),
        "can_invite": can_invite_memberships(active_membership),
        "can_manage_runtime_config": can_manage_runtime_context(active_membership),
    }
