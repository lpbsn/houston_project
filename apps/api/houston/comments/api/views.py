from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.comments.api.serializers import (
    ActionCommentListItemSerializer,
    ActionCommentThreadItemSerializer,
    CommentCreateRequestSerializer,
    CommentItemSerializer,
    serialize_action_comment_list_entry,
    serialize_action_comment_thread,
    serialize_comment,
)
from houston.comments.constants import NOT_ACTION_ROOT_COMMENT_ERROR_DETAIL
from houston.comments.exceptions import CommentValidationError
from houston.comments.permissions import can_resolve_action_comment, is_action_root_comment
from houston.comments.selectors import (
    ActionCommentThreadEntry,
    get_action_for_comments,
    get_signal_for_comments,
    list_action_comments_for_detail,
    list_signal_comments,
)
from houston.comments.services import (
    create_action_comment,
    create_signal_comment,
    resolve_action_comment,
    unresolve_action_comment,
)
from houston.establishments.permissions import HasActiveMembership
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin


class SignalCommentsView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            200: CommentItemSerializer(many=True),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Lists comments on a Signal, oldest first.",
    )
    def get(self, request, establishment_id, signal_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        signal = get_signal_for_comments(
            membership=membership,
            signal_id=uuid.UUID(str(signal_id)),
        )
        if signal is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        comments = list_signal_comments(signal=signal)
        payload = [serialize_comment(comment) for comment in comments]
        return Response(CommentItemSerializer(payload, many=True).data)

    @extend_schema(
        tags=["comments"],
        request=CommentCreateRequestSerializer,
        responses={
            201: CommentItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Creates a comment on a Signal.",
    )
    def post(self, request, establishment_id, signal_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        signal = get_signal_for_comments(
            membership=membership,
            signal_id=uuid.UUID(str(signal_id)),
        )
        if signal is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        request_serializer = CommentCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        try:
            comment = create_signal_comment(
                author_membership=membership,
                signal=signal,
                body=request_serializer.validated_data["body"],
                mentioned_membership_ids=request_serializer.validated_data.get(
                    "mentioned_membership_ids"
                ),
                parent_comment_id=request_serializer.validated_data.get("parent_comment_id"),
            )
        except CommentValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CommentItemSerializer(serialize_comment(comment)).data,
            status=status.HTTP_201_CREATED,
        )


class ActionCommentsView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            200: ActionCommentListItemSerializer(many=True),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Lists comments on an Action, including inherited Signal comments and action "
            "threads, oldest first."
        ),
    )
    def get(self, request, establishment_id, action_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        action = get_action_for_comments(
            membership=membership,
            action_id=uuid.UUID(str(action_id)),
        )
        if action is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        entries = list_action_comments_for_detail(action=action)
        payload = [
            serialize_action_comment_list_entry(
                entry=entry,
                membership=membership,
                action=action,
            )
            for entry in entries
        ]
        return Response(ActionCommentListItemSerializer(payload, many=True).data)

    @extend_schema(
        tags=["comments"],
        request=CommentCreateRequestSerializer,
        responses={
            201: CommentItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Creates a comment on an Action.",
    )
    def post(self, request, establishment_id, action_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        action = get_action_for_comments(
            membership=membership,
            action_id=uuid.UUID(str(action_id)),
        )
        if action is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        request_serializer = CommentCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        try:
            comment = create_action_comment(
                author_membership=membership,
                action=action,
                body=request_serializer.validated_data["body"],
                mentioned_membership_ids=request_serializer.validated_data.get(
                    "mentioned_membership_ids"
                ),
                parent_comment_id=request_serializer.validated_data.get("parent_comment_id"),
            )
        except CommentValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CommentItemSerializer(serialize_comment(comment)).data,
            status=status.HTTP_201_CREATED,
        )


class _ActionCommentResolveBaseView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    def _load_action_and_comment(
        self,
        request,
        action_id,
        comment_id,
    ):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return None, None, None, None

        action = get_action_for_comments(
            membership=membership,
            action_id=uuid.UUID(str(action_id)),
        )
        if action is None:
            return None, None, None, None

        from houston.comments.models import Comment

        comment = Comment.objects.filter(
            id=uuid.UUID(str(comment_id)),
            establishment_id=action.establishment_id,
        ).first()
        if comment is None:
            return None, None, None, None

        if not is_action_root_comment(action=action, comment=comment):
            return membership, action, comment, "ineligible"

        if not can_resolve_action_comment(
            membership=membership,
            action=action,
            comment=comment,
        ):
            return None, None, None, None

        return membership, action, comment, None


class ActionCommentResolveView(_ActionCommentResolveBaseView):
    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            200: ActionCommentThreadItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Marks an action root comment as resolved.",
    )
    def post(self, request, establishment_id, action_id, comment_id):
        membership, action, comment, ineligible = self._load_action_and_comment(
            request,
            action_id,
            comment_id,
        )
        if ineligible == "ineligible":
            return Response(
                {"code": "validation_error", "detail": NOT_ACTION_ROOT_COMMENT_ERROR_DETAIL},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if membership is None or action is None or comment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            resolved_comment = resolve_action_comment(
                action=action,
                comment_id=comment.id,
                resolved_by_membership=membership,
            )
        except CommentValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from houston.comments.selectors import _comments_queryset

        reloaded = _comments_queryset(establishment_id=action.establishment_id).get(
            id=resolved_comment.id
        )
        replies = list(reloaded.replies.all())
        payload = serialize_action_comment_thread(
            entry=ActionCommentThreadEntry(kind="action_thread", root=reloaded, replies=replies),
            membership=membership,
            action=action,
        )
        return Response(ActionCommentThreadItemSerializer(payload).data)


class ActionCommentUnresolveView(_ActionCommentResolveBaseView):
    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            200: ActionCommentThreadItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Marks an action root comment as unresolved.",
    )
    def post(self, request, establishment_id, action_id, comment_id):
        membership, action, comment, ineligible = self._load_action_and_comment(
            request,
            action_id,
            comment_id,
        )
        if ineligible == "ineligible":
            return Response(
                {"code": "validation_error", "detail": NOT_ACTION_ROOT_COMMENT_ERROR_DETAIL},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if membership is None or action is None or comment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            unresolved_comment = unresolve_action_comment(
                action=action,
                comment_id=comment.id,
            )
        except CommentValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from houston.comments.selectors import _comments_queryset

        reloaded = _comments_queryset(establishment_id=action.establishment_id).get(
            id=unresolved_comment.id
        )
        replies = list(reloaded.replies.all())
        payload = serialize_action_comment_thread(
            entry=ActionCommentThreadEntry(kind="action_thread", root=reloaded, replies=replies),
            membership=membership,
            action=action,
        )
        return Response(ActionCommentThreadItemSerializer(payload).data)
