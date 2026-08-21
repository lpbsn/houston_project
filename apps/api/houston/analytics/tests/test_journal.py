from __future__ import annotations

import importlib
from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_CREATED,
    EXECUTION_LIFECYCLE_EVENT_DEADLINE_CHANGED,
    EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE,
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_LIFECYCLE_EVENT_STARTED,
    EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
)
from houston.action_plans.lifecycle_events import record_execution_deadline_changed
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionLifecycleEvent
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.analytics.cutover import apply_analytics_history_cutover
from houston.analytics.journal import (
    COVERAGE_COMPLETE,
    COVERAGE_NOT_COMPARABLE,
    COVERAGE_PARTIAL,
    JournalEvent,
    coverage_for_window,
    execution_end_at_at,
    execution_status_at,
    parse_metadata_datetime,
    signal_status_at,
)
from houston.analytics.models import AnalyticsHistoryCoverage, PatternEstablishmentSighting
from houston.establishments.models import EstablishmentMembership
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    SIGNAL_LIFECYCLE_EVENT_CANCELED,
    SIGNAL_LIFECYCLE_EVENT_CREATED,
    SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
)
from houston.signals.models import Signal, SignalLifecycleEvent
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


_CUTOVER_MAX_QUERIES = 12
_INVENTED_SIGNAL_EVENTS = (SIGNAL_LIFECYCLE_EVENT_CREATED,)
_INVENTED_EXECUTION_EVENTS = (
    EXECUTION_LIFECYCLE_EVENT_CREATED,
    EXECUTION_LIFECYCLE_EVENT_STARTED,
    EXECUTION_LIFECYCLE_EVENT_DEADLINE_CHANGED,
)


def _journal(events) -> list[JournalEvent]:
    return [
        JournalEvent(
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            metadata_safe=event.metadata_safe or {},
        )
        for event in events
    ]


def _create_cutover_signal(establishment, *, status, title, **timestamps) -> Signal:
    return Signal.objects.create(
        establishment=establishment,
        status=status,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary="Summary.",
        issue_focus=title.lower().replace(" ", "-"),
        last_activity_at=timezone.now(),
        **timestamps,
    )


def _create_cutover_execution(
    *,
    establishment,
    created_by,
    business_unit,
    status,
    title,
    end_at=None,
    marked_done_at=None,
    validated_at=None,
    canceled_at=None,
) -> ActionPlanExecution:
    return ActionPlanExecution.objects.create(
        establishment=establishment,
        created_by=created_by,
        title=title,
        pilot_business_unit=business_unit,
        last_activity_at=timezone.now(),
        use_shared_chronology=True,
        status=status,
        end_at=end_at,
        marked_done_at=marked_done_at,
        validated_at=validated_at,
        canceled_at=canceled_at,
    )


def _assert_no_invented_legacy_events() -> None:
    assert not SignalLifecycleEvent.objects.filter(
        event_type__in=_INVENTED_SIGNAL_EVENTS,
    ).exists()
    assert not ActionPlanExecutionLifecycleEvent.objects.filter(
        event_type__in=_INVENTED_EXECUTION_EVENTS,
    ).exists()
    assert PatternEstablishmentSighting.objects.count() == 0


def _standalone_exists_sql(captured: CaptureQueriesContext) -> list[str]:
    standalone = []
    for query in captured.captured_queries:
        sql = query["sql"].strip()
        upper = sql.upper()
        if "EXISTS" in upper and not upper.startswith("INSERT"):
            standalone.append(sql)
    return standalone


def _seed_cutover_mix(*, establishment, owner, business_unit, count: int, prefix: str) -> None:
    now = timezone.now()
    signal_specs = (
        (Signal.Status.IN_PROGRESS, {}),
        (Signal.Status.RESOLVED, {"resolved_at": now}),
        (Signal.Status.CANCELED, {"canceled_at": now}),
        (Signal.Status.ARCHIVED, {"archived_at": now}),
    )
    execution_specs = (
        (EXECUTION_STATUS_PENDING_VALIDATION, {"marked_done_at": now, "end_at": now}),
        (EXECUTION_STATUS_DONE, {"marked_done_at": now, "validated_at": now, "end_at": now}),
        (EXECUTION_STATUS_DONE, {"marked_done_at": now, "end_at": now}),
        (EXECUTION_STATUS_CANCELED, {"canceled_at": now, "end_at": now}),
    )
    signals = [
        Signal(
            establishment=establishment,
            status=signal_specs[index % len(signal_specs)][0],
            routing_status=Signal.RoutingStatus.RESOLVED,
            title=f"{prefix} signal {index}",
            structured_summary="Summary.",
            issue_focus=f"{prefix}-sig-{index}",
            last_activity_at=now,
            **signal_specs[index % len(signal_specs)][1],
        )
        for index in range(count)
    ]
    executions = [
        ActionPlanExecution(
            establishment=establishment,
            created_by=owner,
            title=f"{prefix} execution {index}",
            pilot_business_unit=business_unit,
            last_activity_at=now,
            use_shared_chronology=True,
            status=execution_specs[index % len(execution_specs)][0],
            **execution_specs[index % len(execution_specs)][1],
        )
        for index in range(count)
    ]
    Signal.objects.bulk_create(signals)
    ActionPlanExecution.objects.bulk_create(executions)


def test_legacy_in_progress_signal_status_at_uses_baseline():
    establishment = create_establishment()
    cutover = timezone.now()
    signal = Signal.objects.create(
        establishment=establishment,
        status=Signal.Status.IN_PROGRESS,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title="Legacy in progress",
        structured_summary="Summary.",
        issue_focus="legacy",
        last_activity_at=cutover,
    )
    Signal.objects.filter(pk=signal.pk).update(created_at=cutover - timedelta(days=10))
    SignalLifecycleEvent.objects.create(
        signal=signal,
        establishment=establishment,
        event_type=SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
        occurred_at=cutover,
        metadata_safe={"to_status": Signal.Status.IN_PROGRESS},
    )
    events = _journal(signal.lifecycle_events.all())
    assert (
        signal_status_at(
            at=cutover + timedelta(minutes=1),
            reliable_from=cutover,
            events=events,
        )
        == Signal.Status.IN_PROGRESS
    )
    assert (
        signal_status_at(
            at=cutover - timedelta(minutes=1),
            reliable_from=cutover,
            events=events,
        )
        is None
    )


def test_coverage_previous_before_cutover_is_not_comparable():
    reliable_from = timezone.now()
    window_start = reliable_from - timedelta(days=3)
    window_end = reliable_from + timedelta(days=4)
    assert (
        coverage_for_window(
            window_start=window_start,
            window_end=window_end,
            reliable_from=reliable_from,
            needs_journal=True,
        )
        == COVERAGE_PARTIAL
    )
    assert (
        coverage_for_window(
            window_start=window_start,
            window_end=window_end,
            reliable_from=reliable_from,
            needs_journal=True,
            previous_end=reliable_from - timedelta(days=3),
        )
        == COVERAGE_NOT_COMPARABLE
    )
    assert (
        coverage_for_window(
            window_start=reliable_from + timedelta(hours=1),
            window_end=reliable_from + timedelta(days=7),
            reliable_from=reliable_from,
            needs_journal=True,
        )
        == COVERAGE_COMPLETE
    )


def test_deadline_changed_end_at_at():
    establishment = create_establishment()
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    business_unit = create_business_unit(establishment=establishment, key="kitchen")
    create_membership_with_business_unit_scope(membership=staff, business_unit=business_unit)
    first_end = timezone.now() + timedelta(days=2)
    second_end = first_end + timedelta(days=3)
    _, execution = create_action_plan_with_execution(
        establishment_id=establishment.id,
        created_by=owner,
        pilot_business_unit_id=business_unit.id,
        title="Deadline journal",
        end_at=first_end,
        tasks=[build_task_payload(task="Work", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=staff, business_unit=business_unit)],
    )
    changed_at = timezone.now()
    record_execution_deadline_changed(
        execution=execution,
        from_end_at=first_end,
        to_end_at=second_end,
        actor_membership=owner,
        occurred_at=changed_at,
    )
    events = _journal(
        ActionPlanExecutionLifecycleEvent.objects.filter(action_plan_execution=execution)
    )
    reliable_from = timezone.now() - timedelta(days=1)
    assert (
        execution_end_at_at(at=changed_at, reliable_from=reliable_from, events=events) == first_end
    )
    assert (
        execution_end_at_at(
            at=changed_at + timedelta(seconds=1),
            reliable_from=reliable_from,
            events=events,
        )
        == second_end
    )
    assert ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_DEADLINE_CHANGED,
    ).exists()
    created = ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_CREATED,
    ).get()
    assert created.metadata_safe["initial_status"] == EXECUTION_STATUS_IN_PROGRESS
    assert created.metadata_safe["to_status"] == EXECUTION_STATUS_IN_PROGRESS


def test_cutover_is_idempotent_and_does_not_invent_created():
    establishment = create_establishment()
    signal = Signal.objects.create(
        establishment=establishment,
        status=Signal.Status.IN_PROGRESS,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title="Cutover signal",
        structured_summary="Summary.",
        issue_focus="cutover",
        last_activity_at=timezone.now(),
    )
    first = apply_analytics_history_cutover()
    baseline_count = SignalLifecycleEvent.objects.filter(
        event_type=SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
    ).count()
    second = apply_analytics_history_cutover()
    assert first == second
    assert AnalyticsHistoryCoverage.objects.count() == 1
    assert (
        SignalLifecycleEvent.objects.filter(
            event_type=SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
        ).count()
        == baseline_count
    )
    baseline = SignalLifecycleEvent.objects.get(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
    )
    assert baseline.occurred_at == first
    assert baseline.metadata_safe == {"to_status": Signal.Status.IN_PROGRESS}
    assert not SignalLifecycleEvent.objects.filter(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_CREATED,
    ).exists()
    assert (
        signal_status_at(
            at=first + timedelta(seconds=1),
            reliable_from=first,
            events=_journal(signal.lifecycle_events.all()),
        )
        == Signal.Status.IN_PROGRESS
    )


def test_cutover_signal_terminals_skip_missing_timestamps():
    establishment = create_establishment()
    resolved_at = timezone.now() - timedelta(days=1)
    canceled_at = timezone.now() - timedelta(hours=12)
    archived_at = timezone.now() - timedelta(hours=6)
    in_progress = _create_cutover_signal(
        establishment,
        status=Signal.Status.IN_PROGRESS,
        title="Cutover in progress",
    )
    resolved = _create_cutover_signal(
        establishment,
        status=Signal.Status.RESOLVED,
        title="Cutover resolved",
        resolved_at=resolved_at,
    )
    resolved_without_ts = _create_cutover_signal(
        establishment,
        status=Signal.Status.RESOLVED,
        title="Cutover resolved missing",
    )
    canceled = _create_cutover_signal(
        establishment,
        status=Signal.Status.CANCELED,
        title="Cutover canceled",
        canceled_at=canceled_at,
    )
    archived = _create_cutover_signal(
        establishment,
        status=Signal.Status.ARCHIVED,
        title="Cutover archived",
        archived_at=archived_at,
    )

    reliable_from = apply_analytics_history_cutover()
    apply_analytics_history_cutover()

    def event_types(signal):
        return set(signal.lifecycle_events.values_list("event_type", flat=True))

    assert event_types(in_progress) == {SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE}
    assert event_types(resolved) == {
        SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
        SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    }
    terminal = SignalLifecycleEvent.objects.get(
        signal=resolved,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    )
    assert terminal.occurred_at == resolved_at
    assert terminal.metadata_safe == {"to_status": Signal.Status.RESOLVED}
    assert event_types(resolved_without_ts) == {SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE}
    assert not SignalLifecycleEvent.objects.filter(
        signal=resolved_without_ts,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    ).exists()
    canceled_terminal = SignalLifecycleEvent.objects.get(
        signal=canceled,
        event_type=SIGNAL_LIFECYCLE_EVENT_CANCELED,
    )
    assert canceled_terminal.occurred_at == canceled_at
    archived_terminal = SignalLifecycleEvent.objects.get(
        signal=archived,
        event_type=SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    )
    assert archived_terminal.occurred_at == archived_at
    assert (
        SignalLifecycleEvent.objects.filter(
            signal=resolved,
            event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        ).count()
        == 1
    )
    assert (
        signal_status_at(
            at=reliable_from + timedelta(seconds=1),
            reliable_from=reliable_from,
            events=_journal(resolved.lifecycle_events.all()),
        )
        == Signal.Status.RESOLVED
    )
    _assert_no_invented_legacy_events()


def test_cutover_does_not_invent_canceled_event_from_last_activity_at():
    establishment = create_establishment()
    canceled = _create_cutover_signal(
        establishment,
        status=Signal.Status.CANCELED,
        title="Legacy cancel",
    )
    last_activity = timezone.now() - timedelta(days=9)
    Signal.objects.filter(pk=canceled.pk).update(last_activity_at=last_activity)
    canceled.refresh_from_db()

    apply_analytics_history_cutover()

    assert not SignalLifecycleEvent.objects.filter(
        signal=canceled,
        event_type=SIGNAL_LIFECYCLE_EVENT_CANCELED,
    ).exists()
    baseline = SignalLifecycleEvent.objects.get(
        signal=canceled,
        event_type=SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
    )
    assert baseline.occurred_at != last_activity


def test_cutover_execution_terminals_match_current_status_branches():
    establishment = create_establishment()
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    business_unit = create_business_unit(establishment=establishment, key="kitchen")
    end_at = timezone.now() + timedelta(days=2)
    marked_done_at = timezone.now() - timedelta(hours=3)
    validated_at = timezone.now() - timedelta(hours=1)
    canceled_at = timezone.now() - timedelta(hours=2)

    pending = _create_cutover_execution(
        establishment=establishment,
        created_by=owner,
        business_unit=business_unit,
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        title="Pending validation",
        end_at=end_at,
        marked_done_at=marked_done_at,
    )
    done_validated = _create_cutover_execution(
        establishment=establishment,
        created_by=owner,
        business_unit=business_unit,
        status=EXECUTION_STATUS_DONE,
        title="Done validated",
        end_at=end_at,
        marked_done_at=marked_done_at,
        validated_at=validated_at,
    )
    done_unvalidated = _create_cutover_execution(
        establishment=establishment,
        created_by=owner,
        business_unit=business_unit,
        status=EXECUTION_STATUS_DONE,
        title="Done unvalidated",
        end_at=end_at,
        marked_done_at=marked_done_at,
    )
    done_without_marked = _create_cutover_execution(
        establishment=establishment,
        created_by=owner,
        business_unit=business_unit,
        status=EXECUTION_STATUS_DONE,
        title="Done missing marked",
        end_at=end_at,
        validated_at=validated_at,
    )
    canceled = _create_cutover_execution(
        establishment=establishment,
        created_by=owner,
        business_unit=business_unit,
        status=EXECUTION_STATUS_CANCELED,
        title="Canceled execution",
        end_at=None,
        canceled_at=canceled_at,
    )

    reliable_from = apply_analytics_history_cutover()
    apply_analytics_history_cutover()

    pending_marked = ActionPlanExecutionLifecycleEvent.objects.get(
        action_plan_execution=pending,
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    )
    assert pending_marked.occurred_at == marked_done_at
    assert pending_marked.metadata_safe["to_status"] == EXECUTION_STATUS_PENDING_VALIDATION
    assert parse_metadata_datetime(pending_marked.metadata_safe["end_at"]) == end_at

    done_marked = ActionPlanExecutionLifecycleEvent.objects.get(
        action_plan_execution=done_validated,
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    )
    assert done_marked.occurred_at == marked_done_at
    assert done_marked.metadata_safe["to_status"] == EXECUTION_STATUS_PENDING_VALIDATION
    validated = ActionPlanExecutionLifecycleEvent.objects.get(
        action_plan_execution=done_validated,
        event_type=EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    )
    assert validated.occurred_at == validated_at
    assert validated.metadata_safe["to_status"] == EXECUTION_STATUS_DONE

    unvalidated_marked = ActionPlanExecutionLifecycleEvent.objects.get(
        action_plan_execution=done_unvalidated,
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    )
    assert unvalidated_marked.metadata_safe["to_status"] == EXECUTION_STATUS_DONE
    assert not ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=done_unvalidated,
        event_type=EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    ).exists()

    assert not ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=done_without_marked,
        event_type__in=[
            EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
            EXECUTION_LIFECYCLE_EVENT_VALIDATED,
        ],
    ).exists()

    canceled_event = ActionPlanExecutionLifecycleEvent.objects.get(
        action_plan_execution=canceled,
        event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
    )
    assert canceled_event.occurred_at == canceled_at
    assert canceled_event.metadata_safe["to_status"] == EXECUTION_STATUS_CANCELED
    assert "end_at" in canceled_event.metadata_safe
    assert canceled_event.metadata_safe["end_at"] is None

    assert (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution=done_validated,
            event_type=EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE,
        ).count()
        == 1
    )
    done_events = _journal(done_validated.lifecycle_events.all())
    after = reliable_from + timedelta(seconds=1)
    assert (
        execution_status_at(at=after, reliable_from=reliable_from, events=done_events)
        == EXECUTION_STATUS_DONE
    )
    assert execution_end_at_at(at=after, reliable_from=reliable_from, events=done_events) == end_at
    _assert_no_invented_legacy_events()


def test_cutover_query_count_is_independent_of_object_count():
    establishment = create_establishment()
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    business_unit = create_business_unit(establishment=establishment, key="kitchen")
    apply_analytics_history_cutover()

    _seed_cutover_mix(
        establishment=establishment,
        owner=owner,
        business_unit=business_unit,
        count=12,
        prefix="cutover-a",
    )
    with CaptureQueriesContext(connection) as first:
        apply_analytics_history_cutover()

    _seed_cutover_mix(
        establishment=establishment,
        owner=owner,
        business_unit=business_unit,
        count=24,
        prefix="cutover-b",
    )
    with CaptureQueriesContext(connection) as second:
        apply_analytics_history_cutover()

    assert len(first.captured_queries) == len(second.captured_queries)
    assert len(first.captured_queries) <= _CUTOVER_MAX_QUERIES
    assert _standalone_exists_sql(first) == []
    assert _standalone_exists_sql(second) == []
    insert_sql = [
        query["sql"].strip()
        for query in first.captured_queries
        if query["sql"].lstrip().upper().startswith("INSERT")
    ]
    assert len(insert_sql) == 9
    assert all("NOT EXISTS" in sql.upper() for sql in insert_sql)


def test_analytics_0006_reverse_is_irreversible():
    module = importlib.import_module(
        "houston.analytics.migrations.0006_history_coverage_and_sightings"
    )
    with pytest.raises(IrreversibleError, match="reliable_from"):
        module.refuse_history_cutover_reverse(apps=None, schema_editor=None)
