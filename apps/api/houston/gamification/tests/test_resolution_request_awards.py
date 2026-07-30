from __future__ import annotations

from unittest.mock import patch

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.gamification.constants import (
    DELTA_RESOLUTION_REQUEST_APPROVED,
    DELTA_SIGNAL_RESOLVED,
    REASON_RESOLUTION_REQUEST_APPROVED,
    REASON_SIGNAL_RESOLVED,
    SOURCE_TYPE_SIGNAL,
    SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST,
)
from houston.gamification.exceptions import GamificationValidationError
from houston.gamification.models import PointTransaction
from houston.gamification.services import award_resolution_request_approved_points
from houston.signals.constants import SIGNAL_LIFECYCLE_EVENT_RESOLVED
from houston.signals.exceptions import SignalStateError
from houston.signals.models import (
    Signal,
    SignalLifecycleEvent,
    SignalResolutionRequest,
    SignalSourceObservation,
)
from houston.signals.resolution_request_services import (
    approve_signal_resolution_request,
    cancel_signal_resolution_request_by_requester,
    create_signal_resolution_request,
    reject_signal_resolution_request,
)
from houston.signals.services import resolve_signal
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.testing.factories import create_establishment, create_membership
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import create_minimal_v3_signal

pytestmark = pytest.mark.django_db


def _link_observation(
    *,
    signal: Signal,
    membership: EstablishmentMembership,
    link_type: str,
    text: str = "A" * 20,
) -> SignalSourceObservation:
    observation = create_observation(membership=membership, text=text)
    return SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=link_type,
    )


def _setup_staff_manager_request(*, link_staff_as_observer: bool = False):
    owner = create_membership(
        establishment=create_establishment(name="GAM-03 Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(owner, title="GAM-03 target")
    responsible = signal.responsible_business_unit
    assert responsible is not None

    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    assign_business_unit_scope(staff, responsible)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    assign_business_unit_scope(manager, responsible)

    if link_staff_as_observer:
        _link_observation(
            signal=signal,
            membership=staff,
            link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        )

    request = create_signal_resolution_request(
        signal=signal,
        actor_membership=staff,
    )
    return owner, signal, staff, manager, request


def _gam03_txs(*, membership=None, resolution_request=None):
    qs = PointTransaction.objects.filter(
        reason_code=REASON_RESOLUTION_REQUEST_APPROVED,
        source_type=SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST,
    )
    if membership is not None:
        qs = qs.filter(membership=membership)
    if resolution_request is not None:
        qs = qs.filter(source_id=str(resolution_request.id))
    return list(qs.order_by("created_at", "id"))


def test_approve_awards_requester_not_reviewer():
    _owner, signal, staff, manager, request = _setup_staff_manager_request()

    approve_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED

    requester_txs = _gam03_txs(membership=staff, resolution_request=request)
    assert len(requester_txs) == 1
    assert requester_txs[0].delta == DELTA_RESOLUTION_REQUEST_APPROVED
    assert requester_txs[0].source_id == str(request.id)
    assert requester_txs[0].source_event_id == str(request.id)
    request.refresh_from_db()
    assert requester_txs[0].occurred_at == request.reviewed_at

    assert _gam03_txs(membership=manager) == []


def test_requester_observer_gets_gam03_and_gam02():
    _owner, signal, staff, manager, request = _setup_staff_manager_request(
        link_staff_as_observer=True,
    )

    approve_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )

    gam03 = _gam03_txs(membership=staff, resolution_request=request)
    assert len(gam03) == 1
    assert gam03[0].delta == DELTA_RESOLUTION_REQUEST_APPROVED

    gam02 = list(
        PointTransaction.objects.filter(
            membership=staff,
            reason_code=REASON_SIGNAL_RESOLVED,
            source_type=SOURCE_TYPE_SIGNAL,
            source_id=str(signal.id),
        )
    )
    assert len(gam02) == 1
    assert gam02[0].delta == DELTA_SIGNAL_RESOLVED


def test_manual_resolve_awards_no_gam03():
    owner, signal, _staff, _manager, request = _setup_staff_manager_request()

    resolve_signal(signal=signal, actor_membership=owner)

    request.refresh_from_db()
    assert request.status == SignalResolutionRequest.Status.CANCELED
    assert _gam03_txs() == []


def test_create_reject_cancel_award_no_gam03():
    _owner, signal, staff, manager, request = _setup_staff_manager_request()
    assert _gam03_txs() == []

    reject_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )
    assert _gam03_txs() == []

    request2 = create_signal_resolution_request(
        signal=signal,
        actor_membership=staff,
    )
    cancel_signal_resolution_request_by_requester(
        resolution_request=request2,
        actor_membership=staff,
    )
    assert _gam03_txs() == []


def test_deactivated_requester_still_receives_gam03():
    _owner, _signal, staff, manager, request = _setup_staff_manager_request()
    staff.status = EstablishmentMembership.Status.DEACTIVATED
    staff.save(update_fields=["status", "updated_at"])

    approve_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )

    txs = _gam03_txs(membership=staff, resolution_request=request)
    assert len(txs) == 1
    assert txs[0].delta == DELTA_RESOLUTION_REQUEST_APPROVED


def test_approve_retry_keeps_single_gam03_tx():
    _owner, _signal, staff, manager, request = _setup_staff_manager_request()

    approve_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )
    assert len(_gam03_txs(membership=staff, resolution_request=request)) == 1

    with pytest.raises(SignalStateError):
        approve_signal_resolution_request(
            resolution_request=request,
            actor_membership=manager,
        )

    assert len(_gam03_txs(membership=staff, resolution_request=request)) == 1


def test_blocking_execution_blocks_approve_no_gam03():
    _owner, _signal, staff, manager, request = _setup_staff_manager_request()

    with patch(
        "houston.signals.resolution_request_services._signal_has_blocking_linked_executions",
        return_value=True,
    ):
        with pytest.raises(SignalStateError):
            approve_signal_resolution_request(
                resolution_request=request,
                actor_membership=manager,
            )

    request.refresh_from_db()
    assert request.status == SignalResolutionRequest.Status.PENDING
    assert _gam03_txs() == []


def test_award_points_failure_rolls_back_approve_atomically():
    _owner, signal, staff, manager, request = _setup_staff_manager_request(
        link_staff_as_observer=True,
    )

    with (
        patch(
            "houston.gamification.services.award_points",
            side_effect=GamificationValidationError(
                "forced award failure",
                code="gamification_forced_failure",
            ),
        ),
        patch(
            "houston.notifications.scheduling.schedule_signal_resolution_request_reviewed_notification",
        ) as schedule_reviewed,
        patch(
            "houston.notifications.scheduling.schedule_signal_resolved_notification",
        ) as schedule_resolved,
        pytest.raises(GamificationValidationError),
    ):
        approve_signal_resolution_request(
            resolution_request=request,
            actor_membership=manager,
        )

    request.refresh_from_db()
    signal.refresh_from_db()
    assert request.status == SignalResolutionRequest.Status.PENDING
    assert request.reviewed_at is None
    assert signal.status == Signal.Status.OPEN
    assert not SignalLifecycleEvent.objects.filter(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    ).exists()
    assert PointTransaction.objects.count() == 0
    schedule_reviewed.assert_not_called()
    schedule_resolved.assert_not_called()


def test_helper_idempotent_on_approved_request():
    _owner, _signal, staff, manager, request = _setup_staff_manager_request()
    approve_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )
    request.refresh_from_db()
    assert request.status == SignalResolutionRequest.Status.APPROVED

    award_resolution_request_approved_points(resolution_request=request)
    award_resolution_request_approved_points(resolution_request=request)

    txs = _gam03_txs(membership=staff, resolution_request=request)
    assert len(txs) == 1


def test_helper_rejects_non_approved_request():
    _owner, _signal, _staff, _manager, request = _setup_staff_manager_request()
    assert request.status == SignalResolutionRequest.Status.PENDING

    with pytest.raises(GamificationValidationError) as exc_info:
        award_resolution_request_approved_points(resolution_request=request)
    assert exc_info.value.code == "gamification_resolution_request_not_approved"
    assert _gam03_txs() == []


def test_helper_rejects_approved_without_reviewed_at():
    _owner, _signal, staff, _manager, request = _setup_staff_manager_request()
    request.status = SignalResolutionRequest.Status.APPROVED
    request.reviewed_at = None
    request.reviewed_by_membership = staff
    request.save(
        update_fields=[
            "status",
            "reviewed_at",
            "reviewed_by_membership",
            "updated_at",
        ],
    )

    with pytest.raises(GamificationValidationError) as exc_info:
        award_resolution_request_approved_points(resolution_request=request)
    assert exc_info.value.code == "gamification_resolution_request_reviewed_at_missing"
    assert _gam03_txs() == []
