from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings

# gpt-5-mini rejects non-default temperature; omit it for the alias and dated snapshots.
_GPT5_MINI_MODEL_RE = re.compile(r"^gpt-5-mini(?:-\d{4}-\d{2}-\d{2})?$")

ANALYTICS_PATTERN_PROMPT_VERSION = "analytics_pattern_v2.1"
ANALYTICS_PATTERN_SCHEMA_VERSION = "analytics_pattern_v2"
ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION = (
    "analytics_pattern_duplicate_guard_v2"
)
ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION = (
    "analytics_pattern_duplicate_guard_v1"
)
RESPONSE_FORMAT_JSON_SCHEMA_STRICT = "json_schema_strict"
DUPLICATE_GUARD_REASON_CODES = (
    "same_phenomenon",
    "different_failure_mode",
    "different_process_or_stage",
    "different_operational_state",
    "different_known_cause",
    "ambiguous",
)


class PatternClassifierError(Exception):
    error_code = "pattern_classifier_error"


class PatternClassifierUnavailableError(PatternClassifierError):
    error_code = "provider_unavailable"


class PatternClassifierTimeoutError(PatternClassifierError):
    error_code = "provider_timeout"


class PatternClassifierInvalidOutputError(PatternClassifierError):
    error_code = "invalid_structured_output"

    def __init__(
        self,
        message: str,
        *,
        payload: dict[str, Any] | None = None,
        validation_branch: str = "unknown_invalid_output",
    ):
        super().__init__(message)
        self.payload = payload or {}
        self.validation_branch = validation_branch


class PatternClassifierSchemaError(PatternClassifierError):
    error_code = "invalid_response_schema"


class PatternClassifierProviderBadRequestError(PatternClassifierError):
    error_code = "provider_bad_request"


@dataclass(frozen=True)
class PatternClassifierProviderResponse:
    payload: dict[str, Any]
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    model: str = ""
    provider_request_id: str = ""


@dataclass(frozen=True)
class PatternClassifierResponse:
    canonical_label: str


@dataclass(frozen=True)
class PatternDuplicateGuardResponse:
    result_type: str
    pattern_id: uuid.UUID | None = None
    reason_code: str | None = None


class PatternClassifierProvider(Protocol):
    provider: str

    def classify(
        self,
        *,
        input_payload: dict[str, Any],
    ) -> PatternClassifierProviderResponse: ...

    def assess_duplicate(
        self,
        *,
        input_payload: dict[str, Any],
    ) -> PatternClassifierProviderResponse: ...


class OpenAIPatternClassifierProvider:
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
        self.model = model or settings.HOUSTON_AI_ANALYTICS_PATTERN_MODEL
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.HOUSTON_AI_ANALYTICS_PATTERN_TIMEOUT_SECONDS
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else settings.HOUSTON_AI_ANALYTICS_PATTERN_MAX_RETRIES
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
            raise PatternClassifierUnavailableError("OpenAI SDK is not installed.") from exc
        self._client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )
        return self._client

    def _sampling_kwargs(self) -> dict[str, float]:
        return _openai_sampling_kwargs(self.model)

    def classify(self, *, input_payload: dict[str, Any]) -> PatternClassifierProviderResponse:
        if not self.api_key:
            raise PatternClassifierUnavailableError("OpenAI API key is not configured.")

        try:
            from openai import APIConnectionError, APITimeoutError, BadRequestError
        except ImportError as exc:
            raise PatternClassifierUnavailableError("OpenAI SDK is not installed.") from exc

        try:
            response = self._get_client().chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": json.dumps(input_payload, ensure_ascii=False)},
                ],
                response_format=openai_strict_response_format(),
                **self._sampling_kwargs(),
            )
        except APITimeoutError as exc:
            raise PatternClassifierTimeoutError("OpenAI request timed out.") from exc
        except APIConnectionError as exc:
            raise PatternClassifierUnavailableError("OpenAI is unavailable.") from exc
        except BadRequestError as exc:
            if _is_invalid_response_format_schema_error(exc):
                raise PatternClassifierSchemaError(
                    "OpenAI rejected the analytics pattern response schema.",
                ) from exc
            raise PatternClassifierProviderBadRequestError(
                "OpenAI rejected the analytics pattern request.",
            ) from exc

        self.last_provider_request_id = getattr(response, "id", "") or ""
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise PatternClassifierInvalidOutputError(
                "OpenAI returned an empty response.",
                validation_branch="provider_empty_response",
            )
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise PatternClassifierInvalidOutputError(
                "OpenAI returned invalid JSON.",
                validation_branch="provider_invalid_json",
            ) from exc

        usage = getattr(response, "usage", None)
        return PatternClassifierProviderResponse(
            payload=payload,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            model=self.model,
            provider_request_id=self.last_provider_request_id,
        )

    def assess_duplicate(
        self,
        *,
        input_payload: dict[str, Any],
    ) -> PatternClassifierProviderResponse:
        if not self.api_key:
            raise PatternClassifierUnavailableError("OpenAI API key is not configured.")

        try:
            from openai import APIConnectionError, APITimeoutError, BadRequestError
        except ImportError as exc:
            raise PatternClassifierUnavailableError("OpenAI SDK is not installed.") from exc

        try:
            response = self._get_client().chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _duplicate_guard_system_prompt()},
                    {"role": "user", "content": json.dumps(input_payload, ensure_ascii=False)},
                ],
                response_format=openai_duplicate_guard_response_format(),
                **self._sampling_kwargs(),
            )
        except APITimeoutError as exc:
            raise PatternClassifierTimeoutError("OpenAI request timed out.") from exc
        except APIConnectionError as exc:
            raise PatternClassifierUnavailableError("OpenAI is unavailable.") from exc
        except BadRequestError as exc:
            if _is_invalid_response_format_schema_error(exc):
                raise PatternClassifierSchemaError(
                    "OpenAI rejected the analytics duplicate guard response schema.",
                ) from exc
            raise PatternClassifierProviderBadRequestError(
                "OpenAI rejected the analytics duplicate guard request.",
            ) from exc

        self.last_provider_request_id = getattr(response, "id", "") or ""
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise PatternClassifierInvalidOutputError(
                "OpenAI returned an empty response.",
                validation_branch="duplicate_guard_provider_empty_response",
            )
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise PatternClassifierInvalidOutputError(
                "OpenAI returned invalid JSON.",
                validation_branch="duplicate_guard_provider_invalid_json",
            ) from exc

        usage = getattr(response, "usage", None)
        return PatternClassifierProviderResponse(
            payload=payload,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            model=self.model,
            provider_request_id=self.last_provider_request_id,
        )


class FakePatternClassifierProvider:
    provider = "fake"

    def __init__(
        self,
        *,
        payload: dict[str, Any] | None = None,
        duplicate_guard_payload: dict[str, Any] | None = None,
        exc: Exception | None = None,
        duplicate_guard_exc: Exception | None = None,
    ):
        self._payload = payload
        self._duplicate_guard_payload = duplicate_guard_payload
        self._exc = exc
        self._duplicate_guard_exc = duplicate_guard_exc
        self.calls: list[dict[str, Any]] = []
        self.duplicate_guard_calls: list[dict[str, Any]] = []
        self.model = "fake"

    def classify(self, *, input_payload: dict[str, Any]) -> PatternClassifierProviderResponse:
        self.calls.append(input_payload)
        if self._exc is not None:
            raise self._exc
        payload = (
            self._payload if self._payload is not None else _default_fake_payload(input_payload)
        )
        return PatternClassifierProviderResponse(payload=payload, model=self.model)

    def assess_duplicate(
        self,
        *,
        input_payload: dict[str, Any],
    ) -> PatternClassifierProviderResponse:
        self.duplicate_guard_calls.append(input_payload)
        if self._duplicate_guard_exc is not None:
            raise self._duplicate_guard_exc
        payload = self._duplicate_guard_payload or {
            "result_type": "create_new_pattern",
            "pattern_id": None,
        }
        payload = _duplicate_guard_payload_with_default_reason_code(payload)
        return PatternClassifierProviderResponse(payload=payload, model=self.model)


def parse_pattern_classifier_response(payload: dict[str, Any]) -> PatternClassifierResponse:
    canonical_label = payload.get("canonical_label")
    if set(payload) != {"canonical_label"}:
        raise PatternClassifierInvalidOutputError(
            "Pattern classifier response must include only canonical_label.",
            payload=payload,
            validation_branch="classifier_response_shape_invalid",
        )
    if not isinstance(canonical_label, str):
        raise PatternClassifierInvalidOutputError(
            "Pattern classifier canonical_label must be a string.",
            payload=payload,
            validation_branch="canonical_label_type_invalid",
        )

    return PatternClassifierResponse(canonical_label=canonical_label)


def parse_pattern_duplicate_guard_response(
    payload: dict[str, Any],
) -> PatternDuplicateGuardResponse:
    result_type = payload.get("result_type")
    pattern_id = payload.get("pattern_id")
    reason_code = payload.get("reason_code")
    if reason_code not in DUPLICATE_GUARD_REASON_CODES:
        raise PatternClassifierInvalidOutputError(
            "Pattern duplicate guard response has invalid reason_code.",
            payload=payload,
            validation_branch="duplicate_guard_reason_code_invalid",
        )

    if result_type == "create_new_pattern":
        if pattern_id:
            raise PatternClassifierInvalidOutputError(
                "create_new_pattern response must not include pattern_id.",
                payload=payload,
                validation_branch="duplicate_guard_create_new_shape_invalid",
            )
        if reason_code == "same_phenomenon":
            raise PatternClassifierInvalidOutputError(
                "create_new_pattern response must not use same_phenomenon.",
                payload=payload,
                validation_branch="duplicate_guard_create_reason_code_invalid",
            )
        return PatternDuplicateGuardResponse(
            result_type="create_new_pattern",
            reason_code=reason_code,
        )

    if result_type == "reuse_existing_pattern":
        if not pattern_id:
            raise PatternClassifierInvalidOutputError(
                "reuse_existing_pattern response must include pattern_id.",
                payload=payload,
                validation_branch="duplicate_guard_reuse_existing_shape_invalid",
            )
        if reason_code != "same_phenomenon":
            raise PatternClassifierInvalidOutputError(
                "reuse_existing_pattern response must use same_phenomenon.",
                payload=payload,
                validation_branch="duplicate_guard_reuse_reason_code_invalid",
            )
        try:
            parsed_pattern_id = uuid.UUID(str(pattern_id))
        except (TypeError, ValueError) as exc:
            raise PatternClassifierInvalidOutputError(
                "reuse_existing_pattern response has invalid pattern_id.",
                payload=payload,
                validation_branch="duplicate_guard_pattern_id_invalid",
            ) from exc
        return PatternDuplicateGuardResponse(
            result_type="reuse_existing_pattern",
            pattern_id=parsed_pattern_id,
            reason_code=reason_code,
        )

    raise PatternClassifierInvalidOutputError(
        "Pattern duplicate guard response must be discriminated.",
        payload=payload,
        validation_branch="duplicate_guard_response_discriminator_invalid",
    )


def get_pattern_classifier_provider() -> PatternClassifierProvider:
    provider_name = settings.HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER.strip().lower()
    if provider_name == "fake":
        return FakePatternClassifierProvider()
    if provider_name == "openai":
        return OpenAIPatternClassifierProvider()
    raise PatternClassifierUnavailableError(
        f"Unknown analytics pattern provider: {provider_name!r}"
    )


def classifier_version_for_provider(provider: PatternClassifierProvider) -> str:
    provider_name = provider.provider.strip().lower()
    model = (getattr(provider, "model", "") or "").strip()
    if model:
        return f"{ANALYTICS_PATTERN_SCHEMA_VERSION}:{provider_name}:{model}"
    return f"{ANALYTICS_PATTERN_SCHEMA_VERSION}:{provider_name}"


def openai_strict_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "analytics_pattern_classifier",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "canonical_label": {"type": "string"},
                },
                "required": ["canonical_label"],
            },
        },
    }


def openai_duplicate_guard_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "analytics_pattern_duplicate_guard",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "result_type": {
                        "type": "string",
                        "enum": ["reuse_existing_pattern", "create_new_pattern"],
                    },
                    "pattern_id": {"type": ["string", "null"]},
                    "reason_code": {
                        "type": "string",
                        "enum": list(DUPLICATE_GUARD_REASON_CODES),
                    },
                },
                "required": ["result_type", "pattern_id", "reason_code"],
            },
        },
    }


def _default_fake_payload(input_payload: dict[str, Any]) -> dict[str, Any]:
    return {"canonical_label": "Recurring operational issue"}


def _duplicate_guard_payload_with_default_reason_code(
    payload: dict[str, Any],
) -> dict[str, Any]:
    if "reason_code" in payload:
        return payload
    if payload.get("result_type") == "reuse_existing_pattern":
        return {**payload, "reason_code": "same_phenomenon"}
    return {**payload, "reason_code": "ambiguous"}


def _openai_sampling_kwargs(model: str) -> dict[str, float]:
    if _GPT5_MINI_MODEL_RE.fullmatch((model or "").strip()):
        return {}
    return {"temperature": 0.0}


def _is_invalid_response_format_schema_error(exc: BaseException) -> bool:
    if getattr(exc, "param", None) == "response_format":
        return True
    return "Invalid schema" in str(exc)


_ANALYTICS_PATTERN_SYSTEM_PROMPT = """\
Tu classes un Signal opérationnel Houston dans un motif analytique.
Réponds uniquement avec le JSON strict demandé.

Règles:
- Retourne un canonical_label court qui nomme le phénomène opérationnel.
- Fais converger les formulations différentes du même phénomène vers une formulation
  canonique commune.
- Si deux Signals partagent le même workflow, la même failure family et la même
  unité analytique managériale, tends vers un canonical_label commun.
- Des symptômes wording différents du même phénomène ne doivent pas automatiquement
  produire des labels distincts.
- Ne fusionne pas des phénomènes dont la différence change l'interprétation managériale.
- Retire les détails incidents: instance/numéro, localisation, credential medium,
  item/SKU ou variante locale, et wording propre au Signal.
- Conserve ces détails seulement s'ils changent réellement le workflow, le failure
  mode ou l'interprétation management.
- Conserve l'objet ou la famille d'équipement si cela distingue le phénomène, le
  failure mode ou le processus opérationnel.
- Conserve les précisions de processus, étape, état, environnement ou cause
  explicitement connue qui distinguent deux phénomènes opérationnels.
- Ne déduis pas une cause racine qui n'est pas explicitement présente.
- Même impact ne signifie pas forcément même problème.
- Même équipement ne signifie pas forcément même mode de défaillance.
- En cas d'ambiguïté sémantique, préfère un libellé plus spécifique.
"""


def _system_prompt() -> str:
    return _ANALYTICS_PATTERN_SYSTEM_PROMPT


_ANALYTICS_PATTERN_DUPLICATE_GUARD_SYSTEM_PROMPT = """\
Tu vérifies si un nouveau libellé de motif Analytics est un doublon sémantique.
Réponds uniquement avec le JSON strict demandé.

Règles:
- Examine tous les candidats de la shortlist avant de créer un nouveau motif.
- Si au moins un candidat représente correctement la même unité analytique
  managériale, choisis le meilleur candidat compatible.
- Ignore les candidats incompatibles; ne crée pas simplement parce qu'un autre
  candidat de la shortlist est imparfait.
- Une différence descriptive n'est une frontière analytique que si elle change
  réellement le workflow/process/handoff, le failure mode, l'état opérationnel
  ou une cause explicitement connue.
- Avant reuse_existing_pattern, vérifie qu'aucune de ces différences opérationnelles
  explicites ne serait masquée.
- Avant reason_code=different_process_or_stage, identifie une vraie frontière de
  workflow. Item/SKU, fixture, credential medium, localisation ou wording dans le
  même workflow ne suffisent pas.
- Avant reason_code=different_failure_mode, identifie un comportement ou
  dysfonctionnement réellement incompatible. Une formulation plus spécifique, un
  sous-type ou un état compatible avec le même fault ne suffit pas.
- Une frontière de processus explicite empêche le reuse: stock cuisine/dry
  ingredients et stock bar/beverage sont distincts si leurs flux opérationnels
  sont distincts.
- Réutilise un motif existant si la différence avec le canonical_label est seulement
  contextuelle ou lexicale et que le phénomène opérationnel est le même.
- Une différence de sous-type d'objet ou d'équipement, instance, localisation,
  credential, item/SKU, contexte temporel/local, wording, étape contextuelle,
  état spécifique compatible avec le fault/anomaly du candidat ou formulation
  plus spécifique ne justifie pas à elle seule create_new_pattern.
- Réutilise un candidat si canonical_label et candidat représentent la même unité
  analytique managériale et le même phénomène, processus ou failure mode.
- Un candidat plus général peut être réutilisé s'il représente correctement la
  même série managériale.
- Avant create_new_pattern, exige une vraie différence opérationnelle positive.
- Crée un nouveau motif si la différence change le failure mode, le processus,
  l'étape, l'état ou la cause explicitement connue.
- Crée aussi un nouveau motif si la généralisation masquerait plusieurs problèmes
  distincts pour l'analyse management.
- reason_code=different_failure_mode doit correspondre à un vrai comportement ou
  mode de défaillance incompatible, pas à une spécialisation seule.
- reason_code=different_process_or_stage doit être utilisé seulement lorsqu'une
  vraie frontière de workflow, de processus ou d'étape explique la séparation.
- Le score token_overlap_v1 sert uniquement à retrouver des candidats; ne décide
  jamais du reuse à partir du score seul.
- reason_code=ambiguous signifie qu'après examen de tous les candidats il existe
  une vraie incertitude opérationnelle empêchant un reuse sûr.
- Une simple différence de précision, sous-type, wording, instance, localisation,
  credential, item/SKU ou candidat plus général ne suffit pas à produire ambiguous.
- En cas de vraie ambiguïté, retourne create_new_pattern avec reason_code=ambiguous.
"""


def _duplicate_guard_system_prompt() -> str:
    return _ANALYTICS_PATTERN_DUPLICATE_GUARD_SYSTEM_PROMPT
