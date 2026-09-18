from __future__ import annotations

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
)
from houston.action_plans.lifecycle_events import record_execution_lifecycle_event
from houston.action_plans.models import ActionPlan, ActionPlanExecution
from houston.action_plans.repair_marked_done_snapshots import (
    MODEL_ACTION_PLAN,
    MODEL_EXECUTION,
    MODEL_LIFECYCLE_EVENT,
    MODEL_OBSERVATION,
    MODEL_SIGNAL,
    repair_marked_done_snapshots,
)
from houston.action_plans.tests.helpers import create_open_signal
from houston.core.dev_guards import LocalDevEnvironmentError
from houston.establishments.models import EstablishmentMembership
from houston.observations.models import Observation
from houston.signals.models import Signal, SignalSourceObservation
from houston.testing.auth import build_api_membership
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def enable_local_dev_debug(settings):
    settings.DEBUG = True


def _plan(*, membership, business_unit, title="Plan"):
    return ActionPlan.objects.create(
        establishment=membership.establishment,
        created_by=membership,
        title=title,
        pilot_business_unit=business_unit,
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
    )


def _execution(
    *,
    plan,
    membership,
    business_unit,
    title="Execution",
    start_at=None,
    end_at=None,
    source_signal=None,
    status=EXECUTION_STATUS_DONE,
):
    now = timezone.now()
    return ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        title=title,
        status=status,
        start_at=start_at,
        end_at=end_at,
        marked_done_at=now,
        last_activity_at=now,
        use_shared_chronology=True,
        requires_validation=False,
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
        pilot_business_unit=business_unit,
        source_signal=source_signal,
    )


def _marked_done(*, execution, start_at=None, end_at=None, extra=None):
    metadata = {"to_status": EXECUTION_STATUS_DONE, **(extra or {})}
    if start_at is not None:
        metadata["start_at"] = start_at
    if end_at is not None:
        metadata["end_at"] = end_at
    return record_execution_lifecycle_event(
        execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
        occurred_at=execution.marked_done_at or timezone.now(),
        metadata_safe=metadata,
    )


def test_preserves_valid_snapshot_when_live_window_differs():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    bu = create_business_unit(establishment=membership.establishment, key="salle")
    now = timezone.now()
    plan = _plan(membership=membership, business_unit=bu)
    snapshot_start = now - timedelta(hours=10)
    snapshot_end = now - timedelta(hours=2)
    execution = _execution(
        plan=plan,
        membership=membership,
        business_unit=bu,
        start_at=now - timedelta(hours=20),
        end_at=now + timedelta(hours=5),
    )
    event = _marked_done(execution=execution, start_at=snapshot_start, end_at=snapshot_end)

    report = repair_marked_done_snapshots(dry_run=False)

    event.refresh_from_db()
    assert event.id in report.preserved_event_ids
    assert event.metadata_safe["start_at"] == snapshot_start.isoformat()
    assert event.metadata_safe["end_at"] == snapshot_end.isoformat()
    assert ActionPlanExecution.objects.filter(id=execution.id).exists()


def test_fills_only_start_and_end_from_live_execution():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    bu = create_business_unit(establishment=membership.establishment, key="cuisine")
    now = timezone.now()
    plan = _plan(membership=membership, business_unit=bu)
    start_at = now - timedelta(hours=8)
    end_at = now - timedelta(hours=1)
    execution = _execution(
        plan=plan,
        membership=membership,
        business_unit=bu,
        start_at=start_at,
        end_at=end_at,
    )
    event = _marked_done(
        execution=execution,
        end_at=end_at,
        extra={"to_status": EXECUTION_STATUS_DONE, "cancel_origin": "manual"},
    )

    report = repair_marked_done_snapshots(dry_run=False)

    event.refresh_from_db()
    assert len(report.filled) == 1
    assert event.metadata_safe["start_at"] == start_at.isoformat()
    assert event.metadata_safe["end_at"] == end_at.isoformat()
    assert event.metadata_safe["to_status"] == EXECUTION_STATUS_DONE
    assert event.metadata_safe["cancel_origin"] == "manual"


def test_unrecoverable_with_signal_deletes_full_connected_graph():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    bu = create_business_unit(establishment=membership.establishment, key="bar")
    signal = create_open_signal(owner_membership=membership, title="Broken fridge")
    observation = create_observation(membership=membership)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    bad_plan = _plan(membership=membership, business_unit=bu, title="Bad")
    other_plan = _plan(membership=membership, business_unit=bu, title="Other")
    now = timezone.now()
    bad = _execution(
        plan=bad_plan,
        membership=membership,
        business_unit=bu,
        title="Bad exec",
        start_at=now,
        end_at=now - timedelta(hours=1),
        source_signal=signal,
    )
    other = _execution(
        plan=other_plan,
        membership=membership,
        business_unit=bu,
        title="Other exec",
        start_at=now - timedelta(hours=3),
        end_at=now - timedelta(hours=1),
        source_signal=signal,
        status=EXECUTION_STATUS_IN_PROGRESS,
    )
    _marked_done(execution=bad, end_at=now)

    report = repair_marked_done_snapshots(dry_run=False)

    deleted = {(model, object_id) for model, object_id in report.deleted_objects}
    assert (MODEL_SIGNAL, signal.id) in deleted
    assert (MODEL_ACTION_PLAN, bad_plan.id) in deleted
    assert (MODEL_ACTION_PLAN, other_plan.id) in deleted
    assert (MODEL_EXECUTION, bad.id) in deleted
    assert (MODEL_EXECUTION, other.id) in deleted
    assert (MODEL_OBSERVATION, observation.id) in deleted
    assert not Signal.objects.filter(id=signal.id).exists()
    assert not ActionPlan.objects.filter(id__in=[bad_plan.id, other_plan.id]).exists()
    assert not Observation.objects.filter(id=observation.id).exists()


def test_unrecoverable_without_signal_deletes_full_action_plan_graph():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    bu = create_business_unit(establishment=membership.establishment, key="hall")
    plan = _plan(membership=membership, business_unit=bu)
    now = timezone.now()
    bad = _execution(
        plan=plan,
        membership=membership,
        business_unit=bu,
        title="Bad",
        start_at=None,
        end_at=now,
    )
    sibling = _execution(
        plan=plan,
        membership=membership,
        business_unit=bu,
        title="Sibling",
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
        status=EXECUTION_STATUS_IN_PROGRESS,
    )
    _marked_done(execution=bad, extra={"to_status": EXECUTION_STATUS_DONE})

    report = repair_marked_done_snapshots(dry_run=False)

    deleted_ids = {
        object_id
        for model, object_id in report.deleted_objects
        if model == MODEL_EXECUTION
    }
    assert bad.id in deleted_ids
    assert sibling.id in deleted_ids
    assert not ActionPlan.objects.filter(id=plan.id).exists()


def test_dry_run_lists_objects_and_writes_nothing():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    bu = create_business_unit(establishment=membership.establishment, key="spa")
    plan = _plan(membership=membership, business_unit=bu)
    now = timezone.now()
    execution = _execution(
        plan=plan,
        membership=membership,
        business_unit=bu,
        start_at=None,
        end_at=now,
    )
    event = _marked_done(execution=execution, extra={"to_status": EXECUTION_STATUS_DONE})

    report = repair_marked_done_snapshots(dry_run=True)

    assert report.dry_run is True
    assert report.deleted_objects
    assert ActionPlanExecution.objects.filter(id=execution.id).exists()
    event.refresh_from_db()
    assert "start_at" not in event.metadata_safe
    listed = {(model, object_id) for model, object_id in report.deleted_objects}
    assert (MODEL_EXECUTION, execution.id) in listed
    assert (MODEL_ACTION_PLAN, plan.id) in listed
    assert (MODEL_LIFECYCLE_EVENT, event.id) in listed


def test_confirm_then_rerun_is_idempotent():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    bu = create_business_unit(establishment=membership.establishment, key="pool")
    now = timezone.now()
    plan = _plan(membership=membership, business_unit=bu)
    start_at = now - timedelta(hours=4)
    end_at = now - timedelta(hours=1)
    execution = _execution(
        plan=plan,
        membership=membership,
        business_unit=bu,
        start_at=start_at,
        end_at=end_at,
    )
    _marked_done(execution=execution, end_at=end_at)

    first = repair_marked_done_snapshots(dry_run=False)
    second = repair_marked_done_snapshots(dry_run=False)

    assert first.filled
    assert second.filled == ()
    assert second.deleted_objects == ()


def test_dashboard_population_counts_classifiable_and_excluded():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    bu = create_business_unit(establishment=membership.establishment, key="roof")
    now = timezone.now()
    plan = _plan(membership=membership, business_unit=bu)
    valid = _execution(
        plan=plan,
        membership=membership,
        business_unit=bu,
        title="Valid",
        start_at=now - timedelta(hours=5),
        end_at=now - timedelta(hours=1),
    )
    _marked_done(
        execution=valid,
        start_at=now - timedelta(hours=5),
        end_at=now - timedelta(hours=1),
    )
    missing = _execution(
        plan=_plan(membership=membership, business_unit=bu, title="Other plan"),
        membership=membership,
        business_unit=bu,
        title="Missing",
        start_at=now - timedelta(hours=5),
        end_at=now - timedelta(hours=1),
    )
    _marked_done(execution=missing, end_at=now - timedelta(hours=1))

    report = repair_marked_done_snapshots(dry_run=True)

    assert report.dashboard_before.marked_done_classifiable >= 1
    assert report.dashboard_before.marked_done_excluded >= 1
    assert report.dashboard_after.marked_done_excluded == 0


def test_command_requires_confirm_or_dry_run():
    with pytest.raises(CommandError, match="--confirm"):
        call_command("repair_marked_done_snapshots")


def test_command_dry_run_prints_deleted_objects():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    bu = create_business_unit(establishment=membership.establishment, key="office")
    plan = _plan(membership=membership, business_unit=bu)
    now = timezone.now()
    execution = _execution(
        plan=plan,
        membership=membership,
        business_unit=bu,
        start_at=None,
        end_at=now,
    )
    _marked_done(execution=execution, extra={"to_status": EXECUTION_STATUS_DONE})
    stdout = StringIO()
    call_command("repair_marked_done_snapshots", "--dry-run", stdout=stdout)
    output = stdout.getvalue()
    assert "Dry run" in output
    assert str(execution.id) in output
    assert ActionPlanExecution.objects.filter(id=execution.id).exists()


@patch(
    "houston.action_plans.repair_marked_done_snapshots.assert_local_dev_environment",
    side_effect=LocalDevEnvironmentError("refusing"),
)
def test_refuses_outside_local_dev(mock_guard):
    with pytest.raises(LocalDevEnvironmentError, match="refusing"):
        repair_marked_done_snapshots(dry_run=True)
    mock_guard.assert_called_once()
