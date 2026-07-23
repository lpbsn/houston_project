from __future__ import annotations

from typing import Any

from houston.establishments.models import EstablishmentMembership


def serialize_admin_director(membership: EstablishmentMembership) -> dict[str, Any]:
    """Shared director snapshot for org-admin and establishment-admin payloads."""
    user = membership.user
    display_name = user.get_full_name().strip() or user.username or user.email
    return {
        "membership_id": membership.id,
        "display_name": display_name,
        "email": user.email,
        "status": membership.status,
    }
