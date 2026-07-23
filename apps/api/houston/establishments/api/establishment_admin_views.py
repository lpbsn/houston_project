from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.api.establishment_admin_serializers import (
    EstablishmentAdminMemberFilterOptionsSerializer,
    EstablishmentAdminMembershipInvitationRequestSerializer,
    EstablishmentAdminMembershipListQuerySerializer,
    EstablishmentAdminMembershipListSerializer,
    EstablishmentAdminMembershipSerializer,
    EstablishmentAdminMembershipUpdateRequestSerializer,
    EstablishmentAdminOverviewSerializer,
)
from houston.establishments.api.serializers import (
    DirectorInvitationErrorResponseSerializer,
    DirectorInvitationResponseSerializer,
)
from houston.establishments.establishment_admin_selectors import (
    get_establishment_admin_member_filter_options,
    get_establishment_admin_membership,
    get_establishment_admin_overview,
    list_establishment_admin_memberships,
)
from houston.establishments.membership_scope import (
    InvalidMembershipScopeAssignmentError,
    parse_membership_scope_inputs,
)
from houston.establishments.models import Establishment
from houston.establishments.permissions import (
    CanAccessEstablishmentAdmin,
    resolve_active_establishment_admin_actor,
)
from houston.establishments.services import (
    DirectorCoverageInvariantError,
    DirectorInvitationDuplicateError,
    EstablishmentAdminOwnerForbiddenError,
    InvalidMembershipInvitationInputError,
    InvitedMembershipActivationError,
    MembershipInvitationRoleNotAllowedError,
    MembershipInvitationUserExistsError,
    MembershipManagementForbiddenError,
    MembershipManagementNotFoundError,
    MembershipRoleChangeForbiddenError,
    MembershipUpdateInput,
    activate_membership_for_establishment_admin,
    deactivate_membership_for_establishment_admin,
    invite_membership_for_establishment_admin,
    update_membership_for_establishment_admin,
)


def _resolve_admin_actor(request, establishment_id):
    establishment_exists = Establishment.objects.filter(id=establishment_id).exists()
    if not establishment_exists:
        return None, "not_found"

    actor = resolve_active_establishment_admin_actor(request.user, establishment_id)
    if actor is None:
        establishment = Establishment.objects.filter(id=establishment_id).first()
        if establishment is None or establishment.status != Establishment.Status.ACTIVE:
            return None, "not_found"
        return None, "forbidden"
    return actor, None


def _admin_forbidden_response() -> Response:
    return Response(
        {
            "code": "establishment_admin_forbidden",
            "detail": "You do not have permission to administer this establishment.",
        },
        status=status.HTTP_403_FORBIDDEN,
    )


def _admin_not_found_response() -> Response:
    return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


def _resolve_or_error(request, establishment_id):
    actor, error = _resolve_admin_actor(request, establishment_id)
    if error == "not_found":
        return None, _admin_not_found_response()
    if error == "forbidden":
        return None, _admin_forbidden_response()
    return actor, None


class EstablishmentAdminOverviewView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanAccessEstablishmentAdmin]

    @extend_schema(
        tags=["establishment-admin"],
        responses={
            200: EstablishmentAdminOverviewSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "ACTIVE establishment admin overview with metrics and derived operational "
            "config status. Path-scoped; does not mutate selected establishment."
        ),
    )
    def get(self, request, establishment_id):
        actor, error_response = _resolve_or_error(request, establishment_id)
        if error_response is not None:
            return error_response
        payload = get_establishment_admin_overview(establishment=actor.establishment)
        return Response(EstablishmentAdminOverviewSerializer(payload).data)


class EstablishmentAdminMembershipListView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanAccessEstablishmentAdmin]

    @extend_schema(
        tags=["establishment-admin"],
        operation_id="v1_establishments_admin_memberships_list",
        parameters=[
            OpenApiParameter(name="q", required=False, type=str),
            OpenApiParameter(name="role", required=False, type=str),
            OpenApiParameter(name="status", required=False, type=str),
            OpenApiParameter(name="business_unit_id", required=False, type=str),
        ],
        responses={
            200: EstablishmentAdminMembershipListSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Lists non-Owner memberships for ACTIVE establishment admin. Supports "
            "q/role/status/business_unit_id filters. Path-scoped."
        ),
    )
    def get(self, request, establishment_id):
        actor, error_response = _resolve_or_error(request, establishment_id)
        if error_response is not None:
            return error_response

        query = EstablishmentAdminMembershipListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        results = list_establishment_admin_memberships(
            actor=actor,
            q=query.validated_data.get("q"),
            role=query.validated_data.get("role"),
            status=query.validated_data.get("status"),
            business_unit_id=query.validated_data.get("business_unit_id"),
        )
        return Response(
            EstablishmentAdminMembershipListSerializer({"results": results}).data
        )


class EstablishmentAdminMemberFilterOptionsView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanAccessEstablishmentAdmin]

    @extend_schema(
        tags=["establishment-admin"],
        responses={
            200: EstablishmentAdminMemberFilterOptionsSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description=(
            "Filter options for establishment admin memberships. Path-scoped poles only."
        ),
    )
    def get(self, request, establishment_id):
        actor, error_response = _resolve_or_error(request, establishment_id)
        if error_response is not None:
            return error_response
        payload = get_establishment_admin_member_filter_options(
            establishment=actor.establishment
        )
        return Response(EstablishmentAdminMemberFilterOptionsSerializer(payload).data)


class EstablishmentAdminMembershipInvitationView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanAccessEstablishmentAdmin]

    @extend_schema(
        tags=["establishment-admin"],
        request=EstablishmentAdminMembershipInvitationRequestSerializer,
        responses={
            201: DirectorInvitationResponseSerializer,
            400: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
        },
        description=(
            "Invites a membership on an ACTIVE establishment (no Owner role). Path-scoped."
        ),
    )
    def post(self, request, establishment_id):
        actor, error_response = _resolve_or_error(request, establishment_id)
        if error_response is not None:
            return error_response

        request_serializer = EstablishmentAdminMembershipInvitationRequestSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        try:
            invitation_result = invite_membership_for_establishment_admin(
                actor=actor,
                email=request_serializer.validated_data["email"],
                first_name=request_serializer.validated_data["first_name"],
                last_name=request_serializer.validated_data["last_name"],
                role=request_serializer.validated_data["role"],
                scopes=parse_membership_scope_inputs(
                    request_serializer.validated_data.get("scopes") or []
                ),
            )
        except EstablishmentAdminOwnerForbiddenError as exc:
            return Response(
                {
                    "code": "establishment_admin_owner_forbidden",
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except MembershipManagementNotFoundError:
            return _admin_not_found_response()
        except MembershipManagementForbiddenError:
            return Response(
                {
                    "code": "membership_management_forbidden",
                    "detail": "You cannot invite this membership.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except MembershipInvitationRoleNotAllowedError:
            return Response(
                {
                    "code": "membership_invitation_role_not_allowed",
                    "detail": "This invitation role is not allowed.",
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
        except InvalidMembershipInvitationInputError as exc:
            return Response(
                {"code": "membership_invitation_invalid", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = DirectorInvitationResponseSerializer(
            {
                "membership": invitation_result.membership,
                "invitation_token": invitation_result.invitation_token,
                "invitation_expires_at": invitation_result.invitation_expires_at,
                "invitation_accept_path": f"/invitations/{invitation_result.invitation_token}",
            }
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class EstablishmentAdminMembershipDetailView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanAccessEstablishmentAdmin]

    @extend_schema(
        tags=["establishment-admin"],
        operation_id="v1_establishments_admin_memberships_retrieve",
        responses={
            200: EstablishmentAdminMembershipSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Returns one non-Owner membership for ACTIVE establishment admin.",
    )
    def get(self, request, establishment_id, membership_id):
        actor, error_response = _resolve_or_error(request, establishment_id)
        if error_response is not None:
            return error_response
        payload = get_establishment_admin_membership(
            actor=actor,
            membership_id=membership_id,
        )
        if payload is None:
            return _admin_not_found_response()
        return Response(EstablishmentAdminMembershipSerializer(payload).data)

    @extend_schema(
        tags=["establishment-admin"],
        request=EstablishmentAdminMembershipUpdateRequestSerializer,
        responses={
            200: EstablishmentAdminMembershipSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
        },
        description="Updates role/scopes for a non-Owner membership (path-scoped admin).",
    )
    def patch(self, request, establishment_id, membership_id):
        actor, error_response = _resolve_or_error(request, establishment_id)
        if error_response is not None:
            return error_response

        serializer = EstablishmentAdminMembershipUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            update_membership_for_establishment_admin(
                actor=actor,
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
        except EstablishmentAdminOwnerForbiddenError as exc:
            return Response(
                {
                    "code": "establishment_admin_owner_forbidden",
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except MembershipManagementNotFoundError:
            return _admin_not_found_response()
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

        payload = get_establishment_admin_membership(
            actor=actor,
            membership_id=membership_id,
        )
        if payload is None:
            return _admin_not_found_response()
        return Response(EstablishmentAdminMembershipSerializer(payload).data)


class EstablishmentAdminMembershipDeactivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanAccessEstablishmentAdmin]

    @extend_schema(
        tags=["establishment-admin"],
        request=None,
        responses={
            200: EstablishmentAdminMembershipSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
        },
        description="Deactivates a non-Owner membership (path-scoped admin).",
    )
    def post(self, request, establishment_id, membership_id):
        actor, error_response = _resolve_or_error(request, establishment_id)
        if error_response is not None:
            return error_response

        try:
            membership = deactivate_membership_for_establishment_admin(
                actor=actor,
                membership_id=membership_id,
            )
        except EstablishmentAdminOwnerForbiddenError as exc:
            return Response(
                {
                    "code": "establishment_admin_owner_forbidden",
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except MembershipManagementNotFoundError:
            return _admin_not_found_response()
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

        payload = get_establishment_admin_membership(
            actor=actor,
            membership_id=membership.id,
        )
        if payload is None:
            return _admin_not_found_response()
        return Response(EstablishmentAdminMembershipSerializer(payload).data)


class EstablishmentAdminMembershipActivateView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanAccessEstablishmentAdmin]

    @extend_schema(
        tags=["establishment-admin"],
        request=None,
        responses={
            200: EstablishmentAdminMembershipSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
        description="Reactivates a non-Owner membership (path-scoped admin).",
    )
    def post(self, request, establishment_id, membership_id):
        actor, error_response = _resolve_or_error(request, establishment_id)
        if error_response is not None:
            return error_response

        try:
            membership = activate_membership_for_establishment_admin(
                actor=actor,
                membership_id=membership_id,
            )
        except EstablishmentAdminOwnerForbiddenError as exc:
            return Response(
                {
                    "code": "establishment_admin_owner_forbidden",
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except MembershipManagementNotFoundError:
            return _admin_not_found_response()
        except InvitedMembershipActivationError:
            return Response(
                {
                    "code": "invited_membership_activation_forbidden",
                    "detail": "Invited memberships cannot be activated this way.",
                },
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

        payload = get_establishment_admin_membership(
            actor=actor,
            membership_id=membership.id,
        )
        if payload is None:
            return _admin_not_found_response()
        return Response(EstablishmentAdminMembershipSerializer(payload).data)
