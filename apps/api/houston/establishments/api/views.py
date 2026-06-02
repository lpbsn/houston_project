from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.access import (
    get_api_access_context,
    get_onboarding_access_context,
)
from houston.establishments.ai_onboarding import (
    AIOnboardingFallbackFailedError,
    run_ai_onboarding_interpretation,
)
from houston.establishments.api.serializers import (
    ActivationResponseSerializer,
    ActivationSummaryResponseSerializer,
    ActivityDescriptionRequestSerializer,
    ActivityDescriptionUpdateResponseSerializer,
    AIOnboardingGenerateRequestSerializer,
    DirectorInvitationErrorResponseSerializer,
    DirectorInvitationRequestSerializer,
    DirectorInvitationResponseSerializer,
    EstablishmentMembershipResponseSerializer,
    MarkReadyResponseSerializer,
    MembershipInvitationRequestSerializer,
    MembershipUpdateRequestSerializer,
    OnboardingErrorResponseSerializer,
    OnboardingProposalErrorResponseSerializer,
    OnboardingProposalResponseSerializer,
    OnboardingSessionCreateRequestSerializer,
    OnboardingSessionCreateResponseSerializer,
    OnboardingSessionResponseSerializer,
    OperationalTaxonomyResponseSerializer,
    ProposalCommandResponseSerializer,
    ProposalItemMutationRequestSerializer,
    ProposalSectionDecisionRequestSerializer,
    RuntimeConfigResponseSerializer,
    ScopedUserSearchRequestSerializer,
    ScopedUserSearchResultSerializer,
    WorkspaceSummaryResponseSerializer,
)
from houston.establishments.membership_scope import parse_membership_scope_inputs
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    OnboardingProposal,
    OnboardingSession,
)
from houston.establishments.permissions import (
    CanInviteMemberships,
    CanManageMemberships,
    HasActiveMembership,
)
from houston.establishments.selectors import (
    get_active_onboarding_session_for_establishment,
    get_membership_for_management,
    get_onboarding_proposal_for_actor,
    get_onboarding_session_for_actor,
    get_operational_taxonomy_for_establishment,
    get_runtime_config_for_session,
    get_workspace_summary_for_establishment,
    list_memberships_for_management,
    list_onboarding_proposals_for_actor,
    search_users_for_establishment,
)
from houston.establishments.services import (
    ActiveOnboardingProposalExistsError,
    ActiveOnboardingSessionExistsError,
    CannotDeactivateLastActiveOwnerError,
    CannotDemoteLastActiveOwnerError,
    DirectorInvitationAlreadyExistsError,
    DirectorInvitationDuplicateError,
    DirectorInvitationOwnerNotAllowedError,
    InvalidActivityDescriptionError,
    InvalidDirectorInvitationInputError,
    InvalidMembershipInvitationInputError,
    InvalidMembershipScopeAssignmentError,
    InvalidOnboardingActivationStateError,
    InvalidOnboardingSessionScopeError,
    MembershipInvitationRoleNotAllowedError,
    MembershipManagementForbiddenError,
    MembershipManagementNotFoundError,
    MembershipUpdateInput,
    OnboardingAccessDeniedError,
    OnboardingProposalStateError,
    OnboardingProposalValidationError,
    OnboardingReadinessError,
    OnboardingSessionTerminalError,
    UnsupportedOnboardingSessionSourceModeError,
    activate_onboarding_session,
    apply_onboarding_proposal,
    build_activation_summary,
    deactivate_membership_for_management,
    invite_director_during_onboarding,
    invite_membership_for_establishment,
    mark_onboarding_ready_for_activation,
    reject_onboarding_proposal,
    start_onboarding_session,
    submit_activity_description,
    update_membership_for_management,
    update_onboarding_proposal_items,
    validate_onboarding_proposal_section,
)
from houston.organizations.models import Organization


class MembershipListView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageMemberships,
    ]

    @extend_schema(
        tags=["memberships"],
        responses={
            200: EstablishmentMembershipResponseSerializer(many=True),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Lists memberships for the current active establishment context. Requires "
            "an active selected establishment and owner or director authority."
        ),
    )
    def get(self, request, establishment_id):
        access_context = get_api_access_context(request)
        memberships = list_memberships_for_management(
            current_membership=access_context.active_membership,
            establishment_id=establishment_id,
        )
        if memberships is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = EstablishmentMembershipResponseSerializer(memberships, many=True)
        return Response(serializer.data)


class MembershipDetailView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageMemberships,
    ]

    @extend_schema(
        tags=["memberships"],
        responses={
            200: EstablishmentMembershipResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Returns one membership inside the current active establishment context. "
            "Requires owner or director authority."
        ),
    )
    def get(self, request, establishment_id, membership_id):
        access_context = get_api_access_context(request)
        membership = get_membership_for_management(
            current_membership=access_context.active_membership,
            establishment_id=establishment_id,
            membership_id=membership_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = EstablishmentMembershipResponseSerializer(membership)
        return Response(serializer.data)

    @extend_schema(
        tags=["memberships"],
        request=MembershipUpdateRequestSerializer,
        responses={
            200: EstablishmentMembershipResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Updates the role and active operational-domain assignments for one "
            "membership in the current active establishment context."
        ),
    )
    def patch(self, request, establishment_id, membership_id):
        serializer = MembershipUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_context = get_api_access_context(request)

        try:
            membership = update_membership_for_management(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                membership_id=membership_id,
                update_input=MembershipUpdateInput(
                    role=serializer.validated_data.get("role"),
                    scopes=(
                        parse_membership_scope_inputs(serializer.validated_data["scopes"])
                        if "scopes" in serializer.validated_data
                        else None
                    ),
                ),
            )
        except MembershipManagementNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidMembershipScopeAssignmentError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except CannotDemoteLastActiveOwnerError:
            return Response(
                {"detail": "The last active owner cannot be demoted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except MembershipManagementForbiddenError:
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You cannot manage this membership.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        response_serializer = EstablishmentMembershipResponseSerializer(membership)
        return Response(response_serializer.data)


class MembershipDeactivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageMemberships,
    ]

    @extend_schema(
        tags=["memberships"],
        request=None,
        responses={
            200: EstablishmentMembershipResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Deactivates one membership in the current active establishment context. "
            "The last active owner cannot be deactivated."
        ),
    )
    def post(self, request, establishment_id, membership_id):
        access_context = get_api_access_context(request)

        try:
            membership = deactivate_membership_for_management(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                membership_id=membership_id,
            )
        except MembershipManagementNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except CannotDeactivateLastActiveOwnerError:
            return Response(
                {"detail": "The last active owner cannot be deactivated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except MembershipManagementForbiddenError:
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You cannot manage this membership.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EstablishmentMembershipResponseSerializer(membership)
        return Response(serializer.data)


class EstablishmentOperationalTaxonomyView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageMemberships,
    ]

    @extend_schema(
        tags=["establishments"],
        responses={
            200: OperationalTaxonomyResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Returns the active operational taxonomy tree for membership scope assignment."
        ),
    )
    def get(self, request, establishment_id):
        access_context = get_api_access_context(request)
        taxonomy = get_operational_taxonomy_for_establishment(
            current_membership=access_context.active_membership,
            establishment_id=establishment_id,
        )
        if taxonomy is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OperationalTaxonomyResponseSerializer(taxonomy)
        return Response(serializer.data)


class WorkspaceSummaryView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
    ]

    @extend_schema(
        tags=["establishments"],
        responses={
            200: WorkspaceSummaryResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Returns a read-only establishment workspace summary for the current "
            "active establishment context. Any active member may read this summary."
        ),
    )
    def get(self, request, establishment_id):
        access_context = get_api_access_context(request)
        summary = get_workspace_summary_for_establishment(
            current_membership=access_context.active_membership,
            establishment_id=establishment_id,
        )
        if summary is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = WorkspaceSummaryResponseSerializer(summary)
        return Response(serializer.data)


class MembershipInvitationView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanInviteMemberships,
    ]

    @extend_schema(
        tags=["memberships"],
        request=MembershipInvitationRequestSerializer,
        responses={
            201: DirectorInvitationResponseSerializer,
            400: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Invites a staff or manager member to the active establishment. "
            "Returns a copyable invitation link; email delivery is not included in MVP."
        ),
    )
    def post(self, request, establishment_id):
        request_serializer = MembershipInvitationRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        access_context = get_api_access_context(request)

        try:
            invitation_result = invite_membership_for_establishment(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                email=request_serializer.validated_data["email"],
                first_name=request_serializer.validated_data["first_name"],
                last_name=request_serializer.validated_data["last_name"],
                role=request_serializer.validated_data["role"],
                scopes=parse_membership_scope_inputs(request_serializer.validated_data["scopes"]),
            )
        except MembershipManagementNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except MembershipManagementForbiddenError:
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You cannot invite members for this establishment.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except MembershipInvitationRoleNotAllowedError:
            return Response(
                {
                    "code": "membership_invitation_role_not_allowed",
                    "detail": "Only staff and manager roles can be invited from this workspace.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except DirectorInvitationDuplicateError:
            return Response(
                {
                    "code": "membership_invitation_duplicate",
                    "detail": "This user is already associated with the establishment.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidMembershipInvitationInputError as exc:
            return Response(
                {"code": "membership_invitation_invalid", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidMembershipScopeAssignmentError as exc:
            return Response(
                {"code": "membership_invitation_invalid", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = DirectorInvitationResponseSerializer(
            {
                "membership": invitation_result.membership,
                "invitation_token": invitation_result.invitation_token,
                "invitation_expires_at": invitation_result.invitation_expires_at,
                "invitation_accept_path": (f"/invitations/{invitation_result.invitation_token}"),
            }
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ScopedUserSearchView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
    ]

    @extend_schema(
        tags=["memberships"],
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Search term with a minimum length of 2 characters.",
            )
        ],
        responses={
            200: ScopedUserSearchResultSerializer(many=True),
            400: OpenApiResponse(description="Invalid query parameters."),
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Searches active users in the current active establishment context. "
            "Results are tenant-filtered before serialization and return only a "
            "minimal membership-backed user summary."
        ),
    )
    def get(self, request, establishment_id):
        query_serializer = ScopedUserSearchRequestSerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        access_context = get_api_access_context(request)
        memberships = search_users_for_establishment(
            current_membership=access_context.active_membership,
            establishment_id=establishment_id,
            query=query_serializer.validated_data["q"],
        )
        if memberships is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        response_serializer = ScopedUserSearchResultSerializer(memberships, many=True)
        return Response(response_serializer.data)


# Onboarding HTTP routes authorize via get_onboarding_access_context (path-scoped session,
# draft/active establishment). They do not use CanManageRuntimeContext, which applies to
# active-establishment workspace membership (session-selected context).
_ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME = "configure_runtime"
_ONBOARDING_CAPABILITY_ACTIVATE = "activate"


class OnboardingSessionCreateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=OnboardingSessionCreateRequestSerializer,
        responses={
            200: OnboardingSessionCreateResponseSerializer,
            201: OnboardingSessionCreateResponseSerializer,
            400: OpenApiResponse(response=OnboardingErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Starts or returns an existing non-terminal onboarding session for an "
            "establishment. Supports manual and template source modes only."
        ),
    )
    def post(self, request):
        serializer = OnboardingSessionCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        establishment = _get_onboarding_establishment(
            establishment_id=serializer.validated_data["establishment_id"],
        )
        if establishment is None:
            return _not_found_response()

        access = get_onboarding_access_context(
            actor=request.user,
            session=OnboardingSession(
                organization=establishment.organization,
                establishment=establishment,
            ),
        )
        if access.membership is None:
            return _not_found_response()
        if not access.can_manage:
            return _forbidden_response()

        existing_session = get_active_onboarding_session_for_establishment(
            actor=request.user,
            establishment_id=establishment.id,
        )
        if existing_session is not None:
            return _onboarding_session_start_response(
                session=existing_session,
                created=False,
                response_status=status.HTTP_200_OK,
            )

        try:
            session = start_onboarding_session(
                organization=establishment.organization,
                establishment=establishment,
                started_by=request.user,
                source_mode=serializer.validated_data["source_mode"],
            )
        except UnsupportedOnboardingSessionSourceModeError:
            return Response(
                {
                    "code": "unsupported_source_mode",
                    "detail": "Only manual and template onboarding sessions are supported.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidOnboardingSessionScopeError:
            return Response(
                {
                    "code": "invalid_onboarding_scope",
                    "detail": "Organization must match the establishment organization.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ActiveOnboardingSessionExistsError:
            existing_session = get_active_onboarding_session_for_establishment(
                actor=request.user,
                establishment_id=establishment.id,
            )
            if existing_session is None:
                return Response(
                    {
                        "code": "active_onboarding_session_exists",
                        "detail": (
                            "A non-terminal onboarding session already exists for this "
                            "establishment."
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            return _onboarding_session_start_response(
                session=existing_session,
                created=False,
                response_status=status.HTTP_200_OK,
            )

        return _onboarding_session_start_response(
            session=session,
            created=True,
            response_status=status.HTTP_201_CREATED,
        )


class OnboardingSessionDetailView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        responses={
            200: OnboardingSessionResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Returns one onboarding session visible to the authenticated actor.",
    )
    def get(self, request, session_id):
        session = get_onboarding_session_for_actor(actor=request.user, session_id=session_id)
        if session is None:
            return _not_found_response()

        serializer = OnboardingSessionResponseSerializer(session)
        return Response(serializer.data)


class OnboardingSessionDescriptionView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=ActivityDescriptionRequestSerializer,
        responses={
            200: ActivityDescriptionUpdateResponseSerializer,
            400: OpenApiResponse(response=OnboardingErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=OnboardingErrorResponseSerializer),
        },
        description="Submits the canonical establishment activity description for onboarding.",
    )
    def patch(self, request, session_id):
        serializer = ActivityDescriptionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_response = _get_onboarding_command_session(
            actor=request.user,
            session_id=session_id,
            capability=_ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME,
        )
        if isinstance(session_response, Response):
            return session_response

        try:
            activity_description = submit_activity_description(
                session=session_response,
                actor=request.user,
                description=serializer.validated_data["description"],
            )
        except OnboardingAccessDeniedError:
            return _forbidden_response()
        except InvalidActivityDescriptionError as exc:
            return Response(
                {
                    "code": "invalid_activity_description",
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except OnboardingSessionTerminalError:
            return _terminal_session_response()

        session = get_onboarding_session_for_actor(actor=request.user, session_id=session_id)
        response_serializer = ActivityDescriptionUpdateResponseSerializer(
            {
                "session": session,
                "activity_description": activity_description,
            }
        )
        return Response(response_serializer.data)


class OnboardingSessionRuntimeConfigView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        responses={
            200: RuntimeConfigResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Returns active runtime configuration for an onboarding session.",
    )
    def get(self, request, session_id):
        session = get_onboarding_session_for_actor(actor=request.user, session_id=session_id)
        if session is None:
            return _not_found_response()

        serializer = RuntimeConfigResponseSerializer(
            get_runtime_config_for_session(session=session)
        )
        return Response(serializer.data)


class OnboardingSessionActivationSummaryView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        responses={
            200: ActivationSummaryResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Returns backend activation readiness and blockers for onboarding.",
    )
    def get(self, request, session_id):
        session = get_onboarding_session_for_actor(actor=request.user, session_id=session_id)
        if session is None:
            return _not_found_response()

        return Response(_build_activation_summary_payload(session=session, actor=request.user))


class OnboardingSessionDirectorInvitationView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=DirectorInvitationRequestSerializer,
        responses={
            201: DirectorInvitationResponseSerializer,
            400: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=OnboardingErrorResponseSerializer),
        },
        description=(
            "Invites a Director to the draft establishment for an onboarding session. "
            "Creates or reuses a pending user and an invited director membership."
        ),
    )
    def post(self, request, session_id):
        session_response = _get_onboarding_command_session(
            actor=request.user,
            session_id=session_id,
            capability=_ONBOARDING_CAPABILITY_ACTIVATE,
        )
        if isinstance(session_response, Response):
            return session_response

        request_serializer = DirectorInvitationRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        try:
            invitation_result = invite_director_during_onboarding(
                session=session_response,
                actor=request.user,
                email=request_serializer.validated_data["email"],
                first_name=request_serializer.validated_data["first_name"],
                last_name=request_serializer.validated_data["last_name"],
            )
        except OnboardingAccessDeniedError:
            return _forbidden_response()
        except InvalidOnboardingActivationStateError as exc:
            return Response(
                {"code": "invalid_onboarding_state", "detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except DirectorInvitationOwnerNotAllowedError:
            return Response(
                {
                    "code": "director_invitation_owner_not_allowed",
                    "detail": "The establishment owner cannot be invited as Director.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DirectorInvitationDuplicateError:
            return Response(
                {
                    "code": "director_invitation_duplicate",
                    "detail": "This user is already associated with the establishment.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DirectorInvitationAlreadyExistsError:
            return Response(
                {
                    "code": "director_invitation_already_exists",
                    "detail": "This establishment already has an invited or active Director.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidDirectorInvitationInputError as exc:
            return Response(
                {"code": "director_invitation_invalid", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except OnboardingSessionTerminalError:
            return _terminal_session_response()

        response_serializer = DirectorInvitationResponseSerializer(
            {
                "membership": invitation_result.membership,
                "invitation_token": invitation_result.invitation_token,
                "invitation_expires_at": invitation_result.invitation_expires_at,
                "invitation_accept_path": (f"/invitations/{invitation_result.invitation_token}"),
            }
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class OnboardingSessionMarkReadyView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=None,
        responses={
            200: MarkReadyResponseSerializer,
            400: OpenApiResponse(response=OnboardingErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=OnboardingErrorResponseSerializer),
        },
        description=(
            "Marks an onboarding session ready for activation when backend readiness "
            "passes. This does not activate the establishment."
        ),
    )
    def post(self, request, session_id):
        session_response = _get_onboarding_command_session(
            actor=request.user,
            session_id=session_id,
            capability=_ONBOARDING_CAPABILITY_ACTIVATE,
        )
        if isinstance(session_response, Response):
            return session_response

        try:
            result = mark_onboarding_ready_for_activation(
                session=session_response,
                actor=request.user,
            )
        except OnboardingAccessDeniedError:
            return _forbidden_response()
        except OnboardingReadinessError as exc:
            return Response(
                {
                    "code": "activation_readiness_failed",
                    "detail": "Onboarding session is not ready for activation.",
                    "blockers": exc.readiness["blockers"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except OnboardingSessionTerminalError:
            return _terminal_session_response()

        session = result["session"]
        response_serializer = MarkReadyResponseSerializer(
            {
                "session": session,
                "activation_summary": _build_activation_summary_payload(
                    session=session,
                    actor=request.user,
                ),
            }
        )
        return Response(response_serializer.data)


class OnboardingSessionActivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=None,
        responses={
            200: ActivationResponseSerializer,
            400: OpenApiResponse(response=OnboardingErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=OnboardingErrorResponseSerializer),
        },
        description=(
            "Activates a marked-ready onboarding session and its draft establishment. "
            "Activation is explicit and backend-controlled."
        ),
    )
    def post(self, request, session_id):
        session_response = _get_onboarding_command_session(
            actor=request.user,
            session_id=session_id,
            capability=_ONBOARDING_CAPABILITY_ACTIVATE,
        )
        if isinstance(session_response, Response):
            return session_response

        try:
            result = activate_onboarding_session(
                session=session_response,
                actor=request.user,
            )
        except OnboardingAccessDeniedError:
            return _forbidden_response()
        except OnboardingReadinessError as exc:
            return Response(
                {
                    "code": "activation_readiness_failed",
                    "detail": "Onboarding session is not ready for activation.",
                    "blockers": exc.readiness["blockers"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidOnboardingActivationStateError as exc:
            return Response(
                {
                    "code": "invalid_onboarding_activation_state",
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )

        session = result["session"]
        response_serializer = ActivationResponseSerializer(
            {
                "session": session,
                "activation_summary": _build_activation_summary_payload(
                    session=session,
                    actor=request.user,
                ),
            }
        )
        return Response(response_serializer.data)


class OnboardingSessionProposalListView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        responses={
            200: OnboardingProposalResponseSerializer(many=True),
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Lists onboarding proposals for a path-scoped onboarding session.",
    )
    def get(self, request, session_id):
        session_response = _get_onboarding_command_session(
            actor=request.user,
            session_id=session_id,
            capability=_ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME,
        )
        if isinstance(session_response, Response):
            return session_response

        proposals = list_onboarding_proposals_for_actor(
            actor=request.user,
            session_id=session_response.id,
        )
        if proposals is None:
            return _not_found_response()

        serializer = OnboardingProposalResponseSerializer(proposals, many=True)
        return Response(serializer.data)


class OnboardingSessionProposalDetailView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        responses={
            200: OnboardingProposalResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Returns one onboarding proposal scoped to its onboarding session.",
    )
    def get(self, request, session_id, proposal_id):
        proposal_response = _get_onboarding_command_proposal(
            actor=request.user,
            session_id=session_id,
            proposal_id=proposal_id,
            capability=_ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME,
        )
        if isinstance(proposal_response, Response):
            return proposal_response

        serializer = OnboardingProposalResponseSerializer(proposal_response)
        return Response(serializer.data)


class OnboardingSessionProposalAIGenerateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=AIOnboardingGenerateRequestSerializer,
        responses={
            201: ProposalCommandResponseSerializer,
            400: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
            503: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
        },
        description=(
            "Runs AI onboarding interpretation for a session. The command creates an "
            "OnboardingProposal only and never applies runtime configuration."
        ),
    )
    def post(self, request, session_id):
        serializer = AIOnboardingGenerateRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        session_response = _get_onboarding_command_session(
            actor=request.user,
            session_id=session_id,
            capability=_ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME,
        )
        if isinstance(session_response, Response):
            return session_response

        try:
            proposal = run_ai_onboarding_interpretation(
                session=session_response,
                actor=request.user,
                locale=serializer.validated_data["locale"],
            )
        except InvalidActivityDescriptionError as exc:
            return Response(
                {
                    "code": "invalid_activity_description",
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ActiveOnboardingProposalExistsError:
            return _proposal_conflict_response(
                code="active_onboarding_proposal_exists",
                detail="A non-terminal onboarding proposal already exists for this session.",
            )
        except OnboardingAccessDeniedError:
            return _forbidden_response()
        except AIOnboardingFallbackFailedError:
            return Response(
                {
                    "code": "ai_onboarding_fallback_failed",
                    "detail": "AI onboarding could not create a proposal.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return _proposal_command_response(
            actor=request.user,
            proposal=proposal,
            response_status=status.HTTP_201_CREATED,
        )


class OnboardingSessionProposalSectionDecisionView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=ProposalSectionDecisionRequestSerializer,
        responses={
            200: ProposalCommandResponseSerializer,
            400: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
        },
        description="Accepts or skips one section of an onboarding proposal.",
    )
    def post(self, request, session_id, proposal_id, section):
        serializer = ProposalSectionDecisionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        proposal_response = _get_onboarding_command_proposal(
            actor=request.user,
            session_id=session_id,
            proposal_id=proposal_id,
            capability=_ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME,
        )
        if isinstance(proposal_response, Response):
            return proposal_response

        try:
            proposal = validate_onboarding_proposal_section(
                proposal=proposal_response,
                actor=request.user,
                section=section,
                decision=serializer.validated_data["decision"],
            )
        except OnboardingAccessDeniedError:
            return _forbidden_response()
        except OnboardingProposalValidationError as exc:
            return _proposal_validation_response(exc)
        except OnboardingProposalStateError as exc:
            return _proposal_state_response(str(exc))

        return _proposal_command_response(actor=request.user, proposal=proposal)


class OnboardingSessionProposalItemMutationView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=ProposalItemMutationRequestSerializer,
        responses={
            200: ProposalCommandResponseSerializer,
            400: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
        },
        description="Adds or removes one catalog item from an onboarding proposal payload.",
    )
    def post(self, request, session_id, proposal_id):
        serializer = ProposalItemMutationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        proposal_response = _get_onboarding_command_proposal(
            actor=request.user,
            session_id=session_id,
            proposal_id=proposal_id,
            capability=_ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME,
        )
        if isinstance(proposal_response, Response):
            return proposal_response

        try:
            proposal = update_onboarding_proposal_items(
                proposal=proposal_response,
                actor=request.user,
                section=serializer.validated_data["section"],
                key=serializer.validated_data["key"],
                action=serializer.validated_data["action"],
            )
        except OnboardingAccessDeniedError:
            return _forbidden_response()
        except OnboardingProposalValidationError as exc:
            return _proposal_validation_response(exc)
        except OnboardingProposalStateError as exc:
            return _proposal_state_response(str(exc))

        return _proposal_command_response(actor=request.user, proposal=proposal)


class OnboardingSessionProposalRejectView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=None,
        responses={
            200: ProposalCommandResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
        },
        description="Rejects an onboarding proposal without applying runtime changes.",
    )
    def post(self, request, session_id, proposal_id):
        proposal_response = _get_onboarding_command_proposal(
            actor=request.user,
            session_id=session_id,
            proposal_id=proposal_id,
            capability=_ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME,
        )
        if isinstance(proposal_response, Response):
            return proposal_response

        try:
            proposal = reject_onboarding_proposal(
                proposal=proposal_response,
                actor=request.user,
            )
        except OnboardingAccessDeniedError:
            return _forbidden_response()
        except OnboardingProposalStateError as exc:
            return _proposal_state_response(str(exc))

        return _proposal_command_response(actor=request.user, proposal=proposal)


class OnboardingSessionProposalApplyView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["onboarding"],
        request=None,
        responses={
            200: ProposalCommandResponseSerializer,
            400: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=OnboardingProposalErrorResponseSerializer),
        },
        description=(
            "Applies a validated onboarding proposal into runtime configuration. "
            "This does not activate the establishment."
        ),
    )
    def post(self, request, session_id, proposal_id):
        proposal_response = _get_onboarding_command_proposal(
            actor=request.user,
            session_id=session_id,
            proposal_id=proposal_id,
            capability=_ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME,
        )
        if isinstance(proposal_response, Response):
            return proposal_response

        try:
            proposal = apply_onboarding_proposal(
                proposal=proposal_response,
                actor=request.user,
            )
        except OnboardingAccessDeniedError:
            return _forbidden_response()
        except OnboardingProposalValidationError as exc:
            return _proposal_validation_response(exc)
        except OnboardingProposalStateError as exc:
            return _proposal_state_response(str(exc))
        except OnboardingSessionTerminalError:
            return _terminal_session_response()

        return _proposal_command_response(actor=request.user, proposal=proposal)


def _get_onboarding_establishment(*, establishment_id):
    return (
        Establishment.objects.select_related("organization")
        .filter(
            id=establishment_id,
            status__in={
                Establishment.Status.DRAFT,
                Establishment.Status.ACTIVE,
            },
            organization__status=Organization.Status.ACTIVE,
        )
        .first()
    )


def _get_onboarding_command_session(*, actor, session_id, capability: str):
    session = (
        OnboardingSession.objects.select_related(
            "organization",
            "establishment",
            "establishment__organization",
            "started_by",
        )
        .filter(id=session_id)
        .first()
    )
    if session is None:
        return _not_found_response()

    access = get_onboarding_access_context(actor=actor, session=session)
    if access.membership is None:
        return _not_found_response()

    if access.membership.role not in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return _forbidden_response()

    if capability == _ONBOARDING_CAPABILITY_CONFIGURE_RUNTIME and not access.can_configure_runtime:
        return _not_found_response()

    if capability == _ONBOARDING_CAPABILITY_ACTIVATE and not access.can_activate:
        establishment = access.establishment
        is_idempotent_activate = (
            session.status == OnboardingSession.Status.ACTIVATED
            and establishment is not None
            and establishment.status == Establishment.Status.ACTIVE
            and access.can_manage
        )
        if not is_idempotent_activate:
            return _not_found_response()

    return session


def _get_onboarding_command_proposal(*, actor, session_id, proposal_id, capability: str):
    session_response = _get_onboarding_command_session(
        actor=actor,
        session_id=session_id,
        capability=capability,
    )
    if isinstance(session_response, Response):
        return session_response

    proposal = get_onboarding_proposal_for_actor(
        actor=actor,
        session_id=session_response.id,
        proposal_id=proposal_id,
    )
    if proposal is None:
        return _not_found_response()

    return proposal


def _build_activation_summary_payload(*, session, actor):
    summary = build_activation_summary(session=session)
    access = get_onboarding_access_context(actor=actor, session=session)
    summary["access"] = {"can_activate": access.can_activate}
    summary["effective_can_activate"] = summary["readiness"]["is_ready"] and access.can_activate
    return summary


def _onboarding_session_start_response(*, session, created: bool, response_status: int):
    serializer = OnboardingSessionCreateResponseSerializer(
        {
            "created": created,
            "session": session,
        }
    )
    return Response(serializer.data, status=response_status)


def _proposal_command_response(*, actor, proposal: OnboardingProposal, response_status=200):
    session = get_onboarding_session_for_actor(
        actor=actor,
        session_id=proposal.onboarding_session_id,
    )
    serializer = ProposalCommandResponseSerializer(
        {
            "session": session or proposal.onboarding_session,
            "proposal": proposal,
        }
    )
    return Response(serializer.data, status=response_status)


def _proposal_validation_response(exc: OnboardingProposalValidationError):
    return Response(
        {
            "code": "invalid_onboarding_proposal",
            "detail": "Onboarding proposal payload is invalid.",
            "errors": exc.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _proposal_state_response(detail: str):
    return _proposal_conflict_response(
        code="invalid_onboarding_proposal_state",
        detail=detail or "Onboarding proposal state does not allow this command.",
    )


def _proposal_conflict_response(*, code: str, detail: str):
    return Response(
        {
            "code": code,
            "detail": detail,
        },
        status=status.HTTP_409_CONFLICT,
    )


def _not_found_response():
    return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


def _forbidden_response():
    return Response(
        {"detail": "You do not have permission to manage onboarding."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _terminal_session_response():
    return Response(
        {
            "code": "onboarding_session_terminal",
            "detail": "Terminal onboarding sessions cannot be changed.",
        },
        status=status.HTTP_409_CONFLICT,
    )
