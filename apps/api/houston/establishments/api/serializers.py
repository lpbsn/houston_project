from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from houston.establishments.models import EstablishmentMembership


class MembershipUserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.SerializerMethodField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True, allow_null=True)

    def get_display_name(self, user) -> str:
        full_name = user.get_full_name().strip()
        if full_name:
            return full_name

        if user.username:
            return user.username

        if user.email:
            return user.email

        return str(user.id)


class EstablishmentMembershipResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField(source="establishment.name")
    organization_id = serializers.UUIDField(source="establishment.organization_id")
    organization_name = serializers.CharField(source="establishment.organization.name")
    user = MembershipUserSummarySerializer()
    role = serializers.CharField()
    status = serializers.CharField()
    operational_domains = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_operational_domains(self, membership: EstablishmentMembership) -> list[str]:
        return [
            link.operational_domain.key
            for link in membership.domain_links.all()
            if link.operational_domain.active
        ]


class MembershipUpdateRequestSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=EstablishmentMembership.Role.choices,
        required=False,
    )
    operational_domains = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one of role or operational_domains must be provided."
            )

        return attrs


class ScopedUserSearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField(
        trim_whitespace=True,
        min_length=2,
    )


class ScopedUserSearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="user.id")
    display_name = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email", allow_blank=True, allow_null=True)
    role = serializers.CharField()
    membership_id = serializers.UUIDField(source="id")

    def get_display_name(self, membership: EstablishmentMembership) -> str:
        return MembershipUserSummarySerializer().get_display_name(membership.user)
