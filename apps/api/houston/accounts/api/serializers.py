from __future__ import annotations

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from houston.accounts.models import User


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class ApiErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    errors = serializers.DictField(required=False)


class ValidationErrorResponseSerializer(ApiErrorResponseSerializer):
    errors = serializers.DictField()


class CsrfResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LoginRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class SwitchEstablishmentRequestSerializer(serializers.Serializer):
    establishment_id = serializers.UUIDField()


class UserPublicSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    identity_type = serializers.CharField()


@extend_schema_serializer(component_name="AuthMembershipScopeItem")
class MembershipScopeItemSerializer(serializers.Serializer):
    scope_type = serializers.CharField()
    scope_id = serializers.UUIDField()


@extend_schema_serializer(component_name="AuthMembershipScopeSummary")
class MembershipScopeSummarySerializer(serializers.Serializer):
    module_count = serializers.IntegerField()
    domain_count = serializers.IntegerField()
    subject_count = serializers.IntegerField()


class MembershipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField()
    organization_id = serializers.UUIDField()
    organization_name = serializers.CharField()
    role = serializers.CharField()
    status = serializers.CharField()
    scopes = MembershipScopeItemSerializer(many=True)
    scope_summary = MembershipScopeSummarySerializer()


class BootstrapResponseSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = UserPublicSerializer()
    memberships = MembershipSerializer(many=True)
    active_membership = MembershipSerializer(allow_null=True)


class AuthResponseSerializer(BootstrapResponseSerializer):
    access_token = serializers.CharField()
    access_token_expires_at = serializers.DateTimeField()


def validate_registration_password_pair(
    *,
    attrs: dict,
    email: str,
    first_name: str,
    last_name: str,
) -> dict:
    if attrs["password"] != attrs["password_confirmation"]:
        raise serializers.ValidationError(
            {"password_confirmation": "Passwords do not match."},
        )

    if settings.AUTH_PASSWORD_VALIDATORS:
        provisional_user = User(
            email=User.normalize_email_value(email),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
        )
        try:
            validate_password(attrs["password"], user=provisional_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc

    attrs.pop("password_confirmation")
    return attrs


class RegistrationOwnerValidateRequestSerializer(serializers.Serializer):
    invite_code = serializers.CharField(trim_whitespace=True)
    first_name = serializers.CharField(trim_whitespace=True)
    last_name = serializers.CharField(trim_whitespace=True)
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)
    password_confirmation = serializers.CharField(trim_whitespace=False)

    def validate_first_name(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_last_name(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_invite_code(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_password(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_password_confirmation(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate(self, attrs: dict) -> dict:
        return validate_registration_password_pair(
            attrs=attrs,
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )


class RegistrationRequestSerializer(serializers.Serializer):
    invite_code = serializers.CharField(trim_whitespace=True)
    first_name = serializers.CharField(trim_whitespace=True)
    last_name = serializers.CharField(trim_whitespace=True)
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)
    password_confirmation = serializers.CharField(trim_whitespace=False)
    organization_name = serializers.CharField(trim_whitespace=True)
    establishment_name = serializers.CharField(trim_whitespace=True)

    def validate_first_name(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_last_name(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_organization_name(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_establishment_name(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_invite_code(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_password(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_password_confirmation(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate(self, attrs: dict) -> dict:
        return validate_registration_password_pair(
            attrs=attrs,
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )


class RegistrationErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField(required=False)


class RegistrationResponseSerializer(AuthResponseSerializer):
    establishment_id = serializers.UUIDField()
    onboarding_session_id = serializers.UUIDField()


class DirectorInvitationAcceptRequestSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False)
    password_confirmation = serializers.CharField(trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_password_confirmation(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError(
                {"password_confirmation": "Passwords do not match."},
            )

        if settings.AUTH_PASSWORD_VALIDATORS:
            try:
                validate_password(attrs["password"])
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)}) from exc

        attrs.pop("password_confirmation")
        return attrs


class DirectorInvitationAcceptResponseSerializer(AuthResponseSerializer):
    establishment_id = serializers.UUIDField()
    onboarding_session_id = serializers.UUIDField(required=False)


class DirectorInvitationAcceptErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
