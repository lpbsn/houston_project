from __future__ import annotations

import copy

import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipScope,
    OnboardingCatalogDomain,
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
    OnboardingAccessDeniedError,
    OnboardingProposalStateError,
    OnboardingProposalValidationError,
    apply_onboarding_proposal,
    create_manual_onboarding_proposal,
    create_template_onboarding_proposal,
    validate_onboarding_proposal_payload,
    validate_onboarding_proposal_section,
)
from houston.establishments.tests.conftest import (
    HOTEL_HEBERGEMENT_DOMAIN_KEY,
    create_validated_proposal,
    valid_v2_payload,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(name="Mama Shelter")


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="proposal_owner",
        password="secret",
        status=User.Status.ACTIVE,
    )


@pytest.fixture
def onboarding_session(organization, owner):
    establishment = Establishment.objects.create(
        name="Draft",
        organization=organization,
        status=Establishment.Status.DRAFT,
    )
    session = OnboardingSession.objects.create(
        organization=organization,
        establishment=establishment,
        started_by=owner,
    )
    EstablishmentMembership.objects.create(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    return session


def proposal_error_codes(exc_info) -> set[str]:
    return {error["code"] for error in exc_info.value.errors}


def test_valid_manual_payload_passes_against_active_catalog_rows():
    sanitized = validate_onboarding_proposal_payload(valid_v2_payload())

    assert sanitized["schema_version"] == "onboarding_proposal_v2"
    assert sanitized["operational_modules"][0]["key"] == "hotel"
    assert len(sanitized["operational_domains"]) == 6
    assert len(sanitized["operational_subjects"]) > 0


def test_template_proposal_uses_same_validation_boundary(onboarding_session, owner):
    proposal = create_template_onboarding_proposal(
        session=onboarding_session,
        actor=owner,
        payload=valid_v2_payload(),
    )

    assert proposal.source == OnboardingProposal.Source.TEMPLATE
    assert proposal.status == OnboardingProposal.Status.READY
    assert OperationalModule.objects.count() == 0
    assert OperationalDomain.objects.count() == 0


def test_inactive_catalog_key_is_rejected_as_unknown():
    OnboardingCatalogDomain.objects.filter(key=HOTEL_HEBERGEMENT_DOMAIN_KEY).update(active=False)
    payload = valid_v2_payload()

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        validate_onboarding_proposal_payload(payload)

    assert "unknown_catalog_key" in proposal_error_codes(exc_info)


@pytest.mark.parametrize(
    ("mutate_payload", "expected_code"),
    [
        (lambda payload: payload.update({"roles": []}), "excluded_section"),
        (lambda payload: payload.update({"unexpected": []}), "unknown_section"),
        (
            lambda payload: payload["operational_modules"].append(
                {
                    "key": "hotel",
                    "label": "Hotel duplicate",
                    "reason": "",
                    "confidence_score": None,
                }
            ),
            "duplicate_key",
        ),
        (
            lambda payload: payload["operational_modules"].append(
                {
                    "key": "unknown",
                    "label": "Unknown",
                    "reason": "",
                    "confidence_score": None,
                }
            ),
            "unknown_catalog_key",
        ),
        (
            lambda payload: payload["runtime_vocabulary"].append(
                {
                    "term": "VRV",
                    "meaning": "Duplicate",
                    "mapped_domain_key": HOTEL_HEBERGEMENT_DOMAIN_KEY,
                    "mapped_unit_key": "lobby",
                    "reason": "",
                }
            ),
            "duplicate_term",
        ),
        (
            lambda payload: payload["routing_hints"].append(
                {
                    "pattern": "VRV",
                    "suggested_domain_keys": [HOTEL_HEBERGEMENT_DOMAIN_KEY],
                    "suggested_unit_key": "lobby",
                    "reason": "",
                    "confidence_score": None,
                }
            ),
            "duplicate_pattern",
        ),
        (lambda payload: payload["operational_modules"][0].update({"key": " "}), "blank_key"),
        (
            lambda payload: payload["operational_modules"][0].update({"label": " "}),
            "blank_label",
        ),
        (
            lambda payload: payload["runtime_vocabulary"][0].update({"term": " "}),
            "blank_term",
        ),
        (
            lambda payload: payload["runtime_vocabulary"][0].update({"meaning": " "}),
            "blank_meaning",
        ),
        (
            lambda payload: payload["routing_hints"][0].update({"pattern": " "}),
            "blank_pattern",
        ),
    ],
)
def test_payload_validation_returns_stable_error_codes(mutate_payload, expected_code):
    payload = copy.deepcopy(valid_v2_payload())
    mutate_payload(payload)

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        validate_onboarding_proposal_payload(payload)

    assert expected_code in proposal_error_codes(exc_info)


def test_payload_validation_enforces_caps():
    payload = valid_v2_payload()
    payload["runtime_tags"] = [
        {"key": f"tag_{index}", "label": f"Tag {index}", "related_domain_keys": []}
        for index in range(31)
    ]

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        validate_onboarding_proposal_payload(payload)

    assert "section_cap_exceeded" in proposal_error_codes(exc_info)


def test_payload_validation_rejects_invalid_mappings():
    payload = valid_v2_payload()
    payload["runtime_vocabulary"][0]["mapped_domain_key"] = "pricing"
    payload["runtime_vocabulary"][0]["mapped_unit_key"] = "rooms"
    payload["routing_hints"][0]["suggested_domain_keys"] = ["pricing"]
    payload["routing_hints"][0]["suggested_unit_key"] = "rooms"

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        validate_onboarding_proposal_payload(payload)

    assert {
        "invalid_mapped_domain_key",
        "invalid_mapped_unit_key",
        "invalid_suggested_domain_key",
        "invalid_suggested_unit_key",
    }.issubset(proposal_error_codes(exc_info))


def test_payload_validation_rejects_too_many_suggested_domains():
    payload = valid_v2_payload()
    payload["routing_hints"][0]["suggested_domain_keys"] = [
        domain["key"] for domain in payload["operational_domains"][:5]
    ]

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        validate_onboarding_proposal_payload(payload)

    assert "too_many_suggested_domains" in proposal_error_codes(exc_info)


def test_create_and_section_validation_do_not_mutate_runtime(onboarding_session, owner):
    proposal = create_manual_onboarding_proposal(
        session=onboarding_session,
        actor=owner,
        payload=valid_v2_payload(),
    )
    validate_onboarding_proposal_section(
        proposal=proposal,
        actor=owner,
        section="operational_modules",
        decision="accepted",
    )

    assert OperationalModule.objects.count() == 0
    assert OperationalDomain.objects.count() == 0
    assert OperationalUnit.objects.count() == 0
    onboarding_session.refresh_from_db()
    assert onboarding_session.status == OnboardingSession.Status.VALIDATING_SECTIONS


def test_required_section_cannot_be_skipped(onboarding_session, owner):
    proposal = create_manual_onboarding_proposal(
        session=onboarding_session,
        actor=owner,
        payload=valid_v2_payload(),
    )

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        validate_onboarding_proposal_section(
            proposal=proposal,
            actor=owner,
            section="operational_modules",
            decision="skipped",
        )

    assert "missing_required_section" in proposal_error_codes(exc_info)


def test_manager_cannot_create_or_apply_proposal(onboarding_session):
    manager = User.objects.create_user(
        username="proposal_manager",
        password="secret",
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=manager,
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    with pytest.raises(OnboardingAccessDeniedError):
        create_manual_onboarding_proposal(
            session=onboarding_session,
            actor=manager,
            payload=valid_v2_payload(),
        )


def test_apply_requires_validated_proposal(onboarding_session, owner):
    proposal = create_manual_onboarding_proposal(
        session=onboarding_session,
        actor=owner,
        payload=valid_v2_payload(),
    )

    with pytest.raises(OnboardingProposalStateError):
        apply_onboarding_proposal(proposal=proposal, actor=owner)

    assert OperationalModule.objects.count() == 0


def test_apply_revalidates_against_active_catalog_rows(onboarding_session, owner):
    proposal = create_validated_proposal(onboarding_session, owner)
    OnboardingCatalogDomain.objects.filter(key=HOTEL_HEBERGEMENT_DOMAIN_KEY).update(active=False)

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        apply_onboarding_proposal(proposal=proposal, actor=owner)

    assert "unknown_catalog_key" in proposal_error_codes(exc_info)
    assert OperationalDomain.objects.count() == 0


def test_apply_preserves_omitted_manual_runtime_rows_and_membership_domain(
    onboarding_session,
    owner,
):
    old_domain = OperationalDomain.objects.create(
        establishment=onboarding_session.establishment,
        key="old_domain",
        label="Old domain",
    )
    old_module = OperationalModule.objects.create(
        establishment=onboarding_session.establishment,
        key="old_module",
        label="Old module",
    )
    old_unit = OperationalUnit.objects.create(
        establishment=onboarding_session.establishment,
        key="old_unit",
        label="Old unit",
    )
    old_vocab = RuntimeVocabulary.objects.create(
        establishment=onboarding_session.establishment,
        term="old term",
        meaning="Old meaning",
    )
    old_tag = RuntimeTag.objects.create(
        establishment=onboarding_session.establishment,
        key="old_tag",
        label="Old tag",
    )
    RuntimeTagDomain.objects.create(runtime_tag=old_tag, operational_domain=old_domain)
    old_hint = RoutingHint.objects.create(
        establishment=onboarding_session.establishment,
        pattern="old pattern",
    )
    RoutingHintDomain.objects.create(routing_hint=old_hint, operational_domain=old_domain)
    manager = User.objects.create_user(
        username="proposal_manager_existing_domain",
        password="secret",
        status=User.Status.ACTIVE,
    )
    manager_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    membership_scope = MembershipScope.objects.create(
        membership=manager_membership,
        operational_domain=old_domain,
    )
    onboarding_session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    onboarding_session.ready_for_activation_at = timezone.now()
    onboarding_session.save(
        update_fields=["status", "ready_for_activation_at", "updated_at"],
    )
    proposal = create_validated_proposal(onboarding_session, owner)

    applied = apply_onboarding_proposal(proposal=proposal, actor=owner)

    assert applied.status == OnboardingProposal.Status.APPLIED
    onboarding_session.refresh_from_db()
    onboarding_session.establishment.refresh_from_db()
    assert onboarding_session.status == OnboardingSession.Status.CONFIGURING_RUNTIME
    assert onboarding_session.ready_for_activation_at is None
    assert onboarding_session.activated_at is None
    assert onboarding_session.establishment.status == Establishment.Status.DRAFT

    assert OperationalModule.objects.get(key="hotel").source == OnboardingProposal.Source.MANUAL
    assert OperationalDomain.objects.filter(
        key=HOTEL_HEBERGEMENT_DOMAIN_KEY,
        active=True,
    ).exists()
    assert OperationalUnit.objects.get(key="lobby").active is True
    assert (
        RuntimeVocabulary.objects.get(term="VRV").mapped_domain.key == HOTEL_HEBERGEMENT_DOMAIN_KEY
    )
    assert RuntimeTag.objects.get(key="hvac").domain_links.count() == 1
    assert RoutingHint.objects.get(pattern="VRV").domain_links.count() == 1

    old_domain.refresh_from_db()
    old_module.refresh_from_db()
    old_unit.refresh_from_db()
    old_vocab.refresh_from_db()
    old_tag.refresh_from_db()
    old_hint.refresh_from_db()
    assert old_domain.active is True
    assert old_module.active is True
    assert old_unit.active is True
    assert old_vocab.active is True
    assert old_tag.active is True
    assert old_hint.active is True
    assert old_domain.managed_by_onboarding_proposal is None
    assert old_module.managed_by_onboarding_proposal is None
    assert old_unit.managed_by_onboarding_proposal is None
    assert old_vocab.managed_by_onboarding_proposal is None
    assert old_tag.managed_by_onboarding_proposal is None
    assert old_hint.managed_by_onboarding_proposal is None
    assert MembershipScope.objects.get(id=membership_scope.id).operational_domain == old_domain


def test_apply_deactivates_only_omitted_proposal_managed_runtime_rows(
    onboarding_session,
    owner,
):
    first_proposal = create_validated_proposal(onboarding_session, owner)
    apply_onboarding_proposal(proposal=first_proposal, actor=owner)

    managed_unit = OperationalUnit.objects.get(key="lobby")
    managed_vocab = RuntimeVocabulary.objects.get(term="VRV")
    managed_tag = RuntimeTag.objects.get(key="hvac")
    managed_hint = RoutingHint.objects.get(pattern="VRV")
    assert managed_unit.managed_by_onboarding_proposal == first_proposal
    assert managed_vocab.managed_by_onboarding_proposal == first_proposal
    assert managed_tag.managed_by_onboarding_proposal == first_proposal
    assert managed_hint.managed_by_onboarding_proposal == first_proposal

    payload = valid_v2_payload()
    payload["operational_units"] = []
    payload["runtime_vocabulary"] = []
    payload["runtime_tags"] = []
    payload["routing_hints"] = []
    second_proposal = create_validated_proposal(onboarding_session, owner, payload=payload)

    apply_onboarding_proposal(proposal=second_proposal, actor=owner)

    managed_unit.refresh_from_db()
    managed_vocab.refresh_from_db()
    managed_tag.refresh_from_db()
    managed_hint.refresh_from_db()
    assert managed_unit.active is False
    assert managed_vocab.active is False
    assert managed_tag.active is False
    assert managed_hint.active is False


def test_apply_updates_existing_runtime_rows(onboarding_session, owner):
    OperationalModule.objects.create(
        establishment=onboarding_session.establishment,
        key="hotel",
        label="Old Hotel",
        active=False,
    )
    proposal = create_validated_proposal(onboarding_session, owner)

    apply_onboarding_proposal(proposal=proposal, actor=owner)

    module = OperationalModule.objects.get(
        establishment=onboarding_session.establishment,
        key="hotel",
    )
    assert module.label == "Hôtel"
    assert module.active is True
    assert module.managed_by_onboarding_proposal == proposal
