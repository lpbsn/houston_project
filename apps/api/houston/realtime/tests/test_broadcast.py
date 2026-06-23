from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from houston.accounts.models import UserSession
from houston.accounts.services import revoke_session, switch_selected_establishment
from houston.realtime.groups import establishment_group_name, session_group_name
from houston.realtime.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    login,
)
from houston.signals.services import pin_signal
from houston.signals.tests.conftest import build_api_membership, create_minimal_v3_signal

pytestmark = pytest.mark.django_db(transaction=True)


def test_invalidation_not_emitted_on_transaction_rollback():
    membership = build_api_membership(role="owner")
    signal = create_minimal_v3_signal(membership, title="Rollback")

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                pin_signal(signal=signal, membership=membership)
                raise RuntimeError("force rollback")

        mock_notify.assert_not_called()


def test_invalidation_emitted_after_commit():
    membership = build_api_membership(role="owner")
    signal = create_minimal_v3_signal(membership, title="Commit")

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        pin_signal(signal=signal, membership=membership)

        mock_notify.assert_called_once_with(
            establishment_id=signal.establishment_id,
            subject_type="signal",
            reason="signal.updated",
            entity_id=signal.id,
        )


def test_access_event_uses_session_group_not_establishment_group(api_client):
    establishment = create_establishment()
    user = create_user(username="realtime_session_group")
    create_membership(user=user, establishment=establishment)
    login(api_client, user=user)
    session = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session is not None

    with patch("houston.realtime.broadcast._send_to_group") as mock_send:
        revoke_session(session=session)

        mock_send.assert_called()
        group_names = [call.kwargs["group_name"] for call in mock_send.call_args_list]
        assert session_group_name(session_id=session.id) in group_names
        assert establishment_group_name(establishment_id=establishment.id) not in group_names


def test_switch_establishment_emits_establishment_switched(api_client):
    first = create_establishment(name="First")
    second = create_establishment(name="Second")
    user = create_user(username="realtime_switch")
    create_membership(user=user, establishment=first)
    create_membership(user=user, establishment=second)
    login(api_client, user=user)
    session = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session is not None
    session.selected_establishment = first
    session.save(update_fields=["selected_establishment", "updated_at"])

    with patch("houston.realtime.broadcast.notify_access_event") as mock_notify:
        switch_selected_establishment(session=session, establishment_id=second.id)

        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs["reason"] == "establishment.switched"
        assert mock_notify.call_args.kwargs["session_id"] == session.id


def test_invalidate_payload_has_no_sensitive_fields():
    from houston.realtime.ws_payloads import build_invalidate_payload

    payload = build_invalidate_payload(
        subject_type="signal",
        reason="signal.updated",
        establishment_id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
    )

    allowed = {"type", "subject_type", "reason", "establishment_id", "entity_id", "occurred_at"}
    assert set(payload.keys()) == allowed
    assert payload["type"] == "invalidate"


def test_membership_invalidation_not_emitted_on_transaction_rollback():
    from houston.actions.tests.conftest import build_api_membership_on_establishment
    from houston.establishments.models import EstablishmentMembership
    from houston.notifications.models import Notification
    from houston.notifications.services import create_in_app_notification

    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                create_in_app_notification(
                    establishment_id=owner.establishment_id,
                    recipient_membership=staff,
                    event_key=Notification.EventKey.ACTION_CREATED,
                    subject_type=Notification.SubjectType.ACTION,
                    subject_id=uuid.uuid4(),
                    priority=Notification.Priority.ACTION_REQUIRED,
                    actor_membership=owner,
                    skip_subject_visibility_recheck=True,
                )
                raise RuntimeError("force rollback")

        mock_notify.assert_not_called()


def test_membership_invalidation_emitted_after_commit():
    from houston.actions.tests.conftest import build_api_membership_on_establishment
    from houston.establishments.models import EstablishmentMembership
    from houston.notifications.models import Notification
    from houston.notifications.services import (
        NOTIFICATION_CREATED_REASON,
        NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
        create_in_app_notification,
    )

    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        notification = create_in_app_notification(
            establishment_id=owner.establishment_id,
            recipient_membership=staff,
            event_key=Notification.EventKey.ACTION_CREATED,
            subject_type=Notification.SubjectType.ACTION,
            subject_id=uuid.uuid4(),
            priority=Notification.Priority.ACTION_REQUIRED,
            actor_membership=owner,
            skip_subject_visibility_recheck=True,
        )

        assert notification is not None
        mock_notify.assert_called_once_with(
            establishment_id=owner.establishment_id,
            membership_id=staff.id,
            subject_type=NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
            reason=NOTIFICATION_CREATED_REASON,
            entity_id=notification.id,
        )
