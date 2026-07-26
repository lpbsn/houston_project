from __future__ import annotations

from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone

from houston.action_plans.services import (
    create_action_plan_with_execution,
    mark_action_plan_execution_done,
    validate_action_plan_execution,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.ai.observation_pipeline_schema import PipelineCandidateOutput
from houston.establishments.models import BusinessUnit, EstablishmentMembership
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
)
from houston.signals.tests.conftest import (
    auth_headers,
    create_restaurant_v3_taxonomy,
    login,
    signal_detail_url,
)
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership,
    build_api_membership_on_establishment,
)
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db(transaction=True)

SENSITIVE_MARKERS = (
    "Sensitive signal title",
    "Sensitive observation summary",
    "Do not leak",
)

SIGNAL_CREATED_EVENT_KEYS = frozenset(
    {
        Notification.EventKey.SIGNAL_CREATED,
        Notification.EventKey.SIGNAL_CREATED_UNASSIGNED_GLOBAL,
    }
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


def _assert_mutual_exclusivity(notifications: list[Notification]) -> None:
    event_keys = {item.event_key for item in notifications}
    assert event_keys.issubset(SIGNAL_CREATED_EVENT_KEYS)
    assert len(event_keys) <= 1


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
        canonical_object="canalisation",
        signal_kind="actionable",
        expected_action="repair",
        information_type=None,
        affected_business_unit_routing_key=hotel.routing_key,
        responsible_business_unit_routing_key=maintenance.routing_key,
        activity_subject_routing_key=electricite.routing_key,
        operational_unit_key=None,
        location_text=None,
    )

    signal = create_signal_from_candidate(
        observation=observation,
        candidate=candidate,
        resolved=resolved,
        title=candidate.title,
        structured_summary=candidate.structured_summary,
        routing_status=Signal.RoutingStatus.RESOLVED,
    )

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.SIGNAL_CREATED
    assert notifications[0].actor_membership_id is None
    assert notifications[0].title == f"Nouvelle observation — {maintenance.specific_name}"
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


def test_signal_assigned_without_scoped_staff_notifies_admins_with_pole_title():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    signal = _open_signal(owner)
    pole_name = signal.responsible_business_unit.specific_name
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 2
    assert _recipient_ids(notifications) == {owner.id, director.id}
    assert all(item.event_key == Notification.EventKey.SIGNAL_CREATED for item in notifications)
    assert all(item.title == f"Nouvelle observation — {pole_name}" for item in notifications)
    _assert_mutual_exclusivity(notifications)
    for notification in notifications:
        _assert_generic_copy(notification)


def test_signal_out_of_scope_notifies_admins_with_assigned_pole_title():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assign_business_unit_scope(staff, taxonomy.bar)
    signal = _open_signal(owner)
    pole_name = signal.responsible_business_unit.specific_name
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert _recipient_ids(notifications) == {owner.id, director.id}
    assert staff.id not in _recipient_ids(notifications)
    assert all(item.event_key == Notification.EventKey.SIGNAL_CREATED for item in notifications)
    assert all(item.title == f"Nouvelle observation — {pole_name}" for item in notifications)
    _assert_mutual_exclusivity(notifications)


def test_signal_assigned_admin_fallback_includes_managers_in_triage():
    """When no pole-scoped staff exist, fallback triage includes Managers (Lot 8)."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert _recipient_ids(notifications) == {owner.id, director.id, manager.id}
    assert all(item.event_key == Notification.EventKey.SIGNAL_CREATED for item in notifications)


def test_signal_created_mutual_exclusivity_on_create():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.DIRECTOR)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    _assert_mutual_exclusivity(_notifications_for_signal(signal_id=signal.id))


def test_signal_created_admin_fallback_tenant_isolation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert notifications
    assert all(item.establishment_id == owner.establishment_id for item in notifications)
    assert not Notification.objects.filter(
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=signal.id,
        recipient_membership_id=outsider.id,
    ).exists()


def test_signal_assigned_admin_fallback_inactive_director_excluded():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    director.status = EstablishmentMembership.Status.DEACTIVATED
    director.save(update_fields=["status", "updated_at"])
    signal = _open_signal(owner)
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == owner.id
    assert notifications[0].event_key == Notification.EventKey.SIGNAL_CREATED


def test_signal_truly_unassigned_notifies_triage_roles_unassigned_global():
    """Lot 8 E1: total unassigned notifies Owner, Director, and Managers."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    signal = Signal.objects.create(
        establishment=owner.establishment,
        affected_business_unit=None,
        responsible_business_unit=None,
        activity_subject=None,
        title="Sensitive signal title",
        structured_summary="Sensitive observation summary",
        issue_focus="unassigned focus",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        last_activity_at=timezone.now(),
    )

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 3
    assert _recipient_ids(notifications) == {owner.id, director.id, manager.id}
    assert staff.id not in _recipient_ids(notifications)
    assert all(
        item.event_key == Notification.EventKey.SIGNAL_CREATED_UNASSIGNED_GLOBAL
        for item in notifications
    )
    assert all(item.title == "Observation sans pôle couvert" for item in notifications)
    _assert_mutual_exclusivity(notifications)
    for notification in notifications:
        _assert_generic_copy(notification)


def test_signal_created_uses_catalog_label_when_specific_name_blank():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)
    catalog_label = taxonomy.maintenance.catalog_business_unit.label
    # Whitespace-only specific_name: DB nonempty check passes, display falls back to catalog.
    BusinessUnit.objects.filter(pk=taxonomy.maintenance.pk).update(specific_name=" ")
    Notification.objects.filter(subject_id=signal.id).delete()

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert len(notifications) == 1
    assert notifications[0].event_key == Notification.EventKey.SIGNAL_CREATED
    assert notifications[0].title == f"Nouvelle observation — {catalog_label}"
    assert notifications[0].title != "Nouvelle observation"
    assert notifications[0].title != "Nouvelle observation — "
    _assert_generic_copy(notifications[0])


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


def test_mark_done_validate_emits_signal_resolved_notification():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)

    signal = _open_signal(owner)

    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=taxonomy.maintenance.id,
        title="Sensitive task title",
        source_signal_id=signal.id,
        requires_validation=True,
        tasks=[
            build_task_payload(
                task="Sensitive task instruction",
                business_unit=taxonomy.maintenance,
            )
        ],
        assignees=[
            build_assignee_payload(
                membership=staff,
                business_unit=taxonomy.maintenance,
            )
        ],
    )

    Notification.objects.filter(subject_id=signal.id).delete()

    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner,
    )

    # Le signal ne doit pas être résolu avant validation.
    assert not [
        item
        for item in _notifications_for_signal(signal_id=signal.id)
        if item.event_key == Notification.EventKey.SIGNAL_RESOLVED
    ]

    validate_action_plan_execution(
        execution_id=pending.id,
        actor_membership=owner,
    )

    notifications = [
        item
        for item in _notifications_for_signal(signal_id=signal.id)
        if item.event_key == Notification.EventKey.SIGNAL_RESOLVED
    ]

    assert len(notifications) == 1


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


def test_partial_unassigned_create_notifies_triage_and_pole_staff():
    """Lot 8 E2: partial unassigned → Owner/Director/Managers + scoped pole members."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assign_business_unit_scope(staff, taxonomy.restaurant)
    signal = Signal.objects.create(
        establishment=owner.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=None,
        activity_subject=None,
        title="Sensitive signal title",
        structured_summary="Sensitive observation summary",
        issue_focus="partial focus",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        last_activity_at=timezone.now(),
    )

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert _recipient_ids(notifications) == {owner.id, director.id, manager.id, staff.id}
    assert all(item.event_key == Notification.EventKey.SIGNAL_CREATED for item in notifications)


def test_pin_total_unassigned_notifies_triage_excluding_actor():
    """Lot 8 E3: pin without BU → triage roles, actor excluded."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    signal = Signal.objects.create(
        establishment=owner.establishment,
        affected_business_unit=None,
        responsible_business_unit=None,
        activity_subject=None,
        title="Sensitive signal title",
        structured_summary="Sensitive observation summary",
        issue_focus="unassigned focus",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        last_activity_at=timezone.now(),
    )
    Notification.objects.filter(subject_id=signal.id).delete()

    pin_signal(signal=signal, membership=manager)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert _recipient_ids(notifications) == {owner.id, director.id}
    assert all(item.event_key == Notification.EventKey.SIGNAL_PINNED for item in notifications)


def test_partial_unassigned_with_subject_notifies_triage_and_pole():
    """Lot 8 E2: unassigned subject+responsible without affected → triage ∪ pole."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = Signal.objects.create(
        establishment=owner.establishment,
        affected_business_unit=None,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        title="Sensitive signal title",
        structured_summary="Sensitive observation summary",
        issue_focus="partial subject focus",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        last_activity_at=timezone.now(),
    )

    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert _recipient_ids(notifications) == {owner.id, director.id, manager.id, staff.id}
    assert all(item.event_key == Notification.EventKey.SIGNAL_CREATED for item in notifications)


def test_resolved_attention_keeps_pole_or_triage_fallback():
    """Lot 8 E2: resolved routing keeps pole-or-triage (no forced triage∪pole)."""
    from houston.notifications.recipients import resolve_signal_attention_recipients

    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _open_signal(owner)

    with_pole = resolve_signal_attention_recipients(signal=signal)
    assert {item.id for item in with_pole} == {staff.id}

    # Empty pole → triage fallback including Managers.
    staff.status = EstablishmentMembership.Status.DEACTIVATED
    staff.save(update_fields=["status", "updated_at"])
    fallback = resolve_signal_attention_recipients(signal=signal)
    assert {item.id for item in fallback} == {owner.id, director.id, manager.id}


def test_qualify_inplace_notifies_new_pole_excludes_prior_triage_and_actor():
    """Lot 8 E4 in-place: new pole staff notified; create triage + actor excluded."""
    from houston.signals.models import ExpectedAction
    from houston.signals.services import normalize_issue_focus, qualify_signal_routing

    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = Signal.objects.create(
        establishment=owner.establishment,
        affected_business_unit=None,
        responsible_business_unit=None,
        activity_subject=None,
        title="Sensitive signal title",
        structured_summary="Sensitive observation summary",
        issue_focus="",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        last_activity_at=timezone.now(),
    )
    Notification.objects.filter(subject_id=signal.id).delete()

    focus = normalize_issue_focus("qualify inplace focus")
    qualify_signal_routing(
        signal=signal,
        membership=manager,
        patch={
            "affected_business_unit_id": taxonomy.restaurant.id,
            "responsible_business_unit_id": taxonomy.maintenance.id,
            "activity_subject_id": taxonomy.lighting_subject.id,
            "issue_focus": focus,
            "expected_action": ExpectedAction.REPAIR,
        },
    )

    notifications = _notifications_for_signal(signal_id=signal.id)
    assert _recipient_ids(notifications) == {staff.id}
    assert manager.id not in _recipient_ids(notifications)
    assert owner.id not in _recipient_ids(notifications)
    assert director.id not in _recipient_ids(notifications)
    assert all(item.event_key == Notification.EventKey.SIGNAL_CREATED for item in notifications)


def test_qualify_merge_does_not_renotify_source_survivor_or_actor():
    """Lot 8 E4 merge: previous = source ∪ survivor; notify only truly new on survivor id."""
    from houston.signals.models import ExpectedAction
    from houston.signals.services import normalize_issue_focus, qualify_signal_routing

    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    focus = normalize_issue_focus("qualify merge focus")
    survivor = create_signal_v3_for_membership(
        owner,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        title="Survivor",
        issue_focus=focus,
    )
    source = Signal.objects.create(
        establishment=owner.establishment,
        affected_business_unit=None,
        responsible_business_unit=None,
        activity_subject=None,
        title="Source unassigned",
        structured_summary="Sensitive observation summary",
        issue_focus="",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        last_activity_at=timezone.now(),
    )
    Notification.objects.filter(subject_id__in=[source.id, survivor.id]).delete()

    result = qualify_signal_routing(
        signal=source,
        membership=manager,
        patch={
            "affected_business_unit_id": taxonomy.restaurant.id,
            "responsible_business_unit_id": taxonomy.maintenance.id,
            "activity_subject_id": taxonomy.lighting_subject.id,
            "issue_focus": focus,
            "expected_action": ExpectedAction.REPAIR,
        },
    )
    assert result.qualification_outcome == "merged"
    assert result.surviving_signal_id == survivor.id

    # No new attention on survivor: triage (source) ∪ pole (survivor) covered previous.
    survivor_notifications = _notifications_for_signal(signal_id=survivor.id)
    assert survivor_notifications == []
    assert not Notification.objects.filter(
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=source.id,
        event_key__in=SIGNAL_CREATED_EVENT_KEYS,
    ).exists()
    assert {
        owner.id,
        director.id,
        manager.id,
        staff.id,
    }.isdisjoint(_recipient_ids(survivor_notifications))
