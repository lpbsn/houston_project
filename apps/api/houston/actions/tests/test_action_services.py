from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.services import (
    accept_action,
    create_action,
    mark_action_done,
    validate_action,
)
from houston.actions.tests.conftest import (
    build_api_membership,
    build_api_membership_on_establishment,
    create_signal_for_membership,
    create_taxonomy,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal

pytestmark = pytest.mark.django_db


def test_mark_action_done_sets_marked_done_at_not_validated():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    module, domain, subject = create_taxonomy(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        module_key=module.key,
        domain_key=domain.key,
        subject_key=subject.key,
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
    module, domain, subject = create_taxonomy(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        module_key=module.key,
        domain_key=domain.key,
        subject_key=subject.key,
    )
    action = accept_action(action=action)
    action = mark_action_done(action=action)
    action = validate_action(action=action)

    action.refresh_from_db()
    assert action.status == Action.Status.DONE
    assert action.validated_at is not None


def test_first_linked_action_moves_signal_to_in_progress_and_unpins():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal = create_signal_for_membership(owner, status=Signal.Status.OPEN)
    signal.is_pinned = True
    signal.pinned_at = timezone.now()
    signal.pinned_by_membership = owner
    signal.save()

    module, domain, subject = create_taxonomy(owner.establishment)
    create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked",
        instruction="Work",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        module_key=module.key,
        domain_key=domain.key,
        subject_key=subject.key,
        signal_id=signal.id,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS
    assert signal.is_pinned is False


def test_linked_action_auto_resolves_signal_when_all_done():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal = create_signal_for_membership(owner, status=Signal.Status.IN_PROGRESS)
    module, domain, subject = create_taxonomy(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked",
        instruction="Work",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        module_key=module.key,
        domain_key=domain.key,
        subject_key=subject.key,
        signal_id=signal.id,
    )
    action = accept_action(action=action)
    action = mark_action_done(action=action)
    validate_action(action=action)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
