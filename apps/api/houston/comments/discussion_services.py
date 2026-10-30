from django.db import transaction
from django.utils import timezone

from houston.action_plans.execution_update import update_action_plan_execution
from houston.action_plans.models import ActionPlanExecution
from houston.chat.exceptions import ChatNotFoundError, ChatPermissionError
from houston.comments.models import Comment, CommentAcknowledgement, PlanDiscussionPreference
from houston.comments.permissions import can_resolve_execution_comment
from houston.comments.selectors import get_action_plan_execution_for_comments


def require_execution(*, membership, execution_id):
    execution = get_action_plan_execution_for_comments(
        membership=membership, execution_id=execution_id
    )
    if execution is None:
        raise ChatNotFoundError()
    return execution


@transaction.atomic
def update_discussion_preference(
    *, membership, execution_id, mode=None, seen=False, seen_through=None
):
    execution = require_execution(membership=membership, execution_id=execution_id)
    pref, _ = PlanDiscussionPreference.objects.get_or_create(
        execution=execution, membership=membership
    )
    pref = PlanDiscussionPreference.objects.select_for_update().get(id=pref.id)
    changes = {}
    if mode is not None:
        changes["notification_mode"] = mode
    if seen and seen_through is not None:
        latest = (
            Comment.objects.filter(
                action_plan_execution=execution, created_at__lte=min(seen_through, timezone.now())
            )
            .order_by("-created_at")
            .first()
        )
        if latest and (pref.seen_at is None or latest.created_at > pref.seen_at):
            changes["seen_at"] = latest.created_at
    PlanDiscussionPreference.objects.filter(id=pref.id).update(**changes)


def require_comment(*, membership, comment_id):
    comment = Comment.objects.filter(
        id=comment_id,
        establishment_id=membership.establishment_id,
        action_plan_execution__isnull=False,
    ).first()
    if comment is None:
        raise ChatNotFoundError()
    execution = require_execution(
        membership=membership, execution_id=comment.action_plan_execution_id
    )
    return comment, execution


@transaction.atomic
def update_comment_tool(*, membership, comment_id, operation, active):
    comment, execution = require_comment(membership=membership, comment_id=comment_id)
    if operation == "pin":
        if not can_resolve_execution_comment(
            membership=membership, execution=execution, comment=comment
        ):
            raise ChatPermissionError()
        Comment.objects.filter(id=comment.id).update(pinned_at=timezone.now() if active else None)
    else:
        if active:
            CommentAcknowledgement.objects.get_or_create(comment=comment, membership=membership)
        else:
            CommentAcknowledgement.objects.filter(comment=comment, membership=membership).delete()

    from houston.comments.services import _schedule_comment_invalidation

    _schedule_comment_invalidation(
        establishment_id=membership.establishment_id,
        reason="comment.execution.updated",
        entity_id=execution.id,
    )


@transaction.atomic
def task_from_comment(*, membership, comment_id, title, assigned_membership_id, deadline_at):
    comment, execution = require_comment(membership=membership, comment_id=comment_id)
    # Same lock order and same execution update owner as the regular edit form.
    execution = ActionPlanExecution.objects.select_for_update().get(id=execution.id)
    comment = Comment.objects.select_for_update().get(id=comment.id)
    if comment.created_task_id:
        return comment.created_task_id
    tasks = list(execution.task_executions.select_related("execution_team").order_by("position"))
    pending = [
        dict(
            id=t.id,
            task=t.task,
            description=t.description,
            business_unit_id=t.execution_team.business_unit_id,
            position=t.position,
            assigned_membership_id=t.assigned_membership_id,
            deadline_at=t.deadline_at,
        )
        for t in tasks
        if t.status == "pending"
    ]
    position = max((t.position for t in tasks), default=0) + 1
    business_unit_id = execution.pilot_business_unit_id
    if assigned_membership_id:
        assignment = (
            execution.assignees.filter(membership_id=assigned_membership_id)
            .select_related("execution_team")
            .first()
        )
        if assignment:
            business_unit_id = assignment.execution_team.business_unit_id
    pending.append(
        dict(
            task=title,
            description=comment.body,
            business_unit_id=business_unit_id,
            position=position,
            assigned_membership_id=assigned_membership_id,
            deadline_at=deadline_at,
        )
    )
    update_action_plan_execution(
        execution_id=execution.id,
        actor=membership,
        expected_updated_at=execution.updated_at,
        pending_tasks=pending,
    )
    task = execution.task_executions.get(position=position)
    comment.created_task = task
    comment.save(update_fields=["created_task"])
    from houston.comments.services import _schedule_comment_invalidation

    _schedule_comment_invalidation(
        establishment_id=membership.establishment_id,
        reason="comment.execution.updated",
        entity_id=execution.id,
    )
    return task.id
