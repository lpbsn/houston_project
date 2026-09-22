from __future__ import annotations

from rest_framework import serializers

from houston.action_plans.models import ActionPlanExecution
from houston.comments.models import ActionPlanCommentAttachment, Comment
from houston.comments.permissions import serialize_execution_comment_permission_hints
from houston.comments.selectors import (
    ExecutionCommentListEntry,
    ExecutionCommentThreadEntry,
    InheritedSignalCommentEntry,
)
from houston.comments.upload_services import execution_comment_attachments_are_available
from houston.establishments.models import EstablishmentMembership


def _membership_display_name(membership) -> str:
    from houston.accounts.display import membership_display_name

    return membership_display_name(membership) or ""


def comment_origin(comment: Comment) -> str:
    if comment.signal_id is not None:
        return "signal"
    return "action_plan_execution"


def serialize_action_plan_comment_attachment(
    attachment: ActionPlanCommentAttachment,
    *,
    comment: Comment | None = None,
) -> dict:
    resolved_comment = comment or attachment.comment
    establishment_id = resolved_comment.establishment_id
    thumbnail_key = getattr(attachment.upload, "thumbnail_storage_key", "")
    return {
        "id": attachment.id,
        "kind": attachment.kind,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "original_filename": attachment.original_filename,
        "preview_url": (
            f"/api/v1/establishments/{establishment_id}"
            f"/action-plan-executions/{attachment.action_plan_execution_id}"
            f"/comment-attachments/{attachment.id}/preview/"
        ),
        "thumbnail_url": (
            f"/api/v1/establishments/{establishment_id}"
            f"/action-plan-executions/{attachment.action_plan_execution_id}"
            f"/comment-attachments/{attachment.id}/preview/?variant=thumbnail"
            if thumbnail_key
            else None
        ),
        "comment_id": resolved_comment.id,
        "created_at": attachment.created_at,
        "author_display_name": _membership_display_name(resolved_comment.author_membership),
    }


def _serialize_comment_attachments(
    comment: Comment,
    *,
    execution: ActionPlanExecution | None = None,
) -> list[dict]:
    if comment.action_plan_execution_id is None:
        return []
    resolved_execution = execution or getattr(comment, "action_plan_execution", None)
    if resolved_execution is not None and not execution_comment_attachments_are_available(
        resolved_execution
    ):
        return []
    attachments = getattr(comment, "_prefetched_objects_cache", {}).get(
        "plan_comment_attachments"
    )
    if attachments is None:
        attachments = list(comment.plan_comment_attachments.select_related("upload").all())
    return [
        serialize_action_plan_comment_attachment(attachment, comment=comment)
        for attachment in sorted(attachments, key=lambda item: (item.position, item.id))
    ]


def serialize_comment(
    comment: Comment,
    *,
    execution: ActionPlanExecution | None = None,
    include_attachments: bool = False,
) -> dict:
    mentions = [
        {
            "membership_id": link.mentioned_membership_id,
            "display_name": _membership_display_name(link.mentioned_membership),
        }
        for link in comment.mention_links.all()
    ]
    mentions.sort(key=lambda item: (item["display_name"].casefold(), str(item["membership_id"])))

    payload = {
        "id": comment.id,
        "origin": comment_origin(comment),
        "body": comment.body,
        "author": {
            "membership_id": comment.author_membership_id,
            "display_name": _membership_display_name(comment.author_membership),
        },
        "mentions": mentions,
        "created_at": comment.created_at,
    }
    if include_attachments or comment.action_plan_execution_id is not None:
        payload["attachments"] = _serialize_comment_attachments(comment, execution=execution)
    return payload


def serialize_resolved_by(comment: Comment) -> dict | None:
    if comment.resolved_by_membership_id is None:
        return None
    return {
        "membership_id": comment.resolved_by_membership_id,
        "display_name": _membership_display_name(comment.resolved_by_membership),
    }


def serialize_inherited_signal_comment(*, entry: InheritedSignalCommentEntry) -> dict:
    return {
        "item_type": "inherited_signal",
        **serialize_comment(entry.comment),
    }


def serialize_execution_comment_thread(
    *,
    entry: ExecutionCommentThreadEntry,
    membership: EstablishmentMembership,
    execution: ActionPlanExecution,
) -> dict:
    root = entry.root
    return {
        "item_type": "execution_thread",
        **serialize_comment(root, execution=execution),
        "replies": [serialize_comment(reply, execution=execution) for reply in entry.replies],
        "is_resolved": root.resolved_at is not None,
        "resolved_at": root.resolved_at,
        "resolved_by": serialize_resolved_by(root),
        "permission_hints": serialize_execution_comment_permission_hints(
            membership=membership,
            execution=execution,
            comment=root,
        ),
    }


def serialize_execution_comment_list_entry(
    *,
    entry: ExecutionCommentListEntry,
    membership: EstablishmentMembership,
    execution: ActionPlanExecution,
) -> dict:
    if entry.kind == "inherited_signal":
        return serialize_inherited_signal_comment(entry=entry)
    return serialize_execution_comment_thread(
        entry=entry,
        membership=membership,
        execution=execution,
    )


class CommentAuthorSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()


class CommentMentionSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()


class CommentAttachmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=["image", "document"])
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    original_filename = serializers.CharField()
    preview_url = serializers.CharField()
    thumbnail_url = serializers.CharField(allow_null=True)
    comment_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    author_display_name = serializers.CharField()


class CommentItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()
    attachments = CommentAttachmentSerializer(many=True, required=False)


class CommentPermissionHintsSerializer(serializers.Serializer):
    can_reply = serializers.BooleanField()
    can_resolve = serializers.BooleanField()


class InheritedSignalCommentItemSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=["inherited_signal"])
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()


class ExecutionCommentThreadItemSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=["execution_thread"])
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()
    attachments = CommentAttachmentSerializer(many=True, required=False)
    replies = CommentItemSerializer(many=True)
    is_resolved = serializers.BooleanField()
    resolved_at = serializers.DateTimeField(allow_null=True)
    resolved_by = CommentAuthorSerializer(allow_null=True)
    permission_hints = CommentPermissionHintsSerializer()


class ExecutionCommentListItemSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=["inherited_signal", "execution_thread"])
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()
    attachments = CommentAttachmentSerializer(many=True, required=False)
    replies = CommentItemSerializer(many=True, required=False)
    is_resolved = serializers.BooleanField(required=False)
    resolved_at = serializers.DateTimeField(allow_null=True, required=False)
    resolved_by = CommentAuthorSerializer(allow_null=True, required=False)
    permission_hints = CommentPermissionHintsSerializer(required=False)


class CommentCreateRequestSerializer(serializers.Serializer):
    body = serializers.CharField()
    mentioned_membership_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    parent_comment_id = serializers.UUIDField(required=False, allow_null=True)


class ExecutionCommentCreateRequestSerializer(CommentCreateRequestSerializer):
    attachment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )


class ActionPlanCommentReserveUploadRequestSerializer(serializers.Serializer):
    filename = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()


class ActionPlanCommentReserveUploadResponseSerializer(serializers.Serializer):
    upload_id = serializers.UUIDField()
    put_url = serializers.CharField(allow_blank=True)
    expires_at = serializers.DateTimeField()


class ActionPlanCommentUploadCompleteResponseSerializer(serializers.Serializer):
    upload_id = serializers.UUIDField()
    status = serializers.CharField()
    kind = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField(allow_null=True)
