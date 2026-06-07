import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from houston.accounts.models import User
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    MembershipScope,
    OnboardingCatalogDomain,
    OnboardingCatalogModule,
    OnboardingCatalogUnit,
    OnboardingProposal,
    OnboardingSession,
    OperationalDomain,
    OperationalModule,
    OperationalUnit,
    RoutingHint,
    RoutingHintDomain,
    RuntimeTag,
    RuntimeTagDomain,
    RuntimeVocabulary,
)
from houston.establishments.services import (
    InvalidOnboardingSessionScopeError,
    UnsupportedOnboardingSessionSourceModeError,
    start_onboarding_session,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(name="Mama Shelter")


@pytest.fixture
def establishment(organization):
    return Establishment.objects.create(name="Nice", organization=organization)


@pytest.fixture
def user():
    return User.objects.create_user(username="manager_01", password="secret")


def test_establishment_belongs_to_organization(establishment, organization):
    assert establishment.organization == organization


def test_establishment_status_default(organization):
    establishment = Establishment.objects.create(name="Nice", organization=organization)

    assert establishment.status == Establishment.Status.DRAFT


def test_membership_links_user_and_establishment(user, establishment):
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
    )

    assert membership.user == user
    assert membership.establishment == establishment


def test_membership_role_and_status_defaults(user, establishment):
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
    )

    assert membership.role == EstablishmentMembership.Role.STAFF
    assert membership.status == EstablishmentMembership.Status.INVITED


def test_membership_role_and_status_choices():
    role_field = EstablishmentMembership._meta.get_field("role")
    status_field = EstablishmentMembership._meta.get_field("status")

    assert role_field.choices == EstablishmentMembership.Role.choices
    assert status_field.choices == EstablishmentMembership.Status.choices


def test_operational_domain_defaults(establishment):
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )

    assert domain.active is True
    assert domain.source == OperationalDomain.Source.MANUAL


def test_operational_domain_unique_key_per_establishment(establishment):
    OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )

    with pytest.raises(IntegrityError):
        OperationalDomain.objects.create(
            establishment=establishment,
            key="maintenance",
            label="Maintenance Duplicate",
        )


def test_operational_domain_same_key_allowed_across_establishments(organization, establishment):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    first_domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    second_domain = OperationalDomain.objects.create(
        establishment=other_establishment,
        key="maintenance",
        label="Maintenance",
    )

    assert first_domain.key == second_domain.key


def test_membership_unique_user_establishment_constraint(user, establishment):
    EstablishmentMembership.objects.create(user=user, establishment=establishment)

    with pytest.raises(IntegrityError):
        EstablishmentMembership.objects.create(user=user, establishment=establishment)


def test_auth_user_model_setting():
    from django.conf import settings

    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_membership_scope_unique_domain_per_membership(user, establishment):
    membership = EstablishmentMembership.objects.create(user=user, establishment=establishment)
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    MembershipScope.objects.create(membership=membership, operational_domain=domain)

    with pytest.raises(IntegrityError):
        MembershipScope.objects.create(membership=membership, operational_domain=domain)


def test_membership_delete_cascades_membership_scope(user, establishment):
    membership = EstablishmentMembership.objects.create(user=user, establishment=establishment)
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    MembershipScope.objects.create(membership=membership, operational_domain=domain)

    membership.delete()

    assert MembershipScope.objects.count() == 0


def test_operational_domain_delete_cascades_membership_scope(user, establishment):
    membership = EstablishmentMembership.objects.create(user=user, establishment=establishment)
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )
    MembershipScope.objects.create(membership=membership, operational_domain=domain)

    domain.delete()

    assert MembershipScope.objects.count() == 0


def test_onboarding_session_defaults(organization, establishment, user):
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        started_by=user,
    )

    assert session.status == OnboardingSession.Status.STARTED
    assert session.source_mode == OnboardingSession.SourceMode.MANUAL
    assert session.current_step == ""
    assert session.ai_attempts == 0
    assert session.last_error_code == ""
    assert session.started_at is not None


def test_onboarding_session_status_helpers_classify_terminal_and_non_terminal_statuses():
    assert OnboardingSession.is_non_terminal_status(OnboardingSession.Status.STARTED) is True
    assert (
        OnboardingSession.is_non_terminal_status(OnboardingSession.Status.READY_FOR_ACTIVATION)
        is True
    )
    assert OnboardingSession.is_terminal_status(OnboardingSession.Status.ACTIVATED) is True
    assert OnboardingSession.is_terminal_status(OnboardingSession.Status.FAILED) is True
    assert OnboardingSession.is_terminal_status(OnboardingSession.Status.CANCELED) is True


def test_onboarding_session_source_mode_choices_include_reserved_ai_value():
    source_field = OnboardingSession._meta.get_field("source_mode")

    assert source_field.choices == OnboardingSession.SourceMode.choices
    assert OnboardingSession.SourceMode.AI in {
        choice for choice, _label in OnboardingSession.SourceMode.choices
    }


def test_onboarding_session_unique_non_terminal_session_per_establishment(
    organization,
    establishment,
):
    OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
    )

    with pytest.raises(IntegrityError):
        OnboardingSession.objects.create(
            organization=organization,
            establishment=establishment,
            status=OnboardingSession.Status.CONFIGURING_RUNTIME,
        )


@pytest.mark.parametrize(
    "terminal_status",
    [
        OnboardingSession.Status.ACTIVATED,
        OnboardingSession.Status.FAILED,
        OnboardingSession.Status.CANCELED,
    ],
)
def test_onboarding_session_terminal_session_allows_later_non_terminal_session(
    organization,
    establishment,
    terminal_status,
):
    OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        status=terminal_status,
    )
    next_session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
    )

    assert next_session.status == OnboardingSession.Status.STARTED


def test_onboarding_session_allows_historical_terminal_sessions(
    organization,
    establishment,
):
    first = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        status=OnboardingSession.Status.ACTIVATED,
    )
    second = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        status=OnboardingSession.Status.CANCELED,
    )

    assert first.establishment == second.establishment


def test_onboarding_catalog_rows_are_seeded_by_migration():
    module_keys = set(
        OnboardingCatalogModule.objects.filter(active=True).values_list("key", flat=True)
    )
    assert module_keys == {
        "hotel",
        "restaurant",
        "retail_commerce",
        "coworking_bureau",
        "salle_de_sport",
        "loisirs",
    }
    assert module_keys.isdisjoint({"bar", "rooftop", "seminar_rooms"})

    domain_keys = set(
        OnboardingCatalogDomain.objects.filter(active=True).values_list("key", flat=True)
    )
    assert "hotel__hebergement" in domain_keys
    assert domain_keys.isdisjoint({"maintenance", "housekeeping", "security"})

    assert set(OnboardingCatalogUnit.objects.filter(active=True).values_list("key", flat=True)) >= {
        "lobby",
        "rooms",
        "kitchen",
        "technical_rooms",
        "outdoor_areas",
    }


@pytest.mark.parametrize(
    "model_class",
    [OnboardingCatalogModule, OnboardingCatalogUnit],
)
def test_onboarding_catalog_key_is_unique(model_class):
    model_class.objects.create(key="custom_key", label="Custom")

    with pytest.raises(IntegrityError):
        model_class.objects.create(key="custom_key", label="Duplicate")


def test_onboarding_catalog_domain_key_is_unique():
    module = OnboardingCatalogModule.objects.create(key="custom_module", label="Custom module")
    OnboardingCatalogDomain.objects.create(
        catalog_module=module,
        key="custom_domain",
        label="Custom domain",
    )

    with pytest.raises(IntegrityError):
        OnboardingCatalogDomain.objects.create(
            catalog_module=module,
            key="custom_domain",
            label="Duplicate domain",
        )


@pytest.mark.parametrize(
    ("model_class", "field_values", "expected_field"),
    [
        (OnboardingCatalogModule, {"key": " ", "label": "Hotel"}, "key"),
        (OnboardingCatalogModule, {"key": "hotel", "label": " "}, "label"),
        (OnboardingCatalogDomain, {"key": " ", "label": "Maintenance"}, "key"),
        (OnboardingCatalogDomain, {"key": "hotel__hebergement", "label": " "}, "label"),
        (OnboardingCatalogUnit, {"key": " ", "label": "Lobby"}, "key"),
        (OnboardingCatalogUnit, {"key": "lobby", "label": " "}, "label"),
    ],
)
def test_onboarding_catalog_models_validate_nonblank_fields(
    model_class,
    field_values,
    expected_field,
):
    instance = model_class(**field_values)

    with pytest.raises(ValidationError) as exc_info:
        instance.full_clean()

    assert expected_field in exc_info.value.message_dict


def test_onboarding_catalog_defaults():
    catalog_item = OnboardingCatalogModule.objects.create(
        key="custom_module",
        label="Custom module",
    )

    assert catalog_item.active is True
    assert catalog_item.sort_order == 0


def test_onboarding_proposal_defaults(organization, establishment, user):
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        started_by=user,
    )
    proposal = OnboardingProposal.objects.create(
        onboarding_session=session,
        establishment=establishment,
        created_by=user,
    )

    assert proposal.source == OnboardingProposal.Source.MANUAL
    assert proposal.status == OnboardingProposal.Status.DRAFT
    assert proposal.payload == {}
    assert proposal.section_validation == {}
    assert proposal.validation_errors == []


def test_onboarding_proposal_choices_include_future_ai_source():
    source_field = OnboardingProposal._meta.get_field("source")
    status_field = OnboardingProposal._meta.get_field("status")

    assert source_field.choices == OnboardingProposal.Source.choices
    assert status_field.choices == OnboardingProposal.Status.choices
    assert OnboardingProposal.Source.AI_PROPOSED in {
        choice for choice, _label in OnboardingProposal.Source.choices
    }


def test_onboarding_proposal_validates_establishment_matches_session(
    organization,
    establishment,
):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
    )
    proposal = OnboardingProposal(
        onboarding_session=session,
        establishment=other_establishment,
    )

    with pytest.raises(ValidationError) as exc_info:
        proposal.full_clean()

    assert "establishment" in exc_info.value.message_dict


def test_onboarding_proposal_unique_non_terminal_per_session(
    organization,
    establishment,
):
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
    )
    OnboardingProposal.objects.create(
        onboarding_session=session,
        establishment=establishment,
        status=OnboardingProposal.Status.READY,
    )

    with pytest.raises(IntegrityError):
        OnboardingProposal.objects.create(
            onboarding_session=session,
            establishment=establishment,
            status=OnboardingProposal.Status.PARTIALLY_VALIDATED,
        )


def test_onboarding_proposal_terminal_allows_later_non_terminal(
    organization,
    establishment,
):
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
    )
    OnboardingProposal.objects.create(
        onboarding_session=session,
        establishment=establishment,
        status=OnboardingProposal.Status.REJECTED,
    )
    next_proposal = OnboardingProposal.objects.create(
        onboarding_session=session,
        establishment=establishment,
        status=OnboardingProposal.Status.READY,
    )

    assert next_proposal.status == OnboardingProposal.Status.READY


def test_onboarding_proposal_json_defaults_are_independent(
    organization,
    establishment,
):
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
    )
    first = OnboardingProposal.objects.create(
        onboarding_session=session,
        establishment=establishment,
        status=OnboardingProposal.Status.REJECTED,
    )
    second = OnboardingProposal.objects.create(
        onboarding_session=session,
        establishment=establishment,
        status=OnboardingProposal.Status.FAILED,
    )

    first.payload["x"] = "y"
    first.section_validation["operational_modules"] = "accepted"
    first.validation_errors.append({"code": "example"})

    assert second.payload == {}
    assert second.section_validation == {}
    assert second.validation_errors == []


def test_onboarding_session_validates_organization_matches_establishment(establishment):
    other_organization = Organization.objects.create(name="Other Org")
    session = OnboardingSession(
        organization=other_organization,
        establishment=establishment,
    )

    with pytest.raises(ValidationError) as exc_info:
        session.full_clean()

    assert "organization" in exc_info.value.message_dict


def test_start_onboarding_session_creates_manual_session(organization, establishment, user):
    session = start_onboarding_session(
        organization=organization,
        establishment=establishment,
        started_by=user,
    )

    assert session.status == OnboardingSession.Status.STARTED
    assert session.source_mode == OnboardingSession.SourceMode.MANUAL
    assert session.started_by == user


def test_start_onboarding_session_allows_template_source_mode(
    organization,
    establishment,
):
    session = start_onboarding_session(
        organization=organization,
        establishment=establishment,
        source_mode=OnboardingSession.SourceMode.TEMPLATE,
    )

    assert session.source_mode == OnboardingSession.SourceMode.TEMPLATE


def test_start_onboarding_session_rejects_reserved_ai_source_mode(
    organization,
    establishment,
):
    with pytest.raises(UnsupportedOnboardingSessionSourceModeError):
        start_onboarding_session(
            organization=organization,
            establishment=establishment,
            source_mode=OnboardingSession.SourceMode.AI,
        )


def test_start_onboarding_session_rejects_mismatched_scope(establishment):
    other_organization = Organization.objects.create(name="Other Org")

    with pytest.raises(InvalidOnboardingSessionScopeError):
        start_onboarding_session(
            organization=other_organization,
            establishment=establishment,
        )


def test_start_onboarding_session_returns_existing_non_terminal_session(
    organization,
    establishment,
):
    first = start_onboarding_session(organization=organization, establishment=establishment)
    second = start_onboarding_session(organization=organization, establishment=establishment)

    assert second.id == first.id
    assert OnboardingSession.objects.filter(establishment=establishment).count() == 1


def test_activity_description_is_canonical_per_establishment(establishment):
    description = "A" * ACTIVITY_DESCRIPTION_MIN_LENGTH
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description=description,
    )

    with pytest.raises(IntegrityError):
        EstablishmentActivityDescription.objects.create(
            establishment=establishment,
            description=description,
        )


def test_activity_description_rejects_less_than_minimum_trimmed_length(establishment):
    description = EstablishmentActivityDescription(
        establishment=establishment,
        description=f" {'A' * (ACTIVITY_DESCRIPTION_MIN_LENGTH - 1)} ",
    )

    with pytest.raises(ValidationError) as exc_info:
        description.full_clean()

    assert "description" in exc_info.value.message_dict


def test_activity_description_accepts_minimum_trimmed_length(establishment):
    description = EstablishmentActivityDescription(
        establishment=establishment,
        description=f" {'A' * ACTIVITY_DESCRIPTION_MIN_LENGTH} ",
    )

    description.full_clean()


def test_activity_description_is_not_duplicated_on_establishment_model():
    field_names = {field.name for field in Establishment._meta.fields}

    assert "activity_description" not in field_names


def test_operational_module_unique_key_per_establishment(establishment):
    OperationalModule.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )

    with pytest.raises(IntegrityError):
        OperationalModule.objects.create(
            establishment=establishment,
            key="hotel",
            label="Hotel Duplicate",
        )


def test_operational_module_same_key_allowed_across_establishments(
    organization,
    establishment,
):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    first_module = OperationalModule.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    second_module = OperationalModule.objects.create(
        establishment=other_establishment,
        key="hotel",
        label="Hotel",
    )

    assert first_module.key == second_module.key


def test_operational_unit_unique_key_per_establishment(establishment):
    OperationalUnit.objects.create(
        establishment=establishment,
        key="lobby",
        label="Lobby",
    )

    with pytest.raises(IntegrityError):
        OperationalUnit.objects.create(
            establishment=establishment,
            key="lobby",
            label="Lobby Duplicate",
        )


def test_operational_unit_same_key_allowed_across_establishments(
    organization,
    establishment,
):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    first_unit = OperationalUnit.objects.create(
        establishment=establishment,
        key="lobby",
        label="Lobby",
    )
    second_unit = OperationalUnit.objects.create(
        establishment=other_establishment,
        key="lobby",
        label="Lobby",
    )

    assert first_unit.key == second_unit.key


def test_runtime_vocabulary_unique_term_per_establishment(establishment):
    RuntimeVocabulary.objects.create(
        establishment=establishment,
        term="VRV",
        meaning="HVAC equipment",
    )

    with pytest.raises(IntegrityError):
        RuntimeVocabulary.objects.create(
            establishment=establishment,
            term="VRV",
            meaning="Duplicate",
        )


def test_runtime_vocabulary_same_term_allowed_across_establishments(
    organization,
    establishment,
):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    first_term = RuntimeVocabulary.objects.create(
        establishment=establishment,
        term="VRV",
        meaning="HVAC equipment",
    )
    second_term = RuntimeVocabulary.objects.create(
        establishment=other_establishment,
        term="VRV",
        meaning="HVAC equipment",
    )

    assert first_term.term == second_term.term


def test_runtime_tag_unique_key_per_establishment(establishment):
    RuntimeTag.objects.create(
        establishment=establishment,
        key="rush",
        label="Rush",
    )

    with pytest.raises(IntegrityError):
        RuntimeTag.objects.create(
            establishment=establishment,
            key="rush",
            label="Rush Duplicate",
        )


def test_runtime_tag_same_key_allowed_across_establishments(organization, establishment):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    first_tag = RuntimeTag.objects.create(
        establishment=establishment,
        key="rush",
        label="Rush",
    )
    second_tag = RuntimeTag.objects.create(
        establishment=other_establishment,
        key="rush",
        label="Rush",
    )

    assert first_tag.key == second_tag.key


def test_routing_hint_unique_pattern_per_establishment(establishment):
    RoutingHint.objects.create(
        establishment=establishment,
        pattern="VRV",
    )

    with pytest.raises(IntegrityError):
        RoutingHint.objects.create(
            establishment=establishment,
            pattern="VRV",
        )


def test_routing_hint_same_pattern_allowed_across_establishments(
    organization,
    establishment,
):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    first_hint = RoutingHint.objects.create(
        establishment=establishment,
        pattern="VRV",
    )
    second_hint = RoutingHint.objects.create(
        establishment=other_establishment,
        pattern="VRV",
    )

    assert first_hint.pattern == second_hint.pattern


@pytest.mark.parametrize(
    ("model_class", "field_values", "expected_field"),
    [
        (OperationalModule, {"key": " ", "label": "Hotel"}, "key"),
        (OperationalModule, {"key": "hotel", "label": " "}, "label"),
        (OperationalUnit, {"key": " ", "label": "Lobby"}, "key"),
        (OperationalUnit, {"key": "lobby", "label": " "}, "label"),
        (RuntimeVocabulary, {"term": " ", "meaning": "HVAC equipment"}, "term"),
        (RuntimeVocabulary, {"term": "VRV", "meaning": " "}, "meaning"),
        (RuntimeTag, {"key": " ", "label": "Rush"}, "key"),
        (RuntimeTag, {"key": "rush", "label": " "}, "label"),
        (RoutingHint, {"pattern": " "}, "pattern"),
    ],
)
def test_runtime_models_validate_nonblank_fields(
    establishment,
    model_class,
    field_values,
    expected_field,
):
    instance = model_class(establishment=establishment, **field_values)

    with pytest.raises(ValidationError) as exc_info:
        instance.full_clean()

    assert expected_field in exc_info.value.message_dict


def test_runtime_vocabulary_mapped_domain_must_match_establishment(
    organization,
    establishment,
):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    foreign_domain = OperationalDomain.objects.create(
        establishment=other_establishment,
        key="maintenance",
        label="Maintenance",
    )
    vocabulary = RuntimeVocabulary(
        establishment=establishment,
        term="VRV",
        meaning="HVAC equipment",
        mapped_domain=foreign_domain,
    )

    with pytest.raises(ValidationError) as exc_info:
        vocabulary.full_clean()

    assert "mapped_domain" in exc_info.value.message_dict


def test_runtime_vocabulary_mapped_unit_must_match_establishment(
    organization,
    establishment,
):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    foreign_unit = OperationalUnit.objects.create(
        establishment=other_establishment,
        key="lobby",
        label="Lobby",
    )
    vocabulary = RuntimeVocabulary(
        establishment=establishment,
        term="front desk",
        meaning="Reception desk",
        mapped_unit=foreign_unit,
    )

    with pytest.raises(ValidationError) as exc_info:
        vocabulary.full_clean()

    assert "mapped_unit" in exc_info.value.message_dict


def test_runtime_tag_domain_must_match_establishment(organization, establishment):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    runtime_tag = RuntimeTag.objects.create(
        establishment=establishment,
        key="rush",
        label="Rush",
    )
    foreign_domain = OperationalDomain.objects.create(
        establishment=other_establishment,
        key="restaurant",
        label="Restaurant",
    )
    link = RuntimeTagDomain(
        runtime_tag=runtime_tag,
        operational_domain=foreign_domain,
    )

    with pytest.raises(ValidationError) as exc_info:
        link.full_clean()

    assert "operational_domain" in exc_info.value.message_dict


def test_routing_hint_suggested_unit_must_match_establishment(
    organization,
    establishment,
):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    foreign_unit = OperationalUnit.objects.create(
        establishment=other_establishment,
        key="lobby",
        label="Lobby",
    )
    hint = RoutingHint(
        establishment=establishment,
        pattern="front desk",
        suggested_unit=foreign_unit,
    )

    with pytest.raises(ValidationError) as exc_info:
        hint.full_clean()

    assert "suggested_unit" in exc_info.value.message_dict


def test_routing_hint_domain_must_match_establishment(organization, establishment):
    other_establishment = Establishment.objects.create(name="Cannes", organization=organization)
    hint = RoutingHint.objects.create(
        establishment=establishment,
        pattern="VRV",
    )
    foreign_domain = OperationalDomain.objects.create(
        establishment=other_establishment,
        key="maintenance",
        label="Maintenance",
    )
    link = RoutingHintDomain(
        routing_hint=hint,
        operational_domain=foreign_domain,
    )

    with pytest.raises(ValidationError) as exc_info:
        link.full_clean()

    assert "operational_domain" in exc_info.value.message_dict
