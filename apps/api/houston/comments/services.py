from __future__ import annotations

import uuid

from django.db import transaction
from django.utils import timezone

from houston.accounts.models import User
from houston.actions.models import Action
from houston.comments.constants import (
    ALREADY_RESOLVED_ERROR_DETAIL,
    CANNOT_REPLY_TO_REPLY_ERROR_DETAIL,
    CANNOT_REPLY_TO_SIGNAL_COMMENT_ERROR_DETAIL,
    COMMENT_BODY_MAX_LENGTH,
    INVALID_MENTIONS_ERROR_DETAIL,
    INVALID_PARENT_COMMENT_ERROR_DETAIL,
    NOT_ACTION_ROOT_COMMENT_ERROR_DETAIL,
    NOT_RESOLVED_ERROR_DETAIL,
    SIGNAL_COMMENT_PARENT_NOT_ALLOWED_ERROR_DETAIL,
)
from houston.comments.exceptions import CommentValidationError
from houston.comments.models import Comment, CommentMention
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    Organization,
)
from houston.signals.models import Signal


def normalize_comment_body(body: str) -> str:
    normalized = body.strip()
    if not normalized:
        raise CommentValidationError("Comment body is required.")
    if len(normalized) > COMMENT_BODY_MAX_LENGTH:
        raise CommentValidationError(
            f"Comment body must be at most {COMMENT_BODY_MAX_LENGTH} characters."
        )
    return normalized


def _dedupe_membership_ids(
    mentioned_membership_ids: list[uuid.UUID] | tuple[uuid.UUID, ...] | None,
) -> list[uuid.UUID]:
    if not mentioned_membership_ids:
        return []
    seen: set[uuid.UUID] = set()
    deduped: list[uuid.UUID] = []
    for membership_id in mentioned_membership_ids:
        if membership_id in seen:
            continue
        seen.add(membership_id)
        deduped.append(membership_id)
    return deduped


def _validate_mention_memberships(
    *,
    establishment_id: uuid.UUID,
    mentioned_membership_ids: list[uuid.UUID],
) -> list[EstablishmentMembership]:
    if not mentioned_membership_ids:
        return []

    memberships = list(
        EstablishmentMembership.objects.select_related("user", "establishment__organization")
        .filter(
            id__in=mentioned_membership_ids,
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
            user__status=User.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .order_by("id")
    )
    if len(memberships) != len(mentioned_membership_ids):
        raise CommentValidationError(INVALID_MENTIONS_ERROR_DETAIL)
    return memberships


def _create_mentions(
    *,
    comment: Comment,
    mentioned_memberships: list[EstablishmentMembership],
) -> None:
    if not mentioned_memberships:
        return
    CommentMention.objects.bulk_create(
        [
            CommentMention(
                comment=comment,
                mentioned_membership=membership,
            )
            for membership in mentioned_memberships
        ]
    )


def _get_parent_comment_for_reply(
    *,
    establishment_id: uuid.UUID,
    action: Action,
    parent_comment_id: uuid.UUID,
) -> Comment:
    parent = (
        Comment.objects.filter(
            id=parent_comment_id,
            establishment_id=establishment_id,
        )
        .select_related("parent_comment")
        .first()
    )
    if parent is None:
        raise CommentValidationError(INVALID_PARENT_COMMENT_ERROR_DETAIL)
    if parent.signal_id is not None:
        raise CommentValidationError(CANNOT_REPLY_TO_SIGNAL_COMMENT_ERROR_DETAIL)
    if parent.action_id != action.id:
        raise CommentValidationError(INVALID_PARENT_COMMENT_ERROR_DETAIL)
    if parent.parent_comment_id is not None:
        raise CommentValidationError(CANNOT_REPLY_TO_REPLY_ERROR_DETAIL)
    return parent


def _schedule_comment_invalidation(
    *, establishment_id: uuid.UUID, reason: str, entity_id: uuid.UUID
) -> None:
    from houston.realtime.broadcast import schedule_establishment_invalidation

    schedule_establishment_invalidation(
        establishment_id=establishment_id,
        subject_type="comment",
        reason=reason,
        entity_id=entity_id,
    )


def _schedule_inherited_signal_comment_invalidations(*, signal: Signal) -> None:
    linked_action_ids = Action.objects.filter(
        establishment_id=signal.establishment_id,
        signal_id=signal.id,
    ).values_list("id", flat=True)
    for action_id in linked_action_ids:
        _schedule_comment_invalidation(
            establishment_id=signal.establishment_id,
            reason="comment.signal.inherited",
            entity_id=action_id,
        )


def _get_action_root_comment(
    *,
    establishment_id: uuid.UUID,
    action: Action,
    comment_id: uuid.UUID,
) -> Comment:
    comment = Comment.objects.filter(
        id=comment_id,
        establishment_id=establishment_id,
    ).first()
    if comment is None:
        raise CommentValidationError(INVALID_PARENT_COMMENT_ERROR_DETAIL)
    if comment.signal_id is not None:
        raise CommentValidationError(NOT_ACTION_ROOT_COMMENT_ERROR_DETAIL)
    if comment.parent_comment_id is not None:
        raise CommentValidationError(NOT_ACTION_ROOT_COMMENT_ERROR_DETAIL)
    if comment.action_id != action.id:
        raise CommentValidationError(INVALID_PARENT_COMMENT_ERROR_DETAIL)
    return comment


@transaction.atomic
def create_signal_comment(
    *,
    author_membership: EstablishmentMembership,
    signal: Signal,
    body: str,
    mentioned_membership_ids: list[uuid.UUID] | None = None,
    parent_comment_id: uuid.UUID | None = None,
) -> Comment:
    if parent_comment_id is not None:
        raise CommentValidationError(SIGNAL_COMMENT_PARENT_NOT_ALLOWED_ERROR_DETAIL)

    normalized_body = normalize_comment_body(body)
    deduped_ids = _dedupe_membership_ids(mentioned_membership_ids)
    mentioned_memberships = _validate_mention_memberships(
        establishment_id=signal.establishment_id,
        mentioned_membership_ids=deduped_ids,
    )

    comment = Comment.objects.create(
        establishment_id=signal.establishment_id,
        signal=signal,
        author_membership=author_membership,
        body=normalized_body,
    )
    _create_mentions(comment=comment, mentioned_memberships=mentioned_memberships)
    _schedule_comment_invalidation(
        establishment_id=signal.establishment_id,
        reason="comment.signal.created",
        entity_id=signal.id,
    )
    _schedule_inherited_signal_comment_invalidations(signal=signal)
    return _reload_comment(establishment_id=signal.establishment_id, comment_id=comment.id)


@transaction.atomic
def create_action_comment(
    *,
    author_membership: EstablishmentMembership,
    action: Action,
    body: str,
    mentioned_membership_ids: list[uuid.UUID] | None = None,
    parent_comment_id: uuid.UUID | None = None,
) -> Comment:
    normalized_body = normalize_comment_body(body)
    deduped_ids = _dedupe_membership_ids(mentioned_membership_ids)
    mentioned_memberships = _validate_mention_memberships(
        establishment_id=action.establishment_id,
        mentioned_membership_ids=deduped_ids,
    )

    parent_comment = None
    if parent_comment_id is not None:
        parent_comment = _get_parent_comment_for_reply(
            establishment_id=action.establishment_id,
            action=action,
            parent_comment_id=parent_comment_id,
        )

    comment = Comment.objects.create(
        establishment_id=action.establishment_id,
        action=action,
        author_membership=author_membership,
        parent_comment=parent_comment,
        body=normalized_body,
    )
    _create_mentions(comment=comment, mentioned_memberships=mentioned_memberships)
    _schedule_comment_invalidation(
        establishment_id=action.establishment_id,
        reason="comment.action.created",
        entity_id=action.id,
    )
    return _reload_comment(establishment_id=action.establishment_id, comment_id=comment.id)


@transaction.atomic
def resolve_action_comment(
    *,
    action: Action,
    comment_id: uuid.UUID,
    resolved_by_membership: EstablishmentMembership,
) -> Comment:
    comment = _get_action_root_comment(
        establishment_id=action.establishment_id,
        action=action,
        comment_id=comment_id,
    )
    if comment.resolved_at is not None:
        raise CommentValidationError(ALREADY_RESOLVED_ERROR_DETAIL)

    comment.resolved_at = timezone.now()
    comment.resolved_by_membership = resolved_by_membership
    comment.save(update_fields=["resolved_at", "resolved_by_membership", "updated_at"])
    _schedule_comment_invalidation(
        establishment_id=action.establishment_id,
        reason="comment.action.resolved",
        entity_id=action.id,
    )
    return _reload_comment(establishment_id=action.establishment_id, comment_id=comment.id)


@transaction.atomic
def unresolve_action_comment(
    *,
    action: Action,
    comment_id: uuid.UUID,
) -> Comment:
    comment = _get_action_root_comment(
        establishment_id=action.establishment_id,
        action=action,
        comment_id=comment_id,
    )
    if comment.resolved_at is None:
        raise CommentValidationError(NOT_RESOLVED_ERROR_DETAIL)

    comment.resolved_at = None
    comment.resolved_by_membership = None
    comment.save(update_fields=["resolved_at", "resolved_by_membership", "updated_at"])
    _schedule_comment_invalidation(
        establishment_id=action.establishment_id,
        reason="comment.action.unresolved",
        entity_id=action.id,
    )
    return _reload_comment(establishment_id=action.establishment_id, comment_id=comment.id)


def _reload_comment(*, establishment_id: uuid.UUID, comment_id: uuid.UUID) -> Comment:
    from houston.comments.selectors import _comments_queryset

    comment = _comments_queryset(establishment_id=establishment_id).filter(id=comment_id).first()
    if comment is None:
        raise RuntimeError(f"Comment {comment_id} was not found after create.")
    return comment
