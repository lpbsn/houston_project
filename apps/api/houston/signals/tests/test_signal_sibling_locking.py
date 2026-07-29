from __future__ import annotations

import pytest
from django.db import close_old_connections

from houston.action_plans.constants import SIGNAL_BLOCKING_EXECUTION_STATUSES
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import (
    create_action_plan_with_execution,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.services import cancel_signal, resolve_signal_from_execution_sync
from houston.signals.tests.conftest import build_api_membership, create_minimal_v3_signal
from houston.testing.pipeline import create_observation

pytestmark = pytest.mark.django_db


def _create_linked_execution(
    *,
    owner_membership,
    signal: Signal,
    title: str,
    requires_validation: bool = False,
) -> ActionPlanExecution:
    responsible_business_unit = signal.responsible_business_unit
    assert responsible_business_unit is not None

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=responsible_business_unit.id,
        title=title,
        source_signal_id=signal.id,
        requires_validation=requires_validation,
        tasks=[
            build_task_payload(task=f"Task for {title}", business_unit=responsible_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=responsible_business_unit,
            )
        ],
        use_shared_chronology=True,
    )
    return execution


@pytest.mark.django_db(transaction=True)
def test_concurrent_auto_resolve_and_manual_cancel_created_from_siblings_preserves_invariants(
    api_client,
):
    """Course auto-resolve(sibling_a) ↔ cancel(sibling_b open) sur siblings CREATED_FROM."""
    _ = api_client

    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)

    sibling_a = create_minimal_v3_signal(
        membership,
        title="Sibling A",
        status=Signal.Status.IN_PROGRESS,
    )
    sibling_b = create_minimal_v3_signal(
        membership,
        title="Sibling B",
        status=Signal.Status.OPEN,
    )

    shared_observation = create_observation(
        membership=membership,
        text="shared created_from for siblings",
    )
    SignalSourceObservation.objects.create(
        signal=sibling_a,
        observation=shared_observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    SignalSourceObservation.objects.create(
        signal=sibling_b,
        observation=shared_observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    blocking_execution_a = _create_linked_execution(
        owner_membership=membership,
        signal=sibling_a,
        title="blocking execution for A",
        requires_validation=False,
    )

    from concurrent.futures import ThreadPoolExecutor

    sibling_a_id = sibling_a.id
    sibling_b_id = sibling_b.id

    def run_auto_resolve_a() -> None:
        close_old_connections()
        resolve_signal_from_execution_sync(signal=Signal.objects.get(id=sibling_a_id))

    def run_cancel_b() -> None:
        close_old_connections()
        cancel_signal(
            signal=Signal.objects.get(id=sibling_b_id),
            actor_membership=membership,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_auto_resolve_a), executor.submit(run_cancel_b)]
        for future in futures:
            future.result(timeout=30)

    sibling_a.refresh_from_db()
    sibling_b.refresh_from_db()
    blocking_execution_a.refresh_from_db()

    if sibling_a.status == Signal.Status.RESOLVED:
        assert not ActionPlanExecution.objects.filter(
            source_signal_id=sibling_a.id,
            status__in=SIGNAL_BLOCKING_EXECUTION_STATUSES,
        ).exists()

    if sibling_b.status == Signal.Status.RESOLVED:
        assert not ActionPlanExecution.objects.filter(
            source_signal_id=sibling_b.id,
            status__in=SIGNAL_BLOCKING_EXECUTION_STATUSES,
        ).exists()

    assert blocking_execution_a.status == ActionPlanExecution.Status.CANCELED
    assert sibling_b.status == Signal.Status.CANCELED
