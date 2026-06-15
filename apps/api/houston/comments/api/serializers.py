from __future__ import annotations

from rest_framework import serializers

from houston.comments.models import Comment


def _membership_display_name(membership) -> str:
    user = membership.user
    return user.get_full_name() or user.email or user.username


def comment_origin(comment: Comment) -> str:
    return "signal" if comment.signal_id is not None else "action"


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


class CommentAuthorSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()


class CommentMentionSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()


class CommentItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(choices=["signal", "action"])
    body = serializers.CharField()
    author = CommentAuthorSerializer()
    mentions = CommentMentionSerializer(many=True)
    created_at = serializers.DateTimeField()


class CommentCreateRequestSerializer(serializers.Serializer):
    body = serializers.CharField()
    mentioned_membership_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
