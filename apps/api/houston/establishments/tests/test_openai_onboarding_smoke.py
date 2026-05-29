from __future__ import annotations

import json
import os

import pytest
from django.conf import settings
from django.utils import timezone

from houston.accounts.models import User
from houston.ai.models import AIUsageLog
from houston.establishments.ai_onboarding import run_ai_onboarding_interpretation
from houston.establishments.models import (
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    OnboardingProposal,
    OnboardingSession,
)
from houston.organizations.models import Organization

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.openai_smoke,
]

TEMPLATE_FALLBACK_REASON = "Default onboarding template fallback."


def _openai_smoke_enabled() -> bool:
    return os.environ.get("HOUSTON_RUN_OPENAI_SMOKE_TEST") == "1"


@pytest.fixture
def organization():
    return Organization.objects.create(name="OpenAI Smoke Org")


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="openai_smoke_owner",
        email="openai-smoke@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )


@pytest.fixture
def onboarding_session(organization, owner):
    establishment = Establishment.objects.create(
        name="OpenAI Smoke Establishment",
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


def _skip_if_smoke_not_enabled():
    if not _openai_smoke_enabled():
        pytest.skip(
            "Set HOUSTON_RUN_OPENAI_SMOKE_TEST=1 to run the live OpenAI onboarding smoke test."
        )
    if not settings.OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY is not configured.")


def _assert_not_template_fallback(*, proposal: OnboardingProposal, usage_log: AIUsageLog) -> None:
    assert proposal.source != OnboardingProposal.Source.TEMPLATE
    assert usage_log.status != AIUsageLog.Status.FALLBACK_SUCCEEDED

    payload_blob = json.dumps(proposal.payload)
    assert TEMPLATE_FALLBACK_REASON not in payload_blob, (
        "Expected live OpenAI onboarding (ai_proposed/succeeded) but got template fallback. "
        "Check OPENAI_API_KEY in the API container (make ai-config-check)."
    )


def _assert_token_fields_if_present(usage_log: AIUsageLog) -> None:
    for field_name in ("input_tokens", "output_tokens", "total_tokens"):
        value = getattr(usage_log, field_name)
        if value is not None:
            assert value > 0, f"Expected {field_name} > 0 when present, got {value}"


def test_live_openai_onboarding_smoke(onboarding_session, owner):
    _skip_if_smoke_not_enabled()

    proposal = run_ai_onboarding_interpretation(
        session=onboarding_session,
        actor=owner,
    )

    usage_log = AIUsageLog.objects.get()

    assert proposal.source == OnboardingProposal.Source.AI_PROPOSED, (
        "Expected live OpenAI onboarding (ai_proposed/succeeded) but got template fallback. "
        f"proposal.source={proposal.source!r}, usage_log.status={usage_log.status!r}, "
        f"usage_log.error_code={usage_log.error_code!r}. "
        "Check OPENAI_API_KEY in the API container (make ai-config-check)."
    )
    assert usage_log.status == AIUsageLog.Status.SUCCEEDED
    assert usage_log.provider == "openai"
    assert usage_log.error_code == ""
    assert usage_log.onboarding_proposal_id == proposal.id

    _assert_not_template_fallback(proposal=proposal, usage_log=usage_log)
    _assert_token_fields_if_present(usage_log)

    stored_values = " ".join(str(value) for value in usage_log.__dict__.values())
    assert "sk-" not in stored_values
    assert "Hotel with restaurant" not in stored_values
