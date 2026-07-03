from __future__ import annotations

from dataclasses import dataclass, replace

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
from houston.actions.models import Action, ActionAssignee
from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTaskExecution,
    ChecklistTaskTemplate,
    ChecklistTemplate,
)
from houston.comments.models import Comment, CommentMention
from houston.core.dev_guards import assert_local_dev_environment
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
    action_assignees: int = 0
    actions: int = 0
    checklist_task_executions: int = 0
    checklist_executions: int = 0
    checklist_assignments: int = 0
    checklist_task_templates: int = 0
    checklist_templates: int = 0
    signals: int = 0
    temporary_uploads: int = 0
    media_files: int = 0


@dataclass(frozen=True)
class OperationalCleanupResult:
    counts: OperationalCleanupCounts
    dry_run: bool


def _delete_queryset_count(queryset) -> int:
    deleted_count, _ = queryset.delete()
    return deleted_count


def _delete_comments() -> int:
    deleted_total = 0
    while Comment.objects.exists():
        leaf_ids = list(
            Comment.objects.annotate(reply_count=Count("replies"))
            .filter(reply_count=0)
            .values_list("id", flat=True)[:1000]
        )
        if not leaf_ids:
            break
        deleted_total += _delete_queryset_count(Comment.objects.filter(id__in=leaf_ids))
    return deleted_total


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


def _count_dry_run() -> OperationalCleanupCounts:
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
        action_assignees=ActionAssignee.objects.count(),
        actions=Action.objects.count(),
        checklist_task_executions=ChecklistTaskExecution.objects.count(),
        checklist_executions=ChecklistExecution.objects.count(),
        checklist_assignments=ChecklistAssignment.objects.count(),
        checklist_task_templates=ChecklistTaskTemplate.objects.count(),
        checklist_templates=ChecklistTemplate.objects.count(),
        signals=Signal.objects.count(),
        temporary_uploads=TemporaryUpload.objects.count(),
        media_files=media_file_count,
    )


@transaction.atomic
def _delete_operational_data() -> tuple[OperationalCleanupCounts, list[str]]:
    storage_keys_to_delete: list[str] = []
    counts = OperationalCleanupCounts()

    counts = replace(counts, notifications=_delete_queryset_count(Notification.objects.all()))
    counts = replace(counts, comment_mentions=_delete_queryset_count(CommentMention.objects.all()))
    counts = replace(counts, comments=_delete_comments())

    Observation.objects.update(
        checklist_execution_id=None,
        checklist_task_execution_id=None,
        action_plan_execution_id=None,
        action_plan_execution_task_id=None,
    )

    counts = replace(
        counts,
        signal_source_observations=_delete_queryset_count(SignalSourceObservation.objects.all()),
        candidate_signals=_delete_queryset_count(CandidateSignal.objects.all()),
    )

    storage_keys_to_delete.extend(_collect_observation_media_storage_keys())
    counts = replace(
        counts,
        observation_media=_delete_queryset_count(ObservationMedia.objects.all()),
    )
    counts = replace(
        counts,
        observation_processing=_delete_queryset_count(ObservationProcessing.objects.all()),
        observations=_delete_queryset_count(Observation.objects.all()),
    )

    counts = replace(
        counts,
        action_plan_execution_tasks=_delete_queryset_count(ActionPlanExecutionTask.objects.all()),
        action_plan_execution_teams=_delete_queryset_count(ActionPlanExecutionTeam.objects.all()),
        action_plan_assignees=_delete_queryset_count(ActionPlanAssignee.objects.all()),
        action_plan_executions=_delete_queryset_count(ActionPlanExecution.objects.all()),
        action_plan_schedule_assignees=_delete_queryset_count(
            ActionPlanScheduleAssignee.objects.all()
        ),
        action_plan_schedules=_delete_queryset_count(ActionPlanSchedule.objects.all()),
        action_plan_tasks=_delete_queryset_count(ActionPlanTask.objects.all()),
        action_plans=_delete_queryset_count(ActionPlan.objects.all()),
    )

    counts = replace(
        counts,
        action_assignees=_delete_queryset_count(ActionAssignee.objects.all()),
        actions=_delete_queryset_count(Action.objects.all()),
    )

    counts = replace(
        counts,
        checklist_task_executions=_delete_queryset_count(ChecklistTaskExecution.objects.all()),
        checklist_executions=_delete_queryset_count(ChecklistExecution.objects.all()),
        checklist_assignments=_delete_queryset_count(ChecklistAssignment.objects.all()),
        checklist_task_templates=_delete_queryset_count(ChecklistTaskTemplate.objects.all()),
        checklist_templates=_delete_queryset_count(ChecklistTemplate.objects.all()),
    )

    counts = replace(counts, signals=_delete_queryset_count(Signal.objects.all()))

    storage_keys_to_delete.extend(_collect_temporary_upload_storage_keys())
    counts = replace(
        counts,
        temporary_uploads=_delete_queryset_count(TemporaryUpload.objects.all()),
        media_files=len(storage_keys_to_delete),
    )

    return counts, storage_keys_to_delete


def clean_operational_test_data(*, dry_run: bool = False) -> OperationalCleanupResult:
    assert_local_dev_environment()

    if dry_run:
        return OperationalCleanupResult(counts=_count_dry_run(), dry_run=True)

    counts, storage_keys_to_delete = _delete_operational_data()
    schedule_storage_files_deletion(storage_keys=storage_keys_to_delete)
    return OperationalCleanupResult(counts=counts, dry_run=False)
