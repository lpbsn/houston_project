"""Bounded, source-linked evidence for the sealed investigation dossier.

No live reads during reasoning, no private-chat mining, no new business truth.
Candidate summaries retain details of aggregated observations without copying raw
observations. Operational discussions are testimony, not validated decisions.
"""

from __future__ import annotations

from hashlib import sha256

from django.apps import apps
from django.db.models import Exists, OuterRef

from houston.action_plans.models import (
    ActionPlanAssignee,
    ActionPlanExecutionReview,
    ActionPlanExecutionTask,
)
from houston.brain.collection import DossierRow
from houston.brain.configuration import canonical_json
from houston.comments.models import Comment
from houston.signals.models import CandidateSignal, SignalSourceObservation

EVIDENCE_CATEGORY = "terrain_evidence"
EVIDENCE_FAMILIES = (
    "observation_fact",
    "execution_task",
    "plan_discussion",
    "execution_review",
    "assignment",
)


def _iso(value):
    return value.isoformat() if value is not None else None


def _id(value):
    return str(value) if value is not None else None


def _actor(member):
    if member is None:
        return None
    # Do not use email/username as a fallback in provider context.
    return {
        "membership_id": str(member.id),
        "name": member.user.get_full_name().strip() or "Membre",
    }


def _bounded(run, query, ceiling):
    total = run(query.count)
    rows = run(lambda: list(query.order_by("-created_at", "-id")[:ceiling]))
    return rows, {
        "complete": total == len(rows),
        "total": total,
        "captured": len(rows),
        "omitted": max(0, total - len(rows)),
    }


def _row(kind, obj, payload):
    content = {
        "schema_version": "terrain_evidence_v1",
        "kind": kind,
        "source_id": str(obj.id),
        "created_at": _iso(obj.created_at),
        "source_updated_at": _iso(obj.updated_at),
        **payload,
    }
    # The same source does not acquire a new version just because it is read again.
    versioned = {key: value for key, value in content.items() if key != "as_of"}
    content["source_version"] = sha256(canonical_json(versioned).encode()).hexdigest()
    return DossierRow(
        EVIDENCE_CATEGORY, f"evidence:{kind}:{obj.id}", "source_detail", content, "terrain_evidence"
    )


def collect_terrain_evidence(*, establishment_id, capture_at, ceiling, run):
    """Each family is independently bounded; omissions are explicit in coverage.

    Called inside capture's REPEATABLE READ transaction. All relationships are
    scoped to this establishment, including inconsistent imported relationships.
    The Brain admission/read boundary remains owner/director only.
    """
    rows, coverage = [], {}
    candidates, coverage["observation_fact"] = _bounded(
        run,
        CandidateSignal.objects.filter(
            establishment_id=establishment_id,
            observation__establishment_id=establishment_id,
            observation__submitted_by_membership__establishment_id=establishment_id,
            observation__submitted_at__lte=capture_at,
            result_signal__establishment_id=establishment_id,
            created_at__lte=capture_at,
            outcome__in=[
                CandidateSignal.Outcome.CREATED_SIGNAL,
                CandidateSignal.Outcome.AGGREGATED_SIGNAL,
            ],
        )
        .select_related("observation__submitted_by_membership__user")
        .defer("observation__raw_text"),
        ceiling,
    )
    summarized = CandidateSignal.objects.filter(
        observation_id=OuterRef("observation_id"),
        establishment_id=establishment_id,
        result_signal__establishment_id=establishment_id,
        created_at__lte=capture_at,
        outcome__in=[
            CandidateSignal.Outcome.CREATED_SIGNAL,
            CandidateSignal.Outcome.AGGREGATED_SIGNAL,
        ],
    ).exclude(structured_summary="")
    unrepresented = run(
        lambda: (
            SignalSourceObservation.objects.filter(
                signal__establishment_id=establishment_id,
                observation__establishment_id=establishment_id,
                observation__submitted_at__lte=capture_at,
                created_at__lte=capture_at,
            )
            .filter(~Exists(summarized))
            .values("observation_id")
            .distinct()
            .count()
        )
    )
    coverage["observation_fact"]["observations_without_summary"] = unrepresented
    if unrepresented:
        coverage["observation_fact"]["complete"] = False
    handoffs = _chat_handoffs(
        run, establishment_id, [c.observation_id for c in candidates], capture_at
    )
    for candidate in candidates:
        observation = candidate.observation
        handoff = handoffs.get(observation.id)
        rows.append(
            _row(
                "observation_fact",
                candidate,
                {
                    "title": candidate.title,
                    "text": candidate.structured_summary,
                    "signal_id": str(candidate.result_signal_id),
                    "observation_id": str(observation.id),
                    # Several candidates from one observation are not independent reports.
                    "event_key": f"observation:{observation.id}",
                    "reported_at": _iso(observation.submitted_at),
                    "occurred_at": None,
                    "occurrence_note": (
                        "Date de fait non structurée ; "
                        "ne pas utiliser la date de saisie comme date du fait."
                    ),
                    "author": handoff["author"]
                    if handoff
                    else _actor(observation.submitted_by_membership),
                    "shared_by": _actor(observation.submitted_by_membership) if handoff else None,
                    "handoff": handoff,
                    "source_schema_version": candidate.schema_version,
                    "signal_kind": candidate.signal_kind,
                    "information_type": candidate.information_type,
                    "location_text": candidate.location_text,
                    "epistemic_status": "reported_fact_ai_structured",
                    "media_interpreted": False,
                },
            )
        )

    tasks, coverage["execution_task"] = _bounded(
        run,
        ActionPlanExecutionTask.objects.filter(
            action_plan_execution__establishment_id=establishment_id,
            execution_team__business_unit__establishment_id=establishment_id,
            created_at__lte=capture_at,
        ).select_related("assigned_membership__user", "execution_team__business_unit"),
        ceiling,
    )
    task_links = _task_handoffs(run, establishment_id, [t.id for t in tasks], capture_at)
    for task in tasks:
        member = task.assigned_membership
        author = _actor(member) if member and member.establishment_id == establishment_id else None
        rows.append(
            _row(
                "execution_task",
                task,
                {
                    "title": task.task,
                    "text": task.description,
                    "execution_id": str(task.action_plan_execution_id),
                    "event_key": f"task:{task.id}",
                    "position": task.position,
                    "pole": task.execution_team.business_unit.specific_name,
                    "assigned_to": author,
                    "status_at_capture": task.status,
                    "as_of": _iso(capture_at),
                    "deadline_at": _iso(task.deadline_at),
                    "completed_at": _iso(task.completed_at),
                    "skipped_at": _iso(task.skipped_at),
                    "skipped_reason": task.skipped_reason,
                    "observation_created_at": _iso(task.observation_created_at),
                    "source_comment_id": task_links.get(task.id),
                    "epistemic_status": "recorded_execution_state_not_kpi_result",
                },
            )
        )

    comments, coverage["plan_discussion"] = _bounded(
        run,
        Comment.objects.filter(
            establishment_id=establishment_id,
            action_plan_execution__establishment_id=establishment_id,
            author_membership__establishment_id=establishment_id,
            signal__isnull=True,
            created_at__lte=capture_at,
        ).select_related("author_membership__user"),
        ceiling,
    )
    # PR #359 is independently deployable: inspect only its two known fields.
    comment_fields = {field.name for field in Comment._meta.get_fields()}
    for comment in comments:
        rows.append(
            _row(
                "plan_discussion",
                comment,
                {
                    "title": "Échange dans un plan d’action",
                    "text": comment.body,
                    "execution_id": str(comment.action_plan_execution_id),
                    "event_key": f"comment:{comment.id}",
                    "parent_comment_id": _id(comment.parent_comment_id),
                    "author": _actor(comment.author_membership),
                    "resolved_at": _iso(comment.resolved_at),
                    "pinned_at": _iso(comment.pinned_at) if "pinned_at" in comment_fields else None,
                    "created_task_id": _id(comment.created_task_id)
                    if "created_task" in comment_fields
                    else None,
                    "epistemic_status": "reported_discussion_not_validated_decision",
                },
            )
        )

    reviews, coverage["execution_review"] = _bounded(
        run,
        ActionPlanExecutionReview.objects.filter(
            action_plan_execution__establishment_id=establishment_id,
            reviewer_membership__establishment_id=establishment_id,
            reviewed_at__lte=capture_at,
            created_at__lte=capture_at,
        ).select_related("reviewer_membership__user"),
        ceiling,
    )
    for review in reviews:
        rows.append(
            _row(
                "execution_review",
                review,
                {
                    "title": "Évaluation de la réalisation",
                    "text": review.comment,
                    "execution_id": str(review.action_plan_execution_id),
                    "event_key": f"review:{review.id}",
                    "author": _actor(review.reviewer_membership),
                    "stars": review.stars,
                    "reviewed_at": _iso(review.reviewed_at),
                    "active_at_capture": review.is_active,
                    "epistemic_status": "human_execution_review_not_measured_business_effect",
                },
            )
        )

    assignments, coverage["assignment"] = _bounded(
        run,
        ActionPlanAssignee.objects.filter(
            action_plan_execution__establishment_id=establishment_id,
            membership__establishment_id=establishment_id,
            created_at__lte=capture_at,
        ).select_related("membership__user"),
        ceiling,
    )
    for assignment in assignments:
        rows.append(
            _row(
                "assignment",
                assignment,
                {
                    "title": "Responsabilité dans le plan",
                    "execution_id": str(assignment.action_plan_execution_id),
                    "event_key": f"assignment:{assignment.id}",
                    "assigned_to": _actor(assignment.membership),
                    "start_at": _iso(assignment.start_at),
                    "end_at": _iso(assignment.end_at),
                    "as_of": _iso(capture_at),
                    "epistemic_status": "assignment_at_capture",
                },
            )
        )
    return rows, coverage


def _chat_handoffs(run, establishment_id, observation_ids, capture_at):
    """PR #359 provenance only; never query ChatMessage/ChatConversation contents."""
    try:
        model = apps.get_model("chat", "ChatObservationSource")
    except LookupError:
        return {}
    if not observation_ids:
        return {}
    sources = run(
        lambda: list(
            model.objects.filter(
                observation_id__in=observation_ids,
                observation__establishment_id=establishment_id,
                source_author__establishment_id=establishment_id,
                created_at__lte=capture_at,
            ).select_related("source_author__user")
        )
    )
    # OneToOne(observation): cardinality <= number of captured observations.
    return {
        source.observation_id: {
            "message_id": str(source.source_message_id),
            "reported_at": _iso(source.source_created_at),
            "author": _actor(source.source_author),
            "note": (
                "Contenu explicitement partagé comme observation ; conversation privée non lue."
            ),
        }
        for source in sources
    }


def _task_handoffs(run, establishment_id, task_ids, capture_at):
    if not task_ids or "created_task" not in {f.name for f in Comment._meta.get_fields()}:
        return {}
    links = run(
        lambda: list(
            Comment.objects.filter(
                establishment_id=establishment_id,
                action_plan_execution__establishment_id=establishment_id,
                created_task_id__in=task_ids,
                created_at__lte=capture_at,
            ).values_list("created_task_id", "id")
        )
    )
    # PR #359 makes created_task OneToOne, so this fan-out is bounded.
    return {task_id: str(comment_id) for task_id, comment_id in links}
