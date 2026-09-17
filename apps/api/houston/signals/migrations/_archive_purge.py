"""Historical-model helpers for the Signal archive cutover migration.

Imported only from ``0019_remove_signal_archive``. Operates on ``apps.get_model``.
The leading underscore keeps Django from treating this module as a migration.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from django.db.models import Count, Q


def json_mentions_any_uuid(value: Any, uuid_strings: frozenset[str]) -> bool:
    if value is None:
        return False
    if isinstance(value, uuid.UUID):
        return str(value) in uuid_strings
    if isinstance(value, str):
        return value in uuid_strings
    if isinstance(value, dict):
        return any(json_mentions_any_uuid(item, uuid_strings) for item in value.values()) or any(
            str(key) in uuid_strings for key in value
        )
    if isinstance(value, (list, tuple)):
        return any(json_mentions_any_uuid(item, uuid_strings) for item in value)
    return False


def strip_uuids_from_json(value: Any, uuid_strings: frozenset[str]) -> Any:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return None if str(value) in uuid_strings else value
    if isinstance(value, str):
        return None if value in uuid_strings else value
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if str(key) in uuid_strings:
                continue
            stripped = strip_uuids_from_json(item, uuid_strings)
            if stripped is None and (isinstance(item, str) or isinstance(item, uuid.UUID)):
                continue
            cleaned[key] = stripped
        return cleaned
    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            if isinstance(item, (str, uuid.UUID)) and str(item) in uuid_strings:
                continue
            cleaned_list.append(strip_uuids_from_json(item, uuid_strings))
        return cleaned_list
    if isinstance(value, tuple):
        return tuple(strip_uuids_from_json(list(value), uuid_strings))
    return value


def _uuid_strings(ids) -> frozenset[str]:
    return frozenset(str(item) for item in ids)


def _rewrite_json_field(row, field_name: str, uuid_strings: frozenset[str]) -> bool:
    current = getattr(row, field_name) or {}
    if not json_mentions_any_uuid(current, uuid_strings):
        return False
    setattr(row, field_name, strip_uuids_from_json(current, uuid_strings) or {})
    row.save(update_fields=[field_name, "updated_at"] if hasattr(row, "updated_at") else [field_name])
    return True


def _delete_comment_trees(*, Comment, filter_q: Q) -> None:
    while True:
        leaf_ids = list(
            Comment.objects.filter(filter_q)
            .annotate(reply_count=Count("replies"))
            .filter(reply_count=0)
            .values_list("id", flat=True)[:500]
        )
        if not leaf_ids:
            remaining = Comment.objects.filter(filter_q)
            if remaining.exists():
                raise RuntimeError("Unable to delete comments due to parent_comment PROTECT.")
            return
        Comment.objects.filter(id__in=leaf_ids).delete()


def _delete_point_transactions_respecting_protect(*, PointTransaction, filter_q: Q) -> None:
    tx_ids = set(PointTransaction.objects.filter(filter_q).values_list("id", flat=True))
    if not tx_ids:
        return
    extra = set(
        PointTransaction.objects.filter(reversed_transaction_id__in=tx_ids).values_list(
            "id",
            flat=True,
        )
    )
    tx_ids |= extra
    while tx_ids:
        referenced = set(
            PointTransaction.objects.filter(reversed_transaction_id__in=tx_ids).values_list(
                "reversed_transaction_id",
                flat=True,
            )
        )
        leaves = tx_ids - referenced
        if not leaves:
            raise RuntimeError("Unable to delete PointTransaction rows due to reversed_transaction PROTECT.")
        PointTransaction.objects.filter(id__in=leaves).delete()
        tx_ids -= leaves


def _hard_delete_executions_for_signals(apps, signal_ids: list) -> None:
    if not signal_ids:
        return
    ActionPlanExecution = apps.get_model("action_plans", "ActionPlanExecution")
    Observation = apps.get_model("observations", "Observation")
    Comment = apps.get_model("comments", "Comment")
    Notification = apps.get_model("notifications", "Notification")

    execution_ids = list(
        ActionPlanExecution.objects.filter(source_signal_id__in=signal_ids).values_list(
            "id",
            flat=True,
        )
    )
    if not execution_ids:
        return

    Observation.objects.filter(action_plan_execution_id__in=execution_ids).update(
        action_plan_execution_id=None,
    )
    task_model = apps.get_model("action_plans", "ActionPlanExecutionTask")
    task_ids = list(
        task_model.objects.filter(action_plan_execution_id__in=execution_ids).values_list(
            "id",
            flat=True,
        )
    )
    if task_ids:
        Observation.objects.filter(action_plan_execution_task_id__in=task_ids).update(
            action_plan_execution_task_id=None,
        )

    comment_ids = list(
        Comment.objects.filter(action_plan_execution_id__in=execution_ids).values_list(
            "id",
            flat=True,
        )
    )
    notification_q = Q(subject_type="action_plan_execution", subject_id__in=execution_ids)
    if comment_ids:
        notification_q |= Q(subject_type="comment", subject_id__in=comment_ids)
    Notification.objects.filter(notification_q).delete()
    _delete_comment_trees(
        Comment=Comment,
        filter_q=Q(action_plan_execution_id__in=execution_ids),
    )
    ActionPlanExecution.objects.filter(id__in=execution_ids).delete()


def _scan_json_columns_for_uuids(apps, uuid_strings: frozenset[str]) -> list[str]:
    hits: list[str] = []
    scans = (
        ("signals", "CandidateSignal", "resolution_audit"),
        ("signals", "SignalLifecycleEvent", "metadata_safe"),
        ("action_plans", "ActionPlanExecutionLifecycleEvent", "metadata_safe"),
        ("analytics", "PatternLifecycleEvent", "metadata_safe"),
        ("gamification", "PointTransaction", "metadata_safe"),
        ("action_plans", "ActionPlanPlanningSubmission", "result_snapshot"),
        ("action_plans", "ActionPlanPlanningOutboxEntry", "payload"),
    )
    for app_label, model_name, field_name in scans:
        model = apps.get_model(app_label, model_name)
        for row in model.objects.iterator():
            if json_mentions_any_uuid(getattr(row, field_name), uuid_strings):
                hits.append(f"{app_label}.{model_name}.{field_name}:{row.pk}")
    return hits


def _strip_json_columns(apps, uuid_strings: frozenset[str]) -> None:
    scans = (
        ("signals", "CandidateSignal", "resolution_audit"),
        ("signals", "SignalLifecycleEvent", "metadata_safe"),
        ("action_plans", "ActionPlanExecutionLifecycleEvent", "metadata_safe"),
        ("analytics", "PatternLifecycleEvent", "metadata_safe"),
        ("gamification", "PointTransaction", "metadata_safe"),
        ("action_plans", "ActionPlanPlanningSubmission", "result_snapshot"),
        ("action_plans", "ActionPlanPlanningOutboxEntry", "payload"),
    )
    for app_label, model_name, field_name in scans:
        model = apps.get_model(app_label, model_name)
        for row in model.objects.iterator():
            _rewrite_json_field(row, field_name, uuid_strings)


def purge_archived_signals(apps, schema_editor) -> None:
    Signal = apps.get_model("signals", "Signal")
    SignalSourceObservation = apps.get_model("signals", "SignalSourceObservation")
    SignalLifecycleEvent = apps.get_model("signals", "SignalLifecycleEvent")
    CandidateSignal = apps.get_model("signals", "CandidateSignal")
    SignalResolutionRequest = apps.get_model("signals", "SignalResolutionRequest")
    Comment = apps.get_model("comments", "Comment")
    Notification = apps.get_model("notifications", "Notification")
    PointTransaction = apps.get_model("gamification", "PointTransaction")
    ActionPlanExecution = apps.get_model("action_plans", "ActionPlanExecution")

    archived_ids = list(
        Signal.objects.filter(status="archived").values_list("id", flat=True)
    )
    if not archived_ids:
        return
    archived_set = set(archived_ids)
    uuid_strings = _uuid_strings(archived_ids)

    sources = list(
        Signal.objects.filter(id__in=archived_ids, merged_into_id__isnull=False).values(
            "id",
            "merged_into_id",
            "created_at",
            "first_action_plan_associated_at",
        )
    )
    living_survivor_ids: set = set()
    for source in sources:
        target_id = source["merged_into_id"]
        if target_id in archived_set:
            continue
        living_survivor_ids.add(target_id)
        source_obs_ids = list(
            SignalSourceObservation.objects.filter(signal_id=source["id"]).values_list(
                "observation_id",
                flat=True,
            )
        )
        if source_obs_ids:
            SignalSourceObservation.objects.filter(
                signal_id=target_id,
                observation_id__in=source_obs_ids,
                link_type="merged_from",
            ).delete()
        qualify_created = SignalLifecycleEvent.objects.filter(
            signal_id=target_id,
            event_type="signal.created",
        )
        for event in qualify_created:
            metadata = event.metadata_safe or {}
            if metadata.get("origin") != "qualify_merge":
                continue
            if (
                str(metadata.get("source_signal_id") or "") == str(source["id"])
                or json_mentions_any_uuid(metadata, frozenset({str(source["id"])}))
            ):
                event.delete()

    for survivor_id in living_survivor_ids:
        survivor = Signal.objects.filter(id=survivor_id).first()
        if survivor is None:
            continue
        remaining_created = list(
            SignalLifecycleEvent.objects.filter(
                signal_id=survivor_id,
                event_type="signal.created",
            ).values_list("occurred_at", flat=True)
        )
        if remaining_created:
            survivor.created_at = min(remaining_created)
        execution_times = list(
            ActionPlanExecution.objects.filter(source_signal_id=survivor_id)
            .exclude(source_signal_id__in=archived_ids)
            .values_list("created_at", flat=True)
        )
        survivor.first_action_plan_associated_at = (
            min(execution_times) if execution_times else None
        )
        survivor.save(
            update_fields=["created_at", "first_action_plan_associated_at", "updated_at"]
        )

    _strip_json_columns(apps, uuid_strings)

    _hard_delete_executions_for_signals(apps, archived_ids)

    _delete_comment_trees(Comment=Comment, filter_q=Q(signal_id__in=archived_ids))
    SignalResolutionRequest.objects.filter(signal_id__in=archived_ids).delete()
    Notification.objects.filter(subject_type="signal", subject_id__in=archived_ids).delete()
    _delete_point_transactions_respecting_protect(
        PointTransaction=PointTransaction,
        filter_q=Q(source_type="signal", source_id__in=list(uuid_strings)),
    )
    CandidateSignal.objects.filter(result_signal_id__in=archived_ids).update(result_signal_id=None)
    Signal.objects.filter(id__in=archived_ids).delete()

    leftover = _scan_json_columns_for_uuids(apps, uuid_strings)
    typed_hits = []
    if Notification.objects.filter(subject_type="signal", subject_id__in=archived_ids).exists():
        typed_hits.append("notifications.Notification.subject_id")
    if PointTransaction.objects.filter(
        source_type="signal",
        source_id__in=list(uuid_strings),
    ).exists():
        typed_hits.append("gamification.PointTransaction.source_id")
    leftover.extend(typed_hits)
    if leftover:
        raise RuntimeError(
            "Archived Signal UUIDs remain after purge: " + ", ".join(leftover[:20])
        )


def noop_reverse(apps, schema_editor) -> None:
    return
