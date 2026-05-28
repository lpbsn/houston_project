from __future__ import annotations

import json

import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.ai.models import AIUsageLog
from houston.establishments.ai_onboarding import (
    AIOnboardingInvalidOutputError,
    AIOnboardingProviderResponse,
    AIOnboardingProviderTimeoutError,
    AIOnboardingProviderUnavailableError,
    build_ai_onboarding_input,
    run_ai_onboarding_interpretation,
    validate_ai_onboarding_output,
)
from houston.establishments.models import (
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    OnboardingCatalogDomain,
    OnboardingProposal,
    OnboardingSession,
    OperationalDomain,
    OperationalModule,
    OperationalUnit,
    RoutingHint,
    RuntimeTag,
    RuntimeVocabulary,
)
from houston.establishments.services import OnboardingAccessDeniedError
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


class FakeProvider:
    provider = "fake_openai"
    model = "fake-onboarding-model"

    def __init__(self, payload=None, exc=None):
        self.payload = payload or valid_ai_payload()
        self.exc = exc
        self.calls: list[dict] = []

    def generate(self, input_payload):
        self.calls.append(input_payload)
        if self.exc is not None:
            raise self.exc
        return AIOnboardingProviderResponse(
            payload=self.payload,
            input_tokens=11,
            output_tokens=22,
            total_tokens=33,
            model=self.model,
        )


@pytest.fixture
def organization():
    return Organization.objects.create(name="Mama Shelter")


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="ai_owner",
        email="owner@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )


@pytest.fixture
def onboarding_session(organization, owner):
    establishment = Establishment.objects.create(
        name="Mama Shelter Nice",
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
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description=(
            "Hotel with restaurant, rooftop, seminar rooms, bar, maintenance, "
            "housekeeping, security, and guest experience operations."
        ),
        submitted_by=owner,
        validated_at=timezone.now(),
    )
    return session


def valid_ai_payload() -> dict:
    return {
        "schema_version": "onboarding_proposal_v1",
        "operational_modules": [
            {
                "key": "hotel",
                "label": "Hotel",
                "reason": "The establishment includes hotel operations.",
                "confidence_score": 0.91,
            }
        ],
        "operational_domains": [
            {
                "key": "maintenance",
                "label": "Maintenance",
                "related_modules": ["hotel"],
                "reason": "Maintenance issues need routing.",
                "confidence_score": 0.9,
            },
            {
                "key": "housekeeping",
                "label": "Housekeeping",
                "related_modules": ["hotel"],
                "reason": "Room operations need routing.",
                "confidence_score": 0.88,
            },
            {
                "key": "security",
                "label": "Security",
                "related_modules": ["hotel"],
                "reason": "Safety issues need routing.",
                "confidence_score": 0.82,
            },
        ],
        "operational_units": [
            {
                "key": "lobby",
                "label": "Lobby",
                "related_modules": ["hotel"],
                "reason": "The lobby is a shared operational area.",
                "confidence_score": 0.77,
            }
        ],
        "runtime_vocabulary": [
            {
                "term": "VRV",
                "meaning": "HVAC equipment",
                "mapped_domain_key": "maintenance",
                "mapped_unit_key": "lobby",
                "reason": "The team may use technical HVAC terms.",
            }
        ],
        "runtime_tags": [
            {
                "key": "hvac",
                "label": "HVAC",
                "related_domain_keys": ["maintenance"],
                "reason": "Helps classify HVAC issues.",
            }
        ],
        "routing_hints": [
            {
                "pattern": "VRV",
                "suggested_domain_keys": ["maintenance"],
                "suggested_unit_key": "lobby",
                "reason": "Route HVAC mentions to maintenance.",
                "confidence_score": 0.8,
            }
        ],
    }


def test_input_builder_minimizes_provider_payload(onboarding_session, owner):
    EstablishmentMembership.objects.create(
        user=User.objects.create_user(
            username="sensitive_manager",
            email="manager@example.com",
            password="secret",
            status=User.Status.ACTIVE,
        ),
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    payload = build_ai_onboarding_input(session=onboarding_session, locale="fr-FR")
    serialized = json.dumps(payload)

    assert set(payload) == {
        "establishment_name",
        "activity_description",
        "active_module_catalog",
        "active_domain_catalog",
        "active_unit_catalog",
        "locale",
        "schema_version",
        "prompt_version",
    }
    assert payload["locale"] == "fr-FR"
    assert "Mama Shelter Nice" in serialized
    assert "owner@example.com" not in serialized
    assert "manager@example.com" not in serialized
    assert "sensitive_manager" not in serialized
    assert "membership" not in serialized.lower()
    assert "billing" not in serialized.lower()
    assert "observations" not in serialized.lower()
    assert "signals" not in serialized.lower()
    assert "actions" not in serialized.lower()
    assert "comments" not in serialized.lower()


def test_provider_success_creates_ai_proposal_only(onboarding_session, owner):
    provider = FakeProvider()

    proposal = run_ai_onboarding_interpretation(
        session=onboarding_session,
        actor=owner,
        provider=provider,
    )

    assert provider.calls
    assert proposal.source == OnboardingProposal.Source.AI_PROPOSED
    assert proposal.status == OnboardingProposal.Status.READY
    assert proposal.payload == validate_ai_onboarding_output(valid_ai_payload())
    assert OperationalModule.objects.count() == 0
    assert OperationalDomain.objects.count() == 0
    assert OperationalUnit.objects.count() == 0
    assert RuntimeVocabulary.objects.count() == 0
    assert RuntimeTag.objects.count() == 0
    assert RoutingHint.objects.count() == 0
    onboarding_session.establishment.refresh_from_db()
    assert onboarding_session.establishment.status == Establishment.Status.DRAFT

    usage_log = AIUsageLog.objects.get()
    assert usage_log.status == AIUsageLog.Status.SUCCEEDED
    assert usage_log.ai_domain == AIUsageLog.Domain.ONBOARDING
    assert usage_log.provider == "fake_openai"
    assert usage_log.model == "fake-onboarding-model"
    assert usage_log.input_tokens == 11
    assert usage_log.output_tokens == 22
    assert usage_log.total_tokens == 33
    assert usage_log.onboarding_proposal == proposal
    assert usage_log.onboarding_session == onboarding_session
    assert usage_log.establishment == onboarding_session.establishment
    assert usage_log.error_code == ""


def test_unauthorized_actor_does_not_call_provider(onboarding_session):
    manager = User.objects.create_user(
        username="ai_manager",
        email="ai_manager@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=manager,
        establishment=onboarding_session.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    provider = FakeProvider()

    with pytest.raises(OnboardingAccessDeniedError):
        run_ai_onboarding_interpretation(
            session=onboarding_session,
            actor=manager,
            provider=provider,
        )

    assert provider.calls == []
    assert OnboardingProposal.objects.count() == 0
    assert AIUsageLog.objects.count() == 0


@pytest.mark.parametrize(
    "payload_mutator",
    [
        lambda payload: payload.update({"roles": []}),
        lambda payload: payload["operational_modules"][0].update({"key": "unknown_module"}),
        lambda payload: payload.__setitem__(
            "operational_domains",
            payload["operational_domains"][:1],
        ),
        lambda payload: payload.__setitem__(
            "runtime_tags",
            [
                {
                    "key": f"tag_{index}",
                    "label": f"Tag {index}",
                    "related_domain_keys": [],
                    "reason": "Too many tags.",
                }
                for index in range(31)
            ],
        ),
    ],
)
def test_invalid_provider_output_falls_back_to_template(
    onboarding_session,
    owner,
    payload_mutator,
):
    payload = valid_ai_payload()
    payload_mutator(payload)
    provider = FakeProvider(payload=payload)

    proposal = run_ai_onboarding_interpretation(
        session=onboarding_session,
        actor=owner,
        provider=provider,
    )

    assert proposal.source == OnboardingProposal.Source.TEMPLATE
    assert proposal.status == OnboardingProposal.Status.READY
    assert len(proposal.payload["operational_domains"]) == 3
    assert OperationalModule.objects.count() == 0
    assert OperationalDomain.objects.count() == 0

    usage_log = AIUsageLog.objects.get()
    assert usage_log.status == AIUsageLog.Status.FALLBACK_SUCCEEDED
    assert usage_log.error_code in {
        "invalid_structured_output",
        "invalid_ai_proposal_payload",
    }
    assert usage_log.onboarding_proposal == proposal
    assert AIUsageLog.objects.count() == 1


@pytest.mark.parametrize(
    "exc",
    [
        AIOnboardingProviderTimeoutError("timeout"),
        AIOnboardingProviderUnavailableError("unavailable"),
    ],
)
def test_provider_failure_falls_back_to_template(onboarding_session, owner, exc):
    provider = FakeProvider(exc=exc)

    proposal = run_ai_onboarding_interpretation(
        session=onboarding_session,
        actor=owner,
        provider=provider,
    )

    assert proposal.source == OnboardingProposal.Source.TEMPLATE
    usage_log = AIUsageLog.objects.get()
    assert usage_log.status == AIUsageLog.Status.FALLBACK_SUCCEEDED
    assert usage_log.error_code == exc.error_code
    assert usage_log.onboarding_proposal == proposal
    assert usage_log.input_tokens is None
    assert AIUsageLog.objects.count() == 1


def test_excluded_sections_are_rejected_by_ai_output_validation():
    payload = valid_ai_payload()
    payload["memberships"] = []

    with pytest.raises(AIOnboardingInvalidOutputError):
        validate_ai_onboarding_output(payload)


def test_fallback_failure_logs_one_failed_attempt(onboarding_session, owner):
    OnboardingCatalogDomain.objects.all().update(active=False)
    provider = FakeProvider(exc=AIOnboardingProviderTimeoutError("timeout"))

    with pytest.raises(Exception):
        run_ai_onboarding_interpretation(
            session=onboarding_session,
            actor=owner,
            provider=provider,
        )

    assert provider.calls
    usage_log = AIUsageLog.objects.get()
    assert usage_log.status == AIUsageLog.Status.FALLBACK_FAILED
    assert usage_log.error_code == "provider_timeout"
    assert usage_log.onboarding_proposal is None
    assert AIUsageLog.objects.count() == 1


def test_usage_log_does_not_store_prompt_output_or_api_key(onboarding_session, owner, settings):
    settings.OPENAI_API_KEY = "sk-test-secret"
    provider = FakeProvider()

    run_ai_onboarding_interpretation(
        session=onboarding_session,
        actor=owner,
        provider=provider,
    )

    usage_log = AIUsageLog.objects.get()
    stored_values = " ".join(str(value) for value in usage_log.__dict__.values())
    assert "sk-test-secret" not in stored_values
    assert "activity_description" not in stored_values
    assert "operational_modules" not in stored_values
    assert "Hotel with restaurant" not in stored_values
