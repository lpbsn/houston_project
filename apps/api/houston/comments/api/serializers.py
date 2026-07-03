from __future__ import annotations

from rest_framework import serializers

from houston.action_plans.models import ActionPlanExecution
from houston.actions.models import Action
from houston.comments.models import Comment
from houston.comments.permissions import (
    serialize_comment_permission_hints,
    serialize_execution_comment_permission_hints,
)
from houston.comments.selectors import (
    ActionCommentListEntry,
    ActionCommentThreadEntry,
    ExecutionCommentListEntry,
    ExecutionCommentThreadEntry,
    InheritedSignalCommentEntry,
)
from houston.establishments.models import EstablishmentMembership


def _membership_display_name(membership) -> str:
    user = membership.user
    return user.get_full_name() or user.email or user.username


def comment_origin(comment: Comment) -> str:
    if comment.signal_id is not None:
        return "signal"
    if comment.action_plan_execution_id is not None:
        return "action_plan_execution"
    return "action"


def serialize_comment(comment: Comment) -> dict:
    mentions = [
        {
            "membership_id": link.mentioned_membership_id,
            "display_name": _membership_display_name(link.mentioned_membership),
        }
        for link in comment.mention_links.all()
    ]
    mentions.sort(key=lambda item: (item["display_name"].casefold(), str(item["membership_id"])))

    return {
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


def serialize_resolved_by(comment: Comment) -> dict | None:
    if comment.resolved_by_membership_id is None:
        return None
    return {
        "membership_id": comment.resolved_by_membership_id,
        "display_name": _membership_display_name(comment.resolved_by_membership),
    }


def serialize_action_comment_thread(
    *,
    entry: ActionCommentThreadEntry,
    membership: EstablishmentMembership,
    action: Action,
) -> dict:
    root = entry.root
    return {
        "item_type": "action_thread",
        **serialize_comment(root),
        "replies": [serialize_comment(reply) for reply in entry.replies],
        "is_resolved": root.resolved_at is not None,
        "resolved_at": root.resolved_at,
        "resolved_by": serialize_resolved_by(root),
        "permission_hints": serialize_comment_permission_hints(
            membership=membership,
            action=action,
            comment=root,
        ),
    }


def serialize_inherited_signal_comment(*, entry: InheritedSignalCommentEntry) -> dict:
    return {
        "item_type": "inherited_signal",
        **serialize_comment(entry.comment),
    }


def serialize_action_comment_list_entry(
    *,
    entry: ActionCommentListEntry,
    membership: EstablishmentMembership,
    action: Action,
) -> dict:
    if entry.kind == "inherited_signal":
        return serialize_inherited_signal_comment(entry=entry)
    return serialize_action_comment_thread(
        entry=entry,
        membership=membership,
        action=action,
    )


def serialize_execution_comment_thread(
    *,
    entry: ExecutionCommentThreadEntry,
    membership: EstablishmentMembership,
    execution: ActionPlanExecution,
) -> dict:
    root = entry.root
    return {
        "item_type": "execution_thread",
        **serialize_comment(root),
        "replies": [serialize_comment(reply) for reply in entry.replies],
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


class CommentItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()


class CommentPermissionHintsSerializer(serializers.Serializer):
    can_reply = serializers.BooleanField()
    can_resolve = serializers.BooleanField()


class ActionCommentThreadItemSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=["action_thread"])
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()
    replies = CommentItemSerializer(many=True)
    is_resolved = serializers.BooleanField()
    resolved_at = serializers.DateTimeField(allow_null=True)
    resolved_by = CommentAuthorSerializer(allow_null=True)
    permission_hints = CommentPermissionHintsSerializer()


class InheritedSignalCommentItemSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=["inherited_signal"])
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()


class ActionCommentListItemSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=["inherited_signal", "action_thread"])
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()
    replies = CommentItemSerializer(many=True, required=False)
    is_resolved = serializers.BooleanField(required=False)
    resolved_at = serializers.DateTimeField(allow_null=True, required=False)
    resolved_by = CommentAuthorSerializer(allow_null=True, required=False)
    permission_hints = CommentPermissionHintsSerializer(required=False)


class ExecutionCommentThreadItemSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=["execution_thread"])
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()
    replies = CommentItemSerializer(many=True)
    is_resolved = serializers.BooleanField()
    resolved_at = serializers.DateTimeField(allow_null=True)
    resolved_by = CommentAuthorSerializer(allow_null=True)
    permission_hints = CommentPermissionHintsSerializer()


class ExecutionCommentListItemSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=["inherited_signal", "execution_thread"])
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(
        choices=["signal", "action", "action_plan_execution"],
    )
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()
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
