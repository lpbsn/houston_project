from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import (
    create_action_plan_with_execution,
    mark_action_plan_execution_done,
    reopen_action_plan_execution,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.gamification.constants import (
    DELTA_SIGNAL_MOVED_IN_PROGRESS,
    DELTA_SIGNAL_RESOLVED,
    REASON_SIGNAL_MOVED_IN_PROGRESS,
    REASON_SIGNAL_RESOLVED,
    SOURCE_TYPE_SIGNAL,
)
from houston.gamification.models import PointTransaction
from houston.gamification.services import award_signal_progress_points
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
    SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
)
from houston.signals.lifecycle_events import record_signal_lifecycle_event
from houston.signals.models import Signal, SignalLifecycleEvent, SignalSourceObservation
from houston.signals.resolution_request_services import (
    approve_signal_resolution_request,
    create_signal_resolution_request,
)
from houston.signals.services import cancel_signal, mark_signal_interesting, resolve_signal
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


def _create_linked_execution(*, owner_membership, signal, title: str = "Linked plan"):
    responsible = signal.responsible_business_unit
    assert responsible is not None
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=responsible.id,
        title=title,
        source_signal_id=signal.id,
        requires_validation=False,
        tasks=[build_task_payload(task=f"Task for {title}", business_unit=responsible)],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=responsible,
            )
        ],
        use_shared_chronology=True,
    )
    return execution


def _txs(*, membership=None, signal=None, reason_code=None):
    qs = PointTransaction.objects.all()
    if membership is not None:
        qs = qs.filter(membership=membership)
    if signal is not None:
        qs = qs.filter(source_type=SOURCE_TYPE_SIGNAL, source_id=str(signal.id))
    if reason_code is not None:
        qs = qs.filter(reason_code=reason_code)
    return list(qs.order_by("created_at", "id"))


def test_mark_interesting_creates_lifecycle_without_points():
    membership = create_membership(
        establishment=create_establishment(name="Dedup Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(membership, title="Dedup interesting")
    for i in range(3):
        _link_observation(
            signal=signal,
            membership=membership,
            link_type=SignalSourceObservation.LinkType.CREATED_FROM
            if i == 0
            else SignalSourceObservation.LinkType.AGGREGATED_FROM,
            text=f"{'A' * 19}{i}",
        )

    mark_signal_interesting(signal=signal, actor_membership=membership)

    txs = _txs(membership=membership, signal=signal)
    assert txs == []
    SignalLifecycleEvent.objects.get(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
    )


def test_non_retroactivity_observer_linked_after_in_progress():
    establishment = create_establishment(name="NonRetro Hotel", timezone="UTC")
    alice = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    bob = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    signal = create_minimal_v3_signal(alice, title="Non retro")
    _link_observation(
        signal=signal,
        membership=alice,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    _create_linked_execution(owner_membership=alice, signal=signal, title="Activate")
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS
    assert len(_txs(membership=alice, reason_code=REASON_SIGNAL_MOVED_IN_PROGRESS)) == 1
    assert len(_txs(membership=bob, reason_code=REASON_SIGNAL_MOVED_IN_PROGRESS)) == 0

    _link_observation(
        signal=signal,
        membership=bob,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
        text="B" * 20,
    )

    execution = ActionPlanExecution.objects.get(source_signal=signal)
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=alice,
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED

    assert len(_txs(membership=alice, reason_code=REASON_SIGNAL_RESOLVED)) == 1
    assert len(_txs(membership=bob, reason_code=REASON_SIGNAL_RESOLVED)) == 1
    assert len(_txs(membership=bob, reason_code=REASON_SIGNAL_MOVED_IN_PROGRESS)) == 0
    assert _txs(membership=alice, reason_code=REASON_SIGNAL_RESOLVED)[0].delta == (
        DELTA_SIGNAL_RESOLVED
    )


def test_cumulative_interesting_in_progress_resolved():
    membership = create_membership(
        establishment=create_establishment(name="Cumul Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(membership, title="Cumul path")
    _link_observation(
        signal=signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    mark_signal_interesting(signal=signal, actor_membership=membership)
    _create_linked_execution(owner_membership=membership, signal=signal)
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS

    execution = signal.action_plan_executions.get()
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=membership,
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED

    txs = _txs(membership=membership, signal=signal)
    assert [t.reason_code for t in txs] == [
        REASON_SIGNAL_MOVED_IN_PROGRESS,
        REASON_SIGNAL_RESOLVED,
    ]
    assert [t.delta for t in txs] == [
        DELTA_SIGNAL_MOVED_IN_PROGRESS,
        DELTA_SIGNAL_RESOLVED,
    ]
    assert sum(t.delta for t in txs) == 3


def test_merged_from_excluded():
    establishment = create_establishment(name="Merged Hotel", timezone="UTC")
    creator = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    merged_author = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    signal = create_minimal_v3_signal(creator, title="Merged exclude")
    _link_observation(
        signal=signal,
        membership=creator,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    _link_observation(
        signal=signal,
        membership=merged_author,
        link_type=SignalSourceObservation.LinkType.MERGED_FROM,
        text="M" * 20,
    )

    mark_signal_interesting(signal=signal, actor_membership=creator)

    assert len(_txs(membership=creator, signal=signal)) == 0
    assert len(_txs(membership=merged_author, signal=signal)) == 0


def test_first_lifecycle_guard_skips_duplicate_in_progress_event():
    membership = create_membership(
        establishment=create_establishment(name="Guard Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(membership, title="First guard")
    _link_observation(
        signal=signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    _create_linked_execution(owner_membership=membership, signal=signal)
    assert len(_txs(membership=membership, signal=signal)) == 1

    second = record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
        occurred_at=timezone.now() + timedelta(seconds=1),
        actor_membership=membership,
        metadata_safe={
            "from_status": Signal.Status.INTERESTING,
            "to_status": Signal.Status.IN_PROGRESS,
        },
    )
    award_signal_progress_points(signal=signal, lifecycle_event=second)

    assert len(_txs(membership=membership, signal=signal)) == 1


def test_mark_interesting_does_not_call_award_points():
    membership = create_membership(
        establishment=create_establishment(name="Rollback Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(membership, title="Rollback award")
    _link_observation(
        signal=signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    with patch(
        "houston.gamification.services.award_points",
        side_effect=RuntimeError("forced award failure"),
    ):
        mark_signal_interesting(signal=signal, actor_membership=membership)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.INTERESTING
    assert SignalLifecycleEvent.objects.filter(signal=signal).count() == 1
    assert PointTransaction.objects.count() == 0


def test_cancel_creates_no_points_and_keeps_prior():
    membership = create_membership(
        establishment=create_establishment(name="Cancel Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    prior_signal = create_minimal_v3_signal(membership, title="Prior interesting")
    _link_observation(
        signal=prior_signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    mark_signal_interesting(signal=prior_signal, actor_membership=membership)
    prior_count = PointTransaction.objects.filter(membership=membership).count()
    assert prior_count == 0

    cancelable = create_minimal_v3_signal(membership, title="To cancel")
    _link_observation(
        signal=cancelable,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        text="D" * 20,
    )
    cancel_signal(signal=cancelable, actor_membership=membership)
    cancelable.refresh_from_db()
    assert cancelable.status == Signal.Status.CANCELED
    assert PointTransaction.objects.filter(membership=membership).count() == prior_count
    assert len(_txs(signal=cancelable)) == 0


def test_resolve_via_manual_awards_points():
    membership = create_membership(
        establishment=create_establishment(name="Manual Resolve Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(membership, title="Manual resolve")
    _link_observation(
        signal=signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    resolve_signal(signal=signal, actor_membership=membership)
    txs = _txs(membership=membership, signal=signal)
    assert len(txs) == 1
    assert txs[0].reason_code == REASON_SIGNAL_RESOLVED
    assert txs[0].delta == DELTA_SIGNAL_RESOLVED


def test_resolve_via_resolution_request_approve_awards_points():
    owner = create_membership(
        establishment=create_establishment(name="RR Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(owner, title="RR resolve")
    _link_observation(
        signal=signal,
        membership=owner,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
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

    request = create_signal_resolution_request(
        signal=signal,
        actor_membership=staff,
    )
    approve_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
    txs = _txs(membership=owner, signal=signal)
    assert len(txs) == 1
    assert txs[0].reason_code == REASON_SIGNAL_RESOLVED


def test_in_progress_from_open_and_interesting():
    membership = create_membership(
        establishment=create_establishment(name="IP Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    open_signal = create_minimal_v3_signal(membership, title="Open to IP")
    _link_observation(
        signal=open_signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    _create_linked_execution(
        owner_membership=membership,
        signal=open_signal,
        title="From open",
    )
    open_signal.refresh_from_db()
    assert open_signal.status == Signal.Status.IN_PROGRESS
    assert len(_txs(signal=open_signal, reason_code=REASON_SIGNAL_MOVED_IN_PROGRESS)) == 1

    interesting_signal = create_minimal_v3_signal(membership, title="Interesting to IP")
    _link_observation(
        signal=interesting_signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        text="I" * 20,
    )
    mark_signal_interesting(signal=interesting_signal, actor_membership=membership)
    _create_linked_execution(
        owner_membership=membership,
        signal=interesting_signal,
        title="From interesting",
    )
    interesting_signal.refresh_from_db()
    assert interesting_signal.status == Signal.Status.IN_PROGRESS
    assert (
        len(_txs(signal=interesting_signal, reason_code=REASON_SIGNAL_MOVED_IN_PROGRESS))
        == 1
    )


def test_pending_validation_reopen_creates_no_signal_points():
    membership = create_membership(
        establishment=create_establishment(name="Reopen Stable Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(membership, title="PV reopen")
    _link_observation(
        signal=signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    responsible = signal.responsible_business_unit
    assert responsible is not None
    _, execution = create_action_plan_with_execution(
        establishment_id=membership.establishment_id,
        created_by=membership,
        pilot_business_unit_id=responsible.id,
        title="Needs validation",
        source_signal_id=signal.id,
        requires_validation=True,
        tasks=[build_task_payload(task="Task", business_unit=responsible)],
        assignees=[
            build_assignee_payload(membership=membership, business_unit=responsible)
        ],
        use_shared_chronology=True,
    )
    signal.refresh_from_db()
    assert len(_txs(signal=signal, reason_code=REASON_SIGNAL_MOVED_IN_PROGRESS)) == 1
    before = PointTransaction.objects.filter(
        source_type=SOURCE_TYPE_SIGNAL,
        source_id=str(signal.id),
    ).count()

    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=membership,
    )
    reopen_action_plan_execution(execution_id=pending.id, actor=membership)
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS
    assert (
        PointTransaction.objects.filter(
            source_type=SOURCE_TYPE_SIGNAL,
            source_id=str(signal.id),
        ).count()
        == before
    )


def test_deactivated_membership_still_receives_points():
    establishment = create_establishment(name="Inactive Hotel", timezone="UTC")
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(membership, title="Inactive author")
    _link_observation(
        signal=signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    membership.status = EstablishmentMembership.Status.DEACTIVATED
    membership.save(update_fields=["status", "updated_at"])

    # Actor must be active for mark_interesting permission at API, but service
    # itself does not check actor status — use None actor.
    mark_signal_interesting(signal=signal, actor_membership=None)

    txs = _txs(membership=membership, signal=signal)
    assert txs == []


def test_cross_establishment_membership_not_awarded():
    home = create_establishment(name="Home Hotel", timezone="UTC")
    other = create_establishment(name="Other Hotel", timezone="UTC")
    home_member = create_membership(
        establishment=home,
        role=EstablishmentMembership.Role.OWNER,
    )
    other_member = create_membership(
        establishment=other,
        role=EstablishmentMembership.Role.STAFF,
    )
    signal = create_minimal_v3_signal(home_member, title="Cross estab")
    _link_observation(
        signal=signal,
        membership=home_member,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    # Force an atypical cross-establishment link; query must exclude it.
    foreign_obs = create_observation(membership=other_member, text="X" * 20)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=foreign_obs,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )

    mark_signal_interesting(signal=signal, actor_membership=home_member)

    assert len(_txs(membership=home_member, signal=signal)) == 0
    assert len(_txs(membership=other_member, signal=signal)) == 0


def test_second_linked_plan_does_not_reaward_in_progress():
    membership = create_membership(
        establishment=create_establishment(name="Noop Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(membership, title="Already in progress")
    _link_observation(
        signal=signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    _create_linked_execution(
        owner_membership=membership,
        signal=signal,
        title="First plan",
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS
    assert len(_txs(signal=signal, reason_code=REASON_SIGNAL_MOVED_IN_PROGRESS)) == 1

    _create_linked_execution(
        owner_membership=membership,
        signal=signal,
        title="Second plan",
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS
    assert len(_txs(signal=signal, reason_code=REASON_SIGNAL_MOVED_IN_PROGRESS)) == 1
    assert (
        SignalLifecycleEvent.objects.filter(
            signal=signal,
            event_type=SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
        ).count()
        == 1
    )


def test_second_resolved_lifecycle_via_helper_is_noop():
    membership = create_membership(
        establishment=create_establishment(name="Dup Resolve Hotel", timezone="UTC"),
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_minimal_v3_signal(membership, title="Dup resolved event")
    _link_observation(
        signal=signal,
        membership=membership,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    resolve_signal(signal=signal, actor_membership=membership)
    assert len(_txs(signal=signal)) == 1

    second = record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=timezone.now() + timedelta(seconds=1),
        actor_membership=membership,
        metadata_safe={
            "from_status": Signal.Status.OPEN,
            "to_status": Signal.Status.RESOLVED,
        },
    )
    award_signal_progress_points(signal=signal, lifecycle_event=second)
    assert len(_txs(signal=signal)) == 1
