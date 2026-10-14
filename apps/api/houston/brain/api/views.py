"""HTTP orchestration for Brain. Workflows stay in the domain services."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.brain.admission import admit_brain_work
from houston.brain.api.serializers import (
    BrainActiveWorkSerializer,
    BrainAnalysisDetailSerializer,
    BrainAnalysisListSerializer,
    BrainCancelResponseSerializer,
    BrainDossierItemSerializer,
    BrainFollowUpRequestSerializer,
    BrainFollowUpResponseSerializer,
    BrainKnowledgeVersionListSerializer,
    BrainKnowledgeVersionSerializer,
    BrainLaunchRequestSerializer,
    BrainLaunchResponseSerializer,
    BrainMechanismDecisionRequestSerializer,
    BrainMechanismRevisionRequestSerializer,
    BrainObjectiveDecisionRequestSerializer,
    BrainObjectiveListSerializer,
    BrainObjectiveSerializer,
    BrainPeriodRequestSerializer,
    BrainPlatformMechanismListSerializer,
    BrainPlatformMechanismSerializer,
    BrainPlatformRepresentationSerializer,
    BrainReportingListSerializer,
    BrainReportingResponseSerializer,
    BrainSourcePageSerializer,
    BrainSuggestionConvertRequestSerializer,
    BrainSuggestionConvertResponseSerializer,
    BrainSuggestionRevisionRequestSerializer,
    BrainSuggestionSerializer,
)
from houston.brain.errors import (
    BrainAccessDenied,
    BrainCapacityUnavailable,
    BrainWorkError,
    ReportingRejected,
)
from houston.brain.knowledge import (
    activate_knowledge_version,
    decide_mechanism,
    revise_global_representation,
)
from houston.brain.models import BrainAnalysis, BrainMessage
from houston.brain.objectives import decide_objective
from houston.brain.preview import (
    build_brain_reporting_preview_url,
    resolve_brain_reporting_preview,
)
from houston.brain.runtime import request_analysis_cancel, request_follow_up_cancel
from houston.brain.selectors import (
    active_brain_work,
    analysis_detail,
    analysis_page,
    dossier_item,
    dossier_source_page,
    message_for_admin,
    objective_page,
    objective_state,
    platform_knowledge_versions,
    platform_mechanism,
    platform_mechanism_candidates,
    reporting_detail,
    reporting_page,
    suggestion_payload,
)
from houston.brain.services import confirm_reporting_period, prepare_reporting
from houston.brain.suggestions import convert_suggestion, revise_suggestion
from houston.establishments.permissions import resolve_establishment_admin_actor
from houston.platform.permissions import IsActivePlatformOperator
from houston.uploads.api.views import EstablishmentScopedObservationMixin
from houston.uploads.private_storage import (
    PRIVATE_MEDIA_BACKEND_S3,
    generate_private_media_presigned_get_url,
    get_private_media_storage,
)

_NOT_FOUND = {"detail": "Not found."}
_HIDDEN_CODES = {
    "suggestion_not_found",
    "objective_not_found",
    "mechanism_not_found",
    "knowledge_not_found",
}
_AUTH = [BearerAccessTokenAuthentication]
_USER = [permissions.IsAuthenticated]
_OPERATOR = [permissions.IsAuthenticated, IsActivePlatformOperator]


def _denied():
    return Response(_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)


def _work_error(exc: BrainWorkError):
    return Response(
        {"code": exc.code, "detail": exc.message},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _guard(func):
    try:
        return func()
    except BrainAccessDenied:
        return _denied()
    except BrainCapacityUnavailable as exc:
        return Response(
            {"code": exc.code, "detail": exc.message},
            status=status.HTTP_409_CONFLICT,
        )
    except (BrainWorkError, ReportingRejected) as exc:
        if getattr(exc, "code", "") in _HIDDEN_CODES:
            return _denied()
        return _work_error(exc)


def _with_preview(request, establishment_id, payload: dict) -> dict:
    payload = dict(payload)
    payload["preview_url"] = build_brain_reporting_preview_url(
        request=request,
        establishment_id=establishment_id,
        reporting_id=uuid.UUID(payload["id"]),
        user_id=request.user.id,
    )
    return payload


def _page_args(request) -> tuple:
    return request.query_params.get("limit"), request.query_params.get("cursor")


class BrainReportingListCreateView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        operation_id="v1_establishments_brain_reportings_list",
        tags=["brain"],
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="cursor", type=str, required=False),
        ],
        responses={
            200: BrainReportingListSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        def read():
            page = reporting_page(
                user=request.user,
                establishment_id=self.establishment_id,
                limit=_page_args(request)[0],
                cursor=_page_args(request)[1],
            )
            page["results"] = [
                _with_preview(request, self.establishment_id, row) for row in page["results"]
            ]
            return Response(BrainReportingListSerializer(page).data)

        return _guard(read)

    @extend_schema(
        tags=["brain"],
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "format": "binary"},
                    "period_start": {"type": "string", "format": "date"},
                    "period_end": {"type": "string", "format": "date"},
                },
                "required": ["file"],
            }
        },
        responses={
            201: BrainReportingResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id):
        def create():
            actor = resolve_establishment_admin_actor(request.user, self.establishment_id)
            if actor is None:
                raise BrainAccessDenied()
            uploaded = request.FILES.get("file")
            if uploaded is None:
                raise BrainWorkError(code="missing_file", message="Un fichier est requis.")
            period = BrainPeriodRequestSerializer(
                data={
                    "period_start": request.data.get("period_start") or None,
                    "period_end": request.data.get("period_end") or None,
                }
            )
            start = end = None
            if request.data.get("period_start") or request.data.get("period_end"):
                period.is_valid(raise_exception=False)
                if not period.is_valid():
                    raise BrainWorkError(
                        code="period_invalid",
                        message="La période confirmée doit avoir un début et une fin.",
                    )
                start = period.validated_data["period_start"]
                end = period.validated_data["period_end"]
            reporting = prepare_reporting(
                establishment=actor.establishment,
                author=actor.user,
                filename=uploaded.name,
                content=uploaded,
                period_start=start,
                period_end=end,
            )
            payload = _with_preview(
                request,
                self.establishment_id,
                reporting_detail(
                    user=request.user,
                    establishment_id=self.establishment_id,
                    reporting_id=reporting.id,
                ),
            )
            return Response(
                BrainReportingResponseSerializer(payload).data,
                status=status.HTTP_201_CREATED,
            )

        return _guard(create)


class BrainReportingDetailView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        operation_id="v1_establishments_brain_reportings_retrieve",
        tags=["brain"],
        responses={
            200: BrainReportingResponseSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request, establishment_id, reporting_id):
        def read():
            payload = _with_preview(
                request,
                self.establishment_id,
                reporting_detail(
                    user=request.user,
                    establishment_id=self.establishment_id,
                    reporting_id=reporting_id,
                ),
            )
            return Response(BrainReportingResponseSerializer(payload).data)

        return _guard(read)


class BrainReportingPeriodView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        request=BrainPeriodRequestSerializer,
        responses={
            200: BrainReportingResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, reporting_id):
        def confirm():
            body = BrainPeriodRequestSerializer(data=request.data)
            if not body.is_valid():
                raise BrainWorkError(
                    code="period_invalid",
                    message="La période confirmée doit avoir un début et une fin.",
                )
            reporting = confirm_reporting_period(
                user=request.user,
                establishment_id=self.establishment_id,
                reporting_id=reporting_id,
                period_start=body.validated_data["period_start"],
                period_end=body.validated_data["period_end"],
            )
            payload = _with_preview(
                request,
                self.establishment_id,
                reporting_detail(
                    user=request.user,
                    establishment_id=self.establishment_id,
                    reporting_id=reporting.id,
                ),
            )
            return Response(BrainReportingResponseSerializer(payload).data)

        return _guard(confirm)


class BrainReportingPreviewView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["brain"],
        parameters=[
            OpenApiParameter(name="token", type=str, location=OpenApiParameter.QUERY, required=True)
        ],
        responses={
            200: OpenApiResponse(description="Original reporting file."),
            302: OpenApiResponse(description="Redirect to a short-lived private storage GET."),
            404: OpenApiResponse(description="Not found."),
        },
    )
    def get(self, request, establishment_id, reporting_id):
        reporting = resolve_brain_reporting_preview(
            establishment_id=uuid.UUID(str(establishment_id)),
            reporting_id=uuid.UUID(str(reporting_id)),
            token=request.query_params.get("token", "").strip(),
        )
        if reporting is None:
            raise Http404
        storage = get_private_media_storage()
        if not storage.exists(reporting.storage_key):
            raise Http404
        backend = (settings.HOUSTON_PRIVATE_MEDIA_BACKEND or "").strip().lower()
        if backend == PRIVATE_MEDIA_BACKEND_S3:
            location = generate_private_media_presigned_get_url(name=reporting.storage_key)
            response = HttpResponseRedirect(location)
        else:
            handle = storage.open(reporting.storage_key, "rb")
            response = FileResponse(handle, content_type=reporting.content_type)
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response


class BrainActiveWorkView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        responses={
            200: BrainActiveWorkSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        def read():
            work = active_brain_work(user=request.user, establishment_id=self.establishment_id)
            return Response(BrainActiveWorkSerializer({"work": work}).data)

        return _guard(read)


class BrainAnalysisListCreateView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        operation_id="v1_establishments_brain_analyses_list",
        tags=["brain"],
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="cursor", type=str, required=False),
        ],
        responses={
            200: BrainAnalysisListSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        def read():
            page = analysis_page(
                user=request.user,
                establishment_id=self.establishment_id,
                limit=_page_args(request)[0],
                cursor=_page_args(request)[1],
            )
            return Response(BrainAnalysisListSerializer(page).data)

        return _guard(read)

    @extend_schema(
        tags=["brain"],
        request=BrainLaunchRequestSerializer,
        responses={
            200: BrainLaunchResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id):
        def launch():
            body = BrainLaunchRequestSerializer(data=request.data)
            if not body.is_valid():
                raise BrainWorkError(
                    code="invalid_idempotency_key",
                    message="La demande d'analyse est incomplète.",
                )
            key = body.validated_data["idempotency_key"]
            work = admit_brain_work(
                user=request.user,
                establishment_id=self.establishment_id,
                reporting_id=body.validated_data["reporting_id"],
                idempotency_key=key,
            )
            matched = "active"
            if isinstance(work, BrainAnalysis) and work.idempotency_key == key:
                matched = "request"
            return Response(
                BrainLaunchResponseSerializer(
                    {"matched": matched, "work": _public_work(work)}
                ).data
            )

        return _guard(launch)


class BrainAnalysisDetailView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        operation_id="v1_establishments_brain_analyses_retrieve",
        tags=["brain"],
        responses={
            200: BrainAnalysisDetailSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request, establishment_id, analysis_id):
        def read():
            payload = analysis_detail(
                user=request.user,
                establishment_id=self.establishment_id,
                analysis_id=analysis_id,
            )
            return Response(BrainAnalysisDetailSerializer(payload).data)

        return _guard(read)


class BrainAnalysisCancelView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        request=None,
        responses={
            200: BrainCancelResponseSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, analysis_id):
        def cancel():
            analysis_detail(
                user=request.user,
                establishment_id=self.establishment_id,
                analysis_id=analysis_id,
            )
            current = request_analysis_cancel(analysis_id)
            if not current:
                raise BrainAccessDenied()
            return Response(BrainCancelResponseSerializer({"status": current}).data)

        return _guard(cancel)


class BrainAnalysisSourceView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="cursor", type=str, required=False),
        ],
        responses={
            200: BrainSourcePageSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request, establishment_id, analysis_id):
        def read():
            page = dossier_source_page(
                user=request.user,
                establishment_id=self.establishment_id,
                analysis_id=analysis_id,
                limit=_page_args(request)[0],
                cursor=_page_args(request)[1],
            )
            return Response(BrainSourcePageSerializer(page).data)

        return _guard(read)


class BrainDossierItemView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        responses={
            200: BrainDossierItemSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request, establishment_id, item_id):
        def read():
            payload = dossier_item(
                user=request.user,
                establishment_id=self.establishment_id,
                item_id=item_id,
            )
            return Response(BrainDossierItemSerializer(payload).data)

        return _guard(read)


class BrainFollowUpCreateView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        request=BrainFollowUpRequestSerializer,
        responses={
            200: BrainFollowUpResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, analysis_id):
        def ask():
            body = BrainFollowUpRequestSerializer(data=request.data)
            if not body.is_valid():
                raise BrainWorkError(
                    code="invalid_follow_up",
                    message="Le follow-up n'a pas de demande reconnue.",
                )
            request_id = body.validated_data["request_id"]
            work = admit_brain_work(
                user=request.user,
                establishment_id=self.establishment_id,
                analysis_id=analysis_id,
                request_id=request_id,
                body=body.validated_data["body"],
                purpose=body.validated_data["purpose"],
                cited_item_ids=body.validated_data.get("cited_item_ids") or [],
            )
            matched = "active"
            if (
                isinstance(work, BrainMessage)
                and work.request_id == request_id
                and work.analysis_id == analysis_id
            ):
                matched = "request"
            return Response(
                BrainFollowUpResponseSerializer(
                    {"matched": matched, "work": _public_work(work)}
                ).data
            )

        return _guard(ask)


class BrainFollowUpCancelView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        request=None,
        responses={
            200: BrainCancelResponseSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, message_id):
        def cancel():
            message = message_for_admin(
                user=request.user,
                establishment_id=self.establishment_id,
                message_id=message_id,
            )
            current = request_follow_up_cancel(message.id)
            if not current:
                raise BrainAccessDenied()
            return Response(BrainCancelResponseSerializer({"status": current}).data)

        return _guard(cancel)


class BrainSuggestionRevisionView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        request=BrainSuggestionRevisionRequestSerializer,
        responses={
            200: BrainSuggestionSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, suggestion_id):
        def revise():
            suggestion_payload(
                user=request.user,
                suggestion_id=suggestion_id,
                establishment_id=self.establishment_id,
            )
            body = BrainSuggestionRevisionRequestSerializer(data=request.data)
            if not body.is_valid():
                raise BrainWorkError(
                    code="suggestion_revision_invalid",
                    message="La révision de la suggestion est incomplète.",
                )
            data = body.validated_data
            revise_suggestion(
                user=request.user,
                suggestion_id=suggestion_id,
                expected_revision_id=data["expected_revision_id"],
                title=data["title"],
                description=data.get("description") or "",
                tasks=data.get("tasks"),
                pilot_business_unit_id=data.get("pilot_business_unit_id"),
                assignees=data.get("assignees"),
                start_at=data.get("start_at"),
                end_at=data.get("end_at"),
                occurrence_date=data.get("occurrence_date"),
                all_day=data.get("all_day", False),
                requires_validation=data.get("requires_validation", True),
            )
            payload = suggestion_payload(
                user=request.user,
                suggestion_id=suggestion_id,
                establishment_id=self.establishment_id,
            )
            return Response(BrainSuggestionSerializer(payload).data)

        return _guard(revise)


class BrainSuggestionConvertView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        request=BrainSuggestionConvertRequestSerializer,
        responses={
            200: BrainSuggestionConvertResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, suggestion_id):
        def convert():
            suggestion_payload(
                user=request.user,
                suggestion_id=suggestion_id,
                establishment_id=self.establishment_id,
            )
            body = BrainSuggestionConvertRequestSerializer(data=request.data)
            if not body.is_valid():
                raise BrainWorkError(
                    code="suggestion_revision_invalid",
                    message="La confirmation de la suggestion est incomplète.",
                )
            result = convert_suggestion(
                user=request.user,
                suggestion_id=suggestion_id,
                expected_revision_id=body.validated_data["expected_revision_id"],
            )
            return Response(
                BrainSuggestionConvertResponseSerializer(
                    {
                        "action_plan_id": result.action_plan_id,
                        "created": result.created,
                        "related_plan_ids": list(result.related_plan_ids),
                    }
                ).data
            )

        return _guard(convert)


class BrainObjectiveListView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="cursor", type=str, required=False),
        ],
        responses={
            200: BrainObjectiveListSerializer,
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request, establishment_id):
        def read():
            page = objective_page(
                user=request.user,
                establishment_id=self.establishment_id,
                limit=_page_args(request)[0],
                cursor=_page_args(request)[1],
            )
            return Response(BrainObjectiveListSerializer(page).data)

        return _guard(read)


class BrainObjectiveDecisionView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        request=BrainObjectiveDecisionRequestSerializer,
        responses={
            200: BrainObjectiveSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, objective_id):
        def decide():
            current = objective_state(user=request.user, objective_id=objective_id)
            from houston.brain.models import BrainObjective

            objective = (
                BrainObjective.objects.filter(pk=objective_id).only("establishment_id").first()
            )
            if objective is None or objective.establishment_id != self.establishment_id:
                raise BrainAccessDenied()
            body = BrainObjectiveDecisionRequestSerializer(data=request.data)
            if not body.is_valid():
                raise BrainWorkError(
                    code="objective_decision_invalid",
                    message="La décision d'objectif est incomplète.",
                )
            data = body.validated_data
            decide_objective(
                user=request.user,
                objective_id=objective_id,
                expected_revision_id=data["expected_revision_id"],
                decision=data["decision"],
                indicator=data.get("indicator"),
                unit=data.get("unit"),
                scope=data.get("scope"),
                reference=data.get("reference"),
                target=data.get("target"),
                success_condition=data.get("success_condition"),
                due_on=data.get("due_on"),
                measurement_period_start=data.get("measurement_period_start"),
                measurement_period_end=data.get("measurement_period_end"),
                method=data.get("method"),
                justification=data.get("justification") or "",
            )
            del current
            return Response(
                BrainObjectiveSerializer(
                    objective_state(user=request.user, objective_id=objective_id)
                ).data
            )

        return _guard(decide)


class BrainMechanismRevisionView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = _AUTH
    permission_classes = _USER

    @extend_schema(
        tags=["brain"],
        request=BrainMechanismRevisionRequestSerializer,
        responses={
            200: BrainPlatformRepresentationSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, candidate_id):
        def revise():
            from houston.brain.models import BrainMechanismCandidate

            candidate = (
                BrainMechanismCandidate.objects.filter(pk=candidate_id)
                .only("id", "establishment_id")
                .first()
            )
            if candidate is None or candidate.establishment_id != self.establishment_id:
                raise BrainAccessDenied()
            if resolve_establishment_admin_actor(request.user, self.establishment_id) is None:
                raise BrainAccessDenied()
            body = BrainMechanismRevisionRequestSerializer(data=request.data)
            if not body.is_valid():
                raise BrainWorkError(
                    code="mechanism_representation_invalid",
                    message="La représentation globale est incomplète.",
                )
            data = body.validated_data
            representation = revise_global_representation(
                user=request.user,
                candidate_id=candidate_id,
                formulation=data["formulation"],
                conditions=data.get("conditions") or "",
                limits=data.get("limits") or "",
                uncertainty=data.get("uncertainty") or "",
            )
            return Response(BrainPlatformRepresentationSerializer(representation).data)

        return _guard(revise)


class BrainPlatformKnowledgeView(APIView):
    authentication_classes = _AUTH
    permission_classes = _OPERATOR

    @extend_schema(
        tags=["brain"],
        responses={
            200: BrainKnowledgeVersionListSerializer,
            403: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request):
        def read():
            rows = platform_knowledge_versions(user=request.user)
            return Response(BrainKnowledgeVersionListSerializer({"results": rows}).data)

        return _guard(read)


class BrainPlatformKnowledgeActivateView(APIView):
    authentication_classes = _AUTH
    permission_classes = _OPERATOR

    @extend_schema(
        tags=["brain"],
        request=None,
        responses={
            200: BrainKnowledgeVersionSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, version_id):
        def activate():
            version = activate_knowledge_version(user=request.user, version_id=version_id)
            return Response(
                BrainKnowledgeVersionSerializer(
                    {
                        "id": str(version.id),
                        "formulation": version.global_formulation,
                        "conditions": version.conditions,
                        "limits": version.limits,
                        "uncertainty": version.uncertainty,
                        "approved_at": version.approved_at,
                        "activated_at": version.activated_at,
                        "is_active": version.is_active,
                    }
                ).data
            )

        return _guard(activate)


class BrainPlatformMechanismListView(APIView):
    authentication_classes = _AUTH
    permission_classes = _OPERATOR

    @extend_schema(
        operation_id="v1_platform_brain_mechanisms_list",
        tags=["brain"],
        responses={
            200: BrainPlatformMechanismListSerializer,
            403: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request):
        def read():
            rows = platform_mechanism_candidates(user=request.user)
            return Response(BrainPlatformMechanismListSerializer({"results": rows}).data)

        return _guard(read)


class BrainPlatformMechanismDetailView(APIView):
    authentication_classes = _AUTH
    permission_classes = _OPERATOR

    @extend_schema(
        operation_id="v1_platform_brain_mechanisms_retrieve",
        tags=["brain"],
        responses={
            200: BrainPlatformMechanismSerializer,
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def get(self, request, candidate_id):
        def read():
            payload = platform_mechanism(user=request.user, candidate_id=candidate_id)
            return Response(BrainPlatformMechanismSerializer(payload).data)

        return _guard(read)


class BrainPlatformMechanismDecisionView(APIView):
    authentication_classes = _AUTH
    permission_classes = _OPERATOR

    @extend_schema(
        tags=["brain"],
        request=BrainMechanismDecisionRequestSerializer,
        responses={
            200: BrainPlatformMechanismSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, candidate_id):
        def decide():
            body = BrainMechanismDecisionRequestSerializer(data=request.data)
            if not body.is_valid():
                raise BrainWorkError(
                    code="mechanism_decision_invalid",
                    message="La revue du mécanisme n'est pas reconnue.",
                )
            decide_mechanism(
                user=request.user,
                candidate_id=candidate_id,
                decision=body.validated_data["decision"],
            )
            payload = platform_mechanism(user=request.user, candidate_id=candidate_id)
            return Response(BrainPlatformMechanismSerializer(payload).data)

        return _guard(decide)


def _public_work(work) -> dict:
    if isinstance(work, BrainMessage):
        reporting_id = work.analysis.reporting_id
        if reporting_id is None:
            reporting_id = BrainAnalysis.objects.values_list("reporting_id", flat=True).get(
                pk=work.analysis_id
            )
        return {
            "kind": "follow_up",
            "id": work.id,
            "analysis_id": work.analysis_id,
            "status": work.status,
            "reporting_id": reporting_id,
        }
    return {
        "kind": "analysis",
        "id": work.id,
        "analysis_id": work.id,
        "status": work.status,
        "reporting_id": work.reporting_id,
    }
