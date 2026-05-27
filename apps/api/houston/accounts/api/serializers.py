from __future__ import annotations

from rest_framework import serializers


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class CsrfResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LoginRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class OperationalDomainsField(serializers.ListField):
    child = serializers.CharField()


class UserPublicSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    identity_type = serializers.CharField()


class MembershipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField()
    organization_id = serializers.UUIDField()
    organization_name = serializers.CharField()
    role = serializers.CharField()
    status = serializers.CharField()
    operational_domains = OperationalDomainsField()


class BootstrapResponseSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = UserPublicSerializer()
    memberships = MembershipSerializer(many=True)
    active_membership = MembershipSerializer(allow_null=True)


class AuthResponseSerializer(BootstrapResponseSerializer):
    access_token = serializers.CharField()
    access_token_expires_at = serializers.DateTimeField()
