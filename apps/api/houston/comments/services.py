from __future__ import annotations

import uuid

from django.db import transaction

from houston.accounts.models import User
from houston.actions.models import Action
from houston.comments.constants import (
    COMMENT_BODY_MAX_LENGTH,
    INVALID_MENTIONS_ERROR_DETAIL,
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


@transaction.atomic
def create_signal_comment(
    *,
    author_membership: EstablishmentMembership,
    signal: Signal,
    body: str,
    mentioned_membership_ids: list[uuid.UUID] | None = None,
) -> Comment:
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
    return _reload_comment(establishment_id=signal.establishment_id, comment_id=comment.id)


@transaction.atomic
def create_action_comment(
    *,
    author_membership: EstablishmentMembership,
    action: Action,
    body: str,
    mentioned_membership_ids: list[uuid.UUID] | None = None,
) -> Comment:
    normalized_body = normalize_comment_body(body)
    deduped_ids = _dedupe_membership_ids(mentioned_membership_ids)
    mentioned_memberships = _validate_mention_memberships(
        establishment_id=action.establishment_id,
        mentioned_membership_ids=deduped_ids,
    )

    comment = Comment.objects.create(
        establishment_id=action.establishment_id,
        action=action,
        author_membership=author_membership,
        body=normalized_body,
    )
    _create_mentions(comment=comment, mentioned_memberships=mentioned_memberships)
    return _reload_comment(establishment_id=action.establishment_id, comment_id=comment.id)


def _reload_comment(*, establishment_id: uuid.UUID, comment_id: uuid.UUID) -> Comment:
    from houston.comments.selectors import _comments_queryset

    comment = _comments_queryset(establishment_id=establishment_id).filter(id=comment_id).first()
    if comment is None:
        raise RuntimeError(f"Comment {comment_id} was not found after create.")
    return comment
