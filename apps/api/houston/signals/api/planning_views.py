from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response

from houston.signals.api.record_serializers import (
    FieldRecordSerializer,
    RecordDocumentPageSerializer,
    RecordOrganizationSerializer,
    RecordPlanningRequestSerializer,
    RecordPlanningResponseSerializer,
    RecordPredecessorSerializer,
)
from houston.signals.api.record_views import RecordView
from houston.signals.planning_services import schedule_record, set_record_predecessor
from houston.signals.project_services import organize_record
from houston.signals.record_documents import record_documents


class RecordPlanningView(RecordView):
    @extend_schema(
        tags=["signals"],
        request=RecordPlanningRequestSerializer,
        responses=RecordPlanningResponseSerializer,
    )
    def post(self, request, establishment_id, record_id):
        data = RecordPlanningRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        result = schedule_record(
            actor=self.actor(request), record_id=record_id, **data.validated_data
        )
        return Response(RecordPlanningResponseSerializer(result).data)


class RecordOrganizationView(RecordView):
    @extend_schema(
        tags=["signals"], request=RecordOrganizationSerializer, responses=FieldRecordSerializer
    )
    def post(self, request, establishment_id, record_id):
        actor = self.actor(request)
        data = RecordOrganizationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        organize_record(actor=actor, record_id=record_id, **data.validated_data)
        return self.response_record(actor, record_id)


class RecordPredecessorView(RecordView):
    @extend_schema(
        tags=["signals"], request=RecordPredecessorSerializer, responses=FieldRecordSerializer
    )
    def post(self, request, establishment_id, record_id):
        actor = self.actor(request)
        data = RecordPredecessorSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        set_record_predecessor(actor=actor, record_id=record_id, **data.validated_data)
        return self.response_record(actor, record_id)


class RecordDocumentsView(RecordView):
    @extend_schema(
        tags=["signals"],
        responses=RecordDocumentPageSerializer,
        parameters=[OpenApiParameter("offset", int), OpenApiParameter("q", str)],
    )
    def get(self, request, establishment_id, record_id):
        actor = self.actor(request)
        record = self.record(actor, record_id)
        return Response(
            RecordDocumentPageSerializer(
                record_documents(
                    actor=actor,
                    record=record,
                    offset=self.offset(request),
                    query=request.query_params.get("q", ""),
                )
            ).data
        )
