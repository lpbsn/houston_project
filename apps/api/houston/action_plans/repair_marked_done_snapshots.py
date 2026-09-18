"""One-shot local repair of marked_done start_at/end_at snapshots.

Domain lifecycle services stay insert-only. This module is the only writer
allowed to update ``metadata_safe`` or delete test graphs for this repair.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionFeedPin,
    ActionPlanExecutionLifecycleEvent,
    ActionPlanExecutionReview,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanPlanningOutboxEntry,
    ActionPlanPlanningSubmission,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
    ActionPlanTask,
)
from houston.analytics.journal import parse_metadata_datetime
from houston.analytics.models import PatternIssueReport, SignalPatternAssignment
from houston.comments.models import Comment, CommentMention
from houston.core.dev_guards import assert_local_dev_environment
from houston.gamification.constants import (
    SOURCE_TYPE_ACTION_PLAN_EXECUTION,
    SOURCE_TYPE_SIGNAL,
    SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST,
)
from houston.gamification.models import PointTransaction
from houston.notifications.models import Notification
from houston.observations.models import Observation, ObservationMedia, ObservationProcessing
from houston.signals.models import (
    CandidateSignal,
    Signal,
    SignalLifecycleEvent,
    SignalResolutionRequest,
    SignalSourceObservation,
)
from houston.uploads.models import TemporaryUpload

MODEL_ACTION_PLAN = "action_plans.ActionPlan"
MODEL_ACTION_PLAN_TASK = "action_plans.ActionPlanTask"
MODEL_SCHEDULE = "action_plans.ActionPlanSchedule"
MODEL_SCHEDULE_ASSIGNEE = "action_plans.ActionPlanScheduleAssignee"
MODEL_PLANNING_SUBMISSION = "action_plans.ActionPlanPlanningSubmission"
MODEL_PLANNING_OUTBOX = "action_plans.ActionPlanPlanningOutboxEntry"
MODEL_EXECUTION = "action_plans.ActionPlanExecution"
MODEL_LIFECYCLE_EVENT = "action_plans.ActionPlanExecutionLifecycleEvent"
MODEL_REVIEW = "action_plans.ActionPlanExecutionReview"
MODEL_FEED_PIN = "action_plans.ActionPlanExecutionFeedPin"
MODEL_TEAM = "action_plans.ActionPlanExecutionTeam"
MODEL_ASSIGNEE = "action_plans.ActionPlanAssignee"
MODEL_EXECUTION_TASK = "action_plans.ActionPlanExecutionTask"
MODEL_SIGNAL = "signals.Signal"
MODEL_SIGNAL_EVENT = "signals.SignalLifecycleEvent"
MODEL_SIGNAL_SOURCE = "signals.SignalSourceObservation"
MODEL_RESOLUTION_REQUEST = "signals.SignalResolutionRequest"
MODEL_CANDIDATE = "signals.CandidateSignal"
MODEL_COMMENT = "comments.Comment"
MODEL_MENTION = "comments.CommentMention"
MODEL_NOTIFICATION = "notifications.Notification"
MODEL_POINT = "gamification.PointTransaction"
MODEL_OBSERVATION = "observations.Observation"
MODEL_MEDIA = "observations.ObservationMedia"
MODEL_PROCESSING = "observations.ObservationProcessing"
MODEL_UPLOAD = "uploads.TemporaryUpload"
MODEL_PATTERN_ASSIGNMENT = "analytics.SignalPatternAssignment"
MODEL_PATTERN_REPORT = "analytics.PatternIssueReport"


@dataclass(frozen=True)
class DashboardPopulation:
    marked_done_classifiable: int
    marked_done_excluded: int
    overrun_live: int


@dataclass(frozen=True)
class FillRecord:
    event_id: UUID
    execution_id: UUID
    start_at: str
    end_at: str


@dataclass
class GraphIds:
    execution_ids: set[UUID] = field(default_factory=set)
    plan_ids: set[UUID] = field(default_factory=set)
    signal_ids: set[UUID] = field(default_factory=set)
    observation_ids: set[UUID] = field(default_factory=set)
    schedule_ids: set[UUID] = field(default_factory=set)
    task_ids: set[UUID] = field(default_factory=set)
    seed_execution_ids: tuple[UUID, ...] = ()
    reason: str = ""

    def overlaps(self, other: GraphIds) -> bool:
        return bool(
            self.execution_ids & other.execution_ids
            or self.plan_ids & other.plan_ids
            or self.signal_ids & other.signal_ids
            or self.observation_ids & other.observation_ids
            or self.schedule_ids & other.schedule_ids
        )

    def merge(self, other: GraphIds) -> None:
        self.execution_ids |= other.execution_ids
        self.plan_ids |= other.plan_ids
        self.signal_ids |= other.signal_ids
        self.observation_ids |= other.observation_ids
        self.schedule_ids |= other.schedule_ids
        self.task_ids |= other.task_ids
        self.seed_execution_ids = tuple(
            sorted(set(self.seed_execution_ids) | set(other.seed_execution_ids))
        )


@dataclass(frozen=True)
class RepairReport:
    dry_run: bool
    preserved_event_ids: tuple[UUID, ...]
    filled: tuple[FillRecord, ...]
    deleted_objects: tuple[tuple[str, UUID], ...]
    graphs: tuple[GraphIds, ...]
    dashboard_before: DashboardPopulation
    dashboard_after: DashboardPopulation


def is_valid_window(start_at: datetime | None, end_at: datetime | None) -> bool:
    if start_at is None or end_at is None:
        return False
    if timezone.is_naive(start_at) or timezone.is_naive(end_at):
        return False
    return (end_at - start_at).total_seconds() > 0


def event_snapshot_is_valid(metadata_safe: dict[str, Any] | None) -> bool:
    payload = metadata_safe or {}
    return is_valid_window(
        parse_metadata_datetime(payload.get("start_at")),
        parse_metadata_datetime(payload.get("end_at")),
    )


def _dashboard_population(
    *,
    exclude_event_ids: set[UUID] | None = None,
    exclude_execution_ids: set[UUID] | None = None,
    filled_event_ids: set[UUID] | None = None,
    now: datetime | None = None,
) -> DashboardPopulation:
    skip_events = exclude_event_ids or set()
    skip_executions = exclude_execution_ids or set()
    filled = filled_event_ids or set()
    classifiable = 0
    excluded = 0
    for event in ActionPlanExecutionLifecycleEvent.objects.filter(
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE
    ).only("id", "metadata_safe"):
        if event.id in skip_events:
            continue
        if event.id in filled or event_snapshot_is_valid(event.metadata_safe):
            classifiable += 1
        else:
            excluded += 1
    moment = now or timezone.now()
    overrun = 0
    for execution in ActionPlanExecution.objects.filter(
        status__in=(EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS)
    ).only("id", "start_at", "end_at"):
        if execution.id in skip_executions:
            continue
        if not is_valid_window(execution.start_at, execution.end_at):
            continue
        if execution.end_at is None or execution.end_at >= moment:
            continue
        overrun += 1
    return DashboardPopulation(
        marked_done_classifiable=classifiable,
        marked_done_excluded=excluded,
        overrun_live=overrun,
    )


def _expand_from_executions(seed_execution_ids: set[UUID]) -> GraphIds:
    graph = GraphIds(
        execution_ids=set(seed_execution_ids),
        seed_execution_ids=tuple(sorted(seed_execution_ids)),
    )
    if not seed_execution_ids:
        return graph
    while True:
        before = (
            len(graph.execution_ids),
            len(graph.plan_ids),
            len(graph.signal_ids),
            len(graph.observation_ids),
            len(graph.schedule_ids),
        )
        for row in ActionPlanExecution.objects.filter(id__in=graph.execution_ids).values(
            "action_plan_id",
            "source_signal_id",
            "action_plan_schedule_id",
        ):
            if row["action_plan_id"]:
                graph.plan_ids.add(row["action_plan_id"])
            if row["source_signal_id"]:
                graph.signal_ids.add(row["source_signal_id"])
            if row["action_plan_schedule_id"]:
                graph.schedule_ids.add(row["action_plan_schedule_id"])
        if graph.plan_ids:
            graph.execution_ids.update(
                ActionPlanExecution.objects.filter(action_plan_id__in=graph.plan_ids).values_list(
                    "id", flat=True
                )
            )
            graph.schedule_ids.update(
                ActionPlanSchedule.objects.filter(action_plan_id__in=graph.plan_ids).values_list(
                    "id", flat=True
                )
            )
        if graph.signal_ids:
            graph.execution_ids.update(
                ActionPlanExecution.objects.filter(source_signal_id__in=graph.signal_ids).values_list(
                    "id", flat=True
                )
            )
        if graph.schedule_ids:
            graph.execution_ids.update(
                ActionPlanExecution.objects.filter(
                    action_plan_schedule_id__in=graph.schedule_ids
                ).values_list("id", flat=True)
            )
        graph.task_ids.update(
            ActionPlanExecutionTask.objects.filter(
                action_plan_execution_id__in=graph.execution_ids
            ).values_list("id", flat=True)
        )
        graph.observation_ids.update(
            Observation.objects.filter(action_plan_execution_id__in=graph.execution_ids).values_list(
                "id", flat=True
            )
        )
        if graph.task_ids:
            graph.observation_ids.update(
                Observation.objects.filter(action_plan_execution_task_id__in=graph.task_ids).values_list(
                    "id", flat=True
                )
            )
        if graph.signal_ids:
            graph.observation_ids.update(
                SignalSourceObservation.objects.filter(signal_id__in=graph.signal_ids).values_list(
                    "observation_id", flat=True
                )
            )
        if graph.observation_ids:
            graph.signal_ids.update(
                SignalSourceObservation.objects.filter(
                    observation_id__in=graph.observation_ids
                ).values_list("signal_id", flat=True)
            )
            graph.execution_ids.update(
                Observation.objects.filter(
                    id__in=graph.observation_ids,
                    action_plan_execution_id__isnull=False,
                ).values_list("action_plan_execution_id", flat=True)
            )
        after = (
            len(graph.execution_ids),
            len(graph.plan_ids),
            len(graph.signal_ids),
            len(graph.observation_ids),
            len(graph.schedule_ids),
        )
        if after == before:
            return graph


def _merge_graphs(graphs: list[GraphIds]) -> list[GraphIds]:
    merged: list[GraphIds] = []
    for graph in graphs:
        target = None
        for existing in merged:
            if existing.overlaps(graph):
                target = existing
                break
        if target is None:
            merged.append(graph)
        else:
            target.merge(graph)
    changed = True
    while changed:
        changed = False
        nxt: list[GraphIds] = []
        for graph in merged:
            attached = False
            for existing in nxt:
                if existing.overlaps(graph):
                    existing.merge(graph)
                    attached = True
                    changed = True
                    break
            if not attached:
                nxt.append(graph)
        merged = nxt
    return merged


def _add_ids(bucket: dict[str, set[UUID]], model: str, ids) -> None:
    bucket[model].update(ids)


def _collect_objects(graph: GraphIds) -> dict[str, set[UUID]]:
    objects: dict[str, set[UUID]] = defaultdict(set)
    _add_ids(objects, MODEL_EXECUTION, graph.execution_ids)
    _add_ids(objects, MODEL_ACTION_PLAN, graph.plan_ids)
    _add_ids(objects, MODEL_SIGNAL, graph.signal_ids)
    _add_ids(objects, MODEL_OBSERVATION, graph.observation_ids)
    _add_ids(objects, MODEL_SCHEDULE, graph.schedule_ids)
    _add_ids(objects, MODEL_EXECUTION_TASK, graph.task_ids)
    if graph.plan_ids:
        _add_ids(
            objects,
            MODEL_ACTION_PLAN_TASK,
            ActionPlanTask.objects.filter(action_plan_id__in=graph.plan_ids).values_list(
                "id", flat=True
            ),
        )
        submissions = list(
            ActionPlanPlanningSubmission.objects.filter(action_plan_id__in=graph.plan_ids).values_list(
                "id", flat=True
            )
        )
        _add_ids(objects, MODEL_PLANNING_SUBMISSION, submissions)
        if submissions:
            _add_ids(
                objects,
                MODEL_PLANNING_OUTBOX,
                ActionPlanPlanningOutboxEntry.objects.filter(
                    planning_submission_id__in=submissions
                ).values_list("id", flat=True),
            )
    if graph.schedule_ids:
        _add_ids(
            objects,
            MODEL_SCHEDULE_ASSIGNEE,
            ActionPlanScheduleAssignee.objects.filter(
                action_plan_schedule_id__in=graph.schedule_ids
            ).values_list("id", flat=True),
        )
    if graph.execution_ids:
        _add_ids(
            objects,
            MODEL_LIFECYCLE_EVENT,
            ActionPlanExecutionLifecycleEvent.objects.filter(
                action_plan_execution_id__in=graph.execution_ids
            ).values_list("id", flat=True),
        )
        _add_ids(
            objects,
            MODEL_REVIEW,
            ActionPlanExecutionReview.objects.filter(
                action_plan_execution_id__in=graph.execution_ids
            ).values_list("id", flat=True),
        )
        _add_ids(
            objects,
            MODEL_FEED_PIN,
            ActionPlanExecutionFeedPin.objects.filter(
                action_plan_execution_id__in=graph.execution_ids
            ).values_list("id", flat=True),
        )
        _add_ids(
            objects,
            MODEL_TEAM,
            ActionPlanExecutionTeam.objects.filter(
                action_plan_execution_id__in=graph.execution_ids
            ).values_list("id", flat=True),
        )
        _add_ids(
            objects,
            MODEL_ASSIGNEE,
            ActionPlanAssignee.objects.filter(
                action_plan_execution_id__in=graph.execution_ids
            ).values_list("id", flat=True),
        )
    if graph.signal_ids:
        _add_ids(
            objects,
            MODEL_SIGNAL_EVENT,
            SignalLifecycleEvent.objects.filter(signal_id__in=graph.signal_ids).values_list(
                "id", flat=True
            ),
        )
        _add_ids(
            objects,
            MODEL_SIGNAL_SOURCE,
            SignalSourceObservation.objects.filter(signal_id__in=graph.signal_ids).values_list(
                "id", flat=True
            ),
        )
        _add_ids(
            objects,
            MODEL_RESOLUTION_REQUEST,
            SignalResolutionRequest.objects.filter(signal_id__in=graph.signal_ids).values_list(
                "id", flat=True
            ),
        )
        _add_ids(
            objects,
            MODEL_PATTERN_ASSIGNMENT,
            SignalPatternAssignment.objects.filter(signal_id__in=graph.signal_ids).values_list(
                "id", flat=True
            ),
        )
        _add_ids(
            objects,
            MODEL_PATTERN_REPORT,
            PatternIssueReport.objects.filter(signal_id__in=graph.signal_ids).values_list(
                "id", flat=True
            ),
        )
        _add_ids(
            objects,
            MODEL_CANDIDATE,
            CandidateSignal.objects.filter(result_signal_id__in=graph.signal_ids).values_list(
                "id", flat=True
            ),
        )
    if graph.observation_ids:
        _add_ids(
            objects,
            MODEL_CANDIDATE,
            CandidateSignal.objects.filter(observation_id__in=graph.observation_ids).values_list(
                "id", flat=True
            ),
        )
        _add_ids(
            objects,
            MODEL_MEDIA,
            ObservationMedia.objects.filter(observation_id__in=graph.observation_ids).values_list(
                "id", flat=True
            ),
        )
        _add_ids(
            objects,
            MODEL_PROCESSING,
            ObservationProcessing.objects.filter(
                observation_id__in=graph.observation_ids
            ).values_list("id", flat=True),
        )
        upload_ids = ObservationMedia.objects.filter(
            observation_id__in=graph.observation_ids
        ).values_list("temporary_upload_id", flat=True)
        _add_ids(objects, MODEL_UPLOAD, upload_ids)
    comment_q = Q()
    if graph.signal_ids:
        comment_q |= Q(signal_id__in=graph.signal_ids)
    if graph.execution_ids:
        comment_q |= Q(action_plan_execution_id__in=graph.execution_ids)
    comment_ids: list[UUID] = []
    if comment_q:
        comment_ids = list(Comment.objects.filter(comment_q).values_list("id", flat=True))
        _add_ids(objects, MODEL_COMMENT, comment_ids)
        _add_ids(
            objects,
            MODEL_MENTION,
            CommentMention.objects.filter(comment_id__in=comment_ids).values_list("id", flat=True),
        )
    notification_q = Q()
    if graph.execution_ids:
        notification_q |= Q(
            subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
            subject_id__in=graph.execution_ids,
        )
    if graph.signal_ids:
        notification_q |= Q(
            subject_type=Notification.SubjectType.SIGNAL,
            subject_id__in=graph.signal_ids,
        )
    if comment_ids:
        notification_q |= Q(
            subject_type=Notification.SubjectType.COMMENT,
            subject_id__in=comment_ids,
        )
    if notification_q:
        _add_ids(
            objects,
            MODEL_NOTIFICATION,
            Notification.objects.filter(notification_q).values_list("id", flat=True),
        )
    point_q = Q()
    if graph.execution_ids:
        point_q |= Q(
            source_type=SOURCE_TYPE_ACTION_PLAN_EXECUTION,
            source_id__in=[str(item) for item in graph.execution_ids],
        )
    if graph.signal_ids:
        point_q |= Q(
            source_type=SOURCE_TYPE_SIGNAL,
            source_id__in=[str(item) for item in graph.signal_ids],
        )
    resolution_ids = objects.get(MODEL_RESOLUTION_REQUEST, set())
    if resolution_ids:
        point_q |= Q(
            source_type=SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST,
            source_id__in=[str(item) for item in resolution_ids],
        )
    if point_q:
        tx_ids = set(PointTransaction.objects.filter(point_q).values_list("id", flat=True))
        extra = set(
            PointTransaction.objects.filter(reversed_transaction_id__in=tx_ids).values_list(
                "id", flat=True
            )
        )
        _add_ids(objects, MODEL_POINT, tx_ids | extra)
    return objects


def _flatten_objects(objects: dict[str, set[UUID]]) -> tuple[tuple[str, UUID], ...]:
    rows: list[tuple[str, UUID]] = []
    for model in sorted(objects):
        for object_id in sorted(objects[model], key=str):
            rows.append((model, object_id))
    return tuple(rows)


def _delete_comments(comment_ids: set[UUID]) -> None:
    remaining = set(comment_ids)
    while remaining:
        leaves = list(
            Comment.objects.filter(id__in=remaining)
            .exclude(replies__id__in=remaining)
            .values_list("id", flat=True)[:500]
        )
        if not leaves:
            leftover = Comment.objects.filter(id__in=remaining)
            if leftover.exists():
                raise RuntimeError("Unable to delete comments due to parent_comment PROTECT.")
            return
        Comment.objects.filter(id__in=leaves).delete()
        remaining -= set(leaves)


def _delete_point_transactions(tx_ids: set[UUID]) -> None:
    pending = set(tx_ids)
    extra = set(
        PointTransaction.objects.filter(reversed_transaction_id__in=pending).values_list(
            "id", flat=True
        )
    )
    pending |= extra
    while pending:
        referenced = set(
            PointTransaction.objects.filter(reversed_transaction_id__in=pending).values_list(
                "reversed_transaction_id",
                flat=True,
            )
        )
        leaves = pending - referenced
        if not leaves:
            raise RuntimeError(
                "Unable to delete PointTransaction rows due to reversed_transaction PROTECT."
            )
        PointTransaction.objects.filter(id__in=leaves).delete()
        pending -= leaves


def _apply_deletes(objects: dict[str, set[UUID]]) -> None:
    if objects.get(MODEL_NOTIFICATION):
        Notification.objects.filter(id__in=objects[MODEL_NOTIFICATION]).delete()
    if objects.get(MODEL_MENTION):
        CommentMention.objects.filter(id__in=objects[MODEL_MENTION]).delete()
    if objects.get(MODEL_COMMENT):
        _delete_comments(objects[MODEL_COMMENT])
    if objects.get(MODEL_POINT):
        _delete_point_transactions(objects[MODEL_POINT])
    if objects.get(MODEL_PATTERN_REPORT):
        PatternIssueReport.objects.filter(id__in=objects[MODEL_PATTERN_REPORT]).delete()
    if objects.get(MODEL_PATTERN_ASSIGNMENT):
        SignalPatternAssignment.objects.filter(id__in=objects[MODEL_PATTERN_ASSIGNMENT]).delete()
    if objects.get(MODEL_PLANNING_OUTBOX):
        ActionPlanPlanningOutboxEntry.objects.filter(id__in=objects[MODEL_PLANNING_OUTBOX]).delete()
    if objects.get(MODEL_PLANNING_SUBMISSION):
        ActionPlanPlanningSubmission.objects.filter(id__in=objects[MODEL_PLANNING_SUBMISSION]).delete()
    if objects.get(MODEL_CANDIDATE):
        CandidateSignal.objects.filter(id__in=objects[MODEL_CANDIDATE]).delete()
    if objects.get(MODEL_SIGNAL_SOURCE):
        SignalSourceObservation.objects.filter(id__in=objects[MODEL_SIGNAL_SOURCE]).delete()
    if objects.get(MODEL_RESOLUTION_REQUEST):
        SignalResolutionRequest.objects.filter(id__in=objects[MODEL_RESOLUTION_REQUEST]).delete()
    if objects.get(MODEL_SIGNAL_EVENT):
        SignalLifecycleEvent.objects.filter(id__in=objects[MODEL_SIGNAL_EVENT]).delete()
    if objects.get(MODEL_MEDIA):
        ObservationMedia.objects.filter(id__in=objects[MODEL_MEDIA]).delete()
    if objects.get(MODEL_PROCESSING):
        ObservationProcessing.objects.filter(id__in=objects[MODEL_PROCESSING]).delete()
    if objects.get(MODEL_UPLOAD):
        TemporaryUpload.objects.filter(id__in=objects[MODEL_UPLOAD]).delete()
    if objects.get(MODEL_OBSERVATION):
        Observation.objects.filter(id__in=objects[MODEL_OBSERVATION]).delete()
    if objects.get(MODEL_LIFECYCLE_EVENT):
        ActionPlanExecutionLifecycleEvent.objects.filter(
            id__in=objects[MODEL_LIFECYCLE_EVENT]
        ).delete()
    if objects.get(MODEL_REVIEW):
        ActionPlanExecutionReview.objects.filter(id__in=objects[MODEL_REVIEW]).delete()
    if objects.get(MODEL_FEED_PIN):
        ActionPlanExecutionFeedPin.objects.filter(id__in=objects[MODEL_FEED_PIN]).delete()
    if objects.get(MODEL_ASSIGNEE):
        ActionPlanAssignee.objects.filter(id__in=objects[MODEL_ASSIGNEE]).delete()
    if objects.get(MODEL_EXECUTION_TASK):
        ActionPlanExecutionTask.objects.filter(id__in=objects[MODEL_EXECUTION_TASK]).delete()
    if objects.get(MODEL_TEAM):
        ActionPlanExecutionTeam.objects.filter(id__in=objects[MODEL_TEAM]).delete()
    if objects.get(MODEL_EXECUTION):
        ActionPlanExecution.objects.filter(id__in=objects[MODEL_EXECUTION]).delete()
    if objects.get(MODEL_SCHEDULE_ASSIGNEE):
        ActionPlanScheduleAssignee.objects.filter(id__in=objects[MODEL_SCHEDULE_ASSIGNEE]).delete()
    if objects.get(MODEL_SCHEDULE):
        ActionPlanSchedule.objects.filter(id__in=objects[MODEL_SCHEDULE]).delete()
    if objects.get(MODEL_ACTION_PLAN_TASK):
        ActionPlanTask.objects.filter(id__in=objects[MODEL_ACTION_PLAN_TASK]).delete()
    if objects.get(MODEL_ACTION_PLAN):
        ActionPlan.objects.filter(id__in=objects[MODEL_ACTION_PLAN]).delete()
    if objects.get(MODEL_SIGNAL):
        Signal.objects.filter(id__in=objects[MODEL_SIGNAL]).delete()


def _merge_snapshot(
    event: ActionPlanExecutionLifecycleEvent,
    execution: ActionPlanExecution,
) -> None:
    metadata = dict(event.metadata_safe or {})
    metadata["start_at"] = execution.start_at.isoformat()
    metadata["end_at"] = execution.end_at.isoformat()
    event.metadata_safe = metadata
    event.save(update_fields=["metadata_safe", "updated_at"])


def repair_marked_done_snapshots(*, dry_run: bool) -> RepairReport:
    assert_local_dev_environment()
    dashboard_before = _dashboard_population()
    marked_events = list(
        ActionPlanExecutionLifecycleEvent.objects.filter(
            event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE
        ).select_related("action_plan_execution")
    )
    events_by_execution: dict[UUID, list[ActionPlanExecutionLifecycleEvent]] = defaultdict(list)
    for event in marked_events:
        events_by_execution[event.action_plan_execution_id].append(event)

    preserved: list[UUID] = []
    fills: list[FillRecord] = []
    unrecoverable_seeds: list[UUID] = []
    for execution_id, events in events_by_execution.items():
        execution = events[0].action_plan_execution
        incomplete = [event for event in events if not event_snapshot_is_valid(event.metadata_safe)]
        if not incomplete:
            preserved.extend(event.id for event in events)
            continue
        if is_valid_window(execution.start_at, execution.end_at):
            preserved.extend(event.id for event in events if event not in incomplete)
            for event in incomplete:
                fills.append(
                    FillRecord(
                        event_id=event.id,
                        execution_id=execution.id,
                        start_at=execution.start_at.isoformat(),
                        end_at=execution.end_at.isoformat(),
                    )
                )
            continue
        unrecoverable_seeds.append(execution_id)

    graphs = _merge_graphs(
        [_expand_from_executions({seed}) for seed in unrecoverable_seeds]
    )
    for graph in graphs:
        graph.reason = "unrecoverable marked_done snapshot"

    combined_objects: dict[str, set[UUID]] = defaultdict(set)
    for graph in graphs:
        for model, ids in _collect_objects(graph).items():
            combined_objects[model] |= ids

    deleted_event_ids = combined_objects.get(MODEL_LIFECYCLE_EVENT, set())
    deleted_execution_ids = combined_objects.get(MODEL_EXECUTION, set())
    fill_ids = {record.event_id for record in fills}

    dashboard_after = _dashboard_population(
        exclude_event_ids=deleted_event_ids,
        exclude_execution_ids=deleted_execution_ids,
        filled_event_ids=fill_ids,
    )

    if not dry_run:
        with transaction.atomic():
            fill_by_event = {record.event_id: record for record in fills}
            if fill_by_event:
                for event in ActionPlanExecutionLifecycleEvent.objects.filter(
                    id__in=fill_by_event
                ).select_related("action_plan_execution"):
                    _merge_snapshot(event, event.action_plan_execution)
            _apply_deletes(combined_objects)
        dashboard_after = _dashboard_population()

    return RepairReport(
        dry_run=dry_run,
        preserved_event_ids=tuple(sorted(preserved, key=str)),
        filled=tuple(fills),
        deleted_objects=_flatten_objects(combined_objects),
        graphs=tuple(graphs),
        dashboard_before=dashboard_before,
        dashboard_after=dashboard_after,
    )


def format_repair_report(report: RepairReport) -> str:
    lines: list[str] = []
    mode = "Dry run — no database changes" if report.dry_run else "Applied"
    lines.append(mode)
    lines.append("")
    lines.append("Dashboard population:")
    lines.append(
        "  before: "
        f"marked_done_classifiable={report.dashboard_before.marked_done_classifiable} "
        f"marked_done_excluded={report.dashboard_before.marked_done_excluded} "
        f"overrun_live={report.dashboard_before.overrun_live}"
    )
    lines.append(
        "  after:  "
        f"marked_done_classifiable={report.dashboard_after.marked_done_classifiable} "
        f"marked_done_excluded={report.dashboard_after.marked_done_excluded} "
        f"overrun_live={report.dashboard_after.overrun_live}"
    )
    lines.append("")
    lines.append(f"preserved marked_done: {len(report.preserved_event_ids)}")
    for event_id in report.preserved_event_ids:
        lines.append(f"  {event_id}")
    lines.append(f"filled_from_execution: {len(report.filled)}")
    for record in report.filled:
        lines.append(
            f"  event={record.event_id} execution={record.execution_id} "
            f"start_at={record.start_at} end_at={record.end_at}"
        )
    lines.append(f"deletion graphs: {len(report.graphs)}")
    for index, graph in enumerate(report.graphs, start=1):
        seeds = ",".join(str(item) for item in graph.seed_execution_ids)
        lines.append(f"  graph {index} reason={graph.reason} seed_executions={seeds}")
        for model, object_id in _flatten_objects(_collect_objects(graph)):
            lines.append(f"    {model} {object_id}")
    lines.append(f"deleted objects (union): {len(report.deleted_objects)}")
    for model, object_id in report.deleted_objects:
        lines.append(f"  {model} {object_id}")
    return "\n".join(lines) + "\n"
