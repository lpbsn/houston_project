from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from houston.accounts.models import PlayStoreAccessRequest, User, UserSession
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.resend_client import (
    InvitationEmailPermanentError,
    InvitationEmailTemporaryError,
    send_invitation_email_via_resend,
)
from houston.organizations.models import Organization

RESEND_IDEMPOTENCY_WINDOW = timedelta(hours=24)

PLAY_CLOSED_TESTING_JOIN_URL = "https://play.google.com/apps/testing/app.spore"
PLAY_CLOSED_TESTING_INSTALL_URL = "https://play.google.com/store/apps/details?id=app.spore"

SUBJECT_REQUEST = "Demande d’accès Google Play"
SUBJECT_CORRECTION = "Correction — demande d’accès Google Play"
SUBJECT_RETRANSMISSION = "Nouvelle transmission — demande d’accès Google Play"

_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


class PlayStoreAccessUnavailable(Exception):
    """A new payload cannot be frozen because delivery is not configured."""


class PlayStoreAccessNotAccepted(Exception):
    """Resend did not accept the key that was sent."""


class PlayStoreAccessSuperseded(Exception):
    """The provider result belongs to a key that is no longer current."""


@dataclass(frozen=True)
class _PreparedSend:
    request_id: uuid.UUID
    idempotency_key: uuid.UUID
    to_email: str
    from_email: str
    subject: str
    html_body: str
    text_body: str
    skip_send: bool


def play_store_access_status(record: PlayStoreAccessRequest | None) -> str:
    if record is None:
        return "none"
    if record.provider_accepted_at is not None:
        return "accepted"
    return "pending"


def submit_play_store_access(
    *,
    user: User,
    google_play_email: str,
    establishment_id=None,
    session: UserSession | None = None,
    send=None,
) -> PlayStoreAccessRequest:
    sender = send_invitation_email_via_resend if send is None else send
    normalized_email = _normalize_play_email(google_play_email)
    prepared = _prepare(
        user=user,
        normalized_email=normalized_email,
        establishment_id=establishment_id,
        session=session,
    )
    if prepared.skip_send:
        return PlayStoreAccessRequest.objects.get(pk=prepared.request_id)

    sent_key = prepared.idempotency_key
    try:
        sender(
            to_email=prepared.to_email,
            from_email=prepared.from_email,
            subject=prepared.subject,
            html_body=prepared.html_body,
            text_body=prepared.text_body,
            idempotency_key=str(sent_key),
        )
    except (InvitationEmailTemporaryError, InvitationEmailPermanentError) as exc:
        raise PlayStoreAccessNotAccepted(str(exc)) from exc

    now = timezone.now()
    updated = PlayStoreAccessRequest.objects.filter(
        pk=prepared.request_id,
        idempotency_key=sent_key,
    ).update(provider_accepted_at=now, updated_at=now)
    try:
        current = PlayStoreAccessRequest.objects.get(pk=prepared.request_id)
    except PlayStoreAccessRequest.DoesNotExist as exc:
        raise PlayStoreAccessSuperseded from exc
    if updated == 0 or current.idempotency_key != sent_key:
        raise PlayStoreAccessSuperseded
    return current


def _prepare(
    *,
    user: User,
    normalized_email: str,
    establishment_id,
    session: UserSession | None,
) -> _PreparedSend:
    try:
        return _prepare_locked(
            user=user,
            normalized_email=normalized_email,
            establishment_id=establishment_id,
            session=session,
        )
    except IntegrityError:
        return _prepare_locked(
            user=user,
            normalized_email=normalized_email,
            establishment_id=establishment_id,
            session=session,
        )


def _prepare_locked(
    *,
    user: User,
    normalized_email: str,
    establishment_id,
    session: UserSession | None,
) -> _PreparedSend:
    with transaction.atomic():
        record = (
            PlayStoreAccessRequest.objects.select_for_update().filter(user=user).first()
        )
        now = timezone.now()
        if record is None:
            return _snapshot(
                _create_record(
                    user=user,
                    normalized_email=normalized_email,
                    establishment_id=establishment_id,
                    session=session,
                    now=now,
                    correction=False,
                    retransmission=False,
                ),
                skip_send=False,
            )

        same_address = record.google_play_email == normalized_email
        if same_address and record.provider_accepted_at is not None:
            return _snapshot(record, skip_send=True)

        if same_address and _key_is_current(record, now):
            return _snapshot(record, skip_send=False)

        correction = not same_address
        _replace_payload(
            record=record,
            user=user,
            normalized_email=normalized_email,
            establishment_id=establishment_id,
            session=session,
            now=now,
            correction=correction,
            retransmission=same_address,
        )
        return _snapshot(record, skip_send=False)


def _create_record(
    *,
    user: User,
    normalized_email: str,
    establishment_id,
    session: UserSession | None,
    now,
    correction: bool,
    retransmission: bool,
) -> PlayStoreAccessRequest:
    payload = _freeze_payload(
        user=user,
        normalized_email=normalized_email,
        establishment_id=establishment_id,
        session=session,
        now=now,
        correction=correction,
        retransmission=retransmission,
    )
    return PlayStoreAccessRequest.objects.create(
        user=user,
        google_play_email=normalized_email,
        idempotency_key=uuid.uuid4(),
        idempotency_key_created_at=now,
        provider_accepted_at=None,
        is_address_correction=correction,
        **payload,
    )


def _replace_payload(
    *,
    record: PlayStoreAccessRequest,
    user: User,
    normalized_email: str,
    establishment_id,
    session: UserSession | None,
    now,
    correction: bool,
    retransmission: bool,
) -> None:
    payload = _freeze_payload(
        user=user,
        normalized_email=normalized_email,
        establishment_id=establishment_id,
        session=session,
        now=now,
        correction=correction,
        retransmission=retransmission,
    )
    record.google_play_email = normalized_email
    record.idempotency_key = uuid.uuid4()
    record.idempotency_key_created_at = now
    record.provider_accepted_at = None
    record.is_address_correction = correction
    for field, value in payload.items():
        setattr(record, field, value)
    record.save(
        update_fields=[
            "google_play_email",
            "idempotency_key",
            "idempotency_key_created_at",
            "provider_accepted_at",
            "is_address_correction",
            *payload.keys(),
            "updated_at",
        ]
    )


def _freeze_payload(
    *,
    user: User,
    normalized_email: str,
    establishment_id,
    session: UserSession | None,
    now,
    correction: bool,
    retransmission: bool,
) -> dict[str, str]:
    operator_email = (getattr(settings, "HOUSTON_OPERATOR_EMAIL", "") or "").strip()
    from_email = (getattr(settings, "HOUSTON_INVITATION_EMAIL_FROM", "") or "").strip()
    if not settings.RESEND_API_KEY or not operator_email or not from_email:
        raise PlayStoreAccessUnavailable

    if correction:
        subject = SUBJECT_CORRECTION
    elif retransmission:
        subject = SUBJECT_RETRANSMISSION
    else:
        subject = SUBJECT_REQUEST

    context = {
        "spore_email": (user.email or "").strip() or "non renseignée",
        "establishment_name": _establishment_name(
            user=user,
            establishment_id=establishment_id,
            session=session,
        ),
        "play_email": normalized_email,
        "transmitted_on": _format_transmission_date(now),
        "is_address_correction": correction,
        "is_retransmission": retransmission,
        "join_url": PLAY_CLOSED_TESTING_JOIN_URL,
        "install_url": PLAY_CLOSED_TESTING_INSTALL_URL,
    }
    return {
        "mail_to": operator_email,
        "mail_from": from_email,
        "mail_subject": subject,
        "mail_html": render_to_string("accounts/email/play_store_access.html", context),
        "mail_text": render_to_string("accounts/email/play_store_access.txt", context),
    }


def _snapshot(record: PlayStoreAccessRequest, *, skip_send: bool) -> _PreparedSend:
    return _PreparedSend(
        request_id=record.pk,
        idempotency_key=record.idempotency_key,
        to_email=record.mail_to,
        from_email=record.mail_from,
        subject=record.mail_subject,
        html_body=record.mail_html,
        text_body=record.mail_text,
        skip_send=skip_send,
    )


def _key_is_current(record: PlayStoreAccessRequest, now) -> bool:
    return now - record.idempotency_key_created_at < RESEND_IDEMPOTENCY_WINDOW


def _normalize_play_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized:
        raise PlayStoreAccessUnavailable
    return normalized


def _format_transmission_date(moment) -> str:
    local = timezone.localtime(moment)
    return f"{local.day} {_MONTHS[local.month - 1]} {local.year}"


def _establishment_name(*, user: User, establishment_id, session: UserSession | None) -> str:
    verified = _membership_name(
        user,
        establishment_id,
        (Establishment.Status.ACTIVE, Establishment.Status.DRAFT),
    )
    if verified:
        return verified
    operational = _operational_name(user, session)
    if operational:
        return operational
    pending = _sole_pending_name(user)
    return pending or ""


def _operational_name(user: User, session: UserSession | None) -> str | None:
    selected_id = None if session is None else session.selected_establishment_id
    if selected_id is not None:
        selected = _membership_name(user, selected_id, (Establishment.Status.ACTIVE,))
        if selected:
            return selected
    rows = list(_operational_memberships(user)[:2])
    if len(rows) == 1:
        return _clean_name(rows[0].establishment.name)
    return None


def _sole_pending_name(user: User) -> str | None:
    if _operational_memberships(user).exists():
        return None
    rows = list(_pending_memberships(user)[:2])
    if len(rows) == 1:
        return _clean_name(rows[0].establishment.name)
    return None


def _membership_name(user: User, establishment_id, establishment_statuses) -> str | None:
    if not establishment_id:
        return None
    membership = (
        EstablishmentMembership.objects.select_related("establishment")
        .filter(
            user=user,
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status__in=establishment_statuses,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .first()
    )
    if membership is None:
        return None
    return _clean_name(membership.establishment.name)


def _operational_memberships(user: User):
    return EstablishmentMembership.objects.select_related("establishment").filter(
        user=user,
        status=EstablishmentMembership.Status.ACTIVE,
        establishment__status=Establishment.Status.ACTIVE,
        establishment__organization__status=Organization.Status.ACTIVE,
    )


def _pending_memberships(user: User):
    return EstablishmentMembership.objects.select_related("establishment").filter(
        user=user,
        status=EstablishmentMembership.Status.ACTIVE,
        establishment__status=Establishment.Status.DRAFT,
        establishment__organization__status=Organization.Status.ACTIVE,
    )


def _clean_name(name: str | None) -> str | None:
    cleaned = (name or "").strip()
    return cleaned or None
