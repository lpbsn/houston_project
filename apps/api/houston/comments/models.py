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
    action_plan_execution = models.ForeignKey(
        "action_plans.ActionPlanExecution",
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
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="replies",
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="comments_resolved",
        null=True,
        blank=True,
    )
    body = models.TextField(max_length=COMMENT_BODY_MAX_LENGTH)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["establishment", "signal", "created_at", "id"]),
            models.Index(
                fields=["establishment", "action_plan_execution", "created_at", "id"],
            ),
            models.Index(fields=["parent_comment", "created_at", "id"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        signal__isnull=False,
                        action_plan_execution__isnull=True,
                    )
                    | Q(
                        signal__isnull=True,
                        action_plan_execution__isnull=False,
                    )
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
        indexes = [
            models.Index(
                fields=["mentioned_membership", "comment"],
                name="cmt_mnt_member_comment_idx",
            ),
        ]


class ActionPlanCommentUpload(BaseModel):
    class Status(models.TextChoices):
        RESERVED = "reserved", "Reserved"
        VALIDATED = "validated", "Validated"
        LINKED = "linked", "Linked"
        EXPIRED = "expired", "Expired"

    class Kind(models.TextChoices):
        IMAGE = "image", "Image"
        DOCUMENT = "document", "Document"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="action_plan_comment_uploads",
    )
    action_plan_execution = models.ForeignKey(
        "action_plans.ActionPlanExecution",
        on_delete=models.CASCADE,
        related_name="comment_uploads",
    )
    uploaded_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.CASCADE,
        related_name="action_plan_comment_uploads",
    )
    original_filename = models.CharField(max_length=255)
    declared_content_type = models.CharField(max_length=120)
    declared_size_bytes = models.PositiveIntegerField()
    content_type = models.CharField(max_length=120, blank=True, default="")
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    kind = models.CharField(max_length=16, blank=True, default="")
    storage_key = models.CharField(max_length=512)
    thumbnail_storage_key = models.CharField(max_length=512, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVED)
    expires_at = models.DateTimeField()
    linked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["action_plan_execution", "status", "expires_at"],
                name="apcmt_up_exec_status_exp_idx",
            ),
            models.Index(
                fields=["uploaded_by_membership", "status"],
                name="apcmt_up_member_status_idx",
            ),
        ]


class ActionPlanCommentAttachment(BaseModel):
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="plan_comment_attachments",
    )
    upload = models.OneToOneField(
        ActionPlanCommentUpload,
        on_delete=models.CASCADE,
        related_name="attachment",
    )
    action_plan_execution = models.ForeignKey(
        "action_plans.ActionPlanExecution",
        on_delete=models.CASCADE,
        related_name="comment_attachments",
    )
    position = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=16)
    content_type = models.CharField(max_length=120)
    size_bytes = models.PositiveIntegerField()
    original_filename = models.CharField(max_length=255)

    class Meta:
        ordering = ["position", "id"]
        indexes = [
            models.Index(
                fields=["action_plan_execution", "created_at", "id"],
                name="apcmt_att_exec_created_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["comment", "position"],
                name="uniq_action_plan_comment_attachment_position",
            ),
        ]
