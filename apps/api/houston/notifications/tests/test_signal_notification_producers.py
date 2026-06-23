from __future__ import annotations

from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone

from houston.actions.services import (
    accept_action,
    create_action,
    mark_action_done,
    validate_action,
)
from houston.actions.tests.conftest import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.ai.observation_pipeline_schema import PipelineCandidateOutput
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.signals.exceptions import SignalStateError
from houston.signals.models import Signal
from houston.signals.services import (
    ResolvedTaxonomy,
    aggregate_candidate_into_signal,
    cancel_signal,
    create_signal_from_candidate,
    pin_signal,
    resolve_signal,
    set_signal_urgency,
)
from houston.signals.tests.conftest import (
    auth_headers,
    create_restaurant_v3_taxonomy,
    login,
    signal_detail_url,
)
from houston.testing.auth import build_api_membership
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db(transaction=True)

SENSITIVE_MARKERS = (
    "Sensitive signal title",
    "Sensitive observation summary",
    "Do not leak",
)


def _notifications_for_signal(*, signal_id) -> list[Notification]:
    return list(
        Notification.objects.filter(
            subject_type=Notification.SubjectType.SIGNAL,
            subject_id=signal_id,
        ).order_by("recipient_membership_id", "event_key")
    )


def _recipient_ids(notifications: list[Notification]) -> set:
    return {item.recipient_membership_id for item in notifications}


def _assert_generic_copy(notification: Notification) -> None:
    for marker in SENSITIVE_MARKERS:
        assert marker not in notification.title
        assert marker not in notification.body


def _open_signal(
    owner: EstablishmentMembership,
    *,
    affected=None,
    responsible=None,
    activity_subject=None,
) -> Signal:
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    return create_signal_v3_for_membership(
        owner,
        affected_business_unit=affected or taxonomy.restaurant,
        responsible_business_unit=responsible or taxonomy.maintenance,
        activity_subject=activity_subject or taxonomy.lighting_subject,
        title="Sensitive signal title",
    )


def test_signal_created_notifies_responsible_pole_scope_only():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    observation = create_observation(membership=owner)
    resolved = ResolvedTaxonomy(
        operational_unit=None,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    candidate = PipelineCandidateOutput(
        title="Sensitive signal title",
        structured_summary="Sensitive observation summary",
        issue_focus="fuite eau",
        affected_business_unit_key=hotel.key,
        responsible_business_unit_key=maintenance.key,
        activity_subject_key=electricite.normalized_name,
    )

    signal = create_signal_from_candidate(
        observation=observation,
        candidate=candidate,
        resolved=resolved,
        title=candidate.title,
        structured_summary=candidate.structured_summary,
    )

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.SIGNAL_CREATED
    assert notifications[0].actor_membership_id is None
    _assert_generic_copy(notifications[0])


def test_signal_created_union_affected_and_responsible_poles():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    affected_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    responsible_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(affected_staff, taxonomy.restaurant)
    assign_business_unit_scope(responsible_staff, taxonomy.maintenance)
    signal = _open_signal(
        owner,
        affected=taxonomy.restaurant,
        responsible=taxonomy.maintenance,
    )
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert _recipient_ids(notifications) == {affected_staff.id, responsible_staff.id}


def test_signal_created_double_scope_member_receives_one_notification():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.restaurant)
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id


def test_owner_director_without_pole_scope_receive_no_signal_notification():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert _recipient_ids(notifications) == {staff.id}
    assert owner.id not in _recipient_ids(notifications)
    assert director.id not in _recipient_ids(notifications)


def test_signal_out_of_scope_receives_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assign_business_unit_scope(staff, taxonomy.bar)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    assert _notifications_for_signal(signal_id=signal.id) == []


def test_signal_urgency_changed_to_high_notifies_pole_excludes_actor():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    set_signal_urgency(
        signal=signal,
        urgency=Signal.Urgency.HIGH,
        actor_membership=manager,
    )

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.SIGNAL_URGENCY_CHANGED
    assert notifications[0].priority == Notification.Priority.URGENT


def test_signal_urgency_already_high_emits_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    signal = _open_signal(owner)
    signal.urgency = Signal.Urgency.HIGH
    signal.save(update_fields=["urgency", "updated_at"])
    Notification.objects.filter(subject_id=signal.id).delete()

    with patch(
        "houston.notifications.scheduling.schedule_signal_urgency_changed_notification",
    ) as mock_schedule:
        set_signal_urgency(
            signal=signal,
            urgency=Signal.Urgency.HIGH,
            actor_membership=manager,
        )
        mock_schedule.assert_not_called()

    assert _notifications_for_signal(signal_id=signal.id) == []


def test_signal_pinned_notifies_pole_excludes_actor():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    pin_signal(signal=signal, membership=manager)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.SIGNAL_PINNED


def test_signal_already_pinned_emits_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    signal = _open_signal(owner)
    signal.is_pinned = True
    signal.save(update_fields=["is_pinned", "updated_at"])
    Notification.objects.filter(subject_id=signal.id).delete()

    with patch(
        "houston.notifications.scheduling.schedule_signal_pinned_notification",
    ) as mock_schedule:
        pin_signal(signal=signal, membership=manager)
        mock_schedule.assert_not_called()


def test_signal_resolved_notifies_pole_excludes_actor():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    resolve_signal(signal=signal, actor_membership=manager)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.SIGNAL_RESOLVED


def test_signal_canceled_notifies_pole_excludes_actor():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    cancel_signal(signal=signal, actor_membership=manager)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.SIGNAL_CANCELED


def test_signal_terminal_transition_emits_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _open_signal(owner)
    signal.status = Signal.Status.RESOLVED
    signal.save(update_fields=["status", "updated_at"])
    Notification.objects.filter(subject_id=signal.id).delete()

    with patch(
        "houston.notifications.scheduling.schedule_signal_resolved_notification",
    ) as mock_schedule:
        with pytest.raises(SignalStateError):
            resolve_signal(signal=signal, actor_membership=owner)
        mock_schedule.assert_not_called()


def test_aggregate_emits_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    observation = create_observation(membership=owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    aggregate_candidate_into_signal(signal=signal, observation=observation)

    assert _notifications_for_signal(signal_id=signal.id) == []


def test_auto_resolve_with_actor_none_notifies_pole_members():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )
    Notification.objects.filter(subject_id=signal.id).delete()

    accept_action(action_id=action.id, accepted_by=staff)
    mark_action_done(action_id=action.id)
    validate_action(action_id=action.id)

    notifications = [
        item
        for item in _notifications_for_signal(signal_id=signal.id)
        if item.event_key == Notification.EventKey.SIGNAL_RESOLVED
    ]
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id


def test_signal_notification_rollback_creates_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                cancel_signal(signal=signal, actor_membership=owner)
                raise RuntimeError("force rollback")

        assert _notifications_for_signal(signal_id=signal.id) == []
        mock_notify.assert_not_called()


def test_signal_canceled_e2e_notification_and_detail_navigation(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)

    cancel_signal(signal=signal, actor_membership=manager)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id

    token = login(api_client, user=staff.user)
    response = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == Signal.Status.CANCELED


def test_signal_notification_invalidate_payload_allowlist():
    import uuid

    from houston.notifications.services import NOTIFICATION_CREATED_REASON
    from houston.realtime.ws_payloads import build_invalidate_payload

    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        cancel_signal(signal=signal, actor_membership=owner)

        mock_notify.assert_called_once()
        payload = build_invalidate_payload(
            subject_type="notification",
            reason=NOTIFICATION_CREATED_REASON,
            establishment_id=owner.establishment_id,
            entity_id=uuid.uuid4(),
        )
        forbidden = {
            "title",
            "body",
            "event_key",
            "structured_summary",
            "instruction",
        }
        assert forbidden.isdisjoint(mock_notify.call_args.kwargs.keys())
        assert forbidden.isdisjoint(payload.keys())
