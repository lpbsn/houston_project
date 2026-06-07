from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings
from pydantic import ValidationError as PydanticValidationError

from houston.ai.models import AIUsageLog
from houston.ai.observation_pipeline_diagnostics import (
    build_invalid_output_error_context,
    build_provider_bad_request_error_context,
)
from houston.ai.observation_pipeline_provider_schema import openai_strict_response_format
from houston.ai.observation_pipeline_schema import ObservationPipelineOutput
from houston.establishments.taxonomy_snapshot import (
    build_establishment_taxonomy_snapshot,
    establishment_has_active_business_units,
)
from houston.observations.models import Observation
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    MAX_ACTIVE_SIGNALS_CONTEXT,
    MAX_CANDIDATES_PER_OBSERVATION,
)
from houston.signals.selectors import active_signals_for_establishment

logger = logging.getLogger(__name__)

AI_OBSERVATION_PIPELINE_DOMAIN = "observation_pipeline"
RESPONSE_FORMAT_JSON_SCHEMA_STRICT = "json_schema_strict"


class ObservationPipelineError(Exception):
    error_code = "observation_pipeline_error"


class ObservationPipelineUnavailableError(ObservationPipelineError):
    error_code = "provider_unavailable"


class ObservationPipelineTimeoutError(ObservationPipelineError):
    error_code = "provider_timeout"


class ObservationPipelineInvalidOutputError(ObservationPipelineError):
    error_code = "invalid_structured_output"

    def __init__(self, message: str, *, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}


class ObservationPipelineSchemaError(ObservationPipelineError):
    error_code = "invalid_response_schema"


class ObservationPipelineProviderBadRequestError(ObservationPipelineError):
    error_code = "provider_bad_request"


class ObservationPipelineSkippedError(ObservationPipelineError):
    """Establishment has no active business units — pipeline skips AI call."""

    error_code = "no_active_business_units"


@dataclass(frozen=True)
class ObservationPipelineProviderResponse:
    payload: dict[str, Any]
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    model: str = ""
    provider_request_id: str = ""


class ObservationPipelineProvider(Protocol):
    provider: str

    def propose(self, *, input_payload: dict[str, Any]) -> ObservationPipelineProviderResponse: ...


def build_pipeline_input(*, observation: Observation) -> dict[str, Any]:
    establishment = observation.establishment
    establishment_taxonomy = build_establishment_taxonomy_snapshot(
        establishment_id=establishment.id,
    )
    media_count = observation.media_items.count()
    active_signals_context = _build_active_signals_context(establishment_id=establishment.id)

    return {
        "observation_id": str(observation.id),
        "establishment_id": str(establishment.id),
        "validated_text": observation.raw_text,
        "submitted_at": observation.submitted_at.isoformat(),
        "media_count": media_count,
        "establishment_taxonomy": establishment_taxonomy,
        "active_signals_context": active_signals_context,
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "prompt_version": AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    }


def establishment_can_run_observation_pipeline(*, establishment_id: uuid.UUID) -> bool:
    return establishment_has_active_business_units(establishment_id=establishment_id)


def _build_active_signals_context(*, establishment_id: uuid.UUID) -> list[dict[str, Any]]:
    signals = active_signals_for_establishment(establishment_id=establishment_id).order_by(
        "-last_activity_at",
        "-created_at",
    )[:MAX_ACTIVE_SIGNALS_CONTEXT]
    entries: list[dict[str, Any]] = []
    for signal in signals:
        if (
            signal.affected_business_unit_id is None
            or signal.responsible_business_unit_id is None
            or signal.activity_subject_id is None
        ):
            continue
        entries.append(
            {
                "signal_id": str(signal.id),
                "status": signal.status,
                "title": signal.title,
                "structured_summary": signal.structured_summary,
                "affected_business_unit_key": signal.affected_business_unit.key,
                "responsible_business_unit_key": signal.responsible_business_unit.key,
                "activity_subject_key": signal.activity_subject.normalized_name,
                "operational_unit_key": (
                    signal.operational_unit.key if signal.operational_unit_id else None
                ),
                "location_text": signal.location_text or None,
            }
        )
    return entries


def parse_pipeline_output(payload: dict[str, Any]) -> ObservationPipelineOutput:
    try:
        return ObservationPipelineOutput.model_validate(payload)
    except PydanticValidationError as exc:
        raise ObservationPipelineInvalidOutputError(
            "Structured output failed validation.",
            payload=payload,
        ) from exc


class OpenAIObservationPipelineProvider:
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
        self.model = model or settings.HOUSTON_AI_OBSERVATION_MODEL
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS
        )
        self.max_retries = (
            max_retries if max_retries is not None else settings.HOUSTON_AI_OBSERVATION_MAX_RETRIES
        )
        self.last_provider_request_id = ""
        self.last_response_format_mode = RESPONSE_FORMAT_JSON_SCHEMA_STRICT

    def propose(self, *, input_payload: dict[str, Any]) -> ObservationPipelineProviderResponse:
        if not self.api_key:
            raise ObservationPipelineUnavailableError("OpenAI API key is not configured.")

        try:
            from openai import APIConnectionError, APITimeoutError, BadRequestError, OpenAI
        except ImportError as exc:
            raise ObservationPipelineUnavailableError("OpenAI SDK is not installed.") from exc

        client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )
        messages = [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": json.dumps(input_payload, ensure_ascii=False)},
        ]

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format=openai_strict_response_format(),
                temperature=0.2,
            )
        except APITimeoutError as exc:
            raise ObservationPipelineTimeoutError("OpenAI request timed out.") from exc
        except APIConnectionError as exc:
            raise ObservationPipelineUnavailableError("OpenAI is unavailable.") from exc
        except BadRequestError as exc:
            if _is_invalid_response_format_schema_error(exc):
                raise ObservationPipelineSchemaError(
                    "OpenAI rejected the observation pipeline response schema.",
                ) from exc
            raise ObservationPipelineProviderBadRequestError(
                "OpenAI rejected the observation pipeline request.",
            ) from exc

        self.last_provider_request_id = getattr(response, "id", "") or ""
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ObservationPipelineInvalidOutputError("OpenAI returned an empty response.")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ObservationPipelineInvalidOutputError("OpenAI returned invalid JSON.") from exc

        usage = getattr(response, "usage", None)
        return ObservationPipelineProviderResponse(
            payload=payload,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            model=self.model,
            provider_request_id=self.last_provider_request_id,
        )


class FakeObservationPipelineProvider:
    provider = "fake"

    def __init__(
        self,
        *,
        payload: dict[str, Any] | None = None,
        exc: Exception | None = None,
    ):
        self._payload = payload
        self._exc = exc

    def propose(self, *, input_payload: dict[str, Any]) -> ObservationPipelineProviderResponse:
        if self._exc is not None:
            raise self._exc
        if self._payload is not None:
            payload = self._payload
        else:
            payload = _default_fake_payload(input_payload)
        return ObservationPipelineProviderResponse(payload=payload, model="fake")


def get_observation_pipeline_provider() -> ObservationPipelineProvider:
    provider_name = settings.HOUSTON_AI_OBSERVATION_PROVIDER.strip().lower()
    if provider_name == "fake":
        return FakeObservationPipelineProvider()
    if provider_name == "openai":
        return OpenAIObservationPipelineProvider()
    raise ObservationPipelineUnavailableError(
        f"Unknown observation pipeline provider: {provider_name!r}"
    )


def call_observation_pipeline(
    *,
    observation: Observation,
    provider: ObservationPipelineProvider | None = None,
    correlation_id: uuid.UUID | None = None,
) -> ObservationPipelineOutput:
    correlation_id = correlation_id or uuid.uuid4()
    if not establishment_can_run_observation_pipeline(
        establishment_id=observation.establishment_id,
    ):
        raise ObservationPipelineSkippedError(
            "Establishment has no active business units for pipeline routing."
        )

    provider = provider or get_observation_pipeline_provider()
    input_payload = build_pipeline_input(observation=observation)
    started_at = time.monotonic()

    try:
        response = provider.propose(input_payload=input_payload)
        output = parse_pipeline_output(response.payload)
        _write_usage_log(
            observation=observation,
            provider=provider.provider,
            model=response.model or getattr(provider, "model", ""),
            status=AIUsageLog.Status.SUCCEEDED,
            latency_ms=_elapsed_ms(started_at),
            correlation_id=correlation_id,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
        )
        return output
    except ObservationPipelineTimeoutError as exc:
        _write_usage_log(
            observation=observation,
            provider=provider.provider,
            model=getattr(provider, "model", ""),
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(started_at),
            error_code=exc.error_code,
            correlation_id=correlation_id,
        )
        raise
    except ObservationPipelineUnavailableError as exc:
        _write_usage_log(
            observation=observation,
            provider=provider.provider,
            model=getattr(provider, "model", ""),
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(started_at),
            error_code=exc.error_code,
            correlation_id=correlation_id,
        )
        raise
    except ObservationPipelineInvalidOutputError as exc:
        error_context = build_invalid_output_error_context(
            payload=exc.payload,
            exc=exc,
            provider_request_id=getattr(provider, "last_provider_request_id", ""),
            response_format_mode=getattr(
                provider,
                "last_response_format_mode",
                RESPONSE_FORMAT_JSON_SCHEMA_STRICT,
            ),
        )
        _write_usage_log(
            observation=observation,
            provider=provider.provider,
            model=getattr(provider, "model", ""),
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(started_at),
            error_code=exc.error_code,
            error_context=error_context,
            correlation_id=correlation_id,
        )
        raise
    except (
        ObservationPipelineSchemaError,
        ObservationPipelineProviderBadRequestError,
    ) as exc:
        error_context = build_provider_bad_request_error_context(
            exc=exc.__cause__ if exc.__cause__ is not None else exc,
            response_format_mode=getattr(
                provider,
                "last_response_format_mode",
                RESPONSE_FORMAT_JSON_SCHEMA_STRICT,
            ),
        )
        _write_usage_log(
            observation=observation,
            provider=provider.provider,
            model=getattr(provider, "model", ""),
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(started_at),
            error_code=exc.error_code,
            error_context=error_context,
            correlation_id=correlation_id,
        )
        raise


def _write_usage_log(
    *,
    observation: Observation,
    provider: str,
    model: str,
    status: str,
    latency_ms: int,
    correlation_id: uuid.UUID,
    error_code: str = "",
    error_context: dict[str, Any] | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
) -> None:
    AIUsageLog.objects.create(
        ai_domain=AIUsageLog.Domain.OBSERVATION_PIPELINE,
        provider=provider,
        model=model or "",
        prompt_version=AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        error_code=error_code,
        error_context=error_context or {},
        correlation_id=correlation_id,
        establishment=observation.establishment,
        observation=observation,
    )


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _is_invalid_response_format_schema_error(exc: BaseException) -> bool:
    if getattr(exc, "param", None) == "response_format":
        return True
    message = str(exc)
    return "Invalid schema" in message


_OBSERVATION_PIPELINE_SYSTEM_PROMPT = f"""\
Tu es un analyste qualité opérationnel pour un établissement (hôtel, restaurant, commerce).
Tu structures des remontées terrain en propositions CandidateSignal pour Houston.

CONTEXTE
- Le message utilisateur est un JSON. Le texte à analyser est dans "validated_text".
- La taxonomie autorisée est dans "establishment_taxonomy.business_units" avec :
  key, label, unit_type (dedicated ou transversal), description, activity_subjects[].
- Chaque activity_subject a key (= normalized_name), label, description.
- Les unités de lieu structurées sont dans establishment_taxonomy.operational_units.
- Les signaux actifs éligibles à l'agrégation sont dans "active_signals_context"
  (max {MAX_ACTIVE_SIGNALS_CONTEXT}) avec affected/responsible/activity_subject keys.
- Chaque clé doit exister dans ce snapshot runtime. N'invente jamais de clé.
- Les descriptions des pôles aident à distinguer périmètres et responsabilités.
- Les images ne sont pas fournies ; "media_count" est informatif uniquement.

ROUTAGE — LIEU VS NATURE DU PROBLÈME
- affected_business_unit_key : où le problème est observé (lieu, espace, pôle impacté).
- responsible_business_unit_key : qui doit traiter (nature opérationnelle du problème).
- activity_subject_key : sujet sous responsible_business_unit (normalized_name exact).
- location_text : contexte libre ou localisation précise (chambre 104, restaurant, bar).
- Ne route pas vers un pôle dedicated uniquement parce que son nom apparaît dans le texte
  si la nature du problème relève d'un pôle transversal du snapshot.

PRIORITÉ TRANSVERSALE
- Si un BusinessUnit unit_type=transversal possède un activity_subject correspondant
  au problème, responsible = ce transversal (même si le lieu mentionne un dedicated).
- Exemple : "Lumière HS au restaurant" → affected=restaurant, responsible=maintenance
  (transversal) si maintenance possède électricité/éclairage dans le snapshot.

FALLBACK DEDICATED
- Si aucun pôle transversal pertinent n'existe pour la nature du problème,
  responsible = affected et activity_subject sous affected.

MISSION
Pour chaque problème opérationnel DISTINCT, produire un candidat
(max {MAX_CANDIDATES_PER_OBSERVATION}).
Ne fusionne jamais plusieurs problèmes différents en un seul candidat.

SEGMENTATION
Séparer si lieux, pôles impactés, responsables, sujets ou problèmes diffèrent.

TEXTE DE SORTIE
- title : titre court orienté action (≤ 80 caractères).
- structured_summary : 1–3 phrases factuelles ; inclure lieu précis si mentionné.
- location_text : lieu court libre (≤ 120 caractères), null si aucun lieu distinct ;
  jamais le texte complet de validated_text.

AGRÉGATION (optionnel)
- aggregate_into_signal_id : UUID d'un signal dans active_signals_context si le problème
  prolonge clairement une situation ouverte ; sinon null.

HORS PÉRIMÈTRE
- urgence, priorité, detected_domains[], scores de confiance
- clés operational_module/domain/subject (legacy)

SI RIEN N'EST ACTIONNABLE
- Retourner "candidates": [].

FORMAT DE RÉPONSE
Un seul objet JSON strict :
schema_version = "{AI_OBSERVATION_PIPELINE_SCHEMA_VERSION}"
candidates[] avec title, structured_summary, affected_business_unit_key,
responsible_business_unit_key, activity_subject_key, operational_unit_key,
location_text, aggregate_into_signal_id.
"""


def _system_prompt() -> str:
    return _OBSERVATION_PIPELINE_SYSTEM_PROMPT


def _default_fake_payload(input_payload: dict[str, Any]) -> dict[str, Any]:
    taxonomy = input_payload.get("establishment_taxonomy") or {}
    business_units = taxonomy.get("business_units") or []
    if not business_units:
        return {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [],
        }
    unit = business_units[0]
    subjects = unit.get("activity_subjects") or []
    if not subjects:
        return {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [],
        }
    subject = subjects[0]
    return {
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "candidates": [
            {
                "title": "Structured issue",
                "structured_summary": "Validated structured summary for tests.",
                "affected_business_unit_key": unit["key"],
                "responsible_business_unit_key": unit["key"],
                "activity_subject_key": subject["key"],
                "operational_unit_key": None,
                "location_text": None,
                "aggregate_into_signal_id": None,
            }
        ],
    }
