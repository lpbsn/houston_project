from __future__ import annotations

import uuid

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.permissions import (
    action_plan_execution_visible_to_membership,
    is_action_plan_execution_assignee,
)
from houston.comments.models import Comment
from houston.comments.selectors import (
    get_action_plan_execution_for_comments,
    get_signal_for_comments,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES


def can_access_signal_comments(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
) -> bool:
    return get_signal_for_comments(membership=membership, signal_id=signal_id) is not None


def can_access_action_plan_execution_comments(
    *,
    membership: EstablishmentMembership,
    execution_id: uuid.UUID,
) -> bool:
    return (
        get_action_plan_execution_for_comments(
            membership=membership,
            execution_id=execution_id,
        )
        is not None
    )


def is_execution_root_comment(
    *,
    execution: ActionPlanExecution,
    comment: Comment,
) -> bool:
    return (
        comment.signal_id is None
        and comment.parent_comment_id is None
        and comment.action_plan_execution_id == execution.id
        and comment.establishment_id == execution.establishment_id
    )


def can_reply_to_execution_comment(
    *,
    membership: EstablishmentMembership,
    execution: ActionPlanExecution,
    comment: Comment,
) -> bool:
    if not is_execution_root_comment(execution=execution, comment=comment):
        return False
    return can_access_action_plan_execution_comments(
        membership=membership,
        execution_id=execution.id,
    )


def can_resolve_execution_comment(
    *,
    membership: EstablishmentMembership,
    execution: ActionPlanExecution,
    comment: Comment,
) -> bool:
    if not is_execution_root_comment(execution=execution, comment=comment):
        return False
    if comment.establishment_id != membership.establishment_id:
        return False
    if comment.author_membership_id == membership.id:
        return True
    if is_action_plan_execution_assignee(membership, execution):
        return True
    if execution.created_by_id == membership.id:
        return True
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return action_plan_execution_visible_to_membership(membership, execution)
    return False


def serialize_execution_comment_permission_hints(
    *,
    membership: EstablishmentMembership,
    execution: ActionPlanExecution,
    comment: Comment,
) -> dict[str, bool]:
    return {
        "can_reply": can_reply_to_execution_comment(
            membership=membership,
            execution=execution,
            comment=comment,
        ),
        "can_resolve": can_resolve_execution_comment(
            membership=membership,
            execution=execution,
            comment=comment,
        ),
    }
