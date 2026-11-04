"""Capture record decisions once. Frozen Brain dossiers never reread mutable state."""

from django.db.models import Prefetch

from houston.accounts.display import membership_display_name
from houston.signals.models import SignalExecutionLink, SignalRecordEvent


def record_prefetches(capture_at):
    from houston.brain.models import BrainObjectiveRecord

    return (
        Prefetch(
            "objective_links",
            queryset=BrainObjectiveRecord.objects.filter(created_at__lte=capture_at).order_by("id")[
                :101
            ],
            to_attr="brain_objective_links",
        ),
        Prefetch(
            "record_events",
            queryset=SignalRecordEvent.objects.filter(created_at__lte=capture_at)
            .select_related("actor__user")
            .order_by("-created_at", "-id")[:101],
            to_attr="brain_record_events",
        ),
        Prefetch(
            "work_links",
            queryset=SignalExecutionLink.objects.filter(created_at__lte=capture_at).order_by(
                "created_at", "id"
            )[:101],
            to_attr="brain_work_links",
        ),
    )


def record_context(signal):
    events = getattr(signal, "brain_record_events", [])
    links = getattr(signal, "brain_work_links", [])
    return {
        "record_kind": signal.record_kind,
        "is_project": signal.is_project,
        "is_milestone": signal.is_milestone,
        "parent_project_id": str(signal.parent_project_id) if signal.parent_project_id else None,
        "planning_predecessor_id": str(signal.planning_predecessor_id)
        if signal.planning_predecessor_id
        else None,
        "planned_start_on": signal.planned_start_on.isoformat()
        if signal.planned_start_on
        else None,
        "merged_into_id": str(signal.merged_into_id) if signal.merged_into_id else None,
        "operational_status": signal.status,
        "owner": {
            "id": str(signal.owner_membership_id),
            "name": membership_display_name(signal.owner_membership),
        }
        if signal.owner_membership_id
        else None,
        "deadline": signal.due_on.isoformat() if signal.due_on else None,
        "review_requested_at": signal.review_requested_at.isoformat()
        if signal.review_requested_at
        else None,
        "closure_reason": signal.closure_reason,
        "blocked_reason": signal.blocked_reason,
        "waiting_for_id": str(signal.waiting_for_membership_id)
        if signal.waiting_for_membership_id
        else None,
        "objective_ids": [
            str(link.objective_id) for link in getattr(signal, "brain_objective_links", [])[:100]
        ],
        "execution_ids": [str(link.execution_id) for link in links[:100]],
        "events": [
            {
                "id": str(event.id),
                "kind": event.kind,
                "at": event.created_at.isoformat(),
                "actor": membership_display_name(event.actor),
                "changes": event.changes,
            }
            for event in events[:100]
        ],
        "coverage": {
            "events_complete": len(events) <= 100,
            "links_complete": len(links) <= 100,
            "objectives_complete": len(getattr(signal, "brain_objective_links", [])) <= 100,
        },
        "interpretation": (
            "A project is not a field observation. Work completed, problem resolved "
            "and KPI achieved are separate facts. Count shared execution IDs once. "
            "Merged records preserve history, not additional occurrences."
        ),
    }
