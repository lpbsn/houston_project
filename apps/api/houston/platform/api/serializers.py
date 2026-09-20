from __future__ import annotations

from rest_framework import serializers


class PlatformSessionSerializer(serializers.Serializer):
    platform_operator_active = serializers.BooleanField()
    operator_id = serializers.UUIDField()


class PlatformInviteResponseSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()


class PlatformOnboardingCompleteResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    activated = serializers.BooleanField()
    idempotent = serializers.BooleanField()
    readiness = serializers.DictField()


class PlatformOrganizationListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    has_been_operational = serializers.BooleanField()


class PlatformEstablishmentSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_null=True)
    status = serializers.CharField()


class PlatformOrganizationDetailSerializer(PlatformOrganizationListItemSerializer):
    updated_at = serializers.DateTimeField()
    can_delete = serializers.BooleanField()
    blocking_reasons = serializers.ListField(child=serializers.CharField())
    establishments = PlatformEstablishmentSummarySerializer(many=True)


class PlatformOnboardingSummarySerializer(serializers.Serializer):
    functional_status = serializers.CharField(allow_null=True)
    session_id = serializers.UUIDField(allow_null=True)
    current_step = serializers.CharField(allow_blank=True)
    source_mode = serializers.CharField(allow_blank=True)
    last_error_code = serializers.CharField(allow_blank=True)


class PlatformEstablishmentListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    organization_id = serializers.UUIDField()
    organization_name = serializers.CharField()
    created_at = serializers.DateTimeField()
    onboarding = PlatformOnboardingSummarySerializer()


class PlatformScopeSerializer(serializers.Serializer):
    scope_type = serializers.CharField()
    scope_id = serializers.CharField()
    scope_label = serializers.CharField()


class PlatformMembershipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    user_display_name = serializers.CharField()
    user_email = serializers.EmailField(allow_null=True)
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField(allow_null=True)
    organization_id = serializers.UUIDField()
    organization_name = serializers.CharField()
    role = serializers.CharField()
    status = serializers.CharField()
    scopes = PlatformScopeSerializer(many=True)


class PlatformEstablishmentDetailSerializer(PlatformEstablishmentListItemSerializer):
    timezone = serializers.CharField()
    updated_at = serializers.DateTimeField()
    can_delete = serializers.BooleanField()
    blocking_reasons = serializers.ListField(child=serializers.CharField())


class PlatformUserListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    status = serializers.CharField()
    created_at = serializers.DateTimeField()


class PlatformUserDetailSerializer(PlatformUserListItemSerializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    updated_at = serializers.DateTimeField()


class PlatformOnboardingListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField(allow_null=True)
    organization_id = serializers.UUIDField()
    organization_name = serializers.CharField()
    functional_status = serializers.CharField(allow_null=True)
    session_status = serializers.CharField()
    current_step = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class PlatformOnboardingStartRequestSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=255)
    establishment_name = serializers.CharField(max_length=255, required=False, allow_null=True)


class PlatformInviteRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)


class PlatformDeleteRequestSerializer(serializers.Serializer):
    justification = serializers.CharField(max_length=2000)


class PlatformOrganizationListResponseSerializer(serializers.Serializer):
    next_cursor = serializers.CharField(allow_null=True)
    results = PlatformOrganizationListItemSerializer(many=True)


class PlatformEstablishmentListResponseSerializer(serializers.Serializer):
    next_cursor = serializers.CharField(allow_null=True)
    results = PlatformEstablishmentListItemSerializer(many=True)


class PlatformUserListResponseSerializer(serializers.Serializer):
    next_cursor = serializers.CharField(allow_null=True)
    results = PlatformUserListItemSerializer(many=True)


class PlatformMembershipListResponseSerializer(serializers.Serializer):
    next_cursor = serializers.CharField(allow_null=True)
    results = PlatformMembershipSerializer(many=True)


class PlatformOnboardingListResponseSerializer(serializers.Serializer):
    next_cursor = serializers.CharField(allow_null=True)
    results = PlatformOnboardingListItemSerializer(many=True)
