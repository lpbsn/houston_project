from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections

from houston.establishments.models import EstablishmentMembership
from houston.signals.exceptions import SignalStateError, SignalValidationError
from houston.signals.models import Signal, SignalResolutionRequest
from houston.signals.resolution_request_services import create_signal_resolution_request
from houston.signals.services import resolve_signal
from houston.signals.tests.conftest import build_api_membership, create_minimal_v3_signal
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(transaction=True)
def test_concurrent_manager_create_resolution_request_vs_self_resolve():
    """Course create Manager→Director ↔ resolve du même Manager : XOR + pas de pending+resolved."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, title="Concurrency engagement")
    responsible = signal.responsible_business_unit
    assert responsible is not None

    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    assign_business_unit_scope(manager, responsible)
    build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )

    signal_id = signal.id
    manager_id = manager.id

    def try_create() -> str:
        close_old_connections()
        try:
            create_signal_resolution_request(
                signal=Signal.objects.get(id=signal_id),
                actor_membership=EstablishmentMembership.objects.get(id=manager_id),
            )
            return "create_ok"
        except (SignalStateError, SignalValidationError):
            return "create_fail"

    def try_resolve() -> str:
        close_old_connections()
        try:
            resolve_signal(
                signal=Signal.objects.get(id=signal_id),
                actor_membership=EstablishmentMembership.objects.get(id=manager_id),
            )
            return "resolve_ok"
        except SignalStateError:
            return "resolve_fail"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda fn: fn(), [try_create, try_resolve]))

    signal.refresh_from_db()
    pending = SignalResolutionRequest.objects.filter(
        signal_id=signal_id,
        status=SignalResolutionRequest.Status.PENDING,
    ).first()

    assert not (results.count("create_ok") == 1 and results.count("resolve_ok") == 1)
    assert results.count("create_ok") + results.count("resolve_ok") >= 1
    assert not (
        pending is not None and signal.status == Signal.Status.RESOLVED
    )

    if "create_ok" in results:
        assert pending is not None
        assert pending.requested_by_membership_id == manager_id
        assert (
            pending.review_route
            == SignalResolutionRequest.ReviewRoute.MANAGER_TO_DIRECTOR
        )
        assert signal.status == Signal.Status.OPEN
        with pytest.raises(SignalStateError):
            resolve_signal(signal=signal, actor_membership=manager)

    if "resolve_ok" in results:
        assert signal.status == Signal.Status.RESOLVED
        assert pending is None
