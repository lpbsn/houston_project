from __future__ import annotations

import uuid

from django.db.models import Count, Exists, OuterRef
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.checklists.api.serializers import (
    ChecklistActiveExecutionConflictSerializer,
    ChecklistAssignmentCreateRequestSerializer,
    ChecklistAssignmentSerializer,
    ChecklistAssignmentUpdateRequestSerializer,
    ChecklistExecutionDetailSerializer,
    ChecklistTaskCreateObservationRequestSerializer,
    ChecklistTaskCreateObservationResponseSerializer,
    ChecklistTaskExecutionSerializer,
    ChecklistTaskReorderRequestSerializer,
    ChecklistTaskSkipRequestSerializer,
    ChecklistTaskTemplateCreateRequestSerializer,
    ChecklistTaskTemplateSerializer,
    ChecklistTaskTemplateUpdateRequestSerializer,
    ChecklistTemplateCreateRequestSerializer,
    ChecklistTemplateDetailSerializer,
    ChecklistTemplateExecutionCreateRequestSerializer,
    ChecklistTemplateListItemSerializer,
    ChecklistTemplateScheduleRequestSerializer,
    ChecklistTemplateScheduleResponseSerializer,
    ChecklistTemplateUpdateRequestSerializer,
    serialize_assignment,
    serialize_execution_detail,
    serialize_task_execution,
    serialize_task_template,
    serialize_template_detail,
    serialize_template_list_item,
)
from houston.checklists.constants import ACTIVE_EXECUTION_STATUSES
from houston.checklists.exceptions import (
    ChecklistConflictError,
    ChecklistPermissionError,
    ChecklistValidationError,
)
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.permissions import (
    can_access_checklist_management,
    can_create_checklist_assignment,
    can_create_registered_template,
)
from houston.checklists.selectors import (
    active_assignments_for_management_list,
    get_checklist_assignment_for_detail,
    get_checklist_execution_for_detail,
    get_checklist_task_execution_for_commands,
    get_checklist_task_template_for_management,
    get_checklist_template_for_detail,
    registered_templates_for_catalogue,
)
from houston.checklists.services import (
    activate_checklist_template,
    add_task_template,
    cancel_checklist_execution,
    create_checklist_assignment,
    create_checklist_template,
    create_execution_from_template,
    create_observation_from_task,
    create_registered_checklist_template,
    deactivate_checklist_assignment,
    deactivate_checklist_template,
    delete_checklist_template,
    delete_task_template,
    mark_task_done,
    reorder_task_templates,
    schedule_checklist_from_template,
    skip_task,
    update_checklist_assignment,
    update_checklist_template,
    update_task_template,
)
from houston.establishments.permissions import HasActiveMembership
from houston.observations.models import ObservationProcessing
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin


class EstablishmentScopedChecklistMixin(EstablishmentScopedObservationMixin):
    pass


def _checklist_error_response(exc: Exception) -> Response:
    if isinstance(exc, ChecklistPermissionError):
        return Response(
            {"code": "permission_denied", "detail": str(exc) or "Permission denied."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, ChecklistConflictError):
        return Response(
            {"code": "conflict", "detail": str(exc) or "Conflict."},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, ChecklistValidationError):
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


class ChecklistTemplateListCreateView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        parameters=[
            OpenApiParameter(name="created_by_me", required=False, type=bool),
            OpenApiParameter(name="business_unit_id", required=False, type=str),
        ],
        responses={
            200: ChecklistTemplateListItemSerializer(many=True),
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership
        if not can_access_checklist_management(membership):
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
        queryset = registered_templates_for_catalogue(
            membership=membership,
            created_by_me=created_by_me,
            business_unit_id=business_unit_id,
        )

        queryset = queryset.annotate(
            task_count=Count("task_templates"),
            has_active_execution=Exists(
                ChecklistExecution.objects.filter(
                    checklist_template_id=OuterRef("pk"),
                    status__in=ACTIVE_EXECUTION_STATUSES,
                )
            ),
        ).order_by(
            "-updated_at",
            "-created_at",
        )
        payload = [
            serialize_template_list_item(template, membership=membership) for template in queryset
        ]
        return Response(ChecklistTemplateListItemSerializer(payload, many=True).data)

    @extend_schema(
        tags=["checklists"],
        request=ChecklistTemplateCreateRequestSerializer,
        responses={
            201: ChecklistTemplateDetailSerializer,
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

        body = ChecklistTemplateCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        if not can_create_registered_template(membership):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            if data.get("tasks"):
                template, _execution = create_registered_checklist_template(
                    establishment_id=self.establishment_id,
                    actor=membership,
                    title=data["title"],
                    description=data.get("description", ""),
                    business_unit_id=data["business_unit_id"],
                    tasks=data["tasks"],
                    assign_now=data.get("assign_now", False),
                    assigned_to_id=data.get("assigned_to"),
                    end_at=data.get("end_at"),
                )
            else:
                template = create_checklist_template(
                    establishment_id=self.establishment_id,
                    actor=membership,
                    title=data["title"],
                    description=data.get("description", ""),
                    business_unit_id=data["business_unit_id"],
                )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        template = get_checklist_template_for_detail(
            membership=membership,
            template_id=template.id,
        )
        payload = serialize_template_detail(template, membership=membership)
        return Response(
            ChecklistTemplateDetailSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class ChecklistTemplateDetailView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        responses={
            200: ChecklistTemplateDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        template = get_checklist_template_for_detail(
            membership=membership,
            template_id=uuid.UUID(str(template_id)),
        )
        if template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = serialize_template_detail(template, membership=membership)
        return Response(ChecklistTemplateDetailSerializer(payload).data)

    @extend_schema(
        tags=["checklists"],
        request=ChecklistTemplateUpdateRequestSerializer,
        responses={
            200: ChecklistTemplateDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def patch(self, request, establishment_id, template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        template = get_checklist_template_for_detail(
            membership=membership,
            template_id=uuid.UUID(str(template_id)),
        )
        if template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ChecklistTemplateUpdateRequestSerializer(data=request.data, partial=True)
        body.is_valid(raise_exception=True)

        try:
            template = update_checklist_template(
                template=template,
                actor=membership,
                title=body.validated_data.get("title"),
                description=body.validated_data.get("description"),
            )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        template = get_checklist_template_for_detail(
            membership=membership,
            template_id=template.id,
        )
        payload = serialize_template_detail(template, membership=membership)
        return Response(ChecklistTemplateDetailSerializer(payload).data)

    @extend_schema(
        tags=["checklists"],
        responses={
            204: None,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ChecklistActiveExecutionConflictSerializer),
        },
    )
    def delete(self, request, establishment_id, template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        template = get_checklist_template_for_detail(
            membership=membership,
            template_id=uuid.UUID(str(template_id)),
        )
        if template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            delete_checklist_template(template=template, actor=membership)
        except ChecklistPermissionError as exc:
            return _checklist_error_response(exc)
        except ChecklistConflictError as exc:
            if exc.active_execution_id is not None:
                return Response(
                    ChecklistActiveExecutionConflictSerializer(
                        {
                            "code": "conflict",
                            "detail": str(exc) or "Conflict.",
                            "active_execution_id": exc.active_execution_id,
                        }
                    ).data,
                    status=status.HTTP_409_CONFLICT,
                )
            return _checklist_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChecklistTemplateActivateView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=None,
        responses={
            200: ChecklistTemplateDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, template_id):
        return _template_command_response(
            request=request,
            establishment_id=self.establishment_id,
            template_id=template_id,
            service_fn=activate_checklist_template,
        )


class ChecklistTemplateDeactivateView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=None,
        responses={
            200: ChecklistTemplateDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, template_id):
        return _template_command_response(
            request=request,
            establishment_id=self.establishment_id,
            template_id=template_id,
            service_fn=deactivate_checklist_template,
        )


def _template_command_response(*, request, establishment_id, template_id, service_fn):
    membership = _resolve_membership(request, establishment_id)
    if isinstance(membership, Response):
        return membership

    template = get_checklist_template_for_detail(
        membership=membership,
        template_id=uuid.UUID(str(template_id)),
    )
    if template is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        service_fn(template=template, actor=membership)
    except (ChecklistPermissionError, ChecklistValidationError) as exc:
        return _checklist_error_response(exc)

    template = get_checklist_template_for_detail(
        membership=membership,
        template_id=template.id,
    )
    payload = serialize_template_detail(template, membership=membership)
    return Response(ChecklistTemplateDetailSerializer(payload).data)


class ChecklistTaskTemplateCreateView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=ChecklistTaskTemplateCreateRequestSerializer,
        responses={
            201: ChecklistTaskTemplateSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        template = get_checklist_template_for_detail(
            membership=membership,
            template_id=uuid.UUID(str(template_id)),
        )
        if template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ChecklistTaskTemplateCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data

        try:
            task_template = add_task_template(
                template=template,
                actor=membership,
                task=data["task"],
                position=data.get("position"),
            )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        payload = serialize_task_template(task_template)
        return Response(
            ChecklistTaskTemplateSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class ChecklistTaskTemplateDetailView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=ChecklistTaskTemplateUpdateRequestSerializer,
        responses={
            200: ChecklistTaskTemplateSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def patch(self, request, establishment_id, task_template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        task_template = get_checklist_task_template_for_management(
            membership=membership,
            task_template_id=uuid.UUID(str(task_template_id)),
        )
        if task_template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ChecklistTaskTemplateUpdateRequestSerializer(data=request.data, partial=True)
        body.is_valid(raise_exception=True)

        try:
            task_template = update_task_template(
                task_template=task_template,
                actor=membership,
                task=body.validated_data.get("task"),
                position=body.validated_data.get("position"),
            )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        payload = serialize_task_template(task_template)
        return Response(ChecklistTaskTemplateSerializer(payload).data)

    @extend_schema(
        tags=["checklists"],
        responses={
            204: None,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def delete(self, request, establishment_id, task_template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        task_template = get_checklist_task_template_for_management(
            membership=membership,
            task_template_id=uuid.UUID(str(task_template_id)),
        )
        if task_template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            delete_task_template(task_template=task_template, actor=membership)
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChecklistTaskTemplateReorderView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=ChecklistTaskReorderRequestSerializer,
        responses={
            200: ChecklistTaskTemplateSerializer(many=True),
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        template = get_checklist_template_for_detail(
            membership=membership,
            template_id=uuid.UUID(str(template_id)),
        )
        if template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ChecklistTaskReorderRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        try:
            tasks = reorder_task_templates(
                template=template,
                actor=membership,
                ordered_task_template_ids=body.validated_data["ordered_task_template_ids"],
            )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        payload = [serialize_task_template(task) for task in tasks]
        return Response(ChecklistTaskTemplateSerializer(payload, many=True).data)


class ChecklistAssignmentListView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        responses={
            200: ChecklistAssignmentSerializer(many=True),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        queryset = active_assignments_for_management_list(membership=membership).order_by(
            "-updated_at",
            "-created_at",
        )
        payload = [
            serialize_assignment(assignment, membership=membership) for assignment in queryset
        ]
        return Response(ChecklistAssignmentSerializer(payload, many=True).data)


class ChecklistAssignmentCreateView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=ChecklistAssignmentCreateRequestSerializer,
        responses={
            201: ChecklistAssignmentSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        template = (
            ChecklistTemplate.objects.filter(
                id=uuid.UUID(str(template_id)),
                establishment_id=self.establishment_id,
            )
            .select_related("business_unit")
            .first()
        )
        if template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if not can_create_checklist_assignment(membership, template):
            return Response(
                {"code": "permission_denied", "detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        body = ChecklistAssignmentCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data

        try:
            assignment = create_checklist_assignment(
                template=template,
                actor=membership,
                assigned_to_id=data["assigned_to"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                start_at=data["start_at"],
                end_at=data["end_at"],
                recurrence_days=data.get("recurrence_days"),
            )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        assignment = get_checklist_assignment_for_detail(
            membership=membership,
            assignment_id=assignment.id,
        )
        payload = serialize_assignment(assignment, membership=membership)
        return Response(
            ChecklistAssignmentSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class ChecklistAssignmentDetailView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        responses={
            200: ChecklistAssignmentSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, assignment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        assignment = get_checklist_assignment_for_detail(
            membership=membership,
            assignment_id=uuid.UUID(str(assignment_id)),
        )
        if assignment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = serialize_assignment(assignment, membership=membership)
        return Response(ChecklistAssignmentSerializer(payload).data)

    @extend_schema(
        tags=["checklists"],
        request=ChecklistAssignmentUpdateRequestSerializer,
        responses={
            200: ChecklistAssignmentSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def patch(self, request, establishment_id, assignment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        assignment = get_checklist_assignment_for_detail(
            membership=membership,
            assignment_id=uuid.UUID(str(assignment_id)),
        )
        if assignment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ChecklistAssignmentUpdateRequestSerializer(data=request.data, partial=True)
        body.is_valid(raise_exception=True)

        try:
            assignment = update_checklist_assignment(
                assignment=assignment,
                actor=membership,
                assigned_to_id=body.validated_data.get("assigned_to"),
                start_date=body.validated_data.get("start_date"),
                end_date=body.validated_data.get("end_date"),
                start_at=body.validated_data.get("start_at"),
                end_at=body.validated_data.get("end_at"),
                recurrence_days=body.validated_data.get("recurrence_days"),
            )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        assignment = get_checklist_assignment_for_detail(
            membership=membership,
            assignment_id=assignment.id,
        )
        payload = serialize_assignment(assignment, membership=membership)
        return Response(ChecklistAssignmentSerializer(payload).data)


class ChecklistAssignmentDeactivateView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=None,
        responses={
            200: ChecklistAssignmentSerializer,
            204: OpenApiResponse(description="Assignment removed (no execution history)."),
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
            409: OpenApiResponse(response=ChecklistActiveExecutionConflictSerializer),
        },
    )
    def post(self, request, establishment_id, assignment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        assignment = get_checklist_assignment_for_detail(
            membership=membership,
            assignment_id=uuid.UUID(str(assignment_id)),
        )
        if assignment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            assignment = deactivate_checklist_assignment(
                assignment=assignment,
                actor=membership,
            )
        except ChecklistPermissionError as exc:
            return _checklist_error_response(exc)
        except ChecklistConflictError as exc:
            if exc.active_execution_id is not None:
                return Response(
                    ChecklistActiveExecutionConflictSerializer(
                        {
                            "code": "conflict",
                            "detail": str(exc) or "Conflict.",
                            "active_execution_id": exc.active_execution_id,
                        }
                    ).data,
                    status=status.HTTP_409_CONFLICT,
                )
            return _checklist_error_response(exc)
        except ChecklistValidationError as exc:
            return _checklist_error_response(exc)

        if assignment is None:
            return Response(status=status.HTTP_204_NO_CONTENT)

        payload = serialize_assignment(assignment, membership=membership)
        return Response(ChecklistAssignmentSerializer(payload).data)


class ChecklistTemplateScheduleView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=ChecklistTemplateScheduleRequestSerializer,
        responses={
            201: ChecklistTemplateScheduleResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        template = get_checklist_template_for_detail(
            membership=membership,
            template_id=uuid.UUID(str(template_id)),
        )
        if template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ChecklistTemplateScheduleRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data

        try:
            result = schedule_checklist_from_template(
                template=template,
                actor=membership,
                assigned_to_id=data.get("assigned_to"),
                start_date=data.get("start_date"),
                start_at=data["start_at"],
                end_at=data["end_at"],
                recurrence_days=data.get("recurrence_days"),
                recurrence_end_date=data.get("recurrence_end_date"),
            )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        if result.result_type == "execution":
            if result.execution is None:
                return _checklist_error_response(
                    ChecklistValidationError("Schedule result is incomplete."),
                )
            execution = get_checklist_execution_for_detail(
                membership=membership,
                execution_id=result.execution.id,
            )
            payload = {
                "result_type": "execution",
                "execution": serialize_execution_detail(execution, membership=membership),
                "assignment": None,
            }
        else:
            if result.assignment is None:
                return _checklist_error_response(
                    ChecklistValidationError("Schedule result is incomplete."),
                )
            assignment = get_checklist_assignment_for_detail(
                membership=membership,
                assignment_id=result.assignment.id,
            )
            payload = {
                "result_type": "assignment",
                "execution": None,
                "assignment": serialize_assignment(assignment, membership=membership),
            }

        return Response(
            ChecklistTemplateScheduleResponseSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class ChecklistTemplateExecutionCreateView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=ChecklistTemplateExecutionCreateRequestSerializer,
        responses={
            201: ChecklistExecutionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, template_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        template = get_checklist_template_for_detail(
            membership=membership,
            template_id=uuid.UUID(str(template_id)),
        )
        if template is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ChecklistTemplateExecutionCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data

        try:
            execution = create_execution_from_template(
                template=template,
                actor=membership,
                assigned_to_id=data.get("assigned_to"),
                end_at=data.get("end_at"),
            )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        execution = get_checklist_execution_for_detail(
            membership=membership,
            execution_id=execution.id,
        )
        payload = serialize_execution_detail(execution, membership=membership)
        return Response(
            ChecklistExecutionDetailSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class ChecklistExecutionDetailView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        responses={
            200: ChecklistExecutionDetailSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, execution_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        execution = get_checklist_execution_for_detail(
            membership=membership,
            execution_id=uuid.UUID(str(execution_id)),
        )
        if execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = serialize_execution_detail(execution, membership=membership)
        return Response(ChecklistExecutionDetailSerializer(payload).data)


class ChecklistExecutionCancelView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=None,
        responses={
            200: ChecklistExecutionDetailSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, execution_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership

        execution = get_checklist_execution_for_detail(
            membership=membership,
            execution_id=uuid.UUID(str(execution_id)),
        )
        if execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            execution = cancel_checklist_execution(execution=execution, actor=membership)
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        execution = get_checklist_execution_for_detail(
            membership=membership,
            execution_id=execution.id,
        )
        payload = serialize_execution_detail(execution, membership=membership)
        return Response(ChecklistExecutionDetailSerializer(payload).data)


def _task_command_response(*, request, establishment_id, task_execution_id, service_fn, body=None):
    membership = _resolve_membership(request, establishment_id)
    if isinstance(membership, Response):
        return membership

    task_execution = get_checklist_task_execution_for_commands(
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
    except (ChecklistPermissionError, ChecklistValidationError) as exc:
        return _checklist_error_response(exc)

    payload = serialize_task_execution(task_execution)
    return Response(ChecklistTaskExecutionSerializer(payload).data)


class ChecklistTaskExecutionMarkDoneView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=None,
        responses={
            200: ChecklistTaskExecutionSerializer,
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
            service_fn=mark_task_done,
        )


class ChecklistTaskExecutionSkipView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=ChecklistTaskSkipRequestSerializer,
        responses={
            200: ChecklistTaskExecutionSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, task_execution_id):
        body = ChecklistTaskSkipRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        skipped_reason = body.validated_data.get("skipped_reason")

        def _skip(*, task_execution, actor):
            return skip_task(
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


class ChecklistTaskExecutionCreateObservationView(EstablishmentScopedChecklistMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["checklists"],
        request=ChecklistTaskCreateObservationRequestSerializer,
        responses={
            201: ChecklistTaskCreateObservationResponseSerializer,
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

        task_execution = get_checklist_task_execution_for_commands(
            membership=membership,
            task_execution_id=uuid.UUID(str(task_execution_id)),
        )
        if task_execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        body = ChecklistTaskCreateObservationRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        try:
            updated = create_observation_from_task(
                task_execution=task_execution,
                actor=membership,
                text=body.validated_data["text"],
                temporary_upload_ids=body.validated_data.get("temporary_upload_ids", []),
            )
        except (ChecklistPermissionError, ChecklistValidationError) as exc:
            return _checklist_error_response(exc)

        payload = {
            "task_execution_id": updated.id,
            "observation_id": updated.observation_id,
            "status": updated.status,
            "processing_status": ObservationProcessing.Status.QUEUED,
        }
        return Response(
            ChecklistTaskCreateObservationResponseSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )
