from __future__ import annotations

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from houston.accounts.models import User

REFRESH_TOKEN_TRANSPORT_COOKIE = "cookie"
REFRESH_TOKEN_TRANSPORT_BODY = "body"
REFRESH_TOKEN_TRANSPORT_CHOICES = (
    (REFRESH_TOKEN_TRANSPORT_COOKIE, "Cookie"),
    (REFRESH_TOKEN_TRANSPORT_BODY, "Body"),
)


class RefreshTokenTransportSerializerMixin(serializers.Serializer):
    refresh_token_transport = serializers.ChoiceField(choices=REFRESH_TOKEN_TRANSPORT_CHOICES)


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
    csrf_token = serializers.CharField()


class LoginRequestSerializer(RefreshTokenTransportSerializerMixin):
    identifier = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class RefreshRequestSerializer(RefreshTokenTransportSerializerMixin):
    refresh_token = serializers.CharField(required=False, trim_whitespace=False)

    def validate(self, attrs):
        transport = attrs["refresh_token_transport"]
        raw_refresh_token = attrs.get("refresh_token")
        if transport == REFRESH_TOKEN_TRANSPORT_COOKIE and raw_refresh_token is not None:
            raise serializers.ValidationError(
                {"refresh_token": "Must not be provided for cookie transport."}
            )
        if transport == REFRESH_TOKEN_TRANSPORT_BODY and not raw_refresh_token:
            raise serializers.ValidationError(
                {"refresh_token": "This field is required for body transport."}
            )
        return attrs


class LogoutRequestSerializer(RefreshTokenTransportSerializerMixin):
    refresh_token = serializers.CharField(required=False, trim_whitespace=False)

    def validate(self, attrs):
        if (
            attrs["refresh_token_transport"] == REFRESH_TOKEN_TRANSPORT_COOKIE
            and attrs.get("refresh_token") is not None
        ):
            raise serializers.ValidationError(
                {"refresh_token": "Must not be provided for cookie transport."}
            )
        return attrs


class SwitchEstablishmentRequestSerializer(serializers.Serializer):
    establishment_id = serializers.UUIDField()


class UserPublicSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    identity_type = serializers.CharField()
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)


class UserProfileUpdateRequestSerializer(serializers.Serializer):
    first_name = serializers.CharField(trim_whitespace=True, required=False, allow_blank=True)
    last_name = serializers.CharField(trim_whitespace=True, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field must be provided.")
        return attrs


class AccountDeletionOrganizationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    establishment_names = serializers.ListField(child=serializers.CharField())


class AccountDeletionEstablishmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class AccountDeletionPreviewResponseSerializer(serializers.Serializer):
    requires_organization_closure = serializers.BooleanField()
    organizations = AccountDeletionOrganizationSerializer(many=True)
    leaves_establishments_without_director = AccountDeletionEstablishmentSerializer(many=True)


class AccountDeletionRequestSerializer(RefreshTokenTransportSerializerMixin):
    password = serializers.CharField(trim_whitespace=False)
    close_organizations = serializers.BooleanField(required=False, default=False)
    refresh_token = serializers.CharField(required=False, trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate(self, attrs):
        if (
            attrs["refresh_token_transport"] == REFRESH_TOKEN_TRANSPORT_COOKIE
            and attrs.get("refresh_token") is not None
        ):
            raise serializers.ValidationError(
                {"refresh_token": "Must not be provided for cookie transport."}
            )
        return attrs


@extend_schema_serializer(component_name="AuthMembershipScopeItem")
class MembershipScopeItemSerializer(serializers.Serializer):
    scope_type = serializers.CharField()
    scope_id = serializers.UUIDField()
    scope_label = serializers.CharField()


@extend_schema_serializer(component_name="AuthMembershipScopeSummary")
class MembershipScopeSummarySerializer(serializers.Serializer):
    business_unit_count = serializers.IntegerField()


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


class PendingOnboardingMembershipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField()
    establishment_status = serializers.CharField()
    organization_id = serializers.UUIDField()
    organization_name = serializers.CharField()
    role = serializers.CharField()
    onboarding_session_id = serializers.UUIDField(allow_null=True)
    can_continue_onboarding = serializers.BooleanField()


class BootstrapPermissionHintsSerializer(serializers.Serializer):
    chat_available = serializers.BooleanField()
    can_create_action_plan = serializers.BooleanField()
    can_create_catalog_action_plan = serializers.BooleanField()
    can_view_action_plan_catalog = serializers.BooleanField()
    can_invite = serializers.BooleanField()
    can_manage_runtime_config = serializers.BooleanField()
    can_view_team = serializers.BooleanField()
    can_manage_organization = serializers.BooleanField()
    can_create_establishment = serializers.BooleanField()


class BootstrapResponseSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = UserPublicSerializer()
    memberships = MembershipSerializer(many=True)
    active_membership = MembershipSerializer(allow_null=True)
    pending_onboarding_memberships = PendingOnboardingMembershipSerializer(many=True)
    permission_hints = BootstrapPermissionHintsSerializer()


class AuthResponseSerializer(BootstrapResponseSerializer):
    access_token = serializers.CharField()
    access_token_expires_at = serializers.DateTimeField()
    refresh_token = serializers.CharField(required=False)
    refresh_token_expires_at = serializers.DateTimeField(required=False)


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


class RegistrationRequestSerializer(RefreshTokenTransportSerializerMixin):
    invite_code = serializers.CharField(trim_whitespace=True)
    first_name = serializers.CharField(trim_whitespace=True)
    last_name = serializers.CharField(trim_whitespace=True)
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)
    password_confirmation = serializers.CharField(trim_whitespace=False)
    organization_name = serializers.CharField(trim_whitespace=True)
    establishment_name = serializers.CharField(
        trim_whitespace=True,
        required=False,
        allow_blank=True,
        default="",
    )

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


class DirectorInvitationAcceptRequestSerializer(RefreshTokenTransportSerializerMixin):
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
