from __future__ import annotations

from drf_spectacular.utils import (
    PolymorphicProxySerializer,
    extend_schema_field,
    extend_schema_serializer,
)
from rest_framework import serializers

from houston.establishments.membership_scope import (
    membership_business_unit_scope_ids,
    membership_scope_rows_for_membership,
)
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    BusinessUnit,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.establishments.role_constants import ADMIN_ROLES

PROPOSAL_SCHEMA_VERSION_V3 = "onboarding_proposal_v3"
PROPOSAL_SCHEMA_VERSION_V4 = "onboarding_proposal_v4"


class MembershipUserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.SerializerMethodField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True, allow_null=True)
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)

    def get_display_name(self, user) -> str:
        full_name = user.get_full_name().strip()
        if full_name:
            return full_name

        if user.username:
            return user.username

        if user.email:
            return user.email

        return str(user.id)


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


@extend_schema_serializer(component_name="EstablishmentMembershipScopeWriteItem")
class MembershipScopeWriteItemSerializer(serializers.Serializer):
    scope_type = serializers.ChoiceField(choices=["business_unit"])
    scope_id = serializers.UUIDField()


@extend_schema_serializer(component_name="EstablishmentMembershipScopeSummary")
class MembershipScopeSummarySerializer(serializers.Serializer):
    business_unit_count = serializers.IntegerField()


class EstablishmentMembershipResponseSerializer(serializers.Serializer):
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
        business_unit_id = attrs.get("business_unit_id")
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


class WorkspaceSummaryEstablishmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class WorkspaceSummaryPersonSerializer(serializers.Serializer):
    display_name = serializers.CharField()


class WorkspaceSummaryDirectorSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    status = serializers.ChoiceField(
        choices=[
            EstablishmentMembership.Status.ACTIVE,
            EstablishmentMembership.Status.INVITED,
        ],
    )


class WorkspaceSummaryResponseSerializer(serializers.Serializer):
    establishment = WorkspaceSummaryEstablishmentSerializer()
    owner = WorkspaceSummaryPersonSerializer(allow_null=True)
    director = WorkspaceSummaryDirectorSerializer(allow_null=True)
    active_membership_count = serializers.IntegerField()


class MembershipInvitationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(trim_whitespace=True)
    last_name = serializers.CharField(trim_whitespace=True)
    role = serializers.ChoiceField(
        choices=EstablishmentMembership.Role.choices,
    )
    scopes = MembershipScopeWriteItemSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        role = attrs.get("role")
        scopes = attrs.get("scopes") or []
        if role in {
            EstablishmentMembership.Role.OWNER,
            EstablishmentMembership.Role.DIRECTOR,
        }:
            if scopes:
                raise serializers.ValidationError(
                    {
                        "scopes": (
                            "Operational scopes are not allowed for owner or "
                            "director invitations."
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


class OnboardingOrganizationSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()


class OnboardingEstablishmentSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()


class OnboardingSessionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    organization = OnboardingOrganizationSummarySerializer()
    establishment = OnboardingEstablishmentSummarySerializer()
    started_by_id = serializers.UUIDField(allow_null=True)
    status = serializers.CharField()
    source_mode = serializers.CharField()
    current_step = serializers.CharField()
    ai_attempts = serializers.IntegerField()
    last_error_code = serializers.CharField()
    started_at = serializers.DateTimeField()
    ready_for_activation_at = serializers.DateTimeField(allow_null=True)
    activated_at = serializers.DateTimeField(allow_null=True)
    canceled_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class OnboardingSessionCreateRequestSerializer(serializers.Serializer):
    establishment_id = serializers.UUIDField()
    source_mode = serializers.CharField(
        required=False,
        default=OnboardingSession.SourceMode.MANUAL,
        trim_whitespace=True,
    )

    def validate_source_mode(self, source_mode: str) -> str:
        if source_mode not in {
            OnboardingSession.SourceMode.MANUAL,
            OnboardingSession.SourceMode.TEMPLATE,
        }:
            raise serializers.ValidationError(
                "Only manual and template onboarding sessions are supported.",
                code="unsupported_source_mode",
            )

        return source_mode


class OnboardingSessionCreateResponseSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    session = OnboardingSessionResponseSerializer()


class ActivityDescriptionRequestSerializer(serializers.Serializer):
    description = serializers.CharField(
        trim_whitespace=True,
        min_length=ACTIVITY_DESCRIPTION_MIN_LENGTH,
    )


class ActivityDescriptionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    description = serializers.CharField()
    source = serializers.CharField()
    submitted_by_id = serializers.UUIDField(allow_null=True)
    validated_at = serializers.DateTimeField(allow_null=True)


class ActivityDescriptionUpdateResponseSerializer(serializers.Serializer):
    session = OnboardingSessionResponseSerializer()
    activity_description = ActivityDescriptionResponseSerializer()


class KeyedRuntimeItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    key = serializers.CharField()
    label = serializers.CharField()
    source = serializers.CharField()
    active = serializers.BooleanField()


class RuntimeConfigResponseSerializer(serializers.Serializer):
    activity_description = ActivityDescriptionResponseSerializer(allow_null=True)
    active_business_units = BusinessUnitTreeItemSerializer(many=True, required=False)
    optional_units = KeyedRuntimeItemSerializer(many=True)


class ActivationBlockerSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()


class ActivationReadinessResponseSerializer(serializers.Serializer):
    is_ready = serializers.BooleanField()
    blockers = ActivationBlockerSerializer(many=True)
    counts = serializers.DictField(child=serializers.IntegerField())
    sections = serializers.DictField(child=serializers.DictField())
    establishment_status = serializers.CharField()
    session_status = serializers.CharField()


class OnboardingAccessResponseSerializer(serializers.Serializer):
    can_activate = serializers.BooleanField()


class ActivationSummaryResponseSerializer(serializers.Serializer):
    organization = OnboardingOrganizationSummarySerializer()
    establishment = OnboardingEstablishmentSummarySerializer()
    activity_description = ActivityDescriptionResponseSerializer(allow_null=True)
    active_business_units = BusinessUnitTreeItemSerializer(many=True, required=False)
    optional_units = KeyedRuntimeItemSerializer(many=True)
    initial_owner_director_count = serializers.IntegerField()
    initial_director_count = serializers.IntegerField()
    readiness = ActivationReadinessResponseSerializer()
    blockers = ActivationBlockerSerializer(many=True)
    access = OnboardingAccessResponseSerializer()
    effective_can_activate = serializers.BooleanField()


class DirectorInvitationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(trim_whitespace=True)
    last_name = serializers.CharField(trim_whitespace=True)


class DirectorInvitationResponseSerializer(serializers.Serializer):
    membership = EstablishmentMembershipResponseSerializer()
    invitation_token = serializers.CharField()
    invitation_expires_at = serializers.DateTimeField()
    invitation_accept_path = serializers.CharField()


class DirectorInvitationErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()


class MarkReadyResponseSerializer(serializers.Serializer):
    session = OnboardingSessionResponseSerializer()
    activation_summary = ActivationSummaryResponseSerializer()


class ActivationResponseSerializer(serializers.Serializer):
    session = OnboardingSessionResponseSerializer()
    activation_summary = ActivationSummaryResponseSerializer()


class OnboardingErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    blockers = ActivationBlockerSerializer(many=True, required=False)


class ProposalValidationErrorItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    section = serializers.CharField(required=False)
    field = serializers.CharField(required=False)
    key = serializers.CharField(required=False)


class ProposalBusinessUnitItemV3Serializer(serializers.Serializer):
    client_key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    unit_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    catalog_key = serializers.CharField(required=False, allow_null=True)


class ProposalActivitySubjectItemV3Serializer(serializers.Serializer):
    client_key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    business_unit_client_key = serializers.CharField()
    catalog_key = serializers.CharField(required=False, allow_null=True)


class ProposalBusinessUnitItemV4Serializer(serializers.Serializer):
    client_key = serializers.CharField()
    catalog_key = serializers.CharField()
    specific_name = serializers.CharField()
    instance_description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ProposalActivitySubjectItemV4Serializer(serializers.Serializer):
    client_key = serializers.CharField()
    business_unit_client_key = serializers.CharField()
    catalog_key = serializers.CharField(required=False, allow_null=True)
    label = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")


@extend_schema_serializer(component_name="OnboardingProposalPayloadV3")
class OnboardingProposalPayloadV3Serializer(serializers.Serializer):
    schema_version = serializers.CharField()
    business_units = ProposalBusinessUnitItemV3Serializer(many=True, required=False)
    activity_subjects = ProposalActivitySubjectItemV3Serializer(many=True, required=False)
    excluded_catalog_subject_keys = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
    )

    def validate(self, attrs):
        if attrs.get("schema_version") != PROPOSAL_SCHEMA_VERSION_V3:
            raise serializers.ValidationError(
                {"schema_version": ["Must be onboarding_proposal_v3."]}
            )
        result = {
            "schema_version": PROPOSAL_SCHEMA_VERSION_V3,
            "business_units": attrs.get("business_units", []),
            "activity_subjects": attrs.get("activity_subjects", []),
        }
        excluded = attrs.get("excluded_catalog_subject_keys")
        if excluded:
            result["excluded_catalog_subject_keys"] = excluded
        return result


@extend_schema_serializer(component_name="OnboardingProposalPayloadV4")
class OnboardingProposalPayloadV4Serializer(serializers.Serializer):
    schema_version = serializers.CharField()
    business_units = ProposalBusinessUnitItemV4Serializer(many=True, required=False)
    activity_subjects = ProposalActivitySubjectItemV4Serializer(many=True, required=False)

    def validate(self, attrs):
        if attrs.get("schema_version") != PROPOSAL_SCHEMA_VERSION_V4:
            raise serializers.ValidationError(
                {"schema_version": ["Must be onboarding_proposal_v4."]}
            )
        return {
            "schema_version": PROPOSAL_SCHEMA_VERSION_V4,
            "business_units": attrs.get("business_units", []),
            "activity_subjects": attrs.get("activity_subjects", []),
        }


ONBOARDING_PROPOSAL_PAYLOAD_OPENAPI = PolymorphicProxySerializer(
    component_name="OnboardingProposalPayload",
    serializers={
        PROPOSAL_SCHEMA_VERSION_V3: OnboardingProposalPayloadV3Serializer,
        PROPOSAL_SCHEMA_VERSION_V4: OnboardingProposalPayloadV4Serializer,
    },
    resource_type_field_name="schema_version",
)


@extend_schema_field(ONBOARDING_PROPOSAL_PAYLOAD_OPENAPI)
class OnboardingProposalPayloadField(serializers.Field):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Invalid payload.")
        schema_version = data.get("schema_version")
        if schema_version == PROPOSAL_SCHEMA_VERSION_V4:
            serializer = OnboardingProposalPayloadV4Serializer(data=data)
        elif schema_version == PROPOSAL_SCHEMA_VERSION_V3:
            raise serializers.ValidationError(
                {"schema_version": ["onboarding_proposal_v3 is no longer accepted."]}
            )
        else:
            raise serializers.ValidationError(
                {"schema_version": ["Unsupported onboarding proposal schema version."]}
            )
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def to_representation(self, value):
        if not isinstance(value, dict):
            return value
        schema_version = value.get("schema_version")
        if schema_version == PROPOSAL_SCHEMA_VERSION_V4:
            return OnboardingProposalPayloadV4Serializer(value).data
        if schema_version == PROPOSAL_SCHEMA_VERSION_V3:
            # Historical terminal payloads only (applied/rejected).
            return OnboardingProposalPayloadV3Serializer(value).data
        return value


# Backward-compatible aliases for imports that still reference old names.
OnboardingProposalPayloadSerializer = OnboardingProposalPayloadField
ProposalBusinessUnitItemSerializer = ProposalBusinessUnitItemV4Serializer
ProposalActivitySubjectItemSerializer = ProposalActivitySubjectItemV4Serializer


class OnboardingProposalCreateRequestSerializer(serializers.Serializer):
    payload = OnboardingProposalPayloadField()


class OnboardingProposalUpdateRequestSerializer(serializers.Serializer):
    payload = OnboardingProposalPayloadField()


class OnboardingProposalResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    onboarding_session_id = serializers.UUIDField()
    establishment_id = serializers.UUIDField()
    source = serializers.CharField()
    status = serializers.CharField()
    payload = OnboardingProposalPayloadField()
    section_validation = serializers.DictField(child=serializers.CharField())
    validation_errors = ProposalValidationErrorItemSerializer(many=True)
    created_by_id = serializers.UUIDField(allow_null=True)
    validated_by_id = serializers.UUIDField(allow_null=True)
    applied_by_id = serializers.UUIDField(allow_null=True)
    validated_at = serializers.DateTimeField(allow_null=True)
    applied_at = serializers.DateTimeField(allow_null=True)
    last_error_code = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ProposalCommandResponseSerializer(serializers.Serializer):
    session = OnboardingSessionResponseSerializer()
    proposal = OnboardingProposalResponseSerializer()


class EstablishmentCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(trim_whitespace=False, max_length=255)

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("This field may not be blank.")
        return value


class EstablishmentCreateResponseSerializer(serializers.Serializer):
    establishment_id = serializers.UUIDField()
    organization_id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    onboarding_session_id = serializers.UUIDField()


class OnboardingProposalErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    errors = ProposalValidationErrorItemSerializer(many=True, required=False)
