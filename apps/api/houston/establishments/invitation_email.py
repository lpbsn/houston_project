from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from houston.establishments.models import EstablishmentInvitation, EstablishmentMembership
from houston.establishments.resend_client import (
    send_invitation_email_via_resend,
)

logger = logging.getLogger(__name__)

_INVITATION_EMAIL_ROLES = frozenset(
    {
        EstablishmentMembership.Role.STAFF,
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.DIRECTOR,
    }
)

_ROLE_LABELS_FR = {
    EstablishmentMembership.Role.STAFF: "Staff",
    EstablishmentMembership.Role.MANAGER: "Manager",
    EstablishmentMembership.Role.DIRECTOR: "Directeur",
}


def build_invitation_accept_url(*, raw_token: str) -> str:
    base_url = settings.HOUSTON_PUBLIC_APP_URL.rstrip("/")
    return f"{base_url}/invitations/{raw_token}"


def _format_expires_at_fr(expires_at) -> str:
    localized = timezone.localtime(expires_at)
    return localized.strftime("%d/%m/%Y à %H:%M")


def _build_invitation_email_subject(*, establishment_name: str) -> str:
    return f"Invitation à rejoindre {establishment_name} sur Spore"


def _render_invitation_email_bodies(*, context: dict) -> tuple[str, str]:
    html_body = render_to_string("establishments/email/invitation.html", context)
    text_body = render_to_string("establishments/email/invitation.txt", context)
    return html_body, text_body


def schedule_establishment_invitation_email(
    *,
    invitation: EstablishmentInvitation,
    membership: EstablishmentMembership,
    raw_token: str,
) -> None:
    if membership.role not in _INVITATION_EMAIL_ROLES:
        logger.info(
            "invitation_email_skipped_unsupported_role",
            extra={
                "event": "invitation_email_skipped_unsupported_role",
                "invitation_id": str(invitation.id),
                "membership_id": str(membership.id),
                "establishment_id": str(membership.establishment_id),
                "role": membership.role,
            },
        )
        return

    if not settings.HOUSTON_INVITATION_EMAIL_ENABLED:
        return

    invitation_id = invitation.id
    membership_id = membership.id
    establishment_id = membership.establishment_id

    def _enqueue() -> None:
        from houston.establishments.tasks import send_establishment_invitation_email_task

        try:
            send_establishment_invitation_email_task.apply_async(
                args=[str(invitation_id), raw_token],
                argsrepr=f"('{invitation_id}', '<redacted>')",
                ignore_result=True,
            )
        except Exception:
            logger.exception(
                "invitation_email_enqueue_failed",
                extra={
                    "event": "invitation_email_enqueue_failed",
                    "invitation_id": str(invitation_id),
                    "membership_id": str(membership_id),
                    "establishment_id": str(establishment_id),
                },
            )

    transaction.on_commit(_enqueue)


def send_establishment_invitation_email(
    *,
    invitation_id: str,
    raw_token: str,
) -> None:
    invitation = (
        EstablishmentInvitation.objects.select_related(
            "membership__user",
            "membership__establishment",
        )
        .filter(id=invitation_id)
        .first()
    )
    if invitation is None:
        logger.info(
            "invitation_email_task_skipped",
            extra={
                "event": "invitation_email_task_skipped",
                "invitation_id": invitation_id,
                "reason": "invitation_not_found",
            },
        )
        return

    membership = invitation.membership
    establishment_id = membership.establishment_id
    membership_id = membership.id
    skip_reason = _invitation_skip_reason(invitation=invitation, membership=membership)
    if skip_reason is not None:
        logger.info(
            "invitation_email_task_skipped",
            extra={
                "event": "invitation_email_task_skipped",
                "invitation_id": invitation_id,
                "membership_id": str(membership_id),
                "establishment_id": str(establishment_id),
                "reason": skip_reason,
            },
        )
        return

    user = membership.user
    accept_url = build_invitation_accept_url(raw_token=raw_token)
    role_label = _ROLE_LABELS_FR.get(membership.role, membership.role)
    context = {
        "first_name": user.first_name,
        "establishment_name": membership.establishment.name,
        "role_label": role_label,
        "accept_url": accept_url,
        "expires_at_label": _format_expires_at_fr(invitation.expires_at),
    }
    subject = _build_invitation_email_subject(establishment_name=membership.establishment.name)
    html_body, text_body = _render_invitation_email_bodies(context=context)
    idempotency_key = f"membership-invitation/{invitation.id}"

    send_invitation_email_via_resend(
        to_email=user.email,
        from_email=settings.HOUSTON_INVITATION_EMAIL_FROM,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        idempotency_key=idempotency_key,
    )


def _invitation_skip_reason(
    *,
    invitation: EstablishmentInvitation,
    membership: EstablishmentMembership,
) -> str | None:
    if membership.role not in _INVITATION_EMAIL_ROLES:
        return "unsupported_role"
    if invitation.revoked_at is not None:
        return "revoked"
    if invitation.accepted_at is not None:
        return "accepted"
    if invitation.expires_at <= timezone.now():
        return "expired"
    return None


def build_invitation_idempotency_key(invitation_id: uuid.UUID | str) -> str:
    return f"membership-invitation/{invitation_id}"


__all__ = [
    "build_invitation_accept_url",
    "build_invitation_idempotency_key",
    "schedule_establishment_invitation_email",
    "send_establishment_invitation_email",
]
