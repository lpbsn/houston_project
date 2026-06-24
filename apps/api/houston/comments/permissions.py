from __future__ import annotations

import uuid

from houston.actions.models import Action
from houston.actions.permissions import (
    action_visible_to_membership,
    is_action_assignee,
)
from houston.comments.models import Comment
from houston.comments.selectors import get_action_for_comments, get_signal_for_comments
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES


def can_access_signal_comments(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
) -> bool:
    return get_signal_for_comments(membership=membership, signal_id=signal_id) is not None


def can_access_action_comments(
    *,
    membership: EstablishmentMembership,
    action_id: uuid.UUID,
) -> bool:
    return get_action_for_comments(membership=membership, action_id=action_id) is not None


def is_action_root_comment(*, action: Action, comment: Comment) -> bool:
    return (
        comment.signal_id is None
        and comment.parent_comment_id is None
        and comment.action_id == action.id
        and comment.establishment_id == action.establishment_id
    )


def can_reply_to_action_comment(
    *,
    membership: EstablishmentMembership,
    action: Action,
    comment: Comment,
) -> bool:
    if not is_action_root_comment(action=action, comment=comment):
        return False
    return can_access_action_comments(membership=membership, action_id=action.id)


def can_resolve_action_comment(
    *,
    membership: EstablishmentMembership,
    action: Action,
    comment: Comment,
) -> bool:
    if not is_action_root_comment(action=action, comment=comment):
        return False
    if comment.establishment_id != membership.establishment_id:
        return False
    if comment.author_membership_id == membership.id:
        return True
    if is_action_assignee(membership, action):
        return True
    if action.accepted_by_id == membership.id:
        return True
    if action.created_by_id == membership.id:
        return True
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return action_visible_to_membership(membership, action)
    return False


def serialize_comment_permission_hints(
    *,
    membership: EstablishmentMembership,
    action: Action,
    comment: Comment,
) -> dict[str, bool]:
    return {
        "can_reply": can_reply_to_action_comment(
            membership=membership,
            action=action,
            comment=comment,
        ),
        "can_resolve": can_resolve_action_comment(
            membership=membership,
            action=action,
            comment=comment,
        ),
    }
