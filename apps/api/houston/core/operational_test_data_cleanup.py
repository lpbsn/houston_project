from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.db.models import Count

from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
    ActionPlanTask,
)
from houston.analytics.cutover import reset_history_reliable_from
from houston.analytics.models import (
    OperationalPattern,
    PatternEstablishmentSighting,
    PatternIssueReport,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.comments.models import Comment, CommentMention
from houston.core.dev_guards import assert_local_dev_environment
from houston.gamification.models import BadgeAward, PointTransaction
from houston.notifications.models import Notification
from houston.observations.media_services import schedule_storage_files_deletion
from houston.observations.models import Observation, ObservationMedia, ObservationProcessing
from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.uploads.models import TemporaryUpload


@dataclass(frozen=True)
class OperationalCleanupCounts:
    notifications: int = 0
    comment_mentions: int = 0
    comments: int = 0
    signal_source_observations: int = 0
    candidate_signals: int = 0
    observation_media: int = 0
    observation_processing: int = 0
    observations: int = 0
    action_plan_execution_tasks: int = 0
    action_plan_execution_teams: int = 0
    action_plan_assignees: int = 0
    action_plan_executions: int = 0
    action_plan_schedule_assignees: int = 0
    action_plan_schedules: int = 0
    action_plan_tasks: int = 0
    action_plans: int = 0
    signals: int = 0
    temporary_uploads: int = 0
    media_files: int = 0
    pattern_issue_reports: int = 0
    pattern_sightings: int = 0
    pattern_lifecycle_events: int = 0
    signal_pattern_assignments: int = 0
    operational_patterns: int = 0
    point_transactions: int = 0
    badge_awards: int = 0


@dataclass(frozen=True)
class OperationalCleanupResult:
    counts: OperationalCleanupCounts
    dry_run: bool
    history_reliable_from: datetime | None = None


def _delete_comments() -> None:
    while Comment.objects.exists():
        leaf_ids = list(
            Comment.objects.annotate(reply_count=Count("replies"))
            .filter(reply_count=0)
            .values_list("id", flat=True)[:1000]
        )
        if not leaf_ids:
            break
        Comment.objects.filter(id__in=leaf_ids).delete()


def _delete_operational_patterns() -> None:
    while OperationalPattern.objects.exists():
        referenced_ids = OperationalPattern.objects.filter(
            merged_into_id__isnull=False,
        ).values_list("merged_into_id", flat=True)
        leaf_ids = list(
            OperationalPattern.objects.exclude(id__in=referenced_ids).values_list("id", flat=True)[
                :1000
            ]
        )
        if not leaf_ids:
            raise RuntimeError("OperationalPattern merged_into dependencies prevent cleanup.")
        OperationalPattern.objects.filter(id__in=leaf_ids).delete()


def _collect_observation_media_storage_keys() -> list[str]:
    storage_keys: list[str] = []
    for media in ObservationMedia.objects.select_related("temporary_upload").iterator():
        upload = media.temporary_upload
        storage_key = media.storage_key or (upload.file.name if upload.file else "")
        if storage_key:
            storage_keys.append(storage_key)
    return storage_keys


def _collect_temporary_upload_storage_keys() -> list[str]:
    storage_keys: list[str] = []
    for upload in TemporaryUpload.objects.iterator():
        if upload.file and upload.file.name:
            storage_keys.append(upload.file.name)
    return storage_keys


def _count_named_model_rows() -> OperationalCleanupCounts:
    media_file_count = ObservationMedia.objects.count() + TemporaryUpload.objects.count()
    return OperationalCleanupCounts(
        notifications=Notification.objects.count(),
        comment_mentions=CommentMention.objects.count(),
        comments=Comment.objects.count(),
        signal_source_observations=SignalSourceObservation.objects.count(),
        candidate_signals=CandidateSignal.objects.count(),
        observation_media=ObservationMedia.objects.count(),
        observation_processing=ObservationProcessing.objects.count(),
        observations=Observation.objects.count(),
        action_plan_execution_tasks=ActionPlanExecutionTask.objects.count(),
        action_plan_execution_teams=ActionPlanExecutionTeam.objects.count(),
        action_plan_assignees=ActionPlanAssignee.objects.count(),
        action_plan_executions=ActionPlanExecution.objects.count(),
        action_plan_schedule_assignees=ActionPlanScheduleAssignee.objects.count(),
        action_plan_schedules=ActionPlanSchedule.objects.count(),
        action_plan_tasks=ActionPlanTask.objects.count(),
        action_plans=ActionPlan.objects.count(),
        signals=Signal.objects.count(),
        temporary_uploads=TemporaryUpload.objects.count(),
        media_files=media_file_count,
        pattern_issue_reports=PatternIssueReport.objects.count(),
        pattern_sightings=PatternEstablishmentSighting.objects.count(),
        pattern_lifecycle_events=PatternLifecycleEvent.objects.count(),
        signal_pattern_assignments=SignalPatternAssignment.objects.count(),
        operational_patterns=OperationalPattern.objects.count(),
        point_transactions=PointTransaction.objects.count(),
        badge_awards=BadgeAward.objects.count(),
    )


@transaction.atomic
def _delete_operational_data() -> tuple[list[str], datetime]:
    storage_keys_to_delete: list[str] = []

    Notification.objects.all().delete()
    CommentMention.objects.all().delete()
    _delete_comments()

    Observation.objects.update(
        action_plan_execution_id=None,
        action_plan_execution_task_id=None,
    )

    SignalSourceObservation.objects.all().delete()
    CandidateSignal.objects.all().delete()

    storage_keys_to_delete.extend(_collect_observation_media_storage_keys())
    ObservationMedia.objects.all().delete()
    ObservationProcessing.objects.all().delete()
    Observation.objects.all().delete()

    ActionPlanExecutionTask.objects.all().delete()
    ActionPlanExecutionTeam.objects.all().delete()
    ActionPlanAssignee.objects.all().delete()
    ActionPlanExecution.objects.all().delete()
    ActionPlanScheduleAssignee.objects.all().delete()
    ActionPlanSchedule.objects.all().delete()
    ActionPlanTask.objects.all().delete()
    ActionPlan.objects.all().delete()

    Signal.objects.all().delete()
    SignalPatternAssignment.objects.all().delete()
    PatternIssueReport.objects.all().delete()
    PatternEstablishmentSighting.objects.all().delete()
    PatternLifecycleEvent.objects.all().delete()
    _delete_operational_patterns()
    PointTransaction.objects.filter(reversed_transaction_id__isnull=False).delete()
    PointTransaction.objects.all().delete()
    BadgeAward.objects.all().delete()

    storage_keys_to_delete.extend(_collect_temporary_upload_storage_keys())
    TemporaryUpload.objects.all().delete()

    history_reliable_from = reset_history_reliable_from()
    return storage_keys_to_delete, history_reliable_from


def clean_operational_test_data(*, dry_run: bool = False) -> OperationalCleanupResult:
    assert_local_dev_environment()

    counts = _count_named_model_rows()
    if dry_run:
        return OperationalCleanupResult(counts=counts, dry_run=True)

    storage_keys_to_delete, history_reliable_from = _delete_operational_data()
    schedule_storage_files_deletion(storage_keys=storage_keys_to_delete)
    return OperationalCleanupResult(
        counts=counts,
        dry_run=False,
        history_reliable_from=history_reliable_from,
    )
