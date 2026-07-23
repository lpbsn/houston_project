from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.api.organization_admin_serializers import (
    OrganizationAdminEstablishmentListSerializer,
    OrganizationAdminMemberFilterOptionsSerializer,
    OrganizationAdminMemberListQuerySerializer,
    OrganizationAdminMemberListSerializer,
    OrganizationAdminOverviewSerializer,
    OrganizationAdminOwnerInvitationRequestSerializer,
    OrganizationAdminOwnerListSerializer,
)
from houston.establishments.api.serializers import (
    DirectorInvitationErrorResponseSerializer,
    DirectorInvitationResponseSerializer,
)
from houston.establishments.organization_admin_selectors import (
    get_organization_admin_member_filter_options,
    get_organization_admin_overview,
    list_organization_admin_establishments,
    list_organization_admin_members,
    list_organization_admin_owners,
)
from houston.establishments.permissions import (
    CanManageOrganization,
    resolve_manageable_organization,
)
from houston.establishments.services import (
    DirectorInvitationDuplicateError,
    InvalidMembershipInvitationInputError,
    MembershipInvitationOwnerConflictError,
    MembershipInvitationUserExistsError,
    MembershipManagementForbiddenError,
    OrganizationalOwnerInvariantConflictError,
    invite_organizational_owner_for_organization,
)


def _resolve_path_organization(request, organization_id):
    organization = resolve_manageable_organization(
        request.user,
        preferred_organization_id=organization_id,
    )
    if organization is None:
        return None
    return organization


def _organization_forbidden_response() -> Response:
    return Response(
        {
            "code": "organization_management_forbidden",
            "detail": "You do not have permission to manage this organization.",
        },
        status=status.HTTP_403_FORBIDDEN,
    )


class OrganizationAdminOverviewView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanManageOrganization]

    @extend_schema(
        tags=["organizations"],
        responses={
            200: OrganizationAdminOverviewSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Organization admin overview for Owners. Independent of session "
            "selected establishment."
        ),
    )
    def get(self, request, organization_id):
        organization = _resolve_path_organization(request, organization_id)
        if organization is None:
            return _organization_forbidden_response()
        payload = get_organization_admin_overview(organization=organization)
        return Response(OrganizationAdminOverviewSerializer(payload).data)


class OrganizationAdminEstablishmentListView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanManageOrganization]

    @extend_schema(
        tags=["organizations"],
        responses={
            200: OrganizationAdminEstablishmentListSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Lists ACTIVE and DRAFT establishments for organization admin. "
            "Does not mutate selected establishment."
        ),
    )
    def get(self, request, organization_id):
        organization = _resolve_path_organization(request, organization_id)
        if organization is None:
            return _organization_forbidden_response()
        results = list_organization_admin_establishments(
            organization=organization,
            actor=request.user,
        )
        return Response(
            OrganizationAdminEstablishmentListSerializer({"results": results}).data
        )


class OrganizationAdminMemberListView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanManageOrganization]

    @extend_schema(
        tags=["organizations"],
        parameters=[
            OpenApiParameter(name="q", required=False, type=str),
            OpenApiParameter(name="establishment_id", required=False, type=str),
            OpenApiParameter(name="business_unit_id", required=False, type=str),
            OpenApiParameter(name="role", required=False, type=str),
            OpenApiParameter(name="status", required=False, type=str),
        ],
        responses={
            200: OrganizationAdminMemberListSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Deduplicated organization members across ACTIVE and DRAFT "
            "establishments. Membership statuses include invited, active, and "
            "deactivated."
        ),
    )
    def get(self, request, organization_id):
        organization = _resolve_path_organization(request, organization_id)
        if organization is None:
            return _organization_forbidden_response()

        query = OrganizationAdminMemberListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data

        results = list_organization_admin_members(
            organization=organization,
            q=data.get("q") or None,
            establishment_id=data.get("establishment_id"),
            business_unit_id=data.get("business_unit_id"),
            role=data.get("role"),
            status=data.get("status"),
        )
        return Response(OrganizationAdminMemberListSerializer({"results": results}).data)


class OrganizationAdminMemberFilterOptionsView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanManageOrganization]

    @extend_schema(
        tags=["organizations"],
        responses={
            200: OrganizationAdminMemberFilterOptionsSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description=(
            "Filter options for organization admin members. Not session-scoped; "
            "do not use team endpoints."
        ),
    )
    def get(self, request, organization_id):
        organization = _resolve_path_organization(request, organization_id)
        if organization is None:
            return _organization_forbidden_response()
        payload = get_organization_admin_member_filter_options(organization=organization)
        return Response(OrganizationAdminMemberFilterOptionsSerializer(payload).data)


class OrganizationAdminOwnerListView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanManageOrganization]

    @extend_schema(
        tags=["organizations"],
        responses={
            200: OrganizationAdminOwnerListSerializer,
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
        description="Lists organizational Owners (active and invited), deduplicated by user.",
    )
    def get(self, request, organization_id):
        organization = _resolve_path_organization(request, organization_id)
        if organization is None:
            return _organization_forbidden_response()
        results = list_organization_admin_owners(organization=organization)
        return Response(OrganizationAdminOwnerListSerializer({"results": results}).data)


class OrganizationAdminOwnerInvitationView(APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, CanManageOrganization]

    @extend_schema(
        tags=["organizations"],
        request=OrganizationAdminOwnerInvitationRequestSerializer,
        responses={
            201: DirectorInvitationResponseSerializer,
            400: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
            409: OpenApiResponse(response=DirectorInvitationErrorResponseSerializer),
        },
        description=(
            "Invites or reissues an organizational Owner invitation. Works for "
            "DRAFT-only organizations. Body: email, first_name, last_name only."
        ),
    )
    def post(self, request, organization_id):
        organization = _resolve_path_organization(request, organization_id)
        if organization is None:
            return _organization_forbidden_response()

        request_serializer = OrganizationAdminOwnerInvitationRequestSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        try:
            invitation_result = invite_organizational_owner_for_organization(
                actor=request.user,
                organization_id=organization.id,
                email=request_serializer.validated_data["email"],
                first_name=request_serializer.validated_data["first_name"],
                last_name=request_serializer.validated_data["last_name"],
            )
        except MembershipManagementForbiddenError:
            return _organization_forbidden_response()
        except DirectorInvitationDuplicateError:
            return Response(
                {
                    "code": "membership_invitation_duplicate",
                    "detail": "This user is already associated with the organization.",
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

        response_serializer = DirectorInvitationResponseSerializer(
            {
                "membership": invitation_result.membership,
                "invitation_token": invitation_result.invitation_token,
                "invitation_expires_at": invitation_result.invitation_expires_at,
                "invitation_accept_path": f"/invitations/{invitation_result.invitation_token}",
            }
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
