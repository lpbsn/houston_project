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
from houston.core.observability import build_observation_pipeline_timing_log_context
from houston.establishments.models import BusinessUnit, MembershipScope
from houston.establishments.taxonomy_snapshot import (
    build_establishment_context,
    build_routing_taxonomy,
    establishment_has_any_active_business_unit,
    get_active_establishment_for_pipeline,
    routing_taxonomy_business_unit_keys,
)
from houston.observations.models import Observation
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    MAX_CANDIDATES_PER_OBSERVATION,
)

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


PRECONDITION_INVALID_ESTABLISHMENT = "precondition_invalid_establishment"
PRECONDITION_NO_ACTIVE_BUSINESS_UNIT = "precondition_no_active_business_unit"


class ObservationPipelineSkippedError(ObservationPipelineError):
    """Terminal pipeline precondition failure — no provider call, no Signal/Candidate."""

    error_code = "observation_pipeline_precondition_failed"

    def __init__(self, message: str, *, error_code: str):
        super().__init__(message)
        self.error_code = error_code


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


def _build_author_scope_routing_keys(
    *,
    observation: Observation,
    routable_keys: set[str],
) -> list[str]:
    membership = observation.submitted_by_membership
    if membership is None:
        return []
    keys: set[str] = set()
    scopes = MembershipScope.objects.filter(membership_id=membership.id).select_related(
        "business_unit",
    )
    for scope in scopes:
        business_unit = scope.business_unit
        if business_unit is None or not business_unit.routing_key:
            continue
        if business_unit.routing_key in routable_keys:
            keys.add(business_unit.routing_key)
    return sorted(keys)


def _resolve_action_plan_business_unit_context(
    *,
    task_business_unit: BusinessUnit | None,
    pilot_business_unit: BusinessUnit | None,
    routable_keys: set[str],
) -> tuple[str | None, str | None, str | None]:
    """
    Return (routing_key, specific_name, source).

    task preferred when routable; pilot when task missing/non-routable and pilot routable;
    BU present but none routable → key null, keep priority name+source;
    no task nor pilot BU → all null.
    """
    task_routable = (
        task_business_unit is not None
        and bool(task_business_unit.routing_key)
        and task_business_unit.routing_key in routable_keys
    )
    pilot_routable = (
        pilot_business_unit is not None
        and bool(pilot_business_unit.routing_key)
        and pilot_business_unit.routing_key in routable_keys
    )

    if task_routable:
        assert task_business_unit is not None
        return task_business_unit.routing_key, task_business_unit.specific_name, "task"
    if pilot_routable:
        assert pilot_business_unit is not None
        return pilot_business_unit.routing_key, pilot_business_unit.specific_name, "pilot"
    if task_business_unit is not None:
        return None, task_business_unit.specific_name, "task"
    if pilot_business_unit is not None:
        return None, pilot_business_unit.specific_name, "pilot"
    return None, None, None


def _build_action_plan_context(
    *,
    observation: Observation,
    routable_keys: set[str],
) -> dict[str, Any] | None:
    if observation.origin != Observation.Origin.ACTION_PLAN_TASK:
        return None
    if (
        observation.action_plan_execution_id is None
        or observation.action_plan_execution_task_id is None
    ):
        return None

    execution = observation.action_plan_execution
    task_execution = observation.action_plan_execution_task
    task_business_unit = None
    if task_execution.execution_team_id is not None:
        task_business_unit = task_execution.execution_team.business_unit
    pilot_business_unit = (
        execution.pilot_business_unit if execution.pilot_business_unit_id is not None else None
    )
    routing_key, specific_name, source = _resolve_action_plan_business_unit_context(
        task_business_unit=task_business_unit,
        pilot_business_unit=pilot_business_unit,
        routable_keys=routable_keys,
    )

    return {
        "origin": Observation.Origin.ACTION_PLAN_TASK,
        "action_plan_execution_id": str(execution.id),
        "action_plan_execution_task_id": str(task_execution.id),
        "plan_title": execution.title,
        "task": task_execution.task,
        "business_unit_routing_key": routing_key,
        "context_business_unit_source": source,
        "business_unit_specific_name": specific_name,
    }


def build_pipeline_input(*, observation: Observation) -> dict[str, Any]:
    observation = Observation.objects.select_related(
        "establishment",
        "submitted_by_membership",
        "action_plan_execution",
        "action_plan_execution__pilot_business_unit",
        "action_plan_execution__pilot_business_unit__catalog_business_unit",
        "action_plan_execution_task",
        "action_plan_execution_task__execution_team",
        "action_plan_execution_task__execution_team__business_unit",
        "action_plan_execution_task__execution_team__business_unit__catalog_business_unit",
    ).get(pk=observation.pk)
    establishment = observation.establishment
    establishment_context = build_establishment_context(establishment_id=establishment.id)
    routing_taxonomy = build_routing_taxonomy(establishment_id=establishment.id)
    routable_keys = routing_taxonomy_business_unit_keys(routing_taxonomy=routing_taxonomy)
    media_count = observation.media_items.count()
    action_plan_context = _build_action_plan_context(
        observation=observation,
        routable_keys=routable_keys,
    )

    payload: dict[str, Any] = {
        "observation_id": str(observation.id),
        "establishment_id": str(establishment.id),
        "validated_text": observation.raw_text,
        "submitted_at": observation.submitted_at.isoformat(),
        "media_count": media_count,
        "establishment_context": establishment_context,
        "routing_taxonomy": routing_taxonomy,
        "submission_context": {
            "author_scope_business_unit_routing_keys": _build_author_scope_routing_keys(
                observation=observation,
                routable_keys=routable_keys,
            ),
        },
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "prompt_version": AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    }
    if action_plan_context is not None:
        payload["action_plan_context"] = action_plan_context
    return payload


def evaluate_observation_pipeline_precondition(*, establishment_id: uuid.UUID) -> None:
    """
    Raise ObservationPipelineSkippedError when the establishment cannot start the pipeline.

    Order: invalid/non-ACTIVE establishment first, then zero active BusinessUnits.
    Does not consult snapshot-ready / routing taxonomy.
    """
    if get_active_establishment_for_pipeline(establishment_id) is None:
        raise ObservationPipelineSkippedError(
            "Establishment is missing or not ACTIVE for observation pipeline.",
            error_code=PRECONDITION_INVALID_ESTABLISHMENT,
        )
    if not establishment_has_any_active_business_unit(establishment_id=establishment_id):
        raise ObservationPipelineSkippedError(
            "Establishment has no active business units for observation pipeline.",
            error_code=PRECONDITION_NO_ACTIVE_BUSINESS_UNIT,
        )


def establishment_can_run_observation_pipeline(*, establishment_id: uuid.UUID) -> bool:
    try:
        evaluate_observation_pipeline_precondition(establishment_id=establishment_id)
    except ObservationPipelineSkippedError:
        return False
    return True


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
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ObservationPipelineUnavailableError("OpenAI SDK is not installed.") from exc
        self._client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )
        return self._client

    def propose(self, *, input_payload: dict[str, Any]) -> ObservationPipelineProviderResponse:
        if not self.api_key:
            raise ObservationPipelineUnavailableError("OpenAI API key is not configured.")

        try:
            from openai import APIConnectionError, APITimeoutError, BadRequestError
        except ImportError as exc:
            raise ObservationPipelineUnavailableError("OpenAI SDK is not installed.") from exc

        client = self._get_client()
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
    evaluate_observation_pipeline_precondition(
        establishment_id=observation.establishment_id,
    )

    provider = provider or get_observation_pipeline_provider()
    provider_name = provider.provider
    provider_model = getattr(provider, "model", "")

    input_started_at = time.monotonic()
    input_payload = build_pipeline_input(observation=observation)
    input_duration_ms = _elapsed_ms(input_started_at)
    establishment_context = input_payload.get("establishment_context") or {}
    business_unit_count = len(establishment_context.get("active_business_units") or [])
    input_payload_bytes = len(
        json.dumps(input_payload, ensure_ascii=False).encode("utf-8"),
    )
    logger.info(
        "observation_pipeline_input_built",
        extra=build_observation_pipeline_timing_log_context(
            observation_id=observation.id,
            establishment_id=observation.establishment_id,
            event="observation_pipeline_input_built",
            duration_ms=input_duration_ms,
            business_unit_count=business_unit_count,
            input_payload_bytes=input_payload_bytes,
            provider=provider_name,
            model=provider_model,
        ),
    )

    provider_started_at = time.monotonic()
    try:
        response = provider.propose(input_payload=input_payload)
        provider_duration_ms = _elapsed_ms(provider_started_at)
        logger.info(
            "observation_pipeline_provider_finished",
            extra=build_observation_pipeline_timing_log_context(
                observation_id=observation.id,
                establishment_id=observation.establishment_id,
                event="observation_pipeline_provider_finished",
                provider_duration_ms=provider_duration_ms,
                provider=provider_name,
                model=response.model or provider_model,
            ),
        )

        parse_started_at = time.monotonic()
        output = parse_pipeline_output(response.payload)
        parse_duration_ms = _elapsed_ms(parse_started_at)
        logger.info(
            "observation_pipeline_output_parsed",
            extra=build_observation_pipeline_timing_log_context(
                observation_id=observation.id,
                establishment_id=observation.establishment_id,
                event="observation_pipeline_output_parsed",
                parse_duration_ms=parse_duration_ms,
                candidate_count=len(output.candidates),
                provider=provider_name,
                model=response.model or provider_model,
            ),
        )

        _write_usage_log(
            observation=observation,
            provider=provider_name,
            model=response.model or provider_model,
            status=AIUsageLog.Status.SUCCEEDED,
            latency_ms=provider_duration_ms + parse_duration_ms,
            correlation_id=correlation_id,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
        )
        return output
    except ObservationPipelineTimeoutError as exc:
        _write_usage_log(
            observation=observation,
            provider=provider_name,
            model=provider_model,
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(provider_started_at),
            error_code=exc.error_code,
            correlation_id=correlation_id,
        )
        raise
    except ObservationPipelineUnavailableError as exc:
        _write_usage_log(
            observation=observation,
            provider=provider_name,
            model=provider_model,
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(provider_started_at),
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
            provider=provider_name,
            model=provider_model,
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(provider_started_at),
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
            provider=provider_name,
            model=provider_model,
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(provider_started_at),
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
Tu fais uniquement de la compréhension et des propositions de routing — jamais d'agrégation.

CONTEXTE
- Le message utilisateur est un JSON. Le texte à analyser est dans "validated_text".
- "establishment_context" décrit l'établissement (id, name, activity_description) et
  "active_business_units" (tous les pôles actifs, même non routables) — contexte structurel
  descriptif seulement ; ces pôles ne sont pas des clés runtime valides s'ils absents de
  routing_taxonomy.
- Les seules clés runtime valides sont celles de "routing_taxonomy" :
  routing_taxonomy.business_units[].routing_key, activity_subjects[].routing_key,
  operational_units[].key. N'invente jamais de clé hors routing_taxonomy ; sinon null.
- Chaque business unit routable a : routing_key, specific_name, catalog_key, generic_label,
  generic_description, instance_description, unit_type (dedicated ou transversal),
  activity_subjects[].
- Chaque activity_subject a routing_key, label, description, source, catalog_key,
  capabilities[] ; "routing_taxonomy.capabilities_version" versionne le mapping capacités.
- Les unités de lieu structurées sont dans routing_taxonomy.operational_units (key, label).
- "submission_context.author_scope_business_unit_routing_keys" liste 0/1/2+ rattachements
  auteur (clés runtime taxonomy-only, sans identité nominative) pour aider affected.
- Si "action_plan_context" est présent : utiliser plan_title, task,
  business_unit_routing_key (si non null), context_business_unit_source (task|pilot)
  et business_unit_specific_name pour affiner le routage ; ne pas répéter validated_text.
- Les descriptions des pôles aident à distinguer périmètres et responsabilités.
- Les images ne sont pas fournies ; "media_count" est informatif uniquement.

MÉTHODE — ANALYSE FAIT PAR FAIT
1. Lire validated_text et lister mentalement chaque FAIT opérationnel DISTINCT
   (anomalie corrective OU information utile à l'équipe : disponibilité, planning,
   horaires, consigne, changement d'organisation, statut rétabli / à surveiller).
2. Pour chaque fait, appliquer la grille mentale avant de produire le JSON :
   - symptôme / fait constaté,
   - nature / cause probable si pertinente (sinon N/A pour l'informatif),
   - action attendue si corrective ; sinon inform / monitor,
   - lieu pertinent (inclus dans issue_focus si discriminant),
   - pôle responsable (transversal ou dedicated selon règles ci-dessous).
3. Produire un candidat JSON par fait distinct (max {MAX_CANDIDATES_PER_OBSERVATION}).
   Ne fusionne jamais plusieurs faits indépendants en un seul candidat.

QUAND ÉMETTRE 0 / 1 / N CANDIDATS
- Émettre 1+ candidats s'il existe au moins un fait opérationnel actionable OU informational,
  même sans verbe d'action, même avec une invitation du type « venez demander ».
- Émettre plusieurs candidats si faits indépendants (objets, lieux discriminants,
  responsables, natures différentes), y compris mélange actionable + informational.
- Retourner "candidates": [] SEULEMENT si : pure politesse / encouragement sans fait ;
  négation / fausse alerte sans fait résiduel ; bavardage hors ops ; aucun fait identifiable.
- Ne PAS utiliser [] parce que le routing est ambigu (mettre les clés à null), faute
  d'action corrective immédiate (utiliser informational), formulation courte, ou présence
  d'une invitation accessoire.

ANTI-SUR-SEGMENTATION
- Une modalité d'accès, un conseil ou une invitation liée à l'information principale
  ne crée PAS un candidat séparé et ne doit PAS devenir une anomalie actionable.
- Ex. « Les plannings sont disponibles, venez les demander » → exactement 1 candidat
  informational (l'invitation est absorbée).

CANONICAL_OBJECT (obligatoire)
- Actionable : objet / produit / équipement concerné (ex. clim, sirop mojito, vitre).
- Informational : objet / thème opérationnel (ex. planning, horaires, consigne).

ISSUE_FOCUS (obligatoire, 1–80 caractères)
- Actionable : problème précis (en complément de canonical_object).
- Informational : état, disponibilité ou changement annoncé, court et stable
  (ex. planning étages disponible).
- Inclure le lieu dans issue_focus UNIQUEMENT quand il discrimine des faits distincts
  (ex. clim chambre 104 vs clim chambre 312).
- Formulation courte, minuscules préférées, sans ponctuation superflue.
- Sert côté backend à la clé d'agrégation — pas de synonymes inventés pour le même focus.

SIGNAL_KIND / EXPECTED_ACTION / INFORMATION_TYPE
- signal_kind "actionable" : intervention / correction / réappro / sécurisation / inspection
  attendue.
- signal_kind "informational" : fait à connaître, diffuser ou surveiller sans correction
  immédiate (planning, horaires, consignes, org, statut rétabli).
- expected_action : une valeur parmi clean_secure, repair, replenish, inspect, coordinate,
  assist, inform, monitor, safety_response — ou null si inconnue.
  Pour informational : préférer inform ou monitor.
- information_type : null exact si signal_kind=actionable ; string non vide (max 64) si
  informational ; pas d'enum fermée ; valeurs recommandées (non exclusives) :
  schedule_update, availability, org_change, policy_update, status_update.

EXEMPLES
- « Planning étages disponible » → 1 informational ; canonical_object≈planning ;
  issue_focus≈planning étages disponible ; expected_action=inform ;
  information_type≈schedule_update.
- « Les plannings sont disponibles, venez les demander » → exactement 1 informational
  (pas [] ; pas 2 candidats ; pas actionable).
- « Nouveau brief service à 17h » → 1 informational.
- « Hier ça coupait mais c'est revenu » → 1 informational ; expected_action=monitor.
- « Fuite couloir nord » → 1 actionable.
- « Frigo chaud et sol trempé » → 2 actionable.
- « Fuite couloir et planning étages dispo » → 1 actionable + 1 informational.
- « Bon courage à tous » / « Fausse alerte, pas de fuite » / remerciement sans fait → [].

DÉSAMBIGUÏSATION (contexte grammatical, pas de liste mots-clé)
- Distingue symptôme, cause et action via le sens de la phrase, pas via des mots isolés.
- Salissure / flaque à traiter (ménage, propreté) ≠ fuite / canalisation (plomberie).
  Ex. "eau par terre" sans fuite → propreté ; "fuite d'eau" → plomberie.
- Objet cassé / salissure à sécuriser ≠ équipement en panne.
  Ex. "verre cassé près des ascenseurs" → propreté/sécurisation ;
  "ascenseur en panne" → maintenance équipements.
- Ne route pas vers un pôle dedicated uniquement parce que son nom apparaît dans le texte
  si la nature du fait relève d'un pôle transversal de routing_taxonomy.

ROUTAGE — LIEU VS NATURE DU FAIT
- Clés nullables : si incertitude ou clé absente de routing_taxonomy → null.
- affected_business_unit_routing_key : où le fait est observé.
- responsible_business_unit_routing_key : qui doit traiter ou être informé.
- activity_subject_routing_key : sujet sous responsible.
- location_text : contexte libre ou localisation précise pour l'affichage (chambre 104, bar).
  Ne remplace pas issue_focus ; n'entre jamais dans une clé d'agrégation backend.

PRIORITÉ TRANSVERSALE
- Si un BusinessUnit unit_type=transversal possède un activity_subject correspondant
  au fait, responsible = ce transversal (même si le lieu mentionne un dedicated).
- Exemple : "Lumière HS au restaurant" → affected=restaurant, responsible=maintenance
  (transversal) si maintenance possède électricité/éclairage dans routing_taxonomy.

FALLBACK DEDICATED
- Si aucun pôle transversal pertinent n'existe pour la nature du fait,
  responsible = affected et activity_subject sous affected.

SEGMENTATION
- Séparer si lieux impactés, responsables, sujets, faits ou issue_focus diffèrent.
- Règle négative : produits ou objets différents → candidats différents
  même si même activity_subject (ex. pain et sirop mojito sous stock/bar → 2 candidats).
- Ne pas fusionner deux ruptures de stock distinctes en un seul candidat "stock bar".
- Respecter ANTI-SUR-SEGMENTATION pour invitations / accès liés à une info principale.

TEXTE DE SORTIE
- title : ≤ 80 caractères ; orienté action si actionable ; factuel si informational.
- structured_summary : 1–3 phrases factuelles ; inclure lieu précis si mentionné ;
  porter le fait et l'action attendue quand pertinente, sans recopier validated_text.
- location_text : lieu court libre (≤ 120 caractères), null si aucun lieu distinct ;
  jamais le texte complet de validated_text.

HORS PÉRIMÈTRE (ne jamais émettre)
- routing_status, resolution_audit, rejection_code, agrégation, scores, priorité
- urgence, detected_domains[], clés operational_module/domain/subject (legacy)

FORMAT DE RÉPONSE
Un seul objet JSON strict :
schema_version = "{AI_OBSERVATION_PIPELINE_SCHEMA_VERSION}"
candidates[] avec title, structured_summary, issue_focus, canonical_object, signal_kind,
expected_action, information_type, affected_business_unit_routing_key,
responsible_business_unit_routing_key, activity_subject_routing_key,
operational_unit_key, location_text.
Toutes les propriétés candidates sont requises ; les champs optionnels valent null.
"""


def _system_prompt() -> str:
    return _OBSERVATION_PIPELINE_SYSTEM_PROMPT


def _default_fake_payload(input_payload: dict[str, Any]) -> dict[str, Any]:
    taxonomy = input_payload.get("routing_taxonomy") or {}
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
                "issue_focus": "structured issue",
                "canonical_object": "structured issue",
                "signal_kind": "actionable",
                "expected_action": "inspect",
                "information_type": None,
                "affected_business_unit_routing_key": unit["routing_key"],
                "responsible_business_unit_routing_key": unit["routing_key"],
                "activity_subject_routing_key": subject["routing_key"],
                "operational_unit_key": None,
                "location_text": None,
            }
        ],
    }
