from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.accounts.models import User
from houston.establishments.api.serializers import (
    OnboardingDraftResponseSerializer,
    OnboardingDraftUpdateRequestSerializer,
)
from houston.establishments.models import Establishment, OnboardingSession
from houston.establishments.services import (
    InvalidOnboardingActivationStateError,
    OnboardingDraftNotFoundError,
    OnboardingDraftValidationError,
    OnboardingSessionTerminalError,
    compute_activation_readiness,
)
from houston.organizations.models import Organization
from houston.platform.api.serializers import (
    PlatformDeleteRequestSerializer,
    PlatformEstablishmentDetailSerializer,
    PlatformEstablishmentListItemSerializer,
    PlatformEstablishmentListResponseSerializer,
    PlatformInviteRequestSerializer,
    PlatformInviteResponseSerializer,
    PlatformMembershipListResponseSerializer,
    PlatformMembershipSerializer,
    PlatformOnboardingCompleteResponseSerializer,
    PlatformOnboardingListItemSerializer,
    PlatformOnboardingListResponseSerializer,
    PlatformOnboardingStartRequestSerializer,
    PlatformOrganizationDetailSerializer,
    PlatformOrganizationListItemSerializer,
    PlatformOrganizationListResponseSerializer,
    PlatformSessionSerializer,
    PlatformUserDetailSerializer,
    PlatformUserListItemSerializer,
    PlatformUserListResponseSerializer,
)
from houston.platform.cursor import parse_page_size
from houston.platform.delete_services import (
    delete_platform_establishment,
    delete_platform_organization,
)
from houston.platform.exceptions import PlatformLifecycleDenied, PlatformLifecycleFailed
from houston.platform.onboarding_services import (
    complete_platform_onboarding,
    get_platform_onboarding_draft,
    invite_platform_director,
    invite_platform_owner,
    platform_activation_summary,
    start_platform_onboarding,
    upsert_platform_onboarding_draft,
)
from houston.platform.onboarding_status import derive_onboarding_functional_status
from houston.platform.permissions import IsActivePlatformOperator
from houston.platform.presentation import (
    establishment_queryset,
    membership_queryset,
    onboarding_queryset,
    organization_queryset,
    paginate_created_at_desc,
    serialize_establishment_detail,
    serialize_establishment_list_item,
    serialize_membership,
    serialize_onboarding_list_item,
    serialize_organization_detail,
    serialize_organization_list_item,
    serialize_user_detail,
    serialize_user_list_item,
    user_queryset,
)

_AUTH = [BearerAccessTokenAuthentication]
_PERMS = [permissions.IsAuthenticated, IsActivePlatformOperator]


def _list_query_params(*names: str) -> list[OpenApiParameter]:
    return [OpenApiParameter(name=name, type=str, required=False) for name in names]


def _cursor_response(*, items, next_cursor, serializer_class) -> Response:
    return Response(
        {
            "next_cursor": next_cursor,
            "results": serializer_class(items, many=True).data,
        }
    )


_DENIED_HTTP_400 = frozenset(
    {
        "justification_required",
        "invalid_organization_name",
        "onboarding_draft_invalid",
        "membership_invitation_invalid",
        "invalid_normalized_name",
        "catalog_subject_business_unit_mismatch",
        "validation_error",
    }
)
_DENIED_HTTP_404 = frozenset(
    {
        "draft_not_found",
        "business_unit_not_found",
        "catalog_business_unit_not_found",
    }
)
_DENIED_HTTP_409 = frozenset(
    {
        "establishment_not_deletable",
        "organization_not_deletable",
        "activation_not_ready",
        "invalid_onboarding_state",
        "establishment_already_active",
        "runtime_already_materialized",
        "director_invitation_already_exists",
        "director_invitation_owner_not_allowed",
        "membership_invitation_duplicate",
        "membership_invitation_user_exists",
        "membership_invitation_owner_conflict",
        "organizational_owner_invariant_conflict",
        "catalog_business_unit_inactive",
        "catalog_activity_subject_inactive",
        "duplicate_specific_name",
        "duplicate_transversal_catalog_instance",
        "business_unit_identity_conflict",
        "duplicate_activity_subject_normalized_name",
        "duplicate_activity_subject_routing_key",
        "activity_subject_identity_conflict",
        "conflict_error",
    }
)


def _denied_response(exc: PlatformLifecycleDenied) -> Response:
    if exc.code in _DENIED_HTTP_400:
        http_status = status.HTTP_400_BAD_REQUEST
    elif exc.code in _DENIED_HTTP_404:
        http_status = status.HTTP_404_NOT_FOUND
    elif exc.code in _DENIED_HTTP_409:
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_403_FORBIDDEN
    body: dict = {"code": exc.code, "detail": exc.message}
    if isinstance(exc.extra, dict):
        for key, value in exc.extra.items():
            if key in {"code", "detail"}:
                continue
            body[key] = value
    return Response(body, status=http_status)


class PlatformSessionView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        responses={
            200: PlatformSessionSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request):
        serializer = PlatformSessionSerializer(
            {
                "platform_operator_active": True,
                "operator_id": request.user.pk,
            }
        )
        return Response(serializer.data)


class PlatformOrganizationListView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_organizations_list",
        parameters=_list_query_params("q", "status", "cursor", "limit"),
        responses={200: PlatformOrganizationListResponseSerializer},
    )
    def get(self, request):
        page = paginate_created_at_desc(
            organization_queryset(
                search=request.query_params.get("q", ""),
                status=request.query_params.get("status", ""),
            ),
            cursor=request.query_params.get("cursor"),
            limit=parse_page_size(request.query_params.get("limit")),
        )
        return _cursor_response(
            items=[serialize_organization_list_item(item) for item in page["items"]],
            next_cursor=page["next_cursor"],
            serializer_class=PlatformOrganizationListItemSerializer,
        )


class PlatformOrganizationDetailView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(tags=["platform"], responses={200: PlatformOrganizationDetailSerializer})
    def get(self, request, organization_id):
        organization = Organization.objects.filter(pk=organization_id).first()
        if organization is None:
            return Response(
                {"code": "not_found", "detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            PlatformOrganizationDetailSerializer(serialize_organization_detail(organization)).data
        )


class PlatformOrganizationDeleteView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_organization_delete",
        request=PlatformDeleteRequestSerializer,
        responses={204: None},
    )
    def post(self, request, organization_id):
        organization = Organization.objects.filter(pk=organization_id).first()
        if organization is None:
            return Response(
                {"code": "not_found", "detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PlatformDeleteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            delete_platform_organization(
                operator=request.user,
                organization=organization,
                justification=serializer.validated_data["justification"],
            )
        except PlatformLifecycleDenied as exc:
            return _denied_response(exc)
        except PlatformLifecycleFailed as exc:
            return Response(
                {"code": exc.code, "detail": exc.message},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformEstablishmentListView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_establishments_list",
        parameters=_list_query_params("q", "status", "organization_id", "cursor", "limit"),
        responses={200: PlatformEstablishmentListResponseSerializer},
    )
    def get(self, request):
        page = paginate_created_at_desc(
            establishment_queryset(
                search=request.query_params.get("q", ""),
                status=request.query_params.get("status", ""),
                organization_id=request.query_params.get("organization_id", ""),
            ),
            cursor=request.query_params.get("cursor"),
            limit=parse_page_size(request.query_params.get("limit")),
        )
        return _cursor_response(
            items=[serialize_establishment_list_item(item) for item in page["items"]],
            next_cursor=page["next_cursor"],
            serializer_class=PlatformEstablishmentListItemSerializer,
        )


class PlatformEstablishmentDetailView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(tags=["platform"], responses={200: PlatformEstablishmentDetailSerializer})
    def get(self, request, establishment_id):
        establishment = (
            Establishment.objects.select_related("organization")
            .filter(pk=establishment_id)
            .first()
        )
        if establishment is None:
            return Response(
                {"code": "not_found", "detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            PlatformEstablishmentDetailSerializer(
                serialize_establishment_detail(establishment)
            ).data
        )


class PlatformEstablishmentDeleteView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_establishment_delete",
        request=PlatformDeleteRequestSerializer,
        responses={204: None},
    )
    def post(self, request, establishment_id):
        establishment = Establishment.objects.filter(pk=establishment_id).first()
        if establishment is None:
            return Response(
                {"code": "not_found", "detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PlatformDeleteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            delete_platform_establishment(
                operator=request.user,
                establishment=establishment,
                justification=serializer.validated_data["justification"],
            )
        except PlatformLifecycleDenied as exc:
            return _denied_response(exc)
        except PlatformLifecycleFailed as exc:
            return Response(
                {"code": exc.code, "detail": exc.message},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformUserListView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_users_list",
        parameters=_list_query_params("q", "status", "cursor", "limit"),
        responses={200: PlatformUserListResponseSerializer},
    )
    def get(self, request):
        page = paginate_created_at_desc(
            user_queryset(
                search=request.query_params.get("q", ""),
                status=request.query_params.get("status", ""),
            ),
            cursor=request.query_params.get("cursor"),
            limit=parse_page_size(request.query_params.get("limit")),
        )
        return _cursor_response(
            items=[serialize_user_list_item(item) for item in page["items"]],
            next_cursor=page["next_cursor"],
            serializer_class=PlatformUserListItemSerializer,
        )


class PlatformUserDetailView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(tags=["platform"], responses={200: PlatformUserDetailSerializer})
    def get(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return Response(
                {"code": "not_found", "detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(PlatformUserDetailSerializer(serialize_user_detail(user)).data)


class PlatformMembershipListView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_memberships_list",
        parameters=_list_query_params(
            "user_id",
            "establishment_id",
            "organization_id",
            "role",
            "status",
            "cursor",
            "limit",
        ),
        responses={200: PlatformMembershipListResponseSerializer},
    )
    def get(self, request):
        page = paginate_created_at_desc(
            membership_queryset(
                user_id=request.query_params.get("user_id", ""),
                establishment_id=request.query_params.get("establishment_id", ""),
                organization_id=request.query_params.get("organization_id", ""),
                role=request.query_params.get("role", ""),
                status=request.query_params.get("status", ""),
            ),
            cursor=request.query_params.get("cursor"),
            limit=parse_page_size(request.query_params.get("limit")),
        )
        return _cursor_response(
            items=[serialize_membership(item) for item in page["items"]],
            next_cursor=page["next_cursor"],
            serializer_class=PlatformMembershipSerializer,
        )


class PlatformOnboardingListCreateView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_onboardings_list",
        parameters=_list_query_params("q", "cursor", "limit"),
        responses={200: PlatformOnboardingListResponseSerializer},
    )
    def get(self, request):
        page = paginate_created_at_desc(
            onboarding_queryset(
                search=request.query_params.get("q", ""),
            ),
            cursor=request.query_params.get("cursor"),
            limit=parse_page_size(request.query_params.get("limit")),
        )
        return _cursor_response(
            items=[serialize_onboarding_list_item(item) for item in page["items"]],
            next_cursor=page["next_cursor"],
            serializer_class=PlatformOnboardingListItemSerializer,
        )

    @extend_schema(
        tags=["platform"],
        operation_id="platform_onboardings_create",
        request=PlatformOnboardingStartRequestSerializer,
        responses={201: PlatformOnboardingListItemSerializer},
    )
    def post(self, request):
        serializer = PlatformOnboardingStartRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            session = start_platform_onboarding(
                operator=request.user,
                organization_name=serializer.validated_data["organization_name"],
                establishment_name=serializer.validated_data.get("establishment_name"),
            )
        except PlatformLifecycleDenied as exc:
            return _denied_response(exc)
        return Response(
            PlatformOnboardingListItemSerializer(serialize_onboarding_list_item(session)).data,
            status=status.HTTP_201_CREATED,
        )


def _get_platform_session(session_id) -> OnboardingSession | Response:
    session = (
        OnboardingSession.objects.select_related("establishment", "organization")
        .filter(pk=session_id)
        .first()
    )
    if session is None:
        return Response(
            {"code": "not_found", "detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return session


class PlatformOnboardingDetailView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_onboarding_retrieve",
        responses={200: PlatformOnboardingListItemSerializer},
    )
    def get(self, request, session_id):
        session = _get_platform_session(session_id)
        if isinstance(session, Response):
            return session
        payload = serialize_onboarding_list_item(session)
        payload["readiness"] = compute_activation_readiness(session=session)
        payload["functional_status"] = derive_onboarding_functional_status(
            establishment=session.establishment,
            session=session,
            readiness=payload["readiness"],
        )
        return Response(payload)


class PlatformOnboardingDraftView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS
    serializer_class = OnboardingDraftResponseSerializer

    @extend_schema(tags=["platform"], responses={200: OnboardingDraftResponseSerializer})
    def get(self, request, session_id):
        session = _get_platform_session(session_id)
        if isinstance(session, Response):
            return session
        try:
            payload = get_platform_onboarding_draft(session=session)
        except OnboardingDraftNotFoundError:
            return Response(
                {"code": "draft_not_found", "detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (OnboardingSessionTerminalError, InvalidOnboardingActivationStateError) as exc:
            return Response(
                {"code": "invalid_onboarding_state", "detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(OnboardingDraftResponseSerializer(payload).data)

    @extend_schema(tags=["platform"], request=OnboardingDraftUpdateRequestSerializer)
    def put(self, request, session_id):
        session = _get_platform_session(session_id)
        if isinstance(session, Response):
            return session
        request_serializer = OnboardingDraftUpdateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        try:
            payload = upsert_platform_onboarding_draft(
                operator=request.user,
                session=session,
                payload=request_serializer.validated_data["payload"],
            )
        except OnboardingDraftNotFoundError:
            return Response(
                {"code": "draft_not_found", "detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except OnboardingDraftValidationError as exc:
            return Response(
                {
                    "code": "onboarding_draft_invalid",
                    "detail": "Invalid draft.",
                    "errors": exc.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (OnboardingSessionTerminalError, InvalidOnboardingActivationStateError) as exc:
            return Response(
                {"code": "invalid_onboarding_state", "detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(OnboardingDraftResponseSerializer(payload).data)


class PlatformOnboardingCompleteView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_onboarding_complete",
        request=None,
        responses={200: PlatformOnboardingCompleteResponseSerializer},
    )
    def post(self, request, session_id):
        session = _get_platform_session(session_id)
        if isinstance(session, Response):
            return session
        try:
            result = complete_platform_onboarding(operator=request.user, session=session)
        except PlatformLifecycleDenied as exc:
            return _denied_response(exc)
        return Response(
            {
                "session_id": str(result["session"].id),
                "activated": result["activated"],
                "idempotent": result["idempotent"],
                "readiness": result["readiness"],
            }
        )


class PlatformOnboardingSummaryView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS
    serializer_class = PlatformOnboardingCompleteResponseSerializer

    @extend_schema(
        tags=["platform"],
        operation_id="platform_onboarding_summary",
    )
    def get(self, request, session_id):
        session = _get_platform_session(session_id)
        if isinstance(session, Response):
            return session
        return Response(platform_activation_summary(session=session))


class PlatformOnboardingDirectorInviteView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_onboarding_invite_director",
        request=PlatformInviteRequestSerializer,
        responses={201: PlatformInviteResponseSerializer},
    )
    def post(self, request, session_id):
        session = _get_platform_session(session_id)
        if isinstance(session, Response):
            return session
        serializer = PlatformInviteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation = invite_platform_director(
                operator=request.user,
                session=session,
                **serializer.validated_data,
            )
        except PlatformLifecycleDenied as exc:
            return _denied_response(exc)
        return Response({"membership_id": str(invitation.membership.id)}, status=201)


class PlatformOnboardingOwnerInviteView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    @extend_schema(
        tags=["platform"],
        operation_id="platform_onboarding_invite_owner",
        request=PlatformInviteRequestSerializer,
        responses={201: PlatformInviteResponseSerializer},
    )
    def post(self, request, session_id):
        session = _get_platform_session(session_id)
        if isinstance(session, Response):
            return session
        serializer = PlatformInviteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation = invite_platform_owner(
                operator=request.user,
                session=session,
                **serializer.validated_data,
            )
        except PlatformLifecycleDenied as exc:
            return _denied_response(exc)
        return Response({"membership_id": str(invitation.membership.id)}, status=201)
