from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from django.utils import timezone
from houston.accounts.models import User, UserSession
from houston.chat.permissions import can_access_chat
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization


@dataclass(frozen=True)
class WsAccessValidation:
    ok: bool
    reason: str | None = None


def validate_ws_connection_access(
    *,
    session_id: UUID,
    establishment_id: UUID,
    membership_id: UUID,
    require_selected_establishment: bool = True,
) -> WsAccessValidation:
    session = UserSession.objects.filter(id=session_id).first()
    if session is None:
        return WsAccessValidation(ok=False, reason="access_denied")

    now = timezone.now()
    if session.revoked_at is not None or session.status != UserSession.Status.ACTIVE:
        return WsAccessValidation(ok=False, reason="session_revoked")
    if session.absolute_expires_at <= now:
        return WsAccessValidation(ok=False, reason="session_revoked")

    if require_selected_establishment and session.selected_establishment_id != establishment_id:
        return WsAccessValidation(ok=False, reason="establishment_switched")

    membership = (
        EstablishmentMembership.objects.select_related(
            "user",
            "establishment",
            "establishment__organization",
        )
        .filter(
            id=membership_id,
            status=EstablishmentMembership.Status.ACTIVE,
            user__status=User.Status.ACTIVE,
            establishment_id=establishment_id,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .first()
    )
    if membership is None:
        return WsAccessValidation(ok=False, reason="access_denied")

    if session.user_id != membership.user_id:
        return WsAccessValidation(ok=False, reason="access_denied")

    if not can_access_chat(membership):
        if (
            membership.establishment.status == Establishment.Status.ACTIVE
            and not membership.establishment.chat_enabled
        ):
            return WsAccessValidation(ok=False, reason="chat_disabled")
        return WsAccessValidation(ok=False, reason="access_denied")

    return WsAccessValidation(ok=True)
