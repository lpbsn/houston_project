from __future__ import annotations

import uuid

import pytest

from houston.ai.models import AIUsageLog

pytestmark = pytest.mark.django_db


def test_ai_usage_log_stores_technical_metadata_only():
    usage_log = AIUsageLog.objects.create(
        ai_domain=AIUsageLog.Domain.ONBOARDING,
        provider="openai",
        model="gpt-test",
        prompt_version="ai_onboarding_v1",
        schema_version="onboarding_proposal_v1",
        status=AIUsageLog.Status.SUCCEEDED,
        latency_ms=123,
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        error_code="",
        correlation_id=uuid.uuid4(),
    )

    usage_log.refresh_from_db()
    assert usage_log.ai_domain == AIUsageLog.Domain.ONBOARDING
    assert usage_log.status == AIUsageLog.Status.SUCCEEDED
    assert usage_log.input_tokens == 10
    assert usage_log.output_tokens == 20
    assert usage_log.total_tokens == 30
    assert not hasattr(usage_log, "prompt")
    assert not hasattr(usage_log, "raw_output")
    assert not hasattr(usage_log, "api_key")


def test_ai_usage_log_started_status_can_be_updated_in_place():
    usage_log = AIUsageLog.objects.create(
        ai_domain=AIUsageLog.Domain.ONBOARDING,
        provider="openai",
        model="gpt-test",
        prompt_version="ai_onboarding_v1",
        schema_version="onboarding_proposal_v1",
        status=AIUsageLog.Status.STARTED,
        correlation_id=uuid.uuid4(),
    )

    usage_log.status = AIUsageLog.Status.FALLBACK_SUCCEEDED
    usage_log.error_code = "provider_timeout"
    usage_log.save(update_fields=["status", "error_code", "updated_at"])

    assert AIUsageLog.objects.count() == 1
    usage_log.refresh_from_db()
    assert usage_log.status == AIUsageLog.Status.FALLBACK_SUCCEEDED
    assert usage_log.error_code == "provider_timeout"
