from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.accounts.legal_services import TermsAcceptanceRequiredError
from houston.comments.api.serializers import (
    CommentCreateRequestSerializer,
    CommentItemSerializer,
    ExecutionCommentListItemSerializer,
    ExecutionCommentThreadItemSerializer,
    serialize_comment,
    serialize_execution_comment_list_entry,
    serialize_execution_comment_thread,
)
from houston.comments.constants import NOT_EXECUTION_ROOT_COMMENT_ERROR_DETAIL
from houston.comments.exceptions import CommentValidationError
from houston.comments.permissions import (
    can_resolve_execution_comment,
    is_execution_root_comment,
)
from houston.comments.selectors import (
    ExecutionCommentThreadEntry,
    get_action_plan_execution_for_comments,
    get_signal_for_comments,
    list_action_plan_execution_comments_for_detail,
    list_signal_comments,
)
from houston.comments.services import (
    create_action_plan_execution_comment,
    create_signal_comment,
    resolve_action_plan_execution_comment,
    unresolve_action_plan_execution_comment,
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
        except TermsAcceptanceRequiredError as exc:
            from houston.accounts.api.legal_errors import legal_error_response

            return legal_error_response(exc)
        except CommentValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CommentItemSerializer(serialize_comment(comment)).data,
            status=status.HTTP_201_CREATED,
        )


class ActionPlanExecutionCommentsView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            200: ExecutionCommentListItemSerializer(many=True),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Lists comments on an Action Plan execution, including inherited Signal "
            "comments and execution threads, oldest first."
        ),
    )
    def get(self, request, establishment_id, execution_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        execution = get_action_plan_execution_for_comments(
            membership=membership,
            execution_id=uuid.UUID(str(execution_id)),
        )
        if execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        entries = list_action_plan_execution_comments_for_detail(execution=execution)
        payload = [
            serialize_execution_comment_list_entry(
                entry=entry,
                membership=membership,
                execution=execution,
            )
            for entry in entries
        ]
        return Response(ExecutionCommentListItemSerializer(payload, many=True).data)

    @extend_schema(
        tags=["comments"],
        request=CommentCreateRequestSerializer,
        responses={
            201: CommentItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Creates a comment on an Action Plan execution.",
    )
    def post(self, request, establishment_id, execution_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        execution = get_action_plan_execution_for_comments(
            membership=membership,
            execution_id=uuid.UUID(str(execution_id)),
        )
        if execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        request_serializer = CommentCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        try:
            comment = create_action_plan_execution_comment(
                author_membership=membership,
                execution=execution,
                body=request_serializer.validated_data["body"],
                mentioned_membership_ids=request_serializer.validated_data.get(
                    "mentioned_membership_ids"
                ),
                parent_comment_id=request_serializer.validated_data.get("parent_comment_id"),
            )
        except TermsAcceptanceRequiredError as exc:
            from houston.accounts.api.legal_errors import legal_error_response

            return legal_error_response(exc)
        except CommentValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CommentItemSerializer(serialize_comment(comment)).data,
            status=status.HTTP_201_CREATED,
        )


class _ExecutionCommentResolveBaseView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    def _load_execution_and_comment(
        self,
        request,
        execution_id,
        comment_id,
    ):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return None, None, None, None

        execution = get_action_plan_execution_for_comments(
            membership=membership,
            execution_id=uuid.UUID(str(execution_id)),
        )
        if execution is None:
            return None, None, None, None

        from houston.comments.models import Comment

        comment = Comment.objects.filter(
            id=uuid.UUID(str(comment_id)),
            establishment_id=execution.establishment_id,
        ).first()
        if comment is None:
            return None, None, None, None

        if not is_execution_root_comment(execution=execution, comment=comment):
            return membership, execution, comment, "ineligible"

        if not can_resolve_execution_comment(
            membership=membership,
            execution=execution,
            comment=comment,
        ):
            return None, None, None, None

        return membership, execution, comment, None


class ActionPlanExecutionCommentResolveView(_ExecutionCommentResolveBaseView):
    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            200: ExecutionCommentThreadItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Marks an action plan execution root comment as resolved.",
    )
    def post(self, request, establishment_id, execution_id, comment_id):
        membership, execution, comment, ineligible = self._load_execution_and_comment(
            request,
            execution_id,
            comment_id,
        )
        if ineligible == "ineligible":
            return Response(
                {
                    "code": "validation_error",
                    "detail": NOT_EXECUTION_ROOT_COMMENT_ERROR_DETAIL,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if membership is None or execution is None or comment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            resolved_comment = resolve_action_plan_execution_comment(
                execution=execution,
                comment_id=comment.id,
                resolved_by_membership=membership,
            )
        except CommentValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from houston.comments.selectors import _comments_queryset

        reloaded = _comments_queryset(establishment_id=execution.establishment_id).get(
            id=resolved_comment.id
        )
        replies = list(reloaded.replies.all())
        payload = serialize_execution_comment_thread(
            entry=ExecutionCommentThreadEntry(
                kind="execution_thread",
                root=reloaded,
                replies=replies,
            ),
            membership=membership,
            execution=execution,
        )
        return Response(ExecutionCommentThreadItemSerializer(payload).data)


class ActionPlanExecutionCommentUnresolveView(_ExecutionCommentResolveBaseView):
    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            200: ExecutionCommentThreadItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Marks an action plan execution root comment as unresolved.",
    )
    def post(self, request, establishment_id, execution_id, comment_id):
        membership, execution, comment, ineligible = self._load_execution_and_comment(
            request,
            execution_id,
            comment_id,
        )
        if ineligible == "ineligible":
            return Response(
                {
                    "code": "validation_error",
                    "detail": NOT_EXECUTION_ROOT_COMMENT_ERROR_DETAIL,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if membership is None or execution is None or comment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            unresolved_comment = unresolve_action_plan_execution_comment(
                execution=execution,
                comment_id=comment.id,
            )
        except CommentValidationError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from houston.comments.selectors import _comments_queryset

        reloaded = _comments_queryset(establishment_id=execution.establishment_id).get(
            id=unresolved_comment.id
        )
        replies = list(reloaded.replies.all())
        payload = serialize_execution_comment_thread(
            entry=ExecutionCommentThreadEntry(
                kind="execution_thread",
                root=reloaded,
                replies=replies,
            ),
            membership=membership,
            execution=execution,
        )
        return Response(ExecutionCommentThreadItemSerializer(payload).data)
