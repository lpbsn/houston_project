from __future__ import annotations

from django.db import models
from django.db.models import Q

from houston.comments.constants import COMMENT_BODY_MAX_LENGTH
from houston.core.models import BaseModel


class Comment(BaseModel):
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    signal = models.ForeignKey(
        "signals.Signal",
        on_delete=models.CASCADE,
        related_name="comments",
        null=True,
        blank=True,
    )
    action = models.ForeignKey(
        "actions.Action",
        on_delete=models.CASCADE,
        related_name="comments",
        null=True,
        blank=True,
    )
    author_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="comments_authored",
    )
    body = models.TextField(max_length=COMMENT_BODY_MAX_LENGTH)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["establishment", "signal", "created_at", "id"]),
            models.Index(fields=["establishment", "action", "created_at", "id"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(signal__isnull=False, action__isnull=True)
                    | Q(signal__isnull=True, action__isnull=False)
                ),
                name="comment_exactly_one_parent",
            ),
        ]


class CommentMention(BaseModel):
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="mention_links",
    )
    mentioned_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="comment_mentions_received",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["comment", "mentioned_membership"],
                name="uniq_comment_mention_membership",
            ),
        ]
