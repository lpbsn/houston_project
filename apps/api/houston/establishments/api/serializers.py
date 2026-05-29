from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
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


class RuntimeVocabularyItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    term = serializers.CharField()
    meaning = serializers.CharField()
    mapped_domain_key = serializers.SerializerMethodField()
    mapped_unit_key = serializers.SerializerMethodField()
    source = serializers.CharField()
    active = serializers.BooleanField()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_mapped_domain_key(self, item) -> str | None:
        if isinstance(item, dict):
            return item.get("mapped_domain_key")

        return None if item.mapped_domain_id is None else item.mapped_domain.key

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_mapped_unit_key(self, item) -> str | None:
        if isinstance(item, dict):
            return item.get("mapped_unit_key")

        return None if item.mapped_unit_id is None else item.mapped_unit.key


class RuntimeTagItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    key = serializers.CharField()
    label = serializers.CharField()
    source = serializers.CharField()
    active = serializers.BooleanField()
    domain_keys = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_domain_keys(self, runtime_tag) -> list[str]:
        if isinstance(runtime_tag, dict):
            return runtime_tag.get("domain_keys", [])

        return [link.operational_domain.key for link in runtime_tag.domain_links.all()]


class RoutingHintItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    pattern = serializers.CharField()
    suggested_unit_key = serializers.SerializerMethodField()
    source = serializers.CharField()
    active = serializers.BooleanField()
    domain_keys = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_suggested_unit_key(self, routing_hint) -> str | None:
        if isinstance(routing_hint, dict):
            return routing_hint.get("suggested_unit_key")

        return None if routing_hint.suggested_unit_id is None else routing_hint.suggested_unit.key

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_domain_keys(self, routing_hint) -> list[str]:
        if isinstance(routing_hint, dict):
            return routing_hint.get("domain_keys", [])

        return [link.operational_domain.key for link in routing_hint.domain_links.all()]


class RuntimeConfigResponseSerializer(serializers.Serializer):
    activity_description = ActivityDescriptionResponseSerializer(allow_null=True)
    active_modules = KeyedRuntimeItemSerializer(many=True)
    active_domains = KeyedRuntimeItemSerializer(many=True)
    active_subjects = KeyedRuntimeItemSerializer(many=True)
    optional_units = KeyedRuntimeItemSerializer(many=True)
    optional_vocabulary = RuntimeVocabularyItemSerializer(many=True)
    optional_runtime_tags = RuntimeTagItemSerializer(many=True)
    optional_routing_hints = RoutingHintItemSerializer(many=True)


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
    active_modules = KeyedRuntimeItemSerializer(many=True)
    active_domains = KeyedRuntimeItemSerializer(many=True)
    active_subjects = KeyedRuntimeItemSerializer(many=True)
    optional_units = KeyedRuntimeItemSerializer(many=True)
    optional_vocabulary = RuntimeVocabularyItemSerializer(many=True)
    optional_runtime_tags = RuntimeTagItemSerializer(many=True)
    optional_routing_hints = RoutingHintItemSerializer(many=True)
    initial_owner_director_count = serializers.IntegerField()
    initial_manager_count = serializers.IntegerField()
    managers_with_domains_count = serializers.IntegerField()
    readiness = ActivationReadinessResponseSerializer()
    blockers = ActivationBlockerSerializer(many=True)
    access = OnboardingAccessResponseSerializer()
    effective_can_activate = serializers.BooleanField()


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


class ProposalDomainItemSerializer(ProposalCatalogItemSerializer):
    module_key = serializers.CharField()


class ProposalSubjectItemSerializer(ProposalCatalogItemSerializer):
    domain_key = serializers.CharField()
    module_key = serializers.CharField(required=False)


class ProposalDomainOrUnitItemSerializer(ProposalCatalogItemSerializer):
    related_modules = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )


class ProposalVocabularyItemSerializer(serializers.Serializer):
    term = serializers.CharField()
    meaning = serializers.CharField()
    mapped_domain_key = serializers.CharField(allow_null=True, required=False)
    mapped_unit_key = serializers.CharField(allow_null=True, required=False)
    reason = serializers.CharField(allow_blank=True, required=False)


class ProposalRuntimeTagItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    related_domain_keys = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    reason = serializers.CharField(allow_blank=True, required=False)


class ProposalRoutingHintItemSerializer(serializers.Serializer):
    pattern = serializers.CharField()
    suggested_domain_keys = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    suggested_unit_key = serializers.CharField(allow_null=True, required=False)
    reason = serializers.CharField(allow_blank=True, required=False)
    confidence_score = serializers.FloatField(allow_null=True, required=False)


class OnboardingProposalPayloadSerializer(serializers.Serializer):
    schema_version = serializers.CharField()
    operational_modules = ProposalCatalogItemSerializer(many=True)
    operational_domains = ProposalDomainItemSerializer(many=True)
    operational_subjects = ProposalSubjectItemSerializer(many=True)
    operational_units = ProposalDomainOrUnitItemSerializer(many=True)
    runtime_vocabulary = ProposalVocabularyItemSerializer(many=True)
    runtime_tags = ProposalRuntimeTagItemSerializer(many=True)
    routing_hints = ProposalRoutingHintItemSerializer(many=True)


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


class AIOnboardingGenerateRequestSerializer(serializers.Serializer):
    locale = serializers.CharField(
        required=False,
        default="en-US",
        trim_whitespace=True,
        allow_blank=False,
    )


class ProposalItemMutationRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[("add", "Add"), ("remove", "Remove")])
    section = serializers.ChoiceField(
        choices=[
            ("operational_modules", "Modules"),
            ("operational_domains", "Domains"),
            ("operational_subjects", "Subjects"),
        ]
    )
    key = serializers.CharField()


class ProposalSectionDecisionRequestSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            ("accepted", "Accepted"),
            ("skipped", "Skipped"),
        ],
    )


class ProposalCommandResponseSerializer(serializers.Serializer):
    session = OnboardingSessionResponseSerializer()
    proposal = OnboardingProposalResponseSerializer()


class OnboardingProposalErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    errors = ProposalValidationErrorItemSerializer(many=True, required=False)
