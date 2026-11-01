from drf_spectacular.utils import extend_schema
from houston.accounts.api.legal_errors import legal_error_response
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.accounts.legal_services import AiConsentRequiredError, TermsAcceptanceRequiredError
from houston.action_plans.exceptions import ActionPlanPermissionError, ActionPlanServiceError
from houston.chat.api.serializers import ChatMessageSerializer, serialize_message
from houston.chat.api.views import (
    CanAccessChat,
    EstablishmentScopedChatMixin,
    chat_error_response,
    parse_message_cursor,
    resolve_chat_request_membership,
)
from houston.chat.exceptions import ChatError
from houston.chat.message_tools import (
    acknowledge_message,
    observation_from_message,
    require_message,
    set_conversation_notifications,
)
from houston.chat.selectors import get_active_participant
from houston.chat.workspace_selectors import communication_search, plan_discussions
from houston.comments.discussion_services import (
    require_execution,
    task_from_comment,
    update_comment_tool,
    update_discussion_preference,
)
from houston.comments.exceptions import CommentError, CommentNotFoundError, CommentPermissionError
from houston.comments.models import PlanDiscussionPreference
from houston.establishments.permissions import HasActiveMembership
from houston.observations.exceptions import ObservationValidationError
from houston.uploads.access import resolve_observation_actor_membership
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView


class CommunicationView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership, CanAccessChat]


class WorkspaceQuerySerializer(serializers.Serializer):
    tab = serializers.ChoiceField(choices=["plans", "mentions", "search"], default="plans")
    q = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    cursor = serializers.CharField(required=False)
    unresolved = serializers.BooleanField(default=False)
    files_only = serializers.BooleanField(default=False)
    author_id = serializers.UUIDField(required=False)
    execution_id = serializers.UUIDField(required=False)
    after = serializers.DateTimeField(required=False)
    before = serializers.DateTimeField(required=False)


class WorkspaceItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=["chat", "plan"])
    parent_id = serializers.UUIDField()
    title = serializers.CharField()
    body = serializers.CharField(allow_blank=True)
    author = serializers.CharField()
    created_at = serializers.DateTimeField()
    unresolved = serializers.BooleanField()
    unread = serializers.BooleanField()


class WorkspaceResponseSerializer(serializers.Serializer):
    items = WorkspaceItemSerializer(many=True)
    cursor = serializers.CharField(allow_null=True)


def comment_error_response(exc: CommentError) -> Response:
    if isinstance(exc, CommentNotFoundError):
        return Response(status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, CommentPermissionError):
        return Response(
            {"code": exc.code, "detail": exc.message},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class CommunicationWorkspaceView(CommunicationView):
    @extend_schema(
        tags=["chat"], parameters=[WorkspaceQuerySerializer], responses=WorkspaceResponseSerializer
    )
    def get(self, request, establishment_id):
        member = resolve_chat_request_membership(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        query = WorkspaceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        filters = dict(query.validated_data)
        tab = filters.pop("tab")
        try:
            cursor = parse_message_cursor(filters.pop("cursor", None))
        except ChatError as exc:
            return chat_error_response(exc)
        if cursor and cursor[0].tzinfo is None:
            raise ValidationError("Le curseur doit inclure le fuseau horaire.")
        if tab == "plans":
            result = plan_discussions(
                membership=member, cursor=cursor, unresolved=filters["unresolved"]
            )
        else:
            filters.pop("unresolved")
            result = communication_search(
                membership=member,
                cursor=cursor,
                query=filters.pop("q"),
                mentions=tab == "mentions",
                **filters,
            )
        return Response(WorkspaceResponseSerializer(result).data)


class MessageToolRequestSerializer(serializers.Serializer):
    operation = serializers.ChoiceField(choices=["acknowledge", "observe"])
    active = serializers.BooleanField(default=True)
    text = serializers.CharField(required=False, min_length=10, max_length=1000)


class ToolResultSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    target_id = serializers.UUIDField(required=False, allow_null=True)


class MessageToolView(CommunicationView):
    http_method_names = ["get", "post", "options"]

    @extend_schema(tags=["chat"], responses=ChatMessageSerializer)
    def get(self, request, establishment_id, message_id):
        member = resolve_chat_request_membership(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        try:
            message = require_message(membership=member, message_id=message_id)
        except ChatError as exc:
            return chat_error_response(exc)
        participant = get_active_participant(
            conversation_id=message.conversation_id, membership_id=member.id
        )
        return Response(
            ChatMessageSerializer(
                serialize_message(
                    message,
                    history_cutoff_at=participant.history_cutoff_at,
                    viewer_membership_id=member.id,
                )
            ).data
        )

    @extend_schema(
        tags=["chat"], request=MessageToolRequestSerializer, responses=ToolResultSerializer
    )
    def post(self, request, establishment_id, message_id):
        member = resolve_chat_request_membership(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        tool_request = MessageToolRequestSerializer(data=request.data)
        tool_request.is_valid(raise_exception=True)
        payload = tool_request.validated_data
        try:
            if payload["operation"] == "observe":
                if not payload.get("text"):
                    raise ValidationError("Relisez le texte avant de confirmer son partage.")
                source = observation_from_message(
                    membership=member, message_id=message_id, text=payload["text"]
                )
                # Do not expose the private observation identifier to other participants.
                target = (
                    source.observation_id
                    if source.observation.submitted_by_membership_id == member.id
                    else None
                )
                return Response(dict(success=True, target_id=target))
            acknowledge_message(membership=member, message_id=message_id, active=payload["active"])
        except (TermsAcceptanceRequiredError, AiConsentRequiredError) as exc:
            return legal_error_response(exc)
        except ObservationValidationError as exc:
            raise ValidationError(str(exc)) from exc
        except ChatError as exc:
            return chat_error_response(exc)
        return Response(dict(success=True))


class DiscussionPreferenceSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["all", "mentions", "silent"], required=False)
    seen = serializers.BooleanField(default=False)
    seen_through = serializers.DateTimeField(required=False)


class ConversationNotificationView(CommunicationView):
    http_method_names = ["post", "options"]

    @extend_schema(
        tags=["chat"], request=DiscussionPreferenceSerializer, responses=ToolResultSerializer
    )
    def post(self, request, establishment_id, conversation_id):
        member = resolve_chat_request_membership(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        preference = DiscussionPreferenceSerializer(data=request.data)
        preference.is_valid(raise_exception=True)
        try:
            set_conversation_notifications(
                membership=member,
                conversation_id=conversation_id,
                mode=preference.validated_data.get("mode", "all"),
            )
        except ChatError as exc:
            return chat_error_response(exc)
        return Response(dict(success=True))


class PlanDiscussionPreferenceView(CommunicationView):
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["comments"], request=DiscussionPreferenceSerializer, responses=ToolResultSerializer
    )
    def post(self, request, establishment_id, execution_id):
        member = resolve_plan_member(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        preference = DiscussionPreferenceSerializer(data=request.data)
        preference.is_valid(raise_exception=True)
        try:
            update_discussion_preference(
                membership=member, execution_id=execution_id, **preference.validated_data
            )
        except CommentError as exc:
            return comment_error_response(exc)
        return Response(dict(success=True))

    @extend_schema(tags=["comments"], responses=DiscussionPreferenceSerializer)
    def get(self, request, establishment_id, execution_id):
        member = resolve_plan_member(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        try:
            require_execution(membership=member, execution_id=execution_id)
        except CommentError as exc:
            return comment_error_response(exc)
        preference = PlanDiscussionPreference.objects.filter(
            execution_id=execution_id, membership=member
        ).first()
        return Response(
            dict(mode=preference.notification_mode if preference else "all", seen=False)
        )


class CommentToolRequestSerializer(serializers.Serializer):
    operation = serializers.ChoiceField(choices=["pin", "acknowledge", "task"])
    active = serializers.BooleanField(default=True)
    title = serializers.CharField(required=False, max_length=255)
    assigned_membership_id = serializers.UUIDField(required=False, allow_null=True)
    deadline_at = serializers.DateTimeField(required=False, allow_null=True)


class CommentToolView(CommunicationView):
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]
    http_method_names = ["post", "options"]

    @extend_schema(
        tags=["comments"], request=CommentToolRequestSerializer, responses=ToolResultSerializer
    )
    def post(self, request, establishment_id, comment_id):
        member = resolve_plan_member(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        tool_request = CommentToolRequestSerializer(data=request.data)
        tool_request.is_valid(raise_exception=True)
        payload = tool_request.validated_data
        try:
            if payload["operation"] == "task":
                if not payload.get("title"):
                    raise ValidationError("Donnez un titre à la tâche.")
                task_id = task_from_comment(
                    membership=member,
                    comment_id=comment_id,
                    title=payload["title"],
                    assigned_membership_id=payload.get("assigned_membership_id"),
                    deadline_at=payload.get("deadline_at"),
                )
                return Response(dict(success=True, target_id=task_id))
            update_comment_tool(
                membership=member,
                comment_id=comment_id,
                operation=payload["operation"],
                active=payload["active"],
            )
        except CommentError as exc:
            return comment_error_response(exc)
        except ActionPlanServiceError as exc:
            return Response(
                {"detail": str(exc)},
                status=(
                    status.HTTP_403_FORBIDDEN
                    if isinstance(exc, ActionPlanPermissionError)
                    else status.HTTP_400_BAD_REQUEST
                ),
            )
        return Response(dict(success=True))


def resolve_plan_member(request, establishment_id):
    member = resolve_observation_actor_membership(request, establishment_id=establishment_id)
    if member is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return member
