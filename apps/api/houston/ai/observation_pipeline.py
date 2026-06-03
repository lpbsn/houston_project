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
    modules = list(
        establishment.operational_modules.filter(active=True).values("key", "label").order_by("key")
    )
    domains = list(
        establishment.operational_domains.filter(active=True)
        .select_related("operational_module")
        .values("key", "label", "operational_module__key")
        .order_by("key")
    )
    subjects = list(
        establishment.operational_subjects.filter(active=True)
        .select_related("operational_domain")
        .values("key", "label", "operational_domain__key")
        .order_by("key")
    )
    units = list(
        establishment.operational_units.filter(active=True).values("key", "label").order_by("key")
    )
    media_count = observation.media_items.count()
    active_signals_context = _build_active_signals_context(establishment_id=establishment.id)

    return {
        "observation_id": str(observation.id),
        "establishment_id": str(establishment.id),
        "validated_text": observation.raw_text,
        "submitted_at": observation.submitted_at.isoformat(),
        "media_count": media_count,
        "taxonomy": {
            "modules": modules,
            "domains": domains,
            "subjects": subjects,
            "units": units,
        },
        "active_signals_context": active_signals_context,
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "prompt_version": AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    }


def _build_active_signals_context(*, establishment_id: uuid.UUID) -> list[dict[str, Any]]:
    signals = active_signals_for_establishment(establishment_id=establishment_id).order_by(
        "-last_activity_at",
        "-created_at",
    )[:MAX_ACTIVE_SIGNALS_CONTEXT]
    return [
        {
            "signal_id": str(signal.id),
            "status": signal.status,
            "title": signal.title,
            "structured_summary": signal.structured_summary,
            "operational_module_key": signal.operational_module.key,
            "operational_domain_key": signal.operational_domain.key,
            "operational_subject_key": signal.operational_subject.key,
            "operational_unit_key": (
                signal.operational_unit.key if signal.operational_unit_id else None
            ),
        }
        for signal in signals
    ]


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
- La taxonomie autorisée est dans "taxonomy" (modules, domains, subjects, units).
- Les signaux actifs éligibles à l'agrégation sont dans "active_signals_context"
  (max {MAX_ACTIVE_SIGNALS_CONTEXT}).
- Chaque clé opérationnelle doit exister dans ce snapshot.
  N'invente jamais de clé ni de libellé hors liste.
- Les images ne sont pas fournies ; "media_count" est informatif uniquement.

MISSION
Pour chaque problème opérationnel DISTINCT dans validated_text, produire un candidat.
Un même constat = un candidat. Plusieurs sujets distincts = plusieurs candidats
(max {MAX_CANDIDATES_PER_OBSERVATION}).
Ne fusionne jamais plusieurs problèmes différents en un seul candidat.

SEGMENTATION
Séparer les candidats si : lieux différents, domaines métiers différents, sujets différents,
ou problèmes indépendants (ex. "chambre 204 sale" ET "clim lobby en panne" → 2 candidats).

SPLITTING RULES
- Un candidat = une responsabilité opérationnelle distincte ou une cible de routage distincte.
- Séparer lorsque des équipes, domaines, sujets, lieux ou responsabilités opérationnelles diffèrent.
- Ne fusionne pas des problèmes distincts parce qu'ils apparaissent dans la même phrase ou le même
  rapport.
- Problèmes d'équipement/éclairage et ruptures de stock au bar sont des responsabilités séparées.
- Conserve les lieux partagés ou spécifiques dans title et structured_summary.
- operational_unit_key uniquement si l'unité existe dans le snapshot taxonomy fourni.
- Utilise uniquement les clés module/domain/subject du snapshot ; choisis la clé fournie la plus
  proche ; n'invente jamais de clé.
- Si une clé requise manque dans le snapshot, omets ou rejette ce candidat ; ne la fabrique pas.

EXEMPLE CONCEPTUEL (format uniquement — clés depuis le payload utilisateur)
Input: "The light is flickering at the restaurant entrance.
There is no mojito syrup left at the bar."
Expected: deux candidats — (1) lumière clignotante / entrée → clé maintenance/équipement la plus
proche fournie ; (2) sirop mojito en rupture / bar → clé stock/réassort bar la plus proche fournie.

CATÉGORISATION (obligatoire par candidat)
- operational_module_key : clé module dans taxonomy.modules
- operational_domain_key : clé domaine dans taxonomy.domains (cohérent avec le module)
- operational_subject_key : clé sujet dans taxonomy.subjects (cohérent avec le domaine)
- operational_unit_key : clé unit dans taxonomy.units si un lieu/unité métier connu s'applique ;
  sinon null. Pour "chambre 204", "table 12", "étage 3" : résumer dans structured_summary
  et n'utiliser operational_unit_key que si une unité catalogue correspond.

TEXTE DE SORTIE
- title : titre court orienté action (≤ 80 caractères), sans copier validated_text mot pour mot.
- structured_summary : 1–3 phrases factuelles, opérationnelles, sans citation longue du terrain ;
  inclure lieu précis si mentionné.
- location_text : lieu court libre pour l'affichage (ex. entrée restaurant, bar, chambre 104),
  ≤ 120 caractères, null si aucun lieu distinct ; jamais le texte complet de validated_text.
  Si operational_unit_key est renseigné, location_text est secondaire (affichage catalogue).

AGRÉGATION (optionnel)
- aggregate_into_signal_id : UUID d'un signal listé dans active_signals_context si le problème
  prolonge clairement une situation déjà ouverte ; sinon null.
- Ne jamais inventer d'UUID ni cibler un signal absent de active_signals_context.
- Ne jamais cibler un signal résolu, annulé ou archivé.

HORS PÉRIMÈTRE — NE PAS PRODUIRE
- urgence, priorité, sentiment, mots-clés, action corrective, type incident/idée
- tableaux detected_domains, scores de confiance, catégories en texte libre
- texte brut de l'observation recopié intégralement

SI RIEN N'EST ACTIONNABLE
- Retourner "candidates": [].

FORMAT DE RÉPONSE
Un seul objet JSON strict :
schema_version = "{AI_OBSERVATION_PIPELINE_SCHEMA_VERSION}"
candidates = tableau 0..{MAX_CANDIDATES_PER_OBSERVATION} avec title, structured_summary,
operational_module_key, operational_domain_key, operational_subject_key,
operational_unit_key, location_text, aggregate_into_signal_id.
Clés de premier niveau autorisées : schema_version, candidates uniquement.
Pas de markdown, pas de commentaire hors JSON.
"""


def _system_prompt() -> str:
    return _OBSERVATION_PIPELINE_SYSTEM_PROMPT


def _default_fake_payload(input_payload: dict[str, Any]) -> dict[str, Any]:
    taxonomy = input_payload.get("taxonomy") or {}
    subjects = taxonomy.get("subjects") or []
    modules = taxonomy.get("modules") or []
    if subjects:
        subject = subjects[0]
        domain_key = subject.get("operational_domain__key") or ""
        module_key = next(
            (module["key"] for module in modules if module.get("key")),
            "hotel",
        )
        return {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [
                {
                    "title": "Structured issue",
                    "structured_summary": "Validated structured summary for tests.",
                    "operational_module_key": module_key,
                    "operational_domain_key": domain_key or "hotel__hebergement",
                    "operational_subject_key": subject["key"],
                    "operational_unit_key": None,
                    "location_text": None,
                    "aggregate_into_signal_id": None,
                }
            ],
        }
    return {
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "candidates": [],
    }
