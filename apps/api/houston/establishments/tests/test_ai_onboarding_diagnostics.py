from __future__ import annotations

import json

from pydantic import ValidationError as PydanticValidationError

from houston.establishments.ai_onboarding import AIOnboardingInvalidOutputError
from houston.establishments.ai_onboarding_diagnostics import (
    sanitize_error_context,
    summarize_ai_onboarding_failure,
)
from houston.establishments.services import OnboardingProposalValidationError


def test_summarize_pydantic_failure_without_sensitive_payload():
    try:
        raise PydanticValidationError.from_exception_data(
            "AIOnboardingOutput",
            [
                {
                    "type": "missing",
                    "loc": ("runtime_vocabulary",),
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "extra_forbidden",
                    "loc": ("outcome",),
                    "msg": "Extra inputs are not permitted",
                    "input": "proposal_generated",
                },
            ],
        )
    except PydanticValidationError as exc:
        wrapped = AIOnboardingInvalidOutputError("AI output did not match schema.")
        wrapped.__cause__ = exc
        summary = summarize_ai_onboarding_failure(wrapped)

    assert summary["failure_stage"] == "pydantic"
    assert summary["validation_error_count"] == 2
    assert "runtime_vocabulary" in summary["missing_fields"]
    assert "/outcome" in summary["invalid_field_paths"]
    assert "extra_forbidden" in summary["pydantic_error_types"]
    serialized = json.dumps(summary)
    assert "Hotel with restaurant" not in serialized
    assert "operational_modules" not in serialized


def test_summarize_business_validation_failure_uses_stable_codes():
    exc = OnboardingProposalValidationError(
        [
            {
                "code": "unknown_catalog_key",
                "section": "operational_modules",
                "key": "hospitality",
            },
            {
                "code": "invalid_mapped_domain_key",
                "section": "runtime_vocabulary",
                "field": "mapped_domain_key",
            },
        ]
    )

    summary = summarize_ai_onboarding_failure(exc)

    assert summary["failure_stage"] == "business_validation"
    assert summary["validation_error_count"] == 2
    assert "unknown_catalog_key" in summary["business_error_codes"]
    assert "invalid_mapped_domain_key" in summary["business_error_codes"]
    serialized = json.dumps(summary)
    assert "hospitality" not in serialized


def test_sanitize_error_context_rejects_disallowed_keys_and_sensitive_values():
    context = sanitize_error_context(
        {
            "failure_stage": "pydantic",
            "activity_description": "Hotel with restaurant",
            "prompt": "secret system text",
            "invalid_field_paths": ["/operational_modules/0/key"],
            "unexpected": "value",
        }
    )

    assert context["failure_stage"] == "pydantic"
    assert "activity_description" not in context
    assert "prompt" not in context
    assert "unexpected" not in context
    assert context["invalid_field_paths"] == ["/operational_modules/0/key"]
