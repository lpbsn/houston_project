from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.signals.exceptions import SignalStateError, SignalValidationError
from houston.signals.models import Signal, SignalResolutionRequest
from houston.signals.permissions import can_create_resolution_request, can_resolve_signal
from houston.signals.resolution_request_services import (
    approve_signal_resolution_request,
    cancel_signal_resolution_request_by_requester,
    create_signal_resolution_request,
    reject_signal_resolution_request,
)
from houston.signals.services import resolve_signal
from houston.signals.tests.conftest import build_api_membership, create_minimal_v3_signal
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)

pytestmark = pytest.mark.django_db


def _setup_open_signal_with_responsible_pole():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, title="Resolution request target")
    assert signal.responsible_business_unit_id is not None
    responsible = signal.responsible_business_unit

    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    assign_business_unit_scope(manager, responsible)

    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )

    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    assign_business_unit_scope(staff, responsible)

    return owner, signal, manager, director, staff


def test_staff_creates_staff_to_manager_request_keeps_signal_open():
    _owner, signal, _manager, _director, staff = _setup_open_signal_with_responsible_pole()

    request = create_signal_resolution_request(
        signal=signal,
        actor_membership=staff,
        request_comment="Corrigé sur place",
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.OPEN
    assert request.status == SignalResolutionRequest.Status.PENDING
    assert request.review_route == SignalResolutionRequest.ReviewRoute.STAFF_TO_MANAGER
    assert request.request_comment == "Corrigé sur place"


def test_staff_create_fails_without_eligible_manager():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, title="No manager coverage")
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    assign_business_unit_scope(staff, signal.responsible_business_unit)

    with pytest.raises(SignalValidationError, match="manager"):
        create_signal_resolution_request(signal=signal, actor_membership=staff)


def test_manager_creates_manager_to_director_and_cannot_self_resolve():
    _owner, signal, manager, _director, _staff = _setup_open_signal_with_responsible_pole()

    assert can_resolve_signal(manager, signal) is True
    request = create_signal_resolution_request(signal=signal, actor_membership=manager)
    signal.refresh_from_db()

    assert request.review_route == SignalResolutionRequest.ReviewRoute.MANAGER_TO_DIRECTOR
    assert signal.status == Signal.Status.OPEN
    assert can_resolve_signal(manager, signal) is False
    assert can_create_resolution_request(manager, signal) is False

    with pytest.raises(SignalStateError):
        resolve_signal(signal=signal, actor_membership=manager)


def test_manager_create_fails_without_director():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, title="No director")
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    assign_business_unit_scope(manager, signal.responsible_business_unit)

    with pytest.raises(SignalValidationError, match="director"):
        create_signal_resolution_request(signal=signal, actor_membership=manager)


def test_manager_approve_staff_request_resolves_signal():
    _owner, signal, manager, _director, staff = _setup_open_signal_with_responsible_pole()
    request = create_signal_resolution_request(signal=signal, actor_membership=staff)

    approved = approve_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
        review_comment="OK",
    )

    signal.refresh_from_db()
    assert approved.status == SignalResolutionRequest.Status.APPROVED
    assert approved.review_comment == "OK"
    assert signal.status == Signal.Status.RESOLVED


def test_manager_reject_staff_request_keeps_signal_open():
    _owner, signal, manager, _director, staff = _setup_open_signal_with_responsible_pole()
    request = create_signal_resolution_request(signal=signal, actor_membership=staff)

    rejected = reject_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )

    signal.refresh_from_db()
    assert rejected.status == SignalResolutionRequest.Status.REJECTED
    assert signal.status == Signal.Status.OPEN


def test_director_approve_manager_request():
    _owner, signal, manager, director, _staff = _setup_open_signal_with_responsible_pole()
    request = create_signal_resolution_request(signal=signal, actor_membership=manager)

    approve_signal_resolution_request(
        resolution_request=request,
        actor_membership=director,
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_requester_can_cancel_own_pending_request():
    _owner, signal, manager, _director, _staff = _setup_open_signal_with_responsible_pole()
    request = create_signal_resolution_request(signal=signal, actor_membership=manager)

    canceled = cancel_signal_resolution_request_by_requester(
        resolution_request=request,
        actor_membership=manager,
        cancel_comment="Finalement non",
    )

    signal.refresh_from_db()
    assert canceled.status == SignalResolutionRequest.Status.CANCELED
    assert (
        canceled.canceled_reason
        == SignalResolutionRequest.CanceledReason.CANCELED_BY_REQUESTER
    )
    assert canceled.cancel_comment == "Finalement non"
    assert signal.status == Signal.Status.OPEN
    assert can_resolve_signal(manager, signal) is True


def test_external_resolve_cancels_pending_as_resolved_elsewhere():
    owner, signal, manager, _director, _staff = _setup_open_signal_with_responsible_pole()
    request = create_signal_resolution_request(signal=signal, actor_membership=manager)

    resolve_signal(signal=signal, actor_membership=owner)

    request.refresh_from_db()
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
    assert request.status == SignalResolutionRequest.Status.CANCELED
    assert (
        request.canceled_reason
        == SignalResolutionRequest.CanceledReason.SIGNAL_RESOLVED_ELSEWHERE
    )


def test_ineligible_manager_cannot_review_after_scope_loss():
    _owner, signal, manager, _director, staff = _setup_open_signal_with_responsible_pole()
    request = create_signal_resolution_request(signal=signal, actor_membership=staff)

    manager.scope_links.all().delete()

    from houston.signals.exceptions import SignalPermissionError

    with pytest.raises(SignalPermissionError):
        approve_signal_resolution_request(
            resolution_request=request,
            actor_membership=manager,
        )

    request.refresh_from_db()
    assert request.status == SignalResolutionRequest.Status.PENDING
