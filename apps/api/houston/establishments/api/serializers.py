from __future__ import annotations

from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from houston.establishments.membership_scope import membership_scope_rows_for_membership
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    BusinessUnit,
    EstablishmentMembership,
    OnboardingSession,
)


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


@extend_schema_serializer(component_name="EstablishmentMembershipScopeItem")
class MembershipScopeItemSerializer(serializers.Serializer):
    scope_type = serializers.ChoiceField(choices=["business_unit"])
    scope_id = serializers.UUIDField()


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

    @extend_schema_field(MembershipScopeItemSerializer(many=True))
    def get_scopes(self, membership: EstablishmentMembership) -> list[dict[str, str]]:
        scopes_payload, _ = membership_scope_rows_for_membership(membership)
        return scopes_payload

    @extend_schema_field(MembershipScopeSummarySerializer)
    def get_scope_summary(self, membership: EstablishmentMembership) -> dict[str, int]:
        _, summary = membership_scope_rows_for_membership(membership)
        return summary


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


class ActivitySubjectTreeItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    normalized_name = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()


class BusinessUnitTreeItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    unit_type = serializers.CharField()
    activity_subjects = ActivitySubjectTreeItemSerializer(many=True)


class BusinessUnitTreeResponseSerializer(serializers.Serializer):
    establishment_id = serializers.UUIDField()
    establishment_name = serializers.CharField()
    business_units = BusinessUnitTreeItemSerializer(many=True)


class RuntimeBusinessUnitCreateRequestSerializer(serializers.Serializer):
    label = serializers.CharField(trim_whitespace=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    unit_type = serializers.ChoiceField(
        choices=BusinessUnit.UnitType.choices,
        required=False,
        default=BusinessUnit.UnitType.DEDICATED,
    )
    catalog_key = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class RuntimeBusinessUnitUpdateRequestSerializer(serializers.Serializer):
    label = serializers.CharField(trim_whitespace=True, max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    unit_type = serializers.ChoiceField(
        choices=BusinessUnit.UnitType.choices,
        required=False,
    )


class RuntimeActivitySubjectCreateRequestSerializer(serializers.Serializer):
    label = serializers.CharField(trim_whitespace=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    catalog_key = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class RuntimeConfigErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()


class CatalogBusinessUnitSuggestionSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    default_unit_type = serializers.CharField()


class CatalogActivitySubjectSuggestionSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    business_unit_key = serializers.CharField()


class ScopedUserSearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField(
        trim_whitespace=True,
        min_length=2,
    )

    q = serializers.CharField(
        trim_whitespace=True,
        min_length=2,
    )


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
    scopes = MembershipScopeWriteItemSerializer(many=True)

    def validate(self, attrs):
        scopes = attrs.get("scopes")
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

    def get_display_name(self, membership: EstablishmentMembership) -> str:
        return MembershipUserSummarySerializer().get_display_name(membership.user)


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


class ProposalCatalogItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    reason = serializers.CharField(allow_blank=True, required=False)
    confidence_score = serializers.FloatField(allow_null=True, required=False)


class ProposalDomainOrUnitItemSerializer(ProposalCatalogItemSerializer):
    related_modules = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )


class ProposalBusinessUnitItemSerializer(serializers.Serializer):
    client_key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    unit_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    catalog_key = serializers.CharField(required=False, allow_null=True)


class ProposalActivitySubjectItemSerializer(serializers.Serializer):
    client_key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    business_unit_client_key = serializers.CharField()
    catalog_key = serializers.CharField(required=False, allow_null=True)


class OnboardingProposalPayloadSerializer(serializers.Serializer):
    MANUAL_V2_SCHEMA_VERSION = "onboarding_proposal_v3"

    schema_version = serializers.CharField()
    business_units = ProposalBusinessUnitItemSerializer(many=True, required=False)
    activity_subjects = ProposalActivitySubjectItemSerializer(many=True, required=False)
    excluded_catalog_subject_keys = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
    )
    operational_units = ProposalDomainOrUnitItemSerializer(many=True, required=False)

    def validate(self, attrs):
        schema_version = attrs.get("schema_version")
        if schema_version == self.MANUAL_V2_SCHEMA_VERSION:
            result = {
                "schema_version": schema_version,
                "business_units": attrs.get("business_units", []),
                "activity_subjects": attrs.get("activity_subjects", []),
            }
            excluded = attrs.get("excluded_catalog_subject_keys")
            if excluded:
                result["excluded_catalog_subject_keys"] = excluded
            return result
        return attrs


class OnboardingProposalCreateRequestSerializer(serializers.Serializer):
    payload = OnboardingProposalPayloadSerializer()


class OnboardingProposalUpdateRequestSerializer(serializers.Serializer):
    payload = OnboardingProposalPayloadSerializer()


class OnboardingProposalResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    onboarding_session_id = serializers.UUIDField()
    establishment_id = serializers.UUIDField()
    source = serializers.CharField()
    status = serializers.CharField()
    payload = OnboardingProposalPayloadSerializer()
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


class OnboardingProposalErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    errors = ProposalValidationErrorItemSerializer(many=True, required=False)
