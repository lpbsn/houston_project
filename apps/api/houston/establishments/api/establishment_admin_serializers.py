from __future__ import annotations

from rest_framework import serializers

from houston.establishments.api.serializers import MembershipScopeWriteItemSerializer
from houston.establishments.establishment_admin_selectors import (
    ESTABLISHMENT_ADMIN_MEMBER_ROLES,
    ESTABLISHMENT_ADMIN_MEMBER_STATUSES,
)
from houston.establishments.models import EstablishmentMembership


class EstablishmentAdminDirectorSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display_name = serializers.CharField()
    email = serializers.EmailField()
    status = serializers.CharField()


class EstablishmentAdminMetricsSerializer(serializers.Serializer):
    signals_open = serializers.IntegerField()
    signals_in_progress = serializers.IntegerField()
    action_plans_in_progress = serializers.IntegerField()
    action_plans_scheduled = serializers.IntegerField()
    observations_weekly_average = serializers.FloatField()


class EstablishmentAdminOperationalConfigSerializer(serializers.Serializer):
    status = serializers.CharField()
    active_business_unit_count = serializers.IntegerField()
    active_activity_subject_count = serializers.IntegerField()
    active_business_units_without_subjects_count = serializers.IntegerField()


class EstablishmentAdminOverviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    organization_id = serializers.UUIDField()
    organization_name = serializers.CharField()
    directors = EstablishmentAdminDirectorSerializer(many=True)
    active_member_count = serializers.IntegerField()
    business_unit_count = serializers.IntegerField()
    metrics = EstablishmentAdminMetricsSerializer()
    operational_config = EstablishmentAdminOperationalConfigSerializer()


class EstablishmentAdminMemberBusinessUnitSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()


class EstablishmentAdminMembershipPermissionHintsSerializer(serializers.Serializer):
    can_edit_role = serializers.BooleanField()
    can_edit_scopes = serializers.BooleanField()
    can_edit_status = serializers.BooleanField()
    can_edit_personal_info = serializers.BooleanField()


class EstablishmentAdminMembershipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    role = serializers.CharField()
    status = serializers.CharField()
    business_units = EstablishmentAdminMemberBusinessUnitSerializer(many=True)
    invited_at = serializers.DateTimeField(allow_null=True)
    activated_at = serializers.DateTimeField(allow_null=True)
    permission_hints = EstablishmentAdminMembershipPermissionHintsSerializer()


class EstablishmentAdminMembershipListSerializer(serializers.Serializer):
    results = EstablishmentAdminMembershipSerializer(many=True)


class EstablishmentAdminFilterBusinessUnitSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()


class EstablishmentAdminMemberFilterOptionsSerializer(serializers.Serializer):
    roles = serializers.ListField(child=serializers.CharField())
    statuses = serializers.ListField(child=serializers.CharField())
    business_units = EstablishmentAdminFilterBusinessUnitSerializer(many=True)


class EstablishmentAdminMembershipListQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True)
    business_unit_id = serializers.UUIDField(required=False)
    role = serializers.ChoiceField(
        choices=[
            (EstablishmentMembership.Role.DIRECTOR, "Director"),
            (EstablishmentMembership.Role.MANAGER, "Manager"),
            (EstablishmentMembership.Role.STAFF, "Staff"),
        ],
        required=False,
    )
    status = serializers.ChoiceField(
        choices=EstablishmentMembership.Status.choices,
        required=False,
    )

    def validate_role(self, value: str) -> str:
        if value not in ESTABLISHMENT_ADMIN_MEMBER_ROLES:
            raise serializers.ValidationError("Invalid role filter.")
        return value

    def validate_status(self, value: str) -> str:
        if value not in ESTABLISHMENT_ADMIN_MEMBER_STATUSES:
            raise serializers.ValidationError("Invalid status filter.")
        return value


class EstablishmentAdminMembershipInvitationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(trim_whitespace=True)
    last_name = serializers.CharField(trim_whitespace=True)
    role = serializers.ChoiceField(
        choices=[
            (EstablishmentMembership.Role.DIRECTOR, "Director"),
            (EstablishmentMembership.Role.MANAGER, "Manager"),
            (EstablishmentMembership.Role.STAFF, "Staff"),
        ],
    )
    scopes = MembershipScopeWriteItemSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        role = attrs.get("role")
        scopes = attrs.get("scopes") or []
        if role == EstablishmentMembership.Role.DIRECTOR:
            if scopes:
                raise serializers.ValidationError(
                    {
                        "scopes": (
                            "Operational scopes are not allowed for director invitations."
                        )
                    }
                )
            attrs["scopes"] = []
        return attrs


class EstablishmentAdminMembershipUpdateRequestSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            (EstablishmentMembership.Role.DIRECTOR, "Director"),
            (EstablishmentMembership.Role.MANAGER, "Manager"),
            (EstablishmentMembership.Role.STAFF, "Staff"),
        ],
        required=False,
    )
    scopes = MembershipScopeWriteItemSerializer(many=True, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one of role or scopes must be provided."
            )
        return attrs
