from datetime import date

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.action_plans.exceptions import ActionPlanPermissionError, ActionPlanServiceError
from houston.establishments.permissions import HasActiveMembership
from houston.signals import record_services
from houston.signals.api.record_serializers import (
    FieldRecordCommandSerializer,
    FieldRecordCreateSerializer,
    FieldRecordOptionsSerializer,
    FieldRecordPageSerializer,
    FieldRecordSectionSerializer,
    FieldRecordSerializer,
    FieldRecordUpdateSerializer,
    person,
    serialize_record,
)
from houston.signals.exceptions import SignalPermissionError, SignalServiceError, SignalStateError
from houston.signals.record_selectors import (
    calendar_filter,
    get_record,
    record_queryset,
    stage_filter,
)
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin


class RecordView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    def actor(self, request):
        actor = resolve_observation_actor_membership(
            request, establishment_id=self.establishment_id
        )
        if actor is None:
            raise NotFound()
        return actor

    def record(self, actor, record_id):
        record = get_record(actor, record_id)
        if record is None:
            raise NotFound()
        return record

    def handle_exception(self, exc):
        if isinstance(exc, (SignalServiceError, ActionPlanServiceError)):
            code = (
                403 if isinstance(exc, (SignalPermissionError, ActionPlanPermissionError)) else 400
            )
            if isinstance(exc, SignalStateError):
                code = 409
            return Response(
                {"detail": str(exc), "code": getattr(exc, "code", exc.error_code)}, status=code
            )
        return super().handle_exception(exc)

    def offset(self, request):
        try:
            offset = int(request.query_params.get("offset", 0))
            if not 0 <= offset <= 100000:
                raise ValueError
            return offset
        except ValueError as exc:
            raise ValidationError("Pagination invalide.") from exc

    def response_record(self, actor, record_id):
        record = self.record(actor, record_id)
        payload = serialize_record(record, actor)
        payload["participants"] = [
            person(p.membership)
            for p in record.participants.select_related("membership__user")[:50]
        ]
        return Response(FieldRecordSerializer(payload).data)


class FieldRecordListView(RecordView):
    @extend_schema(
        tags=["signals"],
        responses=FieldRecordPageSerializer,
        operation_id="field_records_list",
        parameters=[
            OpenApiParameter("offset", int),
            OpenApiParameter("stage", str, enum=["todo", "doing", "review", "closed"]),
            OpenApiParameter("day", bool),
            OpenApiParameter("mine", bool),
            OpenApiParameter("q", str),
            OpenApiParameter("pole", str),
            OpenApiParameter("project", str),
            OpenApiParameter("projects", bool),
            OpenApiParameter("from", str),
            OpenApiParameter("to", str),
        ],
    )
    def get(self, request, establishment_id):
        actor = self.actor(request)
        rows = record_queryset(actor)
        if request.query_params.get("projects") == "true":
            rows = rows.filter(is_project=True)
        if request.query_params.get("project"):
            import uuid

            try:
                project_id = uuid.UUID(request.query_params["project"])
            except ValueError as exc:
                raise ValidationError("Projet invalide.") from exc
            project = self.record(actor, project_id)
            if not project.is_project:
                raise ValidationError("Cette fiche n’est pas un projet.")
            rows = rows.filter(parent_project_id=project.id)
        stage = request.query_params.get("stage")
        if stage and stage not in {"todo", "doing", "review", "closed"}:
            raise ValidationError("Étape invalide.")
        rows = rows.filter(stage_filter(stage))
        if request.query_params.get("day") == "true":
            from houston.signals.record_selectors import day_records

            rows = day_records(actor, rows)
        if request.query_params.get("mine") == "true":
            rows = rows.filter(
                Q(owner_membership=actor) | Q(is_reporter=True) | Q(participants__membership=actor)
            )
        if request.query_params.get("q"):
            rows = rows.filter(title__icontains=request.query_params["q"][:100])
        if request.query_params.get("pole"):
            import uuid

            try:
                pole = uuid.UUID(request.query_params["pole"])
            except ValueError as exc:
                raise ValidationError("Pôle invalide.") from exc
            rows = rows.filter(
                Q(responsible_business_unit_id=pole) | Q(affected_business_unit_id=pole)
            )
        if request.query_params.get("from") or request.query_params.get("to"):
            try:
                start, end = (
                    date.fromisoformat(request.query_params["from"]),
                    date.fromisoformat(request.query_params["to"]),
                )
                if not 0 <= (end - start).days <= 93:
                    raise ValueError
            except (KeyError, ValueError) as exc:
                raise ValidationError("Choisissez une période de 1 à 94 jours.") from exc
            rows = rows.filter(
                calendar_filter(start_on=start, end_on=end, zone=actor.establishment.timezone)
            )
        offset = self.offset(request)
        page = list(
            rows.order_by("-is_pinned", "due_on", "-created_at", "-id")[offset : offset + 31]
        )
        return Response(
            FieldRecordPageSerializer(
                {
                    "items": [serialize_record(row, actor) for row in page[:30]],
                    "next_offset": offset + 30 if len(page) > 30 else None,
                    "timezone": actor.establishment.timezone,
                }
            ).data
        )

    @extend_schema(
        tags=["signals"],
        request=FieldRecordCreateSerializer,
        responses={201: FieldRecordSerializer},
    )
    def post(self, request, establishment_id):
        actor = self.actor(request)
        data = FieldRecordCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = record_services.create_record(actor=actor, **data.validated_data)
        response = self.response_record(actor, record.id)
        response.status_code = 201
        return response


class FieldRecordDetailView(RecordView):
    @extend_schema(tags=["signals"], responses=FieldRecordSerializer)
    def get(self, request, establishment_id, record_id):
        return self.response_record(self.actor(request), record_id)

    @extend_schema(
        tags=["signals"], request=FieldRecordUpdateSerializer, responses=FieldRecordSerializer
    )
    def patch(self, request, establishment_id, record_id):
        actor = self.actor(request)
        data = FieldRecordUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = record_services.update_record(
            actor=actor, record_id=record_id, **data.validated_data
        )
        return self.response_record(actor, record.id)


class FieldRecordCommandView(RecordView):
    @extend_schema(
        tags=["signals"], request=FieldRecordCommandSerializer, responses=FieldRecordSerializer
    )
    def post(self, request, establishment_id, record_id):
        actor = self.actor(request)
        data = FieldRecordCommandSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record_services.run_record_command(actor=actor, record_id=record_id, **data.validated_data)
        return self.response_record(actor, record_id)


class FieldRecordSectionView(RecordView):
    @extend_schema(
        tags=["signals"],
        responses=FieldRecordSectionSerializer,
        parameters=[
            OpenApiParameter("offset", int),
            OpenApiParameter(
                "section", str, required=True, enum=["sources", "work", "history", "objectives"]
            ),
        ],
    )
    def get(self, request, establishment_id, record_id):
        from houston.signals.record_sections import record_section

        actor = self.actor(request)
        record = self.record(actor, record_id)
        section = request.query_params.get("section", "sources")
        if section not in {"sources", "work", "history", "objectives"}:
            raise ValidationError("Section inconnue.")
        return Response(
            FieldRecordSectionSerializer(
                record_section(
                    record=record,
                    actor=actor,
                    section=section,
                    offset=self.offset(request),
                )
            ).data
        )


class FieldRecordOptionsView(RecordView):
    @extend_schema(
        tags=["signals"],
        responses=FieldRecordOptionsSerializer,
        parameters=[OpenApiParameter("q", str)],
    )
    def get(self, request, establishment_id):
        from houston.establishments.membership_scope import membership_business_unit_scope_ids
        from houston.establishments.models import BusinessUnit, EstablishmentMembership

        actor = self.actor(request)
        poles = BusinessUnit.objects.filter(establishment_id=actor.establishment_id, active=True)
        if actor.role not in ("owner", "director"):
            poles = poles.filter(pk__in=membership_business_unit_scope_ids(actor))
        members = EstablishmentMembership.objects.filter(
            establishment_id=actor.establishment_id, status="active"
        ).select_related("user")
        if query := request.query_params.get("q", "")[:100]:
            members = members.filter(
                Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query)
            )
        people = list(members.order_by("user__first_name", "id")[:51])
        from houston.brain.models import BrainObjective

        objectives = (
            BrainObjective.objects.filter(
                establishment_id=actor.establishment_id,
                current_revision__isnull=False,
            )
            .select_related("current_revision")
            .order_by("-created_at")
        )
        if actor.role not in ("owner", "director"):
            objectives = objectives.none()
        if query:
            objectives = objectives.filter(current_revision__indicator__icontains=query)

        from houston.action_plans.permissions import can_update_action_plan_execution_content
        from houston.action_plans.selectors import action_plan_execution_feed_queryset

        executions = action_plan_execution_feed_queryset(
            membership=actor, view_mode="general"
        ).filter(status="in_progress")
        if query:
            executions = executions.filter(title__icontains=query)
        choices = [
            e
            for e in executions.order_by("-created_at", "id")[:50]
            if can_update_action_plan_execution_content(actor, e)
        ]
        from houston.signals.record_permissions import can_manage_record

        available_records = record_queryset(actor)
        if query:
            available_records = available_records.filter(title__icontains=query)
        selectable = [
            r
            for r in available_records.filter(due_on__isnull=False).order_by("title", "id")[:100]
            if can_manage_record(actor, r)
        ]
        projects = [
            r
            for r in available_records.filter(is_project=True)
            .exclude(status__in=["resolved", "canceled"])
            .order_by("title", "id")[:100]
            if can_manage_record(actor, r)
        ]
        return Response(
            FieldRecordOptionsSerializer(
                {
                    "poles": [
                        {"id": p.id, "name": p.specific_name}
                        for p in poles.order_by("specific_name")[:200]
                    ],
                    "members": [person(m) for m in people[:50]],
                    "more_members": len(people) > 50,
                    "executions": [{"id": e.id, "name": e.title} for e in choices],
                    "projects": [{"id": r.id, "name": r.title} for r in projects],
                    "records": [{"id": r.id, "name": r.title} for r in selectable if r.due_on],
                    "objectives": [
                        {"id": o.id, "name": o.current_revision.indicator} for o in objectives[:50]
                    ],
                }
            ).data
        )
