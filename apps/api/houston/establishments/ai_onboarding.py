from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from houston.ai.models import AIUsageLog
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    EstablishmentActivityDescription,
    OnboardingCatalogDomain,
    OnboardingCatalogModule,
    OnboardingCatalogUnit,
    OnboardingProposal,
    OnboardingSession,
)
from houston.establishments.services import (
    PROPOSAL_SCHEMA_VERSION,
    ActiveOnboardingProposalExistsError,
    InvalidActivityDescriptionError,
    OnboardingAccessDeniedError,
    OnboardingProposalValidationError,
    create_ai_onboarding_proposal,
    create_template_onboarding_proposal,
    validate_onboarding_proposal_payload,
)

logger = logging.getLogger(__name__)

AI_ONBOARDING_PROMPT_VERSION = "ai_onboarding_v1"
AI_ONBOARDING_DOMAIN = AIUsageLog.Domain.ONBOARDING


class AIOnboardingError(Exception):
    error_code = "ai_onboarding_error"


class AIOnboardingProviderUnavailableError(AIOnboardingError):
    error_code = "provider_unavailable"


class AIOnboardingProviderTimeoutError(AIOnboardingError):
    error_code = "provider_timeout"


class AIOnboardingInvalidOutputError(AIOnboardingError):
    error_code = "invalid_structured_output"


class AIOnboardingFallbackFailedError(AIOnboardingError):
    error_code = "fallback_failed"


@dataclass(frozen=True)
class AIOnboardingProviderResponse:
    payload: dict
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    model: str = ""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _CatalogItem(_StrictModel):
    key: str
    label: str
    reason: str
    confidence_score: float | None


class _DomainOrUnitItem(_CatalogItem):
    related_modules: list[str]


class _VocabularyItem(_StrictModel):
    term: str
    meaning: str
    mapped_domain_key: str | None = None
    mapped_unit_key: str | None = None
    reason: str


class _RuntimeTagItem(_StrictModel):
    key: str
    label: str
    related_domain_keys: list[str]
    reason: str


class _RoutingHintItem(_StrictModel):
    pattern: str
    suggested_domain_keys: list[str]
    suggested_unit_key: str | None = None
    reason: str
    confidence_score: float | None


class _AIOnboardingOutput(_StrictModel):
    schema_version: str
    operational_modules: list[_CatalogItem]
    operational_domains: list[_DomainOrUnitItem]
    operational_units: list[_DomainOrUnitItem]
    runtime_vocabulary: list[_VocabularyItem]
    runtime_tags: list[_RuntimeTagItem]
    routing_hints: list[_RoutingHintItem]


class OpenAIOnboardingProvider:
    provider = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
    ):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model = model or settings.HOUSTON_AI_ONBOARDING_MODEL
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.HOUSTON_AI_ONBOARDING_TIMEOUT_SECONDS
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else settings.HOUSTON_AI_ONBOARDING_MAX_RETRIES
        )

    def generate(self, input_payload: dict) -> AIOnboardingProviderResponse:
        if not self.api_key:
            raise AIOnboardingProviderUnavailableError("OpenAI API key is not configured.")

        try:
            from openai import APIConnectionError, APITimeoutError, OpenAI
        except ImportError as exc:
            raise AIOnboardingProviderUnavailableError("OpenAI SDK is not installed.") from exc

        try:
            client = OpenAI(
                api_key=self.api_key,
                timeout=self.timeout_seconds,
                max_retries=self.max_retries,
            )
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": _system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(input_payload, ensure_ascii=False),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        except APITimeoutError as exc:
            raise AIOnboardingProviderTimeoutError("OpenAI request timed out.") from exc
        except APIConnectionError as exc:
            raise AIOnboardingProviderUnavailableError("OpenAI is unavailable.") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise AIOnboardingInvalidOutputError("OpenAI returned an empty response.")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIOnboardingInvalidOutputError("OpenAI returned invalid JSON.") from exc

        usage = getattr(response, "usage", None)
        return AIOnboardingProviderResponse(
            payload=payload,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            model=self.model,
        )


def build_ai_onboarding_input(
    *,
    session: OnboardingSession,
    locale: str = "en-US",
) -> dict:
    description = _get_valid_activity_description(session)

    return {
        "establishment_name": session.establishment.name,
        "activity_description": description.description,
        "active_module_catalog": _active_catalog_payload(OnboardingCatalogModule),
        "active_domain_catalog": _active_catalog_payload(OnboardingCatalogDomain),
        "active_unit_catalog": _active_catalog_payload(OnboardingCatalogUnit),
        "locale": locale,
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "prompt_version": AI_ONBOARDING_PROMPT_VERSION,
    }


def run_ai_onboarding_interpretation(
    *,
    session: OnboardingSession,
    actor,
    locale: str = "en-US",
    provider: Any | None = None,
) -> OnboardingProposal:
    session = _reload_session(session)
    _ensure_no_open_proposal(session)
    _ensure_can_run_ai_onboarding(session=session, actor=actor)

    input_payload = build_ai_onboarding_input(session=session, locale=locale)
    provider = provider or OpenAIOnboardingProvider()
    provider_name = getattr(provider, "provider", settings.HOUSTON_AI_ONBOARDING_PROVIDER)
    provider_model = getattr(provider, "model", settings.HOUSTON_AI_ONBOARDING_MODEL)
    correlation_id = uuid.uuid4()
    started_at = time.monotonic()
    response: AIOnboardingProviderResponse | None = None

    try:
        response = provider.generate(input_payload)
        sanitized_payload = validate_ai_onboarding_output(response.payload)
        proposal = create_ai_onboarding_proposal(
            session=session,
            actor=actor,
            payload=sanitized_payload,
        )
        _write_usage_log(
            session=session,
            proposal=proposal,
            provider=provider_name,
            model=response.model or provider_model,
            status=AIUsageLog.Status.SUCCEEDED,
            latency_ms=_elapsed_ms(started_at),
            token_response=response,
            error_code="",
            correlation_id=correlation_id,
        )
        _set_session_last_error(session=session, error_code="")
        return proposal
    except Exception as exc:
        error_code = _error_code(exc)
        try:
            proposal = fallback_to_template_proposal(session=session, actor=actor)
        except Exception as fallback_exc:
            _write_usage_log(
                session=session,
                proposal=None,
                provider=provider_name,
                model=(response.model if response is not None else provider_model),
                status=AIUsageLog.Status.FALLBACK_FAILED,
                latency_ms=_elapsed_ms(started_at),
                token_response=response,
                error_code=error_code,
                correlation_id=correlation_id,
            )
            _set_session_last_error(
                session=session,
                error_code=AIOnboardingFallbackFailedError.error_code,
            )
            raise AIOnboardingFallbackFailedError(str(fallback_exc)) from fallback_exc

        _write_usage_log(
            session=session,
            proposal=proposal,
            provider=provider_name,
            model=(response.model if response is not None else provider_model),
            status=AIUsageLog.Status.FALLBACK_SUCCEEDED,
            latency_ms=_elapsed_ms(started_at),
            token_response=response,
            error_code=error_code,
            correlation_id=correlation_id,
        )
        _set_session_last_error(session=session, error_code=error_code)
        return proposal


def validate_ai_onboarding_output(raw_output: dict) -> dict:
    try:
        output = _AIOnboardingOutput.model_validate(raw_output)
    except PydanticValidationError as exc:
        raise AIOnboardingInvalidOutputError("AI output did not match schema.") from exc

    return validate_onboarding_proposal_payload(output.model_dump(mode="json"))


def fallback_to_template_proposal(
    *,
    session: OnboardingSession,
    actor,
) -> OnboardingProposal:
    payload = _fallback_template_payload()
    return create_template_onboarding_proposal(
        session=session,
        actor=actor,
        payload=payload,
    )


def _system_prompt() -> str:
    return (
        "You generate Houston onboarding runtime proposals. Return one JSON object only. "
        "Use only catalog keys supplied in the input for modules, domains, and units. "
        "Never include roles, memberships, billing, checklists, signal examples, "
        "observations, signals, actions, comments, permissions, personal data, emails, "
        "phone numbers, or exact addresses. The JSON must match schema_version "
        f"{PROPOSAL_SCHEMA_VERSION} and contain only operational_modules, "
        "operational_domains, operational_units, runtime_vocabulary, runtime_tags, "
        "and routing_hints."
    )


def _get_valid_activity_description(
    session: OnboardingSession,
) -> EstablishmentActivityDescription:
    description = (
        EstablishmentActivityDescription.objects.filter(establishment=session.establishment)
        .select_related("establishment")
        .first()
    )
    if description is None or description.validated_at is None:
        raise InvalidActivityDescriptionError("A validated activity description is required.")
    if len((description.description or "").strip()) < ACTIVITY_DESCRIPTION_MIN_LENGTH:
        raise InvalidActivityDescriptionError(
            f"Activity description must be at least {ACTIVITY_DESCRIPTION_MIN_LENGTH} characters."
        )
    return description


def _active_catalog_payload(model_class) -> list[dict]:
    return [
        {
            "key": item.key,
            "label": item.label,
            "description": item.description,
        }
        for item in model_class.objects.filter(active=True).order_by("sort_order", "key")
    ]


def _fallback_template_payload() -> dict:
    modules = list(
        OnboardingCatalogModule.objects.filter(active=True).order_by("sort_order", "key")
    )
    domains = list(
        OnboardingCatalogDomain.objects.filter(active=True).order_by("sort_order", "key")
    )
    if not modules or len(domains) < 3:
        raise OnboardingProposalValidationError(
            [
                {
                    "code": "insufficient_active_catalog",
                    "section": "operational_domains",
                }
            ]
        )

    module = modules[0]
    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "operational_modules": [
            {
                "key": module.key,
                "label": module.label,
                "reason": "Default onboarding template fallback.",
                "confidence_score": None,
            }
        ],
        "operational_domains": [
            {
                "key": domain.key,
                "label": domain.label,
                "related_modules": [module.key],
                "reason": "Default onboarding template fallback.",
                "confidence_score": None,
            }
            for domain in domains[:3]
        ],
        "operational_units": [],
        "runtime_vocabulary": [],
        "runtime_tags": [],
        "routing_hints": [],
    }


def _ensure_no_open_proposal(session: OnboardingSession) -> None:
    if OnboardingProposal.objects.filter(
        onboarding_session=session,
        status__in=OnboardingProposal.NON_TERMINAL_STATUSES,
    ).exists():
        raise ActiveOnboardingProposalExistsError(
            "A non-terminal onboarding proposal already exists for this session."
        )


def _ensure_can_run_ai_onboarding(*, session: OnboardingSession, actor) -> None:
    from houston.establishments.access import get_onboarding_access_context

    access = get_onboarding_access_context(actor=actor, session=session)
    if not access.can_configure_runtime:
        raise OnboardingAccessDeniedError


def _reload_session(session: OnboardingSession) -> OnboardingSession:
    return OnboardingSession.objects.select_related(
        "organization",
        "establishment",
        "establishment__organization",
    ).get(id=session.id)


def _write_usage_log(
    *,
    session: OnboardingSession,
    proposal: OnboardingProposal | None,
    provider: str,
    model: str,
    status: str,
    latency_ms: int,
    token_response: AIOnboardingProviderResponse | None,
    error_code: str,
    correlation_id: uuid.UUID,
) -> None:
    try:
        AIUsageLog.objects.create(
            ai_domain=AIUsageLog.Domain.ONBOARDING,
            provider=provider,
            model=model,
            prompt_version=AI_ONBOARDING_PROMPT_VERSION,
            schema_version=PROPOSAL_SCHEMA_VERSION,
            status=status,
            latency_ms=latency_ms,
            input_tokens=None if token_response is None else token_response.input_tokens,
            output_tokens=None if token_response is None else token_response.output_tokens,
            total_tokens=None if token_response is None else token_response.total_tokens,
            error_code=error_code,
            correlation_id=correlation_id,
            establishment=session.establishment,
            onboarding_session=session,
            onboarding_proposal=proposal,
        )
    except Exception:
        logger.warning(
            "Failed to write AI usage log.",
            extra={
                "ai_domain": AIUsageLog.Domain.ONBOARDING,
                "provider": provider,
                "status": status,
                "error_code": "ai_usage_log_failed",
            },
            exc_info=True,
        )


def _set_session_last_error(*, session: OnboardingSession, error_code: str) -> None:
    OnboardingSession.objects.filter(id=session.id).update(last_error_code=error_code)


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((time.monotonic() - started_at) * 1000))


def _error_code(exc: Exception) -> str:
    if isinstance(exc, AIOnboardingError):
        return exc.error_code
    if isinstance(exc, InvalidActivityDescriptionError):
        return "invalid_activity_description"
    if isinstance(exc, OnboardingProposalValidationError):
        return "invalid_ai_proposal_payload"
    return "ai_onboarding_error"
