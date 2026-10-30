from drf_spectacular.utils import extend_schema
from houston.accounts.api.legal_errors import legal_error_response
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.accounts.legal_services import AiConsentRequiredError, TermsAcceptanceRequiredError
from houston.action_plans.exceptions import ActionPlanPermissionError, ActionPlanServiceError
from houston.chat.api.serializers import ChatMessageSerializer
from houston.chat.api.views import (
    CanAccessChat,
    EstablishmentScopedChatMixin,
    _chat_error_response,
    _parse_message_cursor,
    _resolve_membership,
)
from houston.chat.exceptions import ChatError
from houston.chat.message_tools import (
    acknowledge_message,
    observation_from_message,
    require_message,
    set_conversation_notifications,
)
from houston.chat.workspace_selectors import communication_search, plan_discussions
from houston.comments.discussion_services import (
    require_execution,
    task_from_comment,
    update_comment_tool,
    update_discussion_preference,
)
from houston.comments.models import PlanDiscussionPreference
from houston.establishments.permissions import HasActiveMembership
from houston.observations.exceptions import ObservationValidationError
from rest_framework import permissions, serializers
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


class CommunicationWorkspaceView(CommunicationView):
    @extend_schema(
        tags=["chat"], parameters=[WorkspaceQuerySerializer], responses=WorkspaceResponseSerializer
    )
    def get(self, request, establishment_id):
        member = _resolve_membership(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        s = WorkspaceQuerySerializer(data=request.query_params)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        tab = data.pop("tab")
        try:
            cursor = _parse_message_cursor(data.pop("cursor", None))
        except ChatError as exc:
            return _chat_error_response(exc)
        if cursor and cursor[0].tzinfo is None:
            raise ValidationError("Le curseur doit inclure le fuseau horaire.")
        if tab == "plans":
            result = plan_discussions(
                membership=member, cursor=cursor, unresolved=data["unresolved"]
            )
        else:
            data.pop("unresolved")
            result = communication_search(
                membership=member,
                cursor=cursor,
                query=data.pop("q"),
                mentions=tab == "mentions",
                **data,
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
        from houston.chat.api.serializers import ChatMessageSerializer, serialize_message
        from houston.chat.selectors import get_active_participant

        member = _resolve_membership(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        try:
            message = require_message(membership=member, message_id=message_id)
        except ChatError as exc:
            return _chat_error_response(exc)
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
        member = _resolve_membership(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        s = MessageToolRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        try:
            if data["operation"] == "observe":
                if not data.get("text"):
                    raise ValidationError("Relisez le texte avant de confirmer son partage.")
                source = observation_from_message(
                    membership=member, message_id=message_id, text=data["text"]
                )
                # Do not expose the private observation identifier to other participants.
                target = (
                    source.observation_id
                    if source.observation.submitted_by_membership_id == member.id
                    else None
                )
                return Response(dict(success=True, target_id=target))
            acknowledge_message(membership=member, message_id=message_id, active=data["active"])
        except (TermsAcceptanceRequiredError, AiConsentRequiredError) as exc:
            return legal_error_response(exc)
        except ObservationValidationError as exc:
            raise ValidationError(str(exc)) from exc
        except ChatError as exc:
            return _chat_error_response(exc)
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
        member = _resolve_membership(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        s = DiscussionPreferenceSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            set_conversation_notifications(
                membership=member,
                conversation_id=conversation_id,
                mode=s.validated_data.get("mode", "all"),
            )
        except ChatError as exc:
            return _chat_error_response(exc)
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
        s = DiscussionPreferenceSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            update_discussion_preference(
                membership=member, execution_id=execution_id, **s.validated_data
            )
        except ChatError as exc:
            return _chat_error_response(exc)
        return Response(dict(success=True))

    @extend_schema(tags=["comments"], responses=DiscussionPreferenceSerializer)
    def get(self, request, establishment_id, execution_id):
        member = resolve_plan_member(request, self.establishment_id)
        if isinstance(member, Response):
            return member
        try:
            require_execution(membership=member, execution_id=execution_id)
        except ChatError as exc:
            return _chat_error_response(exc)
        pref = PlanDiscussionPreference.objects.filter(
            execution_id=execution_id, membership=member
        ).first()
        return Response(dict(mode=pref.notification_mode if pref else "all", seen=False))


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
        s = CommentToolRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            if d["operation"] == "task":
                if not d.get("title"):
                    raise ValidationError("Donnez un titre à la tâche.")
                task_id = task_from_comment(
                    membership=member,
                    comment_id=comment_id,
                    title=d["title"],
                    assigned_membership_id=d.get("assigned_membership_id"),
                    deadline_at=d.get("deadline_at"),
                )
                return Response(dict(success=True, target_id=task_id))
            update_comment_tool(
                membership=member,
                comment_id=comment_id,
                operation=d["operation"],
                active=d["active"],
            )
        except ChatError as exc:
            return _chat_error_response(exc)
        except ActionPlanServiceError as exc:
            return Response(
                dict(detail=str(exc)),
                status=403 if isinstance(exc, ActionPlanPermissionError) else 400,
            )
        return Response(dict(success=True))


def resolve_plan_member(request, establishment_id):
    from houston.uploads.access import resolve_observation_actor_membership

    member = resolve_observation_actor_membership(request, establishment_id=establishment_id)
    return member if member is not None else Response(status=404)
