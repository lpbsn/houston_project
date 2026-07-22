from __future__ import annotations

from rest_framework import serializers

from houston.establishments.models import EstablishmentMembership
from houston.establishments.organization_admin_selectors import (
    ORGANIZATION_ADMIN_MEMBER_ROLES,
    ORGANIZATION_ADMIN_MEMBER_STATUSES,
)


class OrganizationAdminOverviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    active_establishment_count = serializers.IntegerField()
    draft_establishment_count = serializers.IntegerField()


class OrganizationAdminDirectorSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()
    email = serializers.EmailField()
    status = serializers.CharField()


class OrganizationAdminEstablishmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    directors = OrganizationAdminDirectorSerializer(many=True)
    active_member_count = serializers.IntegerField()
    business_unit_count = serializers.IntegerField()
    onboarding_session_id = serializers.UUIDField(allow_null=True)
    onboarding_current_step = serializers.CharField(allow_blank=True)
    can_continue_onboarding = serializers.BooleanField()


class OrganizationAdminEstablishmentListSerializer(serializers.Serializer):
    results = OrganizationAdminEstablishmentSerializer(many=True)


class OrganizationAdminMemberBusinessUnitSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()


class OrganizationAdminMemberMembershipSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField()
    establishment_status = serializers.CharField()
    role = serializers.CharField()
    status = serializers.CharField()
    business_units = OrganizationAdminMemberBusinessUnitSerializer(many=True)


class OrganizationAdminMemberSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    memberships = OrganizationAdminMemberMembershipSerializer(many=True)


class OrganizationAdminMemberListSerializer(serializers.Serializer):
    results = OrganizationAdminMemberSerializer(many=True)


class OrganizationAdminFilterEstablishmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()


class OrganizationAdminFilterBusinessUnitSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    establishment_id = serializers.UUIDField()


class OrganizationAdminMemberFilterOptionsSerializer(serializers.Serializer):
    establishments = OrganizationAdminFilterEstablishmentSerializer(many=True)
    business_units = OrganizationAdminFilterBusinessUnitSerializer(many=True)
    roles = serializers.ListField(child=serializers.CharField())
    statuses = serializers.ListField(child=serializers.CharField())


class OrganizationAdminOwnerSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    status = serializers.CharField()
    invited_at = serializers.DateTimeField(allow_null=True)
    can_resend_invitation = serializers.BooleanField()


class OrganizationAdminOwnerListSerializer(serializers.Serializer):
    results = OrganizationAdminOwnerSerializer(many=True)


class OrganizationAdminOwnerInvitationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(trim_whitespace=True)
    last_name = serializers.CharField(trim_whitespace=True)


class OrganizationAdminMemberListQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True)
    establishment_id = serializers.UUIDField(required=False)
    business_unit_id = serializers.UUIDField(required=False)
    role = serializers.ChoiceField(
        choices=EstablishmentMembership.Role.choices,
        required=False,
    )
    status = serializers.ChoiceField(
        choices=EstablishmentMembership.Status.choices,
        required=False,
    )

    def validate_role(self, value: str) -> str:
        if value not in ORGANIZATION_ADMIN_MEMBER_ROLES:
            raise serializers.ValidationError("Invalid role filter.")
        return value

    def validate_status(self, value: str) -> str:
        if value not in ORGANIZATION_ADMIN_MEMBER_STATUSES:
            raise serializers.ValidationError("Invalid status filter.")
        return value
