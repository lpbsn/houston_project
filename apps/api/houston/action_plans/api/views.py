from __future__ import annotations

import uuid

from django.db.models import Count
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    PolymorphicProxySerializer,
    extend_schema,
)
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.action_plans.api.serializers import (
    ActionPlanActiveExecutionConflictSerializer,
    ActionPlanCreateRequestSerializer,
    ActionPlanDetailSerializer,
    ActionPlanExecutionDetailSerializer,
    ActionPlanListItemSerializer,
    ActionPlanScheduleCreateRequestSerializer,
    ActionPlanScheduleDetailSerializer,
    ActionPlanScheduleUpdateRequestSerializer,
    ActionPlanTaskCreateObservationRequestSerializer,
    ActionPlanTaskCreateObservationResponseSerializer,
    ActionPlanTaskExecutionSerializer,
    ActionPlanTaskSkipRequestSerializer,
    ActionPlanUpdateRequestSerializer,
    ActionPlanUseRequestSerializer,
    serialize_action_plan_detail,
    serialize_action_plan_list_item,
    serialize_execution_detail,
    serialize_schedule_detail,
    serialize_task_execution,
)
from houston.action_plans.exceptions import (
    ActionPlanConflictError,
    ActionPlanPermissionError,
    ActionPlanStateError,
    ActionPlanValidationError,
)
from houston.action_plans.execution_feed import build_action_plan_execution_feed_page
from houston.action_plans.feed_cursor import (
    ActionPlanExecutionFeedCursorError,
    parse_action_plan_execution_feed_cursor,
)
from houston.action_plans.feed_serializers import (
    ActionPlanExecutionFeedResponseSerializer,
    serialize_action_plan_execution_feed_item,
)
from houston.action_plans.permissions import can_view_action_plan_catalog
from houston.action_plans.schedule_services import (
    create_action_plan_schedule,
    deactivate_action_plan_schedule,
    update_action_plan_schedule,
)
from houston.action_plans.selectors import (
    catalog_action_plans_for_list,
    get_action_plan_execution_for_detail,
    get_action_plan_execution_task_for_command,
    get_action_plan_for_detail,
    get_action_plan_schedule_for_detail,
)
from houston.action_plans.services import (
    activate_action_plan,
    cancel_action_plan_execution,
    create_action_plan,
    create_action_plan_with_execution,
    create_action_plan_with_optional_schedule,
    create_execution_from_action_plan,
    create_observation_from_execution_task,
    deactivate_action_plan,
    mark_action_plan_execution_done,
    mark_execution_task_done,
    reopen_action_plan_execution,
    skip_execution_task,
    update_action_plan,
    validate_action_plan_execution,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import HasActiveMembership
from houston.establishments.timezone_utils import establishment_local_date
from houston.observations.models import ObservationProcessing
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin


class EstablishmentScopedActionPlanMixin(EstablishmentScopedObservationMixin):
    pass


DEFAULT_FEED_PAGE_SIZE = 25
MAX_FEED_PAGE_SIZE = 50


def _parse_feed_page_size(raw: str | None) -> int:
    if raw is None or raw == "":
        return DEFAULT_FEED_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_FEED_PAGE_SIZE
    return min(max(value, 1), MAX_FEED_PAGE_SIZE)


def _action_plan_error_response(exc: Exception) -> Response:
    if isinstance(exc, ActionPlanPermissionError):
        return Response(
            {"code": "permission_denied", "detail": str(exc) or "Permission denied."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, ActionPlanStateError):
        return Response(
            {
                "code": "invalid_action_plan_state",
                "detail": str(exc) or "Invalid action plan state.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, ActionPlanValidationError):
        return Response(
            {"code": "validation_error", "detail": str(exc) or "Validation failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {"code": "api_error", "detail": "Request failed."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _resolve_membership(request, establishment_id) -> Response | object:
    membership = resolve_observation_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return membership


def _task_payloads(tasks_data: list[dict]) -> list[dict]:
    return [
        {
            "task": item["task"],
            "business_unit_id": item["business_unit_id"],
            "position": item.get("position"),
        }
        for item in tasks_data
    ]


def _assignee_payloads(assignees_data: list[dict]) -> list[dict]:
    return [
        {
            "membership_id": item["membership_id"],
            "business_unit_id": item["business_unit_id"],
            "start_at": item.get("start_at"),
            "visible_from": item.get("visible_from"),
            "end_at": item.get("end_at"),
        }
        for item in assignees_data
    ]


def _schedule_assignee_payloads(assignees_data: list[dict]) -> list[dict]:
    return [
        {
            "membership_id": item["membership_id"],
            "business_unit_id": item["business_unit_id"],
            "start_at": item.get("start_at"),
            "end_at": item.get("end_at"),
        }
        for item in assignees_data
    ]


def _action_plan_conflict_response(exc: ActionPlanConflictError) -> Response:
    if exc.active_execution_id is not None:
        return Response(
            ActionPlanActiveExecutionConflictSerializer(
                {
                    "code": "conflict",
                    "detail": str(exc) or "Conflict.",
                    "active_execution_id": exc.active_execution_id,
                }
            ).data,
            status=status.HTTP_409_CONFLICT,
        )
    return _action_plan_error_response(exc)


def _is_catalog_create(*, validated_data: dict, membership) -> bool:
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if validated_data.get("source_signal_id"):
        return False
    if validated_data.get("assignees"):
        return False
    return validated_data.get("is_reusable") is True


_ACTION_PLAN_CREATE_201_RESPONSE = PolymorphicProxySerializer(
    component_name="ActionPlanCreate201Response",
    serializers=[
        ActionPlanDetailSerializer,
        ActionPlanExecutionDetailSerializer,
    ],
    resource_type_field_name=None,
)


class ActionPlanListCreateView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        parameters=[
            OpenApiParameter(name="created_by_me", required=False, type=bool),
            OpenApiParameter(name="business_unit_id", required=False, type=str),
        ],
        responses={
            200: ActionPlanListItemSerializer(many=True),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership
        if not can_view_action_plan_catalog(membership):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        created_by_me = request.query_params.get("created_by_me", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        business_unit_id = None
        business_unit_raw = request.query_params.get("business_unit_id", "").strip()
        if business_unit_raw:
            try:
                business_unit_id = uuid.UUID(business_unit_raw)
            except ValueError:
                return Response(
                    {
                        "code": "validation_error",
                        "detail": "business_unit_id must be a valid UUID.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        queryset = (
            catalog_action_plans_for_list(
                membership=membership,
                created_by_me=created_by_me,
                business_unit_id=business_unit_id,
            )
            .annotate(
                task_count=Count("tasks", distinct=True),
                involved_pole_count=Count("tasks__business_unit", distinct=True),
            )
            .order_by("-updated_at", "-created_at")
        )
        payload = [
            serialize_action_plan_list_item(action_plan, membership=membership)
            for action_plan in queryset
        ]
        return Response(ActionPlanListItemSerializer(payload, many=True).data)

    @extend_schema(
        tags=["action-plans"],
        request=ActionPlanCreateRequestSerializer,
        responses={
            201: _ACTION_PLAN_CREATE_201_RESPONSE,
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

        body = ActionPlanCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        schedule_data = data.get("schedule")

        try:
            if schedule_data is not None:
                action_plan, execution = create_action_plan_with_optional_schedule(
                    establishment_id=self.establishment_id,
                    created_by=membership,
                    pilot_business_unit_id=data["pilot_business_unit_id"],
                    title=data["title"],
                    description=data.get("description", ""),
                    requires_validation=data.get("requires_validation", True),
                    tasks=_task_payloads(data.get("tasks") or []),
                    schedule=schedule_data,
                    assignees=_assignee_payloads(data.get("assignees") or []),
                    source_signal_id=data.get("source_signal_id"),
                    use_shared_chronology=data.get("use_shared_chronology", False),
                    start_at=data.get("start_at"),
                    end_at=data.get("end_at"),
                    visible_from=data.get("visible_from"),
                    occurrence_date=data.get("occurrence_date"),
                )
                if execution is not None:
                    execution = get_action_plan_execution_for_detail(
                        membership=membership,
                        execution_id=execution.id,
                    )
                    payload = serialize_execution_detail(execution, membership=membership)
                    return Response(
                        ActionPlanExecutionDetailSerializer(payload).data,
                        status=status.HTTP_201_CREATED,
                    )

                action_plan = get_action_plan_for_detail(
                    membership=membership,
                    action_plan_id=action_plan.id,
                )
                payload = serialize_action_plan_detail(action_plan, membership=membership)
                return Response(
                    ActionPlanDetailSerializer(payload).data,
                    status=status.HTTP_201_CREATED,
                )

            if _is_catalog_create(validated_data=data, membership=membership):
                action_plan = create_action_plan(
                    establishment_id=self.establishment_id,
                    created_by=membership,
                    pilot_business_unit_id=data["pilot_business_unit_id"],
                    title=data["title"],
                    description=data.get("description", ""),
                    requires_validation=data.get("requires_validation", True),
                    is_reusable=True,
                    tasks=_task_payloads(data.get("tasks") or []),
                )
                action_plan = get_action_plan_for_detail(
                    membership=membership,
                    action_plan_id=action_plan.id,
                )
                payload = serialize_action_plan_detail(action_plan, membership=membership)
                return Response(
                    ActionPlanDetailSerializer(payload).data,
                    status=status.HTTP_201_CREATED,
                )

            _, execution = create_action_plan_with_execution(
                establishment_id=self.establishment_id,
                created_by=membership,
                pilot_business_unit_id=data["pilot_business_unit_id"],
                title=data["title"],
                description=data.get("description", ""),
                requires_validation=data.get("requires_validation", True),
                tasks=_task_payloads(data.get("tasks") or []),
                assignees=_assignee_payloads(data.get("assignees") or []),
                source_signal_id=data.get("source_signal_id"),
                is_reusable=data.get("is_reusable", False),
                use_shared_chronology=data.get("use_shared_chronology", False),
                start_at=data.get("start_at"),
                end_at=data.get("end_at"),
                visible_from=data.get("visible_from"),
                occurrence_date=data.get("occurrence_date"),
            )
        except (ActionPlanPermissionError, ActionPlanValidationError, ActionPlanStateError) as exc:
            return _action_plan_error_response(exc)

        execution = get_action_plan_execution_for_detail(
            membership=membership,
            execution_id=execution.id,
        )
        payload = serialize_execution_detail(execution, membership=membership)
        return Response(
            ActionPlanExecutionDetailSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class ActionPlanDetailView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        responses={
            200: ActionPlanDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, action_plan_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        action_plan = get_action_plan_for_detail(
            membership=membership,
            action_plan_id=uuid.UUID(str(action_plan_id)),
        )
        if action_plan is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = serialize_action_plan_detail(action_plan, membership=membership)
        return Response(ActionPlanDetailSerializer(payload).data)

    @extend_schema(
        tags=["action-plans"],
        request=ActionPlanUpdateRequestSerializer,
        responses={
            200: ActionPlanDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def patch(self, request, establishment_id, action_plan_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        action_plan = get_action_plan_for_detail(
            membership=membership,
            action_plan_id=uuid.UUID(str(action_plan_id)),
        )
        if action_plan is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ActionPlanUpdateRequestSerializer(data=request.data, partial=True)
        body.is_valid(raise_exception=True)

        try:
            action_plan = update_action_plan(
                action_plan=action_plan,
                actor=membership,
                title=body.validated_data.get("title"),
                description=body.validated_data.get("description"),
            )
        except (ActionPlanPermissionError, ActionPlanValidationError) as exc:
            return _action_plan_error_response(exc)

        action_plan = get_action_plan_for_detail(
            membership=membership,
            action_plan_id=action_plan.id,
        )
        payload = serialize_action_plan_detail(action_plan, membership=membership)
        return Response(ActionPlanDetailSerializer(payload).data)


def _action_plan_command_response(*, request, establishment_id, action_plan_id, service_fn):
    membership = _resolve_membership(request, establishment_id)
    if isinstance(membership, Response):
        return membership

    action_plan = get_action_plan_for_detail(
        membership=membership,
        action_plan_id=uuid.UUID(str(action_plan_id)),
    )
    if action_plan is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        service_fn(action_plan=action_plan, actor=membership)
    except (ActionPlanPermissionError, ActionPlanValidationError) as exc:
        return _action_plan_error_response(exc)

    action_plan = get_action_plan_for_detail(
        membership=membership,
        action_plan_id=action_plan.id,
    )
    payload = serialize_action_plan_detail(action_plan, membership=membership)
    return Response(ActionPlanDetailSerializer(payload).data)


class ActionPlanActivateView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=None,
        responses={
            200: ActionPlanDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, action_plan_id):
        return _action_plan_command_response(
            request=request,
            establishment_id=self.establishment_id,
            action_plan_id=action_plan_id,
            service_fn=activate_action_plan,
        )


class ActionPlanDeactivateView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=None,
        responses={
            200: ActionPlanDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, action_plan_id):
        return _action_plan_command_response(
            request=request,
            establishment_id=self.establishment_id,
            action_plan_id=action_plan_id,
            service_fn=deactivate_action_plan,
        )


class ActionPlanUseView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=ActionPlanUseRequestSerializer,
        responses={
            201: ActionPlanExecutionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, action_plan_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        action_plan = get_action_plan_for_detail(
            membership=membership,
            action_plan_id=uuid.UUID(str(action_plan_id)),
        )
        if action_plan is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ActionPlanUseRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data

        try:
            execution = create_execution_from_action_plan(
                action_plan_id=action_plan.id,
                actor=membership,
                assignees=_assignee_payloads(data.get("assignees") or []),
                use_shared_chronology=data.get("use_shared_chronology", False),
                start_at=data.get("start_at"),
                end_at=data.get("end_at"),
                visible_from=data.get("visible_from"),
                occurrence_date=data.get("occurrence_date"),
            )
        except (ActionPlanPermissionError, ActionPlanValidationError) as exc:
            return _action_plan_error_response(exc)

        execution = get_action_plan_execution_for_detail(
            membership=membership,
            execution_id=execution.id,
        )
        payload = serialize_execution_detail(execution, membership=membership)
        return Response(
            ActionPlanExecutionDetailSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class ActionPlanExecutionDetailView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        responses={
            200: ActionPlanExecutionDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, execution_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        execution = get_action_plan_execution_for_detail(
            membership=membership,
            execution_id=uuid.UUID(str(execution_id)),
        )
        if execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = serialize_execution_detail(execution, membership=membership)
        return Response(ActionPlanExecutionDetailSerializer(payload).data)


def _execution_command_response(*, request, establishment_id, execution_id, service_fn):
    membership = _resolve_membership(request, establishment_id)
    if isinstance(membership, Response):
        return membership

    execution = get_action_plan_execution_for_detail(
        membership=membership,
        execution_id=uuid.UUID(str(execution_id)),
    )
    if execution is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        execution = service_fn(
            execution_id=execution.id,
            actor_membership=membership,
        )
    except (ActionPlanPermissionError, ActionPlanValidationError, ActionPlanStateError) as exc:
        return _action_plan_error_response(exc)

    execution = get_action_plan_execution_for_detail(
        membership=membership,
        execution_id=execution.id,
    )
    payload = serialize_execution_detail(execution, membership=membership)
    return Response(ActionPlanExecutionDetailSerializer(payload).data)


class ActionPlanExecutionMarkDoneView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=None,
        responses={
            200: ActionPlanExecutionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, execution_id):
        return _execution_command_response(
            request=request,
            establishment_id=self.establishment_id,
            execution_id=execution_id,
            service_fn=mark_action_plan_execution_done,
        )


class ActionPlanExecutionValidateView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=None,
        responses={
            200: ActionPlanExecutionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, execution_id):
        return _execution_command_response(
            request=request,
            establishment_id=self.establishment_id,
            execution_id=execution_id,
            service_fn=validate_action_plan_execution,
        )


def _reopen_execution(*, execution_id, actor_membership):
    return reopen_action_plan_execution(
        execution_id=execution_id,
        actor=actor_membership,
    )


def _cancel_execution(*, execution_id, actor_membership):
    return cancel_action_plan_execution(
        execution_id=execution_id,
        actor=actor_membership,
    )


class ActionPlanExecutionReopenView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=None,
        responses={
            200: ActionPlanExecutionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, execution_id):
        return _execution_command_response(
            request=request,
            establishment_id=self.establishment_id,
            execution_id=execution_id,
            service_fn=_reopen_execution,
        )


class ActionPlanExecutionCancelView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=None,
        responses={
            200: ActionPlanExecutionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, execution_id):
        return _execution_command_response(
            request=request,
            establishment_id=self.establishment_id,
            execution_id=execution_id,
            service_fn=_cancel_execution,
        )


def _task_command_response(*, request, establishment_id, task_execution_id, service_fn, body=None):
    membership = _resolve_membership(request, establishment_id)
    if isinstance(membership, Response):
        return membership

    task_execution = get_action_plan_execution_task_for_command(
        membership=membership,
        task_execution_id=uuid.UUID(str(task_execution_id)),
    )
    if task_execution is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        task_execution = service_fn(
            task_execution=task_execution,
            actor=membership,
            **(body or {}),
        )
    except (ActionPlanPermissionError, ActionPlanValidationError, ActionPlanStateError) as exc:
        return _action_plan_error_response(exc)

    payload = serialize_task_execution(task_execution, membership=membership)
    return Response(ActionPlanTaskExecutionSerializer(payload).data)


class ActionPlanExecutionTaskMarkDoneView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=None,
        responses={
            200: ActionPlanTaskExecutionSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, task_execution_id):
        return _task_command_response(
            request=request,
            establishment_id=self.establishment_id,
            task_execution_id=task_execution_id,
            service_fn=mark_execution_task_done,
        )


class ActionPlanExecutionTaskSkipView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=ActionPlanTaskSkipRequestSerializer,
        responses={
            200: ActionPlanTaskExecutionSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, task_execution_id):
        body = ActionPlanTaskSkipRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        skipped_reason = body.validated_data.get("skipped_reason")

        def _skip(*, task_execution, actor):
            return skip_execution_task(
                task_execution=task_execution,
                actor=actor,
                skipped_reason=skipped_reason,
            )

        return _task_command_response(
            request=request,
            establishment_id=self.establishment_id,
            task_execution_id=task_execution_id,
            service_fn=_skip,
        )


class ActionPlanExecutionTaskCreateObservationView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=ActionPlanTaskCreateObservationRequestSerializer,
        responses={
            201: ActionPlanTaskCreateObservationResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, task_execution_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        task_execution = get_action_plan_execution_task_for_command(
            membership=membership,
            task_execution_id=uuid.UUID(str(task_execution_id)),
        )
        if task_execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ActionPlanTaskCreateObservationRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        try:
            updated = create_observation_from_execution_task(
                task_execution=task_execution,
                actor=membership,
                text=body.validated_data["text"],
                temporary_upload_ids=body.validated_data.get("temporary_upload_ids", []),
            )
        except (ActionPlanPermissionError, ActionPlanValidationError) as exc:
            return _action_plan_error_response(exc)

        payload = {
            "task_execution_id": updated.id,
            "observation_id": updated.observation_id,
            "status": updated.status,
            "processing_status": ObservationProcessing.Status.QUEUED,
        }
        return Response(
            ActionPlanTaskCreateObservationResponseSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class ActionPlanScheduleCreateView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=ActionPlanScheduleCreateRequestSerializer,
        responses={
            201: ActionPlanScheduleDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, action_plan_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        action_plan = get_action_plan_for_detail(
            membership=membership,
            action_plan_id=uuid.UUID(str(action_plan_id)),
        )
        if action_plan is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ActionPlanScheduleCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data

        try:
            schedule = create_action_plan_schedule(
                action_plan=action_plan,
                actor=membership,
                start_date=data.get("start_date")
                or establishment_local_date(establishment=action_plan.establishment),
                end_date=data["end_date"],
                start_at=data["start_at"],
                end_at=data["end_at"],
                recurrence_days=data["recurrence_days"],
                assignees=_schedule_assignee_payloads(data.get("assignees") or []),
                use_shared_chronology=data.get("use_shared_chronology", False),
            )
        except (ActionPlanPermissionError, ActionPlanValidationError) as exc:
            return _action_plan_error_response(exc)

        schedule = get_action_plan_schedule_for_detail(
            membership=membership,
            schedule_id=schedule.id,
        )
        payload = serialize_schedule_detail(schedule, membership=membership)
        return Response(
            ActionPlanScheduleDetailSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class ActionPlanScheduleDetailView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        responses={
            200: ActionPlanScheduleDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, schedule_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        schedule = get_action_plan_schedule_for_detail(
            membership=membership,
            schedule_id=uuid.UUID(str(schedule_id)),
        )
        if schedule is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = serialize_schedule_detail(schedule, membership=membership)
        return Response(ActionPlanScheduleDetailSerializer(payload).data)

    @extend_schema(
        tags=["action-plans"],
        request=ActionPlanScheduleUpdateRequestSerializer,
        responses={
            200: ActionPlanScheduleDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def patch(self, request, establishment_id, schedule_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        schedule = get_action_plan_schedule_for_detail(
            membership=membership,
            schedule_id=uuid.UUID(str(schedule_id)),
        )
        if schedule is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ActionPlanScheduleUpdateRequestSerializer(data=request.data, partial=True)
        body.is_valid(raise_exception=True)
        data = body.validated_data

        try:
            schedule = update_action_plan_schedule(
                schedule=schedule,
                actor=membership,
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                start_at=data.get("start_at"),
                end_at=data.get("end_at"),
                recurrence_days=data.get("recurrence_days"),
                assignees=(
                    _schedule_assignee_payloads(data["assignees"]) if "assignees" in data else None
                ),
                use_shared_chronology=data.get("use_shared_chronology"),
            )
        except (ActionPlanPermissionError, ActionPlanValidationError) as exc:
            return _action_plan_error_response(exc)

        schedule = get_action_plan_schedule_for_detail(
            membership=membership,
            schedule_id=schedule.id,
        )
        payload = serialize_schedule_detail(schedule, membership=membership)
        return Response(ActionPlanScheduleDetailSerializer(payload).data)


class ActionPlanScheduleDeactivateView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        request=None,
        responses={
            200: ActionPlanScheduleDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ActionPlanActiveExecutionConflictSerializer),
        },
    )
    def post(self, request, establishment_id, schedule_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        schedule = get_action_plan_schedule_for_detail(
            membership=membership,
            schedule_id=uuid.UUID(str(schedule_id)),
        )
        if schedule is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            schedule = deactivate_action_plan_schedule(
                schedule=schedule,
                actor=membership,
            )
        except ActionPlanConflictError as exc:
            return _action_plan_conflict_response(exc)
        except (ActionPlanPermissionError, ActionPlanValidationError) as exc:
            return _action_plan_error_response(exc)

        schedule = get_action_plan_schedule_for_detail(
            membership=membership,
            schedule_id=schedule.id,
        )
        payload = serialize_schedule_detail(schedule, membership=membership)
        return Response(ActionPlanScheduleDetailSerializer(payload).data)


class ActionPlanExecutionFeedView(EstablishmentScopedActionPlanMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
    ]

    @extend_schema(
        tags=["action-plans"],
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
            200: ActionPlanExecutionFeedResponseSerializer,
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

        page_size = _parse_feed_page_size(request.query_params.get("page_size"))
        try:
            cursor = parse_action_plan_execution_feed_cursor(
                request.query_params.get("cursor"),
            )
        except ActionPlanExecutionFeedCursorError as exc:
            return Response(
                {"code": "validation_error", "detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        executions, has_more, next_cursor = build_action_plan_execution_feed_page(
            membership=membership,
            view_mode=view_mode,  # type: ignore[arg-type]
            page_size=page_size,
            cursor=cursor,
        )

        serialized_items = [
            {
                "item_type": "action_plan_execution",
                "action_plan_execution": serialize_action_plan_execution_feed_item(
                    execution=execution,
                    membership=membership,
                ),
            }
            for execution in executions
        ]
        payload = {
            "items": serialized_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
        return Response(ActionPlanExecutionFeedResponseSerializer(payload).data)
