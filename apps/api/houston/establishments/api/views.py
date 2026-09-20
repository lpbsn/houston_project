from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.access import get_api_access_context
from houston.establishments.api.serializers import (
    ActivitySubjectTreeItemSerializer,
    BusinessUnitTreeItemSerializer,
    BusinessUnitTreeResponseSerializer,
    CatalogActivitySubjectSuggestionSerializer,
    CatalogBusinessUnitSuggestionSerializer,
    DirectorInvitationErrorResponseSerializer,
    DirectorInvitationResponseSerializer,
    EstablishmentMembershipDetailResponseSerializer,
    EstablishmentMembershipResponseSerializer,
    MembershipInvitationRequestSerializer,
    MembershipReinviteResponseSerializer,
    MembershipUpdateRequestSerializer,
    RuntimeActivitySubjectCreateRequestSerializer,
    RuntimeBusinessUnitCreateRequestSerializer,
    RuntimeBusinessUnitUpdateRequestSerializer,
    RuntimeConfigErrorResponseSerializer,
    ScopedUserSearchRequestSerializer,
    ScopedUserSearchResultSerializer,
)
from houston.establishments.business_unit_catalog import (
    suggest_activity_subjects,
    suggest_business_units,
)
from houston.establishments.invitation_email import build_invitation_accept_path
from houston.establishments.membership_scope import parse_membership_scope_inputs
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.permissions import (
    CanManageRuntimeContext,
    CanViewTeamMemberships,
    HasActiveMembership,
    can_invite_memberships,
    can_manage_runtime_context,
)
from houston.establishments.selectors import (
    get_business_units_for_establishment,
    get_membership_for_invitation,
    get_membership_for_team_detail,
    list_memberships_for_team,
    search_users_for_establishment,
    serialize_activity_subject_tree_item,
    serialize_business_unit_tree_item,
)
from houston.establishments.services import (
    CannotDeactivateLastActiveOwnerError,
    DirectorCoverageInvariantError,
    DirectorInvitationDuplicateError,
    InvalidMembershipInvitationInputError,
    InvalidMembershipScopeAssignmentError,
    InvitedMembershipActivationError,
    MembershipInvitationOwnerConflictError,
    MembershipInvitationRoleNotAllowedError,
    MembershipInvitationUserExistsError,
    MembershipManagementForbiddenError,
    MembershipManagementNotFoundError,
    MembershipReinviteConflictError,
    MembershipRoleChangeForbiddenError,
    MembershipUpdateInput,
    OrganizationalOwnerInvariantConflictError,
    RuntimeConfigConflictError,
    RuntimeConfigNotFoundError,
    activate_membership_for_management,
    create_runtime_activity_subject,
    create_runtime_business_unit,
    deactivate_membership_for_management,
    deactivate_runtime_activity_subject,
    deactivate_runtime_business_unit,
    invite_membership_for_establishment,
    reactivate_runtime_activity_subject,
    reactivate_runtime_business_unit,
    reinvite_membership_for_establishment,
    resolve_stale_owner_actor_membership_for_deactivation,
    update_membership_for_management,
    update_runtime_business_unit,
)


def _membership_response(membership, *, actor_membership) -> Response:
    serializer = EstablishmentMembershipResponseSerializer(
        membership,
        context={"actor_membership": actor_membership},
    )
    return Response(serializer.data)


def _membership_detail_response(membership, *, actor_membership) -> Response:
    serializer = EstablishmentMembershipDetailResponseSerializer(
        membership,
        context={"actor_membership": actor_membership},
    )
    return Response(serializer.data)


def _not_found_response():
    return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


def _runtime_config_conflict_response(exc: RuntimeConfigConflictError):
    return Response(
        {
            "code": exc.code,
            "detail": exc.detail,
        },
        status=status.HTTP_409_CONFLICT,
    )


class MembershipListView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewTeamMemberships,
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
            "an active selected establishment membership."
        ),
    )
    def get(self, request, establishment_id):
        access_context = get_api_access_context(request)
        memberships = list_memberships_for_team(
            current_membership=access_context.active_membership,
            establishment_id=establishment_id,
        )
        if memberships is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = EstablishmentMembershipResponseSerializer(
            memberships,
            many=True,
            context={"actor_membership": access_context.active_membership},
        )
        return Response(serializer.data)


class MembershipDetailView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewTeamMemberships,
    ]

    @extend_schema(
        tags=["memberships"],
        responses={
            200: EstablishmentMembershipDetailResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Returns one membership inside the current active establishment context."
        ),
    )
    def get(self, request, establishment_id, membership_id):
        access_context = get_api_access_context(request)
        membership = get_membership_for_team_detail(
            current_membership=access_context.active_membership,
            establishment_id=establishment_id,
            membership_id=membership_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return _membership_detail_response(
            membership,
            actor_membership=access_context.active_membership,
        )

    @extend_schema(
        tags=["memberships"],
        request=MembershipUpdateRequestSerializer,
        responses={
            200: EstablishmentMembershipDetailResponseSerializer,
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
        except MembershipRoleChangeForbiddenError:
            return Response(
                {
                    "code": "membership_role_change_forbidden",
                    "detail": "This membership role change is not allowed.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except DirectorCoverageInvariantError as exc:
            return Response(
                {
                    "code": "director_coverage_invariant",
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )
        except MembershipManagementForbiddenError:
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You cannot manage this membership.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return _membership_detail_response(
            membership,
            actor_membership=access_context.active_membership,
        )


class MembershipReinviteView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewTeamMemberships,
    ]

    @extend_schema(
        tags=["memberships"],
        request=None,
        responses={
            200: MembershipReinviteResponseSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Reissues the pending invitation for an invited membership: revokes the "
            "previous live token, creates a new invitation, and schedules email when "
            "enabled. Returns the new token for manual copy."
        ),
    )
    def post(self, request, establishment_id, membership_id):
        access_context = get_api_access_context(request)
        current_membership = access_context.active_membership

        if not can_invite_memberships(current_membership):
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You do not have permission to invite memberships.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            invitation_result = reinvite_membership_for_establishment(
                current_membership=current_membership,
                establishment_id=establishment_id,
                membership_id=membership_id,
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
                    "detail": (
                        "This role cannot be invited from this workspace with your "
                        "current membership."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except MembershipReinviteConflictError:
            return Response(
                {
                    "code": "membership_reinvite_conflict",
                    "detail": "This membership cannot be reinvited in its current state.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        response_serializer = MembershipReinviteResponseSerializer(
            {
                "membership": invitation_result.membership,
                "invitation_token": invitation_result.invitation_token,
                "invitation_expires_at": invitation_result.invitation_expires_at,
                "invitation_accept_path": build_invitation_accept_path(
                    raw_token=invitation_result.invitation_token
                ),
                "email_scheduling_status": invitation_result.email_scheduling_status,
            },
            context={"actor_membership": current_membership},
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class MembershipDeactivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
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
            409: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
        },
        description=(
            "Deactivates one membership in the current active establishment context. "
            "Owner deactivation fans out across draft and active establishments in the "
            "organization. The last full-coverage active owner cannot be deactivated."
        ),
    )
    def post(self, request, establishment_id, membership_id):
        access_context = get_api_access_context(request)
        current_membership = access_context.active_membership
        if current_membership is None:
            current_membership = resolve_stale_owner_actor_membership_for_deactivation(
                user=request.user,
                establishment_id=establishment_id,
                membership_id=membership_id,
            )
        if current_membership is None:
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You cannot manage this membership.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            membership = deactivate_membership_for_management(
                current_membership=current_membership,
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
        except DirectorCoverageInvariantError as exc:
            return Response(
                {
                    "code": "director_coverage_invariant",
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )
        except OrganizationalOwnerInvariantConflictError as exc:
            return Response(
                {
                    "code": "organizational_owner_invariant_conflict",
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )
        except MembershipManagementForbiddenError:
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You cannot manage this membership.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EstablishmentMembershipResponseSerializer(
            membership,
            context={"actor_membership": current_membership},
        )
        return Response(serializer.data)


class MembershipActivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanViewTeamMemberships,
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
            409: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
        },
        description=(
            "Activates one membership in the current active establishment context. "
            "Owner reactivation fans out across draft and active establishments in the "
            "organization without issuing an invitation email. Invited memberships "
            "cannot be activated until the invitation is accepted."
        ),
    )
    def post(self, request, establishment_id, membership_id):
        access_context = get_api_access_context(request)

        try:
            membership = activate_membership_for_management(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                membership_id=membership_id,
            )
        except MembershipManagementNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvitedMembershipActivationError:
            return Response(
                {
                    "code": "invited_membership_activation_forbidden",
                    "detail": "Invited memberships cannot be activated until accepted.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except OrganizationalOwnerInvariantConflictError as exc:
            return Response(
                {
                    "code": "organizational_owner_invariant_conflict",
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )
        except MembershipManagementForbiddenError:
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You cannot manage this membership.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EstablishmentMembershipResponseSerializer(
            membership,
            context={"actor_membership": access_context.active_membership},
        )
        return Response(serializer.data)


class EstablishmentBusinessUnitTreeView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes_get = [
        permissions.IsAuthenticated,
        HasActiveMembership,
    ]
    permission_classes_post = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageRuntimeContext,
    ]

    def get_permissions(self):
        if self.request.method == "POST":
            return [permission() for permission in self.permission_classes_post]
        return [permission() for permission in self.permission_classes_get]

    @extend_schema(
        tags=["establishments"],
        parameters=[
            OpenApiParameter(
                name="include_inactive",
                required=False,
                type=bool,
                description=(
                    "When true and the actor can manage runtime context, include inactive "
                    "business units."
                ),
            ),
        ],
        responses={
            200: BusinessUnitTreeResponseSerializer,
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Returns the BusinessUnit / ActivitySubject tree for the establishment.",
    )
    def get(self, request, establishment_id):
        access_context = get_api_access_context(request)
        include_inactive_raw = request.query_params.get("include_inactive", "").strip().lower()
        include_inactive = include_inactive_raw in {
            "1",
            "true",
            "yes",
        } and can_manage_runtime_context(access_context.active_membership)
        tree = get_business_units_for_establishment(
            current_membership=access_context.active_membership,
            establishment_id=establishment_id,
            include_inactive=include_inactive,
        )
        if tree is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = BusinessUnitTreeResponseSerializer(tree)
        return Response(serializer.data)

    @extend_schema(
        tags=["establishments"],
        request=RuntimeBusinessUnitCreateRequestSerializer,
        responses={
            201: BusinessUnitTreeItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=RuntimeConfigErrorResponseSerializer),
        },
        description="Creates a runtime business unit for an active establishment.",
    )
    def post(self, request, establishment_id):
        serializer = RuntimeBusinessUnitCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_context = get_api_access_context(request)

        try:
            business_unit = create_runtime_business_unit(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                catalog_key=serializer.validated_data["catalog_key"],
                specific_name=serializer.validated_data["specific_name"],
                instance_description=serializer.validated_data.get(
                    "instance_description",
                    "",
                ),
            )
        except RuntimeConfigNotFoundError:
            return _not_found_response()
        except RuntimeConfigConflictError as exc:
            return _runtime_config_conflict_response(exc)

        response_serializer = BusinessUnitTreeItemSerializer(
            serialize_business_unit_tree_item(business_unit=business_unit)
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class EstablishmentBusinessUnitDetailView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageRuntimeContext,
    ]

    @extend_schema(
        tags=["establishments"],
        request=RuntimeBusinessUnitUpdateRequestSerializer,
        responses={
            200: BusinessUnitTreeItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=RuntimeConfigErrorResponseSerializer),
        },
        description="Updates a runtime business unit specific_name and/or instance_description.",
    )
    def patch(self, request, establishment_id, business_unit_id):
        serializer = RuntimeBusinessUnitUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_context = get_api_access_context(request)

        try:
            business_unit = update_runtime_business_unit(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                business_unit_id=business_unit_id,
                specific_name=serializer.validated_data.get("specific_name"),
                instance_description=serializer.validated_data.get("instance_description"),
            )
        except RuntimeConfigNotFoundError:
            return _not_found_response()
        except RuntimeConfigConflictError as exc:
            return _runtime_config_conflict_response(exc)

        response_serializer = BusinessUnitTreeItemSerializer(
            serialize_business_unit_tree_item(business_unit=business_unit)
        )
        return Response(response_serializer.data)


class EstablishmentBusinessUnitReactivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageRuntimeContext,
    ]

    @extend_schema(
        tags=["establishments"],
        request=None,
        responses={
            200: BusinessUnitTreeItemSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=RuntimeConfigErrorResponseSerializer),
        },
        description="Reactivates an inactive runtime business unit without reseeding subjects.",
    )
    def post(self, request, establishment_id, business_unit_id):
        access_context = get_api_access_context(request)

        try:
            business_unit = reactivate_runtime_business_unit(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                business_unit_id=business_unit_id,
            )
        except RuntimeConfigNotFoundError:
            return _not_found_response()
        except RuntimeConfigConflictError as exc:
            return _runtime_config_conflict_response(exc)

        response_serializer = BusinessUnitTreeItemSerializer(
            serialize_business_unit_tree_item(business_unit=business_unit)
        )
        return Response(response_serializer.data)


class EstablishmentBusinessUnitDeactivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageRuntimeContext,
    ]

    @extend_schema(
        tags=["establishments"],
        request=None,
        responses={
            200: BusinessUnitTreeItemSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=RuntimeConfigErrorResponseSerializer),
        },
        description="Soft-deactivates a runtime business unit and its activity subjects.",
    )
    def post(self, request, establishment_id, business_unit_id):
        access_context = get_api_access_context(request)

        try:
            business_unit = deactivate_runtime_business_unit(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                business_unit_id=business_unit_id,
            )
        except RuntimeConfigNotFoundError:
            return _not_found_response()
        except RuntimeConfigConflictError as exc:
            return _runtime_config_conflict_response(exc)

        response_serializer = BusinessUnitTreeItemSerializer(
            serialize_business_unit_tree_item(business_unit=business_unit)
        )
        return Response(response_serializer.data)


class EstablishmentActivitySubjectCreateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageRuntimeContext,
    ]

    @extend_schema(
        tags=["establishments"],
        request=RuntimeActivitySubjectCreateRequestSerializer,
        responses={
            201: ActivitySubjectTreeItemSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=RuntimeConfigErrorResponseSerializer),
        },
        description="Creates a runtime activity subject under a business unit.",
    )
    def post(self, request, establishment_id, business_unit_id):
        serializer = RuntimeActivitySubjectCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_context = get_api_access_context(request)
        catalog_key = serializer.validated_data.get("catalog_key")
        normalized_catalog_key = catalog_key.strip() if isinstance(catalog_key, str) else None
        if normalized_catalog_key == "":
            normalized_catalog_key = None

        try:
            activity_subject = create_runtime_activity_subject(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                business_unit_id=business_unit_id,
                label=serializer.validated_data.get("label"),
                description=serializer.validated_data.get("description", ""),
                catalog_key=normalized_catalog_key,
            )
        except RuntimeConfigNotFoundError:
            return _not_found_response()
        except RuntimeConfigConflictError as exc:
            return _runtime_config_conflict_response(exc)

        response_serializer = ActivitySubjectTreeItemSerializer(
            serialize_activity_subject_tree_item(activity_subject=activity_subject)
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class EstablishmentActivitySubjectReactivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageRuntimeContext,
    ]

    @extend_schema(
        tags=["establishments"],
        request=None,
        responses={
            200: ActivitySubjectTreeItemSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=RuntimeConfigErrorResponseSerializer),
        },
        description="Reactivates an inactive runtime activity subject.",
    )
    def post(self, request, establishment_id, activity_subject_id):
        access_context = get_api_access_context(request)

        try:
            activity_subject = reactivate_runtime_activity_subject(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                activity_subject_id=activity_subject_id,
            )
        except RuntimeConfigNotFoundError:
            return _not_found_response()
        except RuntimeConfigConflictError as exc:
            return _runtime_config_conflict_response(exc)

        response_serializer = ActivitySubjectTreeItemSerializer(
            serialize_activity_subject_tree_item(activity_subject=activity_subject)
        )
        return Response(response_serializer.data)


class EstablishmentActivitySubjectDeactivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanManageRuntimeContext,
    ]

    @extend_schema(
        tags=["establishments"],
        request=None,
        responses={
            200: ActivitySubjectTreeItemSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=RuntimeConfigErrorResponseSerializer),
        },
        description="Soft-deactivates a runtime activity subject.",
    )
    def post(self, request, establishment_id, activity_subject_id):
        access_context = get_api_access_context(request)

        try:
            activity_subject = deactivate_runtime_activity_subject(
                current_membership=access_context.active_membership,
                establishment_id=establishment_id,
                activity_subject_id=activity_subject_id,
            )
        except RuntimeConfigNotFoundError:
            return _not_found_response()
        except RuntimeConfigConflictError as exc:
            return _runtime_config_conflict_response(exc)

        response_serializer = ActivitySubjectTreeItemSerializer(
            serialize_activity_subject_tree_item(activity_subject=activity_subject)
        )
        return Response(response_serializer.data)


class CatalogBusinessUnitSuggestView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["catalog"],
        parameters=[
            OpenApiParameter(name="q", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
        ],
        responses={200: CatalogBusinessUnitSuggestionSerializer(many=True)},
        description="Autocomplete suggestions for BusinessUnit labels (catalog only).",
    )
    def get(self, request):
        query = request.query_params.get("q", "")
        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20
        suggestions = suggest_business_units(query=query, limit=limit)
        serializer = CatalogBusinessUnitSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)


class CatalogActivitySubjectSuggestView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["catalog"],
        parameters=[
            OpenApiParameter(name="q", type=str, required=False),
            OpenApiParameter(name="business_unit_key", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
        ],
        responses={200: CatalogActivitySubjectSuggestionSerializer(many=True)},
        description="Autocomplete suggestions for ActivitySubject labels (catalog only).",
    )
    def get(self, request):
        query = request.query_params.get("q", "")
        business_unit_key = request.query_params.get("business_unit_key")
        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20
        suggestions = suggest_activity_subjects(
            business_unit_key=business_unit_key or None,
            query=query,
            limit=limit,
        )
        serializer = CatalogActivitySubjectSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)


class MembershipInvitationView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["memberships"],
        request=MembershipInvitationRequestSerializer,
        responses={
            201: DirectorInvitationResponseSerializer,
            400: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
        },
        description=(
            "Invites a staff, manager, or director to the establishment. Director "
            "invitations require an active path establishment. Organizational owner "
            "invitations are not accepted on this endpoint. Returns a copyable "
            "invitation link; an invitation email is sent asynchronously when enabled."
        ),
    )
    def post(self, request, establishment_id):
        request_serializer = MembershipInvitationRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        access_context = get_api_access_context(request)
        current_membership = access_context.active_membership
        if (
            current_membership is None
            or current_membership.establishment_id != establishment_id
        ):
            # No matching ACTIVE session selection: allow draft-path invites only.
            # ACTIVE path without matching selection must switch first —
            # do not reopen multi-est bypass. Drafts are never session-selectable;
            # fallback uses the actor's active membership on the path draft.
            path_membership = get_membership_for_invitation(
                user=request.user,
                establishment_id=establishment_id,
            )
            if (
                path_membership is None
                or path_membership.establishment.status != Establishment.Status.DRAFT
            ):
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            current_membership = path_membership
        if not can_invite_memberships(current_membership):
            if current_membership.role == EstablishmentMembership.Role.STAFF:
                return Response(
                    {
                        "code": "permission_denied",
                        "detail": "You do not have permission to invite memberships.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You cannot invite members for this establishment.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            invitation_result = invite_membership_for_establishment(
                current_membership=current_membership,
                establishment_id=establishment_id,
                email=request_serializer.validated_data["email"],
                first_name=request_serializer.validated_data["first_name"],
                last_name=request_serializer.validated_data["last_name"],
                role=request_serializer.validated_data["role"],
                scopes=parse_membership_scope_inputs(
                    request_serializer.validated_data.get("scopes") or []
                ),
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
                    "detail": (
                        "This role cannot be invited from this workspace with your "
                        "current membership."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except DirectorInvitationDuplicateError:
            return Response(
                {
                    "code": "membership_invitation_duplicate",
                    "detail": "This user is already associated with the establishment.",
                },
                status=status.HTTP_409_CONFLICT,
            )
        except MembershipInvitationUserExistsError as exc:
            return Response(
                {
                    "code": "membership_invitation_user_exists",
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )
        except MembershipInvitationOwnerConflictError as exc:
            return Response(
                {
                    "code": "membership_invitation_owner_conflict",
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )
        except OrganizationalOwnerInvariantConflictError as exc:
            return Response(
                {
                    "code": "organizational_owner_invariant_conflict",
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
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
                "invitation_accept_path": build_invitation_accept_path(
                    raw_token=invitation_result.invitation_token
                ),
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
                required=False,
                description=(
                    "Search term with a minimum length of 2 characters. "
                    "May be omitted only for context=assignee when business_unit_id "
                    "is provided, to list members covering that BusinessUnit."
                ),
            ),
            OpenApiParameter(
                name="business_unit_id",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "When provided, limits results to active members covering this "
                    "BusinessUnit (Owner/Director implicitly; Manager/Staff via scope)."
                ),
            ),
            OpenApiParameter(
                name="context",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=["assignee", "mention"],
                description=(
                    "assignee: scope-aware search for task/plan assignment. "
                    "mention: establishment-wide active member search for comments."
                ),
            ),
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
            "Use context=assignee for scope-aware assignment pickers; "
            "context=mention for comment @mentions. "
            "q is required with a minimum length of 2, except for context=assignee "
            "with business_unit_id, which may omit q to list covering members. "
            "Results are tenant-filtered before serialization."
        ),
    )
    def get(self, request, establishment_id):
        query_serializer = ScopedUserSearchRequestSerializer(
            data=request.query_params,
            context={"establishment_id": establishment_id},
        )
        query_serializer.is_valid(raise_exception=True)

        access_context = get_api_access_context(request)
        memberships = search_users_for_establishment(
            current_membership=access_context.active_membership,
            establishment_id=establishment_id,
            query=query_serializer.validated_data.get("q") or "",
            business_unit=query_serializer.validated_data.get("business_unit"),
            context=query_serializer.validated_data.get("context", "assignee"),
        )
        if memberships is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        response_serializer = ScopedUserSearchResultSerializer(memberships, many=True)
        return Response(response_serializer.data)


