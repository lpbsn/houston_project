from __future__ import annotations

import uuid

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.actions.action_classification import reject_legacy_classification_keys
from houston.actions.api.serializers import (
    ActionCreateRequestSerializer,
    ActionDetailSerializer,
    ActionDueAtRequestSerializer,
    ActionReassignRequestSerializer,
    ExecutionFeedResponseSerializer,
    serialize_action_detail,
    serialize_action_feed_item,
)
from houston.actions.exceptions import ActionStateError, ActionValidationError
from houston.actions.execution_feed import build_execution_feed_page
from houston.actions.execution_feed_cursor import (
    ExecutionFeedCursorError,
    parse_execution_feed_cursor,
)
from houston.actions.models import Action
from houston.actions.permissions import (
    can_accept_action,
    can_cancel_action,
    can_mark_action_done,
    can_reassign_action,
    can_reopen_action,
    can_update_action_due_at,
    can_validate_action_on_object,
)
from houston.actions.selectors import get_action_for_detail
from houston.actions.services import (
    accept_action,
    cancel_action,
    create_action,
    mark_action_done,
    reassign_action,
    reopen_action,
    update_action_due_at,
    validate_action,
)
from houston.checklists.feed_serializers import serialize_checklist_feed_item
from houston.establishments.permissions import HasActiveMembership, can_create_action
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 50


class EstablishmentScopedActionMixin(EstablishmentScopedObservationMixin):
    pass


def _parse_page_size(raw: str | None) -> int:
    if raw is None or raw == "":
        return DEFAULT_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return min(max(value, 1), MAX_PAGE_SIZE)


def _action_overdue(action: Action) -> bool:
    if action.status in {Action.Status.DONE, Action.Status.CANCELED}:
        return False
    return action.due_at < timezone.now()


def _action_command_error_response(exc: Exception) -> Response:
    if isinstance(exc, ActionValidationError):
        return Response(
            {"code": exc.error_code, "detail": str(exc) or "Validation failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, ActionStateError):
        return Response(
            {"code": exc.error_code, "detail": "Invalid action state."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {"code": "api_error", "detail": "Request failed."},
        status=status.HTTP_400_BAD_REQUEST,
    )


class ExecutionFeedView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
    ]

    @extend_schema(
        tags=["actions"],
        parameters=[
            OpenApiParameter(
                name="view_mode",
                required=True,
                type=str,
                enum=["personal", "general"],
            ),
            OpenApiParameter(name="page_size", required=False, type=int),
            OpenApiParameter(
                name="cursor",
                required=False,
                type=str,
                description="Opaque pagination cursor from a previous response next_cursor.",
            ),
        ],
        responses={
            200: ExecutionFeedResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        view_mode = request.query_params.get("view_mode", "").strip().lower()
        if view_mode not in {"personal", "general"}:
            return Response(
                {
                    "code": "validation_error",
                    "detail": "view_mode must be personal or general.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        page_size = _parse_page_size(request.query_params.get("page_size"))
        try:
            cursor = parse_execution_feed_cursor(request.query_params.get("cursor"))
        except ExecutionFeedCursorError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        feed_items, has_more, next_cursor = build_execution_feed_page(
            membership=membership,
            view_mode=view_mode,  # type: ignore[arg-type]
            page_size=page_size,
            cursor=cursor,
        )

        serialized_items = []
        for feed_item in feed_items:
            if feed_item.item_type == "action":
                serialized_items.append(
                    {
                        "item_type": "action",
                        "action": serialize_action_feed_item(
                            action=feed_item.action,
                            membership=membership,
                            is_overdue=_action_overdue(feed_item.action),
                        ),
                        "checklist": None,
                    }
                )
            else:
                serialized_items.append(
                    {
                        "item_type": "checklist",
                        "action": None,
                        "checklist": serialize_checklist_feed_item(
                            execution=feed_item.checklist,
                        ),
                    }
                )

        payload = {
            "items": serialized_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
        return Response(ExecutionFeedResponseSerializer(payload).data)


class ActionCreateView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
    ]

    @extend_schema(
        tags=["actions"],
        request=ActionCreateRequestSerializer,
        responses={
            201: ActionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if not can_create_action(membership):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            reject_legacy_classification_keys(payload=request.data)
        except ActionValidationError as exc:
            return _action_command_error_response(exc)

        body = ActionCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data

        try:
            action = create_action(
                establishment_id=self.establishment_id,
                created_by=membership,
                title=data["title"],
                instruction=data["instruction"],
                assignee_ids=data["assignee_ids"],
                due_at=data["due_at"],
                requires_validation=data.get("requires_validation", True),
                signal_id=data.get("signal"),
                responsible_business_unit_id=data.get("responsible_business_unit_id"),
            )
        except ActionValidationError as exc:
            return _action_command_error_response(exc)

        action = get_action_for_detail(membership=membership, action_id=action.id)
        payload = serialize_action_detail(
            action=action,
            membership=membership,
            is_overdue=_action_overdue(action),
        )
        return Response(ActionDetailSerializer(payload).data, status=status.HTTP_201_CREATED)


class ActionDetailView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
    ]

    @extend_schema(
        tags=["actions"],
        responses={
            200: ActionDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, action_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        action = get_action_for_detail(
            membership=membership,
            action_id=uuid.UUID(str(action_id)),
        )
        if action is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = serialize_action_detail(
            action=action,
            membership=membership,
            is_overdue=_action_overdue(action),
        )
        return Response(ActionDetailSerializer(payload).data)


class ActionAcceptView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["actions"],
        request=None,
        responses={
            200: ActionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, action_id):
        return _action_transition_response(
            request=request,
            establishment_id=self.establishment_id,
            action_id=action_id,
            permission_check=can_accept_action,
            execute_transition=lambda locked_action_id, actor: accept_action(
                action_id=locked_action_id,
                accepted_by=actor,
            ),
        )


class ActionMarkDoneView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["actions"],
        request=None,
        responses={
            200: ActionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, action_id):
        return _action_transition_response(
            request=request,
            establishment_id=self.establishment_id,
            action_id=action_id,
            permission_check=can_mark_action_done,
            execute_transition=lambda locked_action_id, _actor: mark_action_done(
                action_id=locked_action_id,
            ),
        )


class ActionValidateView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["actions"],
        request=None,
        responses={
            200: ActionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, action_id):
        return _action_transition_response(
            request=request,
            establishment_id=self.establishment_id,
            action_id=action_id,
            permission_check=can_validate_action_on_object,
            execute_transition=lambda locked_action_id, _actor: validate_action(
                action_id=locked_action_id,
            ),
        )


class ActionReopenView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["actions"],
        request=None,
        responses={
            200: ActionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, action_id):
        return _action_transition_response(
            request=request,
            establishment_id=self.establishment_id,
            action_id=action_id,
            permission_check=can_reopen_action,
            execute_transition=lambda locked_action_id, _actor: reopen_action(
                action_id=locked_action_id,
            ),
        )


class ActionCancelView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["actions"],
        request=None,
        responses={
            200: ActionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, action_id):
        return _action_transition_response(
            request=request,
            establishment_id=self.establishment_id,
            action_id=action_id,
            permission_check=can_cancel_action,
            execute_transition=lambda locked_action_id, _actor: cancel_action(
                action_id=locked_action_id,
            ),
        )


class ActionReassignView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["actions"],
        request=ActionReassignRequestSerializer,
        responses={200: ActionDetailSerializer},
    )
    def post(self, request, establishment_id, action_id):
        membership, action, error = _load_action_for_command(
            request=request,
            establishment_id=self.establishment_id,
            action_id=action_id,
        )
        if error is not None:
            return error
        if not can_reassign_action(membership, action):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )
        body = ActionReassignRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            action = reassign_action(
                action_id=action.id,
                assignee_ids=body.validated_data["assignee_ids"],
            )
        except (ActionStateError, ActionValidationError) as exc:
            return _action_command_error_response(exc)
        action = get_action_for_detail(membership=membership, action_id=action.id)
        payload = serialize_action_detail(
            action=action,
            membership=membership,
            is_overdue=_action_overdue(action),
        )
        return Response(ActionDetailSerializer(payload).data)


class ActionDueAtView(EstablishmentScopedActionMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["actions"],
        request=ActionDueAtRequestSerializer,
        responses={200: ActionDetailSerializer},
    )
    def patch(self, request, establishment_id, action_id):
        membership, action, error = _load_action_for_command(
            request=request,
            establishment_id=self.establishment_id,
            action_id=action_id,
        )
        if error is not None:
            return error
        if not can_update_action_due_at(membership, action):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )
        body = ActionDueAtRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            action = update_action_due_at(
                action_id=action.id,
                due_at=body.validated_data["due_at"],
            )
        except ActionStateError as exc:
            return _action_command_error_response(exc)
        action = get_action_for_detail(membership=membership, action_id=action.id)
        payload = serialize_action_detail(
            action=action,
            membership=membership,
            is_overdue=_action_overdue(action),
        )
        return Response(ActionDetailSerializer(payload).data)


def _load_action_for_command(*, request, establishment_id, action_id):
    membership = resolve_observation_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return None, None, Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    action = get_action_for_detail(
        membership=membership,
        action_id=uuid.UUID(str(action_id)),
    )
    if action is None:
        return (
            membership,
            None,
            Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            ),
        )
    return membership, action, None


def _action_transition_response(
    *,
    request,
    establishment_id,
    action_id,
    permission_check,
    execute_transition,
) -> Response:
    membership, action, error = _load_action_for_command(
        request=request,
        establishment_id=establishment_id,
        action_id=action_id,
    )
    if error is not None:
        return error
    if not permission_check(membership, action):
        return Response(
            {"code": "permission_denied", "detail": "Permission denied."},
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        action = execute_transition(action.id, membership)
    except (ActionStateError, ActionValidationError) as exc:
        return _action_command_error_response(exc)
    action = get_action_for_detail(membership=membership, action_id=action.id)
    payload = serialize_action_detail(
        action=action,
        membership=membership,
        is_overdue=_action_overdue(action),
    )
    return Response(ActionDetailSerializer(payload).data)
