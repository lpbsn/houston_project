from __future__ import annotations

import uuid

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import AccessTokenAuthContext, BearerAccessTokenAuthentication
from houston.chat.access import (
    resolve_chat_actor_membership,
    resolve_chat_settings_actor_membership,
)
from houston.chat.api.serializers import (
    ChatAddParticipantRequestSerializer,
    ChatConversationDetailSerializer,
    ChatConversationListResponseSerializer,
    ChatCreateConversationResponseSerializer,
    ChatCreateDmRequestSerializer,
    ChatCreateGroupRequestSerializer,
    ChatEligibleMembershipsResponseSerializer,
    ChatMessageListResponseSerializer,
    ChatRenameGroupRequestSerializer,
    ChatSettingsPatchRequestSerializer,
    ChatStatusSerializer,
    ChatWsTicketResponseSerializer,
    conversation_title,
    serialize_conversation_detail,
    serialize_membership_summary,
    serialize_message,
    serialize_participant_summary,
)
from houston.chat.constants import CHAT_ELIGIBLE_MEMBERSHIPS_QUERY_MAX_LENGTH
from houston.chat.exceptions import (
    ChatError,
    ChatNotFoundError,
    ChatPermissionError,
    ChatValidationError,
)
from houston.chat.models import ChatConversation
from houston.chat.permissions import can_delete_group, can_manage_group
from houston.chat.selectors import (
    get_conversation_for_participant,
    get_eligible_chat_memberships_queryset,
    get_latest_message,
    get_latest_messages_by_conversation_ids,
    is_conversation_unread,
    list_conversations_for_membership,
    list_messages_for_conversation,
)
from houston.chat.services import (
    add_group_participant,
    build_chat_status,
    create_group_conversation,
    create_or_get_dm_conversation,
    delete_group_conversation,
    leave_group_conversation,
    mark_conversation_seen,
    promote_group_participant,
    remove_group_participant,
    rename_group_conversation,
    update_establishment_chat_enabled,
)
from houston.chat.ws_ticket import issue_ws_ticket
from houston.establishments.permissions import HasActiveMembership
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

DEFAULT_MESSAGE_PAGE_SIZE = 50
MAX_MESSAGE_PAGE_SIZE = 100


class ChatRateLimitedMixin:
    throttle_scope: str

    def get_throttles(self):
        if not settings.HOUSTON_CHAT_RATE_LIMIT_ENABLED:
            return []
        return [ScopedRateThrottle()]


class EstablishmentScopedChatMixin:
    establishment_id: uuid.UUID | None = None

    def initial(self, request, *args, **kwargs):
        raw_id = self.kwargs.get("establishment_id")
        self.establishment_id = uuid.UUID(str(raw_id))
        super().initial(request, *args, **kwargs)


class CanAccessChat(permissions.BasePermission):
    message = "You do not have permission to access chat for this establishment."

    def has_permission(self, request, view) -> bool:
        membership = resolve_chat_actor_membership(
            request,
            establishment_id=view.establishment_id,
        )
        return membership is not None


def _resolve_membership(request, establishment_id: uuid.UUID):
    membership = resolve_chat_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return membership


def _resolve_settings_membership(request, establishment_id: uuid.UUID):
    membership = resolve_chat_settings_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return membership


def _chat_error_response(exc: ChatError) -> Response:
    if isinstance(exc, ChatNotFoundError):
        return Response(status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, ChatPermissionError):
        return Response(
            {"code": exc.code, "detail": exc.message},
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, ChatValidationError):
        return Response(
            {"code": exc.code, "detail": exc.message},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {"code": exc.code, "detail": str(exc)},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _parse_message_page_size(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_MESSAGE_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ChatValidationError("Invalid page_size.") from None
    if value < 1 or value > MAX_MESSAGE_PAGE_SIZE:
        raise ChatValidationError(f"page_size must be between 1 and {MAX_MESSAGE_PAGE_SIZE}.")
    return value


def _parse_message_cursor(raw: str | None) -> tuple[object, uuid.UUID] | None:
    if not raw:
        return None
    parts = raw.split("|", 1)
    if len(parts) != 2:
        raise ChatValidationError("Invalid cursor.")
    from django.utils.dateparse import parse_datetime

    created_at = parse_datetime(parts[0])
    if created_at is None:
        raise ChatValidationError("Invalid cursor.")
    try:
        message_id = uuid.UUID(parts[1])
    except ValueError as exc:
        raise ChatValidationError("Invalid cursor.") from exc
    return created_at, message_id


def _message_cursor(message) -> str:
    return f"{message.created_at.isoformat()}|{message.id}"


def _serialize_conversation_list_item(
    *,
    conversation: ChatConversation,
    viewer_membership_id: uuid.UUID,
    latest_message=None,
) -> dict:
    participant = None
    active_participants = []
    for item in conversation.participants.all():
        if item.left_at is not None:
            continue
        active_participants.append(item)
        if item.membership_id == viewer_membership_id:
            participant = item
    unread = (
        is_conversation_unread(participant=participant, latest_message=latest_message)
        if participant is not None
        else False
    )
    return {
        "id": conversation.id,
        "type": conversation.type,
        "title": conversation_title(
            conversation=conversation,
            viewer_membership_id=viewer_membership_id,
        ),
        "unread": unread,
        "last_message_at": conversation.last_message_at,
        "last_message_preview": serialize_message(latest_message) if latest_message else None,
        "participants": [serialize_participant_summary(item) for item in active_participants],
    }


class ChatWsTicketView(ChatRateLimitedMixin, EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]
    throttle_scope = settings.CHAT_THROTTLE_SCOPE_WS_TICKET

    @extend_schema(
        tags=["chat"],
        request=None,
        responses={
            200: ChatWsTicketResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        auth_context = request.auth
        if not isinstance(auth_context, AccessTokenAuthContext):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        ticket, expires_in = issue_ws_ticket(
            membership=membership,
            session_id=auth_context.session.id,
        )
        serializer = ChatWsTicketResponseSerializer({"ticket": ticket, "expires_in": expires_in})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChatStatusView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["chat"],
        responses={
            200: ChatStatusSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        from houston.establishments.access import get_api_access_context

        access_context = get_api_access_context(request)
        membership = access_context.active_membership
        if membership is None or membership.establishment_id != self.establishment_id:
            return Response(status=status.HTTP_404_NOT_FOUND)

        payload = build_chat_status(membership=membership)
        return Response(ChatStatusSerializer(payload.__dict__).data)


class ChatConversationListView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        operation_id="chat_conversations_list",
        responses={
            200: ChatConversationListResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        conversations = list(
            list_conversations_for_membership(
                establishment_id=self.establishment_id,
                membership_id=membership.id,
            )
        )
        latest_messages_by_conversation_id = get_latest_messages_by_conversation_ids(
            [conversation.id for conversation in conversations]
        )
        items = [
            _serialize_conversation_list_item(
                conversation=conversation,
                viewer_membership_id=membership.id,
                latest_message=latest_messages_by_conversation_id.get(conversation.id),
            )
            for conversation in conversations
        ]
        return Response(ChatConversationListResponseSerializer({"items": items}).data)


class ChatCreateDmView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        request=ChatCreateDmRequestSerializer,
        responses={
            200: ChatCreateConversationResponseSerializer,
            201: ChatCreateConversationResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        body = ChatCreateDmRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            conversation, created = create_or_get_dm_conversation(
                actor_membership=membership,
                target_membership_id=body.validated_data["membership_id"],
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        conversation = get_conversation_for_participant(
            establishment_id=self.establishment_id,
            conversation_id=conversation.id,
            membership_id=membership.id,
        )
        participant = next(
            item for item in conversation.participants.all() if item.membership_id == membership.id
        )
        latest_message = get_latest_message(conversation.id)
        payload = serialize_conversation_detail(
            conversation=conversation,
            viewer_membership_id=membership.id,
            unread=is_conversation_unread(participant=participant, latest_message=latest_message),
            can_manage=False,
            can_delete=False,
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            ChatCreateConversationResponseSerializer(
                {"conversation": payload, "created": created}
            ).data,
            status=response_status,
        )


class ChatCreateGroupView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        request=ChatCreateGroupRequestSerializer,
        responses={
            201: ChatCreateConversationResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        body = ChatCreateGroupRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            conversation = create_group_conversation(
                actor_membership=membership,
                title=body.validated_data["title"],
                membership_ids=body.validated_data["membership_ids"],
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        conversation = get_conversation_for_participant(
            establishment_id=self.establishment_id,
            conversation_id=conversation.id,
            membership_id=membership.id,
        )
        payload = serialize_conversation_detail(
            conversation=conversation,
            viewer_membership_id=membership.id,
            unread=False,
            can_manage=can_manage_group(membership, conversation),
            can_delete=can_delete_group(membership, conversation),
        )
        return Response(
            ChatCreateConversationResponseSerializer(
                {"conversation": payload, "created": True}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ChatConversationDetailView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        operation_id="chat_conversation_retrieve",
        responses={
            200: ChatConversationDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, conversation_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        conversation = get_conversation_for_participant(
            establishment_id=self.establishment_id,
            conversation_id=uuid.UUID(str(conversation_id)),
            membership_id=membership.id,
        )
        if conversation is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        participant = next(
            item for item in conversation.participants.all() if item.membership_id == membership.id
        )
        latest_message = get_latest_message(conversation.id)
        payload = serialize_conversation_detail(
            conversation=conversation,
            viewer_membership_id=membership.id,
            unread=is_conversation_unread(participant=participant, latest_message=latest_message),
            can_manage=can_manage_group(membership, conversation),
            can_delete=can_delete_group(membership, conversation),
        )
        return Response(ChatConversationDetailSerializer(payload).data)

    @extend_schema(
        tags=["chat"],
        request=ChatRenameGroupRequestSerializer,
        responses={
            200: ChatConversationDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def patch(self, request, establishment_id, conversation_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        body = ChatRenameGroupRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            conversation = rename_group_conversation(
                actor_membership=membership,
                conversation_id=uuid.UUID(str(conversation_id)),
                title=body.validated_data["title"],
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        conversation = get_conversation_for_participant(
            establishment_id=self.establishment_id,
            conversation_id=conversation.id,
            membership_id=membership.id,
        )
        participant = next(
            item for item in conversation.participants.all() if item.membership_id == membership.id
        )
        latest_message = get_latest_message(conversation.id)
        payload = serialize_conversation_detail(
            conversation=conversation,
            viewer_membership_id=membership.id,
            unread=is_conversation_unread(participant=participant, latest_message=latest_message),
            can_manage=can_manage_group(membership, conversation),
            can_delete=can_delete_group(membership, conversation),
        )
        return Response(ChatConversationDetailSerializer(payload).data)

    @extend_schema(
        tags=["chat"],
        responses={
            204: OpenApiResponse(description="Group deleted."),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def delete(self, request, establishment_id, conversation_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        try:
            delete_group_conversation(
                actor_membership=membership,
                conversation_id=uuid.UUID(str(conversation_id)),
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatConversationMessagesView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        parameters=[
            OpenApiParameter(name="page_size", required=False, type=int),
            OpenApiParameter(name="cursor", required=False, type=str),
        ],
        responses={
            200: ChatMessageListResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, conversation_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        conversation = get_conversation_for_participant(
            establishment_id=self.establishment_id,
            conversation_id=uuid.UUID(str(conversation_id)),
            membership_id=membership.id,
        )
        if conversation is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            page_size = _parse_message_page_size(request.query_params.get("page_size"))
            cursor = _parse_message_cursor(request.query_params.get("cursor"))
        except ChatValidationError as exc:
            return _chat_error_response(exc)

        before_created_at = cursor[0] if cursor else None
        before_id = cursor[1] if cursor else None
        messages = list_messages_for_conversation(
            conversation_id=conversation.id,
            limit=page_size + 1,
            before_created_at=before_created_at,
            before_id=before_id,
        )
        has_more = len(messages) > page_size
        page = messages[:page_size]
        page.reverse()
        return Response(
            ChatMessageListResponseSerializer(
                {
                    "items": [serialize_message(message) for message in page],
                    "has_more": has_more,
                }
            ).data
        )


class ChatConversationSeenView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        request=None,
        responses={
            204: OpenApiResponse(description="Conversation marked as seen."),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, conversation_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        try:
            mark_conversation_seen(
                actor_membership=membership,
                conversation_id=uuid.UUID(str(conversation_id)),
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatEligibleMembershipsView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        parameters=[OpenApiParameter(name="q", required=False, type=str)],
        responses={
            200: ChatEligibleMembershipsResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        query = request.query_params.get("q")
        if query and len(query) > CHAT_ELIGIBLE_MEMBERSHIPS_QUERY_MAX_LENGTH:
            return Response(
                {
                    "code": "validation_error",
                    "detail": (
                        "q must be at most "
                        f"{CHAT_ELIGIBLE_MEMBERSHIPS_QUERY_MAX_LENGTH} characters."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        memberships = get_eligible_chat_memberships_queryset(
            establishment_id=self.establishment_id,
            query=query,
        ).exclude(id=membership.id)
        items = [serialize_membership_summary(item) for item in memberships[:100]]
        return Response(ChatEligibleMembershipsResponseSerializer({"items": items}).data)


class ChatAddParticipantView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        request=ChatAddParticipantRequestSerializer,
        responses={
            201: OpenApiResponse(description="Participant added."),
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, conversation_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        body = ChatAddParticipantRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            add_group_participant(
                actor_membership=membership,
                conversation_id=uuid.UUID(str(conversation_id)),
                target_membership_id=body.validated_data["membership_id"],
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        return Response(status=status.HTTP_201_CREATED)


class ChatRemoveParticipantView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        responses={
            204: OpenApiResponse(description="Participant removed."),
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def delete(self, request, establishment_id, conversation_id, membership_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        try:
            remove_group_participant(
                actor_membership=membership,
                conversation_id=uuid.UUID(str(conversation_id)),
                target_membership_id=uuid.UUID(str(membership_id)),
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatPromoteParticipantView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        request=None,
        responses={
            204: OpenApiResponse(description="Participant promoted."),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, conversation_id, membership_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        try:
            promote_group_participant(
                actor_membership=membership,
                conversation_id=uuid.UUID(str(conversation_id)),
                target_membership_id=uuid.UUID(str(membership_id)),
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatLeaveConversationView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        request=None,
        responses={
            204: OpenApiResponse(description="Left group."),
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, conversation_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        try:
            leave_group_conversation(
                actor_membership=membership,
                conversation_id=uuid.UUID(str(conversation_id)),
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatSettingsView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["chat"],
        request=ChatSettingsPatchRequestSerializer,
        responses={
            200: ChatStatusSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def patch(self, request, establishment_id):
        membership = _resolve_settings_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        body = ChatSettingsPatchRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            update_establishment_chat_enabled(
                actor_membership=membership,
                chat_enabled=body.validated_data["chat_enabled"],
            )
        except ChatError as exc:
            return _chat_error_response(exc)

        membership.establishment.refresh_from_db(fields=["chat_enabled", "updated_at"])
        payload = build_chat_status(membership=membership)
        return Response(ChatStatusSerializer(payload.__dict__).data)
