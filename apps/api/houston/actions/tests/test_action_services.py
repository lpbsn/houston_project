from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.utils import timezone

from houston.actions.exceptions import (
    ActionPermissionError,
    ActionStateError,
    ActionValidationError,
)
from houston.actions.models import Action, ActionAssignee
from houston.actions.permissions import can_mark_action_done
from houston.actions.services import (
    accept_action,
    cancel_action,
    create_action,
    mark_action_done,
    reassign_action,
    reopen_action,
    validate_action,
)
from houston.actions.tests.conftest import (
    assign_business_unit_scope,
    build_api_membership,
    build_api_membership_on_establishment,
    create_signal_v3_for_membership,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.taxonomy import hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _open_action(*, owner, staff, maintenance, requires_validation: bool = True):
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
        requires_validation=requires_validation,
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_accept_only_one_succeeds():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff_a = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    staff_b = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assignee_ids=[staff_a.id, staff_b.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )

    def try_accept(membership: EstablishmentMembership) -> str:
        close_old_connections()
        try:
            accept_action(action_id=action.id, accepted_by=membership)
            return "ok"
        except ActionStateError:
            return "error"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(try_accept, [staff_a, staff_b]))

    assert results.count("ok") == 1
    assert results.count("error") == 1
    action.refresh_from_db()
    assert action.status == Action.Status.IN_PROGRESS
    assert action.accepted_by_id in {staff_a.id, staff_b.id}


def test_accept_action_transitions_open_to_in_progress():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)

    action = accept_action(action_id=action.id, accepted_by=staff)

    action.refresh_from_db()
    assert action.status == Action.Status.IN_PROGRESS
    assert action.accepted_at is not None
    assert action.accepted_by_id == staff.id


def test_in_progress_accepted_by_backfill_unlocks_mark_done():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    action = accept_action(action_id=action.id, accepted_by=staff)

    action.accepted_by = None
    action.save(update_fields=["accepted_by"])
    assert can_mark_action_done(staff, action) is False

    # Simulates 0005 backfill: accepted_by_id = legacy assigned_to (single assignee).
    action.accepted_by_id = staff.id
    action.save(update_fields=["accepted_by_id"])
    assert can_mark_action_done(staff, action) is True


def test_accept_action_rejects_done_state():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    action.status = Action.Status.DONE
    action.save(update_fields=["status", "updated_at"])

    with pytest.raises(ActionStateError, match="cannot be accepted"):
        accept_action(action_id=action.id, accepted_by=staff)


def test_reopen_action_from_pending_validation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    action = accept_action(action_id=action.id, accepted_by=staff)
    action = mark_action_done(action_id=action.id, actor_membership=staff)

    action = reopen_action(action_id=action.id, actor=owner)

    action.refresh_from_db()
    assert action.status == Action.Status.REOPENED
    assert action.accepted_at is None
    assert action.accepted_by_id is None


def test_cancel_action_from_open():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)

    action = cancel_action(action_id=action.id, actor=owner)

    action.refresh_from_db()
    assert action.status == Action.Status.CANCELED


def test_cancel_action_rejects_done_state():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    action.status = Action.Status.DONE
    action.save(update_fields=["status", "updated_at"])

    with pytest.raises(ActionStateError, match="cannot be canceled"):
        cancel_action(action_id=action.id, actor=owner)


def test_reassign_action_updates_assignees_open():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)

    action = reassign_action(
        action_id=action.id,
        assignee_ids=[other_staff.id],
        actor=owner,
    )

    action.refresh_from_db()
    assignee_ids = set(
        ActionAssignee.objects.filter(action_id=action.id).values_list("membership_id", flat=True)
    )
    assert assignee_ids == {other_staff.id}
    assert action.status == Action.Status.OPEN


def test_reassign_action_keeps_reopened_status():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    action.status = Action.Status.REOPENED
    action.save(update_fields=["status", "updated_at"])

    action = reassign_action(
        action_id=action.id,
        assignee_ids=[other_staff.id],
        actor=owner,
    )

    action.refresh_from_db()
    assert action.status == Action.Status.REOPENED


def test_reassign_in_progress_resets_acceptance():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    action = accept_action(action_id=action.id, accepted_by=staff)

    action = reassign_action(
        action_id=action.id,
        assignee_ids=[other_staff.id],
        actor=owner,
    )

    action.refresh_from_db()
    assert action.status == Action.Status.OPEN
    assert action.accepted_by_id is None
    assert action.accepted_at is None


def test_reassign_rejects_pending_validation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    action = accept_action(action_id=action.id, accepted_by=staff)
    action = mark_action_done(action_id=action.id, actor_membership=staff)

    with pytest.raises(ActionStateError, match="cannot be reassigned"):
        reassign_action(
            action_id=action.id,
            assignee_ids=[other_staff.id],
            actor=owner,
        )


def test_reassign_rejects_done_state():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    action.status = Action.Status.DONE
    action.save(update_fields=["status", "updated_at"])

    with pytest.raises(ActionStateError, match="cannot be reassigned"):
        reassign_action(
            action_id=action.id,
            assignee_ids=[other_staff.id],
            actor=owner,
        )


def test_create_action_rejects_duplicate_assignees():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)

    with pytest.raises(ActionValidationError, match="Duplicate assignees"):
        create_action(
            establishment_id=owner.establishment_id,
            created_by=owner,
            title="Task",
            instruction="Do it",
            assignee_ids=[staff.id, staff.id],
            due_at=timezone.now() + timezone.timedelta(days=1),
            responsible_business_unit_id=maintenance.id,
        )


def test_mark_action_done_sets_marked_done_at_not_validated():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    action = accept_action(action_id=action.id, accepted_by=staff)
    action = mark_action_done(action_id=action.id, actor_membership=staff)

    action.refresh_from_db()
    assert action.status == Action.Status.PENDING_VALIDATION
    assert action.marked_done_at is not None
    assert action.validated_at is None


def test_mark_action_done_without_validation_goes_directly_done():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(
        owner=owner,
        staff=staff,
        maintenance=maintenance,
        requires_validation=False,
    )
    action = accept_action(action_id=action.id, accepted_by=staff)
    action = mark_action_done(action_id=action.id, actor_membership=staff)

    action.refresh_from_db()
    assert action.status == Action.Status.DONE
    assert action.marked_done_at is not None
    assert action.validated_at is None


def test_linked_action_without_validation_resolves_signal_on_mark_done():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.IN_PROGRESS,
    )
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked",
        instruction="Work",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
        requires_validation=False,
    )
    action = accept_action(action_id=action.id, accepted_by=staff)
    mark_action_done(action_id=action.id, actor_membership=staff)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_validate_action_sets_validated_at():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    action = accept_action(action_id=action.id, accepted_by=staff)
    action = mark_action_done(action_id=action.id, actor_membership=staff)
    action = validate_action(action_id=action.id, actor_membership=owner)

    action.refresh_from_db()
    assert action.status == Action.Status.DONE
    assert action.validated_at is not None


def test_linked_action_copies_classification_from_signal():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )

    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked",
        instruction="Work",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )

    assert action.affected_business_unit_id == hotel.id
    assert action.responsible_business_unit_id == maintenance.id
    assert action.activity_subject_id == electricite.id


def test_linked_action_rejects_signal_without_classification():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal = Signal.objects.create(
        establishment=owner.establishment,
        title="Unclassified",
        structured_summary="Summary",
        location_text="",
        status=Signal.Status.OPEN,
        last_activity_at=timezone.now(),
    )

    with pytest.raises(ActionValidationError, match="missing affected business unit"):
        create_action(
            establishment_id=owner.establishment_id,
            created_by=owner,
            title="Linked",
            instruction="Work",
            assignee_ids=[staff.id],
            due_at=timezone.now() + timezone.timedelta(days=1),
            signal_id=signal.id,
        )


def test_free_action_stores_responsible_only():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)

    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Free task",
        instruction="Inspect",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=hotel.id,
    )

    assert action.signal_id is None
    assert action.responsible_business_unit_id == hotel.id
    assert action.affected_business_unit_id is None
    assert action.activity_subject_id is None


def test_staff_can_create_self_assigned_free_action_in_scope():
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(staff.establishment)
    assign_business_unit_scope(staff, maintenance)

    action = create_action(
        establishment_id=staff.establishment_id,
        created_by=staff,
        title="Free task",
        instruction="Inspect",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )

    assert action.created_by_id == staff.id
    assert list(
        ActionAssignee.objects.filter(action_id=action.id).values_list("membership_id", flat=True)
    ) == [staff.id]


def test_staff_cannot_create_free_action_out_of_scope():
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(staff.establishment)
    assign_business_unit_scope(staff, hotel)

    with pytest.raises(ActionValidationError, match="Not allowed"):
        create_action(
            establishment_id=staff.establishment_id,
            created_by=staff,
            title="Free task",
            instruction="Inspect",
            assignee_ids=[staff.id],
            due_at=timezone.now() + timezone.timedelta(days=1),
            responsible_business_unit_id=maintenance.id,
        )


def test_staff_cannot_create_linked_action_even_in_scope():
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(staff.establishment)
    assign_business_unit_scope(staff, maintenance)
    signal = create_signal_v3_for_membership(
        staff,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.OPEN,
    )

    with pytest.raises(ActionValidationError, match="cannot create linked actions"):
        create_action(
            establishment_id=staff.establishment_id,
            created_by=staff,
            title="Linked",
            instruction="Work",
            assignee_ids=[staff.id],
            due_at=timezone.now() + timezone.timedelta(days=1),
            signal_id=signal.id,
        )


def test_staff_cannot_create_free_action_assigned_to_other():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)

    with pytest.raises(ActionValidationError, match="only create actions assigned to themselves"):
        create_action(
            establishment_id=owner.establishment_id,
            created_by=staff,
            title="Free task",
            instruction="Inspect",
            assignee_ids=[other_staff.id],
            due_at=timezone.now() + timezone.timedelta(days=1),
            responsible_business_unit_id=maintenance.id,
        )


def test_staff_cannot_create_multi_assignee_free_action():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)

    with pytest.raises(ActionValidationError, match="only create actions assigned to themselves"):
        create_action(
            establishment_id=owner.establishment_id,
            created_by=staff,
            title="Free task",
            instruction="Inspect",
            assignee_ids=[staff.id, other_staff.id],
            due_at=timezone.now() + timezone.timedelta(days=1),
            responsible_business_unit_id=maintenance.id,
        )


def test_free_action_rejects_manager_out_of_scope():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager, hotel)

    with pytest.raises(ActionValidationError, match="Not allowed"):
        create_action(
            establishment_id=owner.establishment_id,
            created_by=manager,
            title="Free task",
            instruction="Inspect",
            assignee_ids=[staff.id],
            due_at=timezone.now() + timezone.timedelta(days=1),
            responsible_business_unit_id=maintenance.id,
        )


def test_first_linked_action_moves_signal_to_in_progress_and_unpins():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.OPEN,
    )
    signal.is_pinned = True
    signal.pinned_at = timezone.now()
    signal.pinned_by_membership = owner
    signal.save()

    create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked",
        instruction="Work",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS
    assert signal.is_pinned is False


def test_linked_action_auto_resolves_signal_when_all_done():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.IN_PROGRESS,
    )
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked",
        instruction="Work",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )
    action = accept_action(action_id=action.id, accepted_by=staff)
    action = mark_action_done(action_id=action.id, actor_membership=staff)
    validate_action(action_id=action.id, actor_membership=owner)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_mark_action_done_rejects_non_accepted_assignee():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assignee_ids=[staff.id, other_staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    action = accept_action(action_id=action.id, accepted_by=staff)

    with pytest.raises(ActionPermissionError, match="Not allowed to mark this action done"):
        mark_action_done(action_id=action.id, actor_membership=other_staff)


def test_validate_action_rejects_staff():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=staff, maintenance=maintenance)
    action = accept_action(action_id=action.id, accepted_by=staff)
    action = mark_action_done(action_id=action.id, actor_membership=staff)

    with pytest.raises(ActionPermissionError, match="Not allowed to validate this action"):
        validate_action(action_id=action.id, actor_membership=staff)


def test_sync_signal_resolves_when_one_done_one_canceled():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.IN_PROGRESS,
    )
    done_action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Done linked",
        instruction="Work",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )
    canceled_action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Canceled linked",
        instruction="Work",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )
    done_action = accept_action(action_id=done_action.id, accepted_by=staff)
    done_action = mark_action_done(action_id=done_action.id, actor_membership=staff)
    validate_action(action_id=done_action.id, actor_membership=owner)
    cancel_action(action_id=canceled_action.id, actor=owner)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_sync_signal_reopens_when_all_linked_actions_canceled():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.IN_PROGRESS,
    )
    signal.is_pinned = True
    signal.pinned_at = timezone.now()
    signal.pinned_by_membership = owner
    signal.save()

    action_a = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked A",
        instruction="Work",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )
    action_b = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked B",
        instruction="Work",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )
    cancel_action(action_id=action_a.id, actor=owner)
    cancel_action(action_id=action_b.id, actor=owner)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.OPEN
    assert signal.is_pinned is False
