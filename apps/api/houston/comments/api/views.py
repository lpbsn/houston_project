from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.comments.api.serializers import (
    CommentCreateRequestSerializer,
    CommentItemSerializer,
    serialize_comment,
)
from houston.comments.exceptions import CommentValidationError
from houston.comments.selectors import (
    get_action_for_comments,
    get_signal_for_comments,
    list_action_comments,
    list_signal_comments,
)
from houston.comments.services import create_action_comment, create_signal_comment
from houston.establishments.permissions import HasActiveMembership
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin


class SignalCommentsView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["comments"],
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
        responses={
            200: CommentItemSerializer(many=True),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Lists comments on an Action, including inherited Signal comments, oldest first."
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

        comments = list_action_comments(action=action)
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
