from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.exceptions import ActionValidationError
from houston.actions.models import Action
from houston.actions.services import (
    accept_action,
    create_action,
    mark_action_done,
    validate_action,
)
from houston.actions.tests.conftest import (
    assign_business_unit_scope,
    build_api_membership,
    build_api_membership_on_establishment,
    create_signal_v3_for_membership,
)
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.models import Signal

pytestmark = pytest.mark.django_db


def _hotel_maintenance_setup(establishment):
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
    )
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    electricite = create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Électricité",
    )
    return hotel, maintenance, electricite


def test_mark_action_done_sets_marked_done_at_not_validated():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    action = accept_action(action=action)
    action = mark_action_done(action=action)

    action.refresh_from_db()
    assert action.status == Action.Status.PENDING_VALIDATION
    assert action.marked_done_at is not None
    assert action.validated_at is None


def test_validate_action_sets_validated_at():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    action = accept_action(action=action)
    action = mark_action_done(action=action)
    action = validate_action(action=action)

    action.refresh_from_db()
    assert action.status == Action.Status.DONE
    assert action.validated_at is not None


def test_linked_action_copies_classification_from_signal():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
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
        assigned_to_id=staff.id,
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
            assigned_to_id=staff.id,
            due_at=timezone.now() + timezone.timedelta(days=1),
            signal_id=signal.id,
        )


def test_free_action_stores_responsible_only():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)

    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Free task",
        instruction="Inspect",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=hotel.id,
    )

    assert action.signal_id is None
    assert action.responsible_business_unit_id == hotel.id
    assert action.affected_business_unit_id is None
    assert action.activity_subject_id is None


def test_free_action_rejects_manager_out_of_scope():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager, hotel)

    with pytest.raises(ActionValidationError, match="Not allowed"):
        create_action(
            establishment_id=owner.establishment_id,
            created_by=manager,
            title="Free task",
            instruction="Inspect",
            assigned_to_id=staff.id,
            due_at=timezone.now() + timezone.timedelta(days=1),
            responsible_business_unit_id=maintenance.id,
        )


def test_first_linked_action_moves_signal_to_in_progress_and_unpins():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
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
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS
    assert signal.is_pinned is False


def test_linked_action_auto_resolves_signal_when_all_done():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
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
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )
    action = accept_action(action=action)
    action = mark_action_done(action=action)
    validate_action(action=action)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
