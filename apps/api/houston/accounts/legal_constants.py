from __future__ import annotations

CURRENT_TERMS_VERSION = "cgu-v1"
CURRENT_AI_CONSENT_VERSION = "openai-v1"

TERMS_ACCEPTANCE_REQUIRED_CODE = "terms_acceptance_required"
TERMS_ACCEPTANCE_REQUIRED_DETAIL = (
    "Accept the terms of use before publishing content visible to other members."
)
AI_CONSENT_REQUIRED_CODE = "ai_consent_required"
AI_CONSENT_REQUIRED_DETAIL = (
    "Consent to OpenAI processing is required before transcription, observation analysis, "
    "or analytics pattern classification."
)
INVALID_TERMS_VERSION_CODE = "invalid_terms_version"
INVALID_AI_CONSENT_VERSION_CODE = "invalid_ai_consent_version"

# openai-v1 scope (source of truth for disclosure copy):
# - observation text to OpenAI for the signal pipeline
# - request-scoped audio to OpenAI for transcription (not stored)
# - structured signal title / summary / issue_focus to OpenAI for analytics pattern
#   classification (and duplicate-guard follow-up)
# - photos and chat are not sent
AI_CONSENT_SCOPE_V1 = (
    "observation_text_pipeline",
    "transcription_audio",
    "analytics_signal_pattern",
)
