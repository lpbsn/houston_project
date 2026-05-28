from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.establishments.access import get_api_access_context
from houston.establishments.api.serializers import (
    EstablishmentMembershipResponseSerializer,
    MembershipUpdateRequestSerializer,
    ScopedUserSearchRequestSerializer,
    ScopedUserSearchResultSerializer,
)
from houston.establishments.permissions import (
    CanManageMemberships,
    HasActiveMembership,
)
from houston.establishments.selectors import (
    get_membership_for_management,
    list_memberships_for_management,
    search_users_for_establishment,
)
from houston.establishments.services import (
    CannotDeactivateLastActiveOwnerError,
    CannotDemoteLastActiveOwnerError,
    InvalidMembershipDomainAssignmentError,
    MembershipManagementNotFoundError,
    MembershipUpdateInput,
    deactivate_membership_for_management,
    update_membership_for_management,
)


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
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
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
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
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
            400: OpenApiResponse(response=DetailResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
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
                    operational_domains=serializer.validated_data.get("operational_domains"),
                ),
            )
        except MembershipManagementNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidMembershipDomainAssignmentError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except CannotDemoteLastActiveOwnerError:
            return Response(
                {"detail": "The last active owner cannot be demoted."},
                status=status.HTTP_400_BAD_REQUEST,
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
            400: OpenApiResponse(response=DetailResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            403: OpenApiResponse(response=DetailResponseSerializer),
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

        serializer = EstablishmentMembershipResponseSerializer(membership)
        return Response(serializer.data)


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
