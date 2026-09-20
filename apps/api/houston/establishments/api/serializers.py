from __future__ import annotations

from drf_spectacular.utils import (
    extend_schema_field,
    extend_schema_serializer,
)
from rest_framework import serializers

from houston.establishments.membership_scope import (
    membership_business_unit_scope_ids,
    membership_scope_rows_for_membership,
)
from houston.establishments.models import (
    BusinessUnit,
    EstablishmentMembership,
)
from houston.establishments.role_constants import ADMIN_ROLES


class EmptyStringForNullMixin:
    null_as_empty_fields: tuple[str, ...] = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field_name in self.null_as_empty_fields:
            if data.get(field_name) is None:
                data[field_name] = ""
        return data


class MembershipUserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.SerializerMethodField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True, allow_null=True)
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)

    def get_display_name(self, user) -> str:
        from houston.accounts.display import user_display_name

        return user_display_name(user)


@extend_schema_serializer(component_name="EstablishmentMembershipScopeItem")
class MembershipScopeItemSerializer(serializers.Serializer):
    scope_type = serializers.ChoiceField(choices=["business_unit"])
    scope_id = serializers.UUIDField()
    scope_label = serializers.CharField()


@extend_schema_serializer(component_name="EstablishmentMembershipPermissionHints")
class MembershipPermissionHintsSerializer(serializers.Serializer):
    can_edit_role = serializers.BooleanField()
    can_edit_scopes = serializers.BooleanField()
    can_edit_status = serializers.BooleanField()
    can_edit_personal_info = serializers.BooleanField()
    can_reinvite = serializers.BooleanField()


@extend_schema_serializer(component_name="EstablishmentMembershipPendingInvitation")
class MembershipPendingInvitationSerializer(serializers.Serializer):
    expires_at = serializers.DateTimeField()
    is_expired = serializers.BooleanField()


@extend_schema_serializer(component_name="EstablishmentMembershipScopeWriteItem")
class MembershipScopeWriteItemSerializer(serializers.Serializer):
    scope_type = serializers.ChoiceField(choices=["business_unit"])
    scope_id = serializers.UUIDField()


@extend_schema_serializer(component_name="EstablishmentMembershipScopeSummary")
class MembershipScopeSummarySerializer(serializers.Serializer):
    business_unit_count = serializers.IntegerField()


class EstablishmentMembershipResponseSerializer(EmptyStringForNullMixin, serializers.Serializer):
    null_as_empty_fields = ("establishment_name",)

    id = serializers.UUIDField()
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField(source="establishment.name")
    organization_id = serializers.UUIDField(source="establishment.organization_id")
    organization_name = serializers.CharField(source="establishment.organization.name")
    user = MembershipUserSummarySerializer()
    role = serializers.CharField()
    status = serializers.CharField()
    scopes = serializers.SerializerMethodField()
    scope_summary = serializers.SerializerMethodField()
    permission_hints = serializers.SerializerMethodField()

    @extend_schema_field(MembershipScopeItemSerializer(many=True))
    def get_scopes(self, membership: EstablishmentMembership) -> list[dict[str, str]]:
        scopes_payload, _ = membership_scope_rows_for_membership(membership)
        return scopes_payload

    @extend_schema_field(MembershipScopeSummarySerializer)
    def get_scope_summary(self, membership: EstablishmentMembership) -> dict[str, int]:
        _, summary = membership_scope_rows_for_membership(membership)
        return summary

    @extend_schema_field(MembershipPermissionHintsSerializer)
    def get_permission_hints(self, membership: EstablishmentMembership) -> dict[str, bool]:
        from houston.establishments.permission_hints import build_membership_permission_hints

        actor_membership = self.context.get("actor_membership")
        return build_membership_permission_hints(
            actor_membership=actor_membership,
            target_membership=membership,
        )


@extend_schema_serializer(component_name="EstablishmentMembershipDetailResponse")
class EstablishmentMembershipDetailResponseSerializer(EstablishmentMembershipResponseSerializer):
    last_invited_at = serializers.SerializerMethodField()
    pending_invitation = serializers.SerializerMethodField()

    def _invitation_fields(self, membership: EstablishmentMembership) -> dict:
        cache = self.context.setdefault("_invitation_detail_fields_by_id", {})
        membership_id = str(membership.id)
        if membership_id not in cache:
            from houston.establishments.selectors import build_membership_invitation_detail_fields

            cache[membership_id] = build_membership_invitation_detail_fields(membership)
        return cache[membership_id]

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_last_invited_at(self, membership: EstablishmentMembership):
        return self._invitation_fields(membership)["last_invited_at"]

    @extend_schema_field(MembershipPendingInvitationSerializer(allow_null=True))
    def get_pending_invitation(self, membership: EstablishmentMembership):
        return self._invitation_fields(membership)["pending_invitation"]


@extend_schema_serializer(component_name="MembershipReinviteResponse")
class MembershipReinviteResponseSerializer(serializers.Serializer):
    membership = EstablishmentMembershipDetailResponseSerializer()
    invitation_token = serializers.CharField()
    invitation_expires_at = serializers.DateTimeField()
    invitation_accept_path = serializers.CharField()
    email_scheduling_status = serializers.ChoiceField(choices=["requested", "disabled"])


class DirectorInvitationResponseSerializer(serializers.Serializer):
    membership = EstablishmentMembershipResponseSerializer()
    invitation_token = serializers.CharField()
    invitation_expires_at = serializers.DateTimeField()
    invitation_accept_path = serializers.CharField()


class DirectorInvitationErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()


class MembershipUpdateRequestSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=EstablishmentMembership.Role.choices,
        required=False,
    )
    scopes = MembershipScopeWriteItemSerializer(many=True, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one of role or scopes must be provided.")

        return attrs


class BusinessUnitGenericSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    unit_type = serializers.CharField()


class ActivitySubjectTreeItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    catalog_key = serializers.CharField(required=False)
    label = serializers.CharField()
    description = serializers.CharField()
    source = serializers.CharField()
    active = serializers.BooleanField()
    is_generic = serializers.BooleanField()


class BusinessUnitTreeItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    specific_name = serializers.CharField()
    instance_description = serializers.CharField()
    active = serializers.BooleanField()
    generic = BusinessUnitGenericSerializer()
    activity_subjects = ActivitySubjectTreeItemSerializer(many=True)


class BusinessUnitTreeResponseSerializer(serializers.Serializer):
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField()
    business_units = BusinessUnitTreeItemSerializer(many=True)


class RuntimeBusinessUnitCreateRequestSerializer(serializers.Serializer):
    catalog_key = serializers.CharField(trim_whitespace=True, max_length=100)
    specific_name = serializers.CharField(trim_whitespace=True, max_length=255)
    instance_description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class RuntimeBusinessUnitUpdateRequestSerializer(serializers.Serializer):
    specific_name = serializers.CharField(
        trim_whitespace=True,
        max_length=255,
        required=False,
    )
    instance_description = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one of specific_name or instance_description must be provided."
            )
        return attrs


class RuntimeActivitySubjectCreateRequestSerializer(serializers.Serializer):
    label = serializers.CharField(
        trim_whitespace=True,
        max_length=255,
        required=False,
        allow_null=True,
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    catalog_key = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def validate(self, attrs):
        catalog_key = attrs.get("catalog_key")
        if isinstance(catalog_key, str) and catalog_key.strip() == "":
            catalog_key = None
            attrs["catalog_key"] = None
        label = attrs.get("label")
        if catalog_key is None and not (isinstance(label, str) and label.strip()):
            raise serializers.ValidationError(
                {"label": ["Label is required when catalog_key is omitted."]}
            )
        return attrs


class RuntimeConfigErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()


class CatalogBusinessUnitSuggestionSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    unit_type = serializers.CharField()


class CatalogActivitySubjectSuggestionSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    business_unit_key = serializers.CharField()


class ScopedUserSearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField(
        trim_whitespace=True,
        required=False,
        allow_blank=True,
        default="",
        min_length=2,
    )
    business_unit_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    context = serializers.ChoiceField(
        choices=["assignee", "mention"],
        required=False,
        default="assignee",
        help_text=(
            "assignee: scope-aware search for task/plan assignment. "
            "mention: establishment-wide active member search for comments."
        ),
    )

    def validate(self, attrs):
        query = (attrs.get("q") or "").strip()
        attrs["q"] = query
        context = attrs.get("context") or "assignee"
        business_unit_id = attrs.get("business_unit_id")
        allow_empty_query = context == "assignee" and business_unit_id is not None
        if not allow_empty_query and len(query) < 2:
            raise serializers.ValidationError(
                {"q": ["Ensure this field has at least 2 characters."]},
            )

        if business_unit_id is None:
            return attrs

        establishment_id = self.context.get("establishment_id")
        if establishment_id is None:
            return attrs

        business_unit = BusinessUnit.objects.filter(
            id=business_unit_id,
            establishment_id=establishment_id,
            active=True,
        ).first()
        if business_unit is None:
            raise serializers.ValidationError(
                {"business_unit_id": "Invalid business unit."},
            )

        attrs["business_unit"] = business_unit
        return attrs


class MembershipInvitationRequestSerializer(serializers.Serializer):
    """Session Team invite body. Owner invites use organization-admin endpoints."""

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

        if not scopes:
            raise serializers.ValidationError(
                {
                    "scopes": (
                        "At least one operational scope is required "
                        "for staff and manager invitations."
                    )
                }
            )

        return attrs


class ScopedUserSearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="user.id")
    display_name = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email", allow_blank=True, allow_null=True)
    role = serializers.CharField()
    membership_id = serializers.UUIDField(source="id")
    business_unit_ids = serializers.SerializerMethodField()

    def get_display_name(self, membership: EstablishmentMembership) -> str:
        return MembershipUserSummarySerializer().get_display_name(membership.user)

    def get_business_unit_ids(self, membership: EstablishmentMembership) -> list[str]:
        if membership.role in ADMIN_ROLES:
            return []
        scope_ids = membership_business_unit_scope_ids(membership)
        return [str(bu_id) for bu_id in sorted(scope_ids, key=str)]


class OnboardingDraftValidationErrorItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    section = serializers.CharField(required=False)
    field = serializers.CharField(required=False, allow_null=True)
    key = serializers.CharField(required=False, allow_null=True)


class OnboardingDraftValidationSerializer(serializers.Serializer):
    mode = serializers.CharField()
    is_ready_for_complete = serializers.BooleanField()
    errors = OnboardingDraftValidationErrorItemSerializer(many=True)


class OnboardingDraftResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    onboarding_session_id = serializers.UUIDField()
    updated_at = serializers.DateTimeField()
    payload = serializers.JSONField()
    validation = OnboardingDraftValidationSerializer()


class OnboardingDraftUpdateRequestSerializer(serializers.Serializer):
    payload = serializers.JSONField()
