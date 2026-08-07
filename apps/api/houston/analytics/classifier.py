from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings

ANALYTICS_PATTERN_PROMPT_VERSION = "analytics_pattern_v1"
ANALYTICS_PATTERN_SCHEMA_VERSION = "analytics_pattern_v1"
ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION = (
    "analytics_pattern_duplicate_guard_v1"
)
ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION = (
    "analytics_pattern_duplicate_guard_v1"
)
RESPONSE_FORMAT_JSON_SCHEMA_STRICT = "json_schema_strict"


class PatternClassifierError(Exception):
    error_code = "pattern_classifier_error"


class PatternClassifierUnavailableError(PatternClassifierError):
    error_code = "provider_unavailable"


class PatternClassifierTimeoutError(PatternClassifierError):
    error_code = "provider_timeout"


class PatternClassifierInvalidOutputError(PatternClassifierError):
    error_code = "invalid_structured_output"

    def __init__(self, message: str, *, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}


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
    result_type: str
    pattern_id: uuid.UUID | None = None
    canonical_label: str = ""


@dataclass(frozen=True)
class PatternDuplicateGuardResponse:
    result_type: str
    pattern_id: uuid.UUID | None = None


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
                temperature=0.0,
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
            raise PatternClassifierInvalidOutputError("OpenAI returned an empty response.")
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise PatternClassifierInvalidOutputError("OpenAI returned invalid JSON.") from exc

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
                temperature=0.0,
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
            raise PatternClassifierInvalidOutputError("OpenAI returned an empty response.")
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise PatternClassifierInvalidOutputError("OpenAI returned invalid JSON.") from exc

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
        return PatternClassifierProviderResponse(payload=payload, model=self.model)


def parse_pattern_classifier_response(payload: dict[str, Any]) -> PatternClassifierResponse:
    result_type = payload.get("result_type")
    pattern_id = payload.get("pattern_id")
    canonical_label = payload.get("canonical_label")

    if result_type == "existing_pattern":
        if not pattern_id or canonical_label:
            raise PatternClassifierInvalidOutputError(
                "existing_pattern response must include only pattern_id.",
                payload=payload,
            )
        try:
            parsed_pattern_id = uuid.UUID(str(pattern_id))
        except (TypeError, ValueError) as exc:
            raise PatternClassifierInvalidOutputError(
                "existing_pattern response has invalid pattern_id.",
                payload=payload,
            ) from exc
        return PatternClassifierResponse(
            result_type="existing_pattern",
            pattern_id=parsed_pattern_id,
        )

    if result_type == "new_pattern":
        if pattern_id or not isinstance(canonical_label, str):
            raise PatternClassifierInvalidOutputError(
                "new_pattern response must include only canonical_label.",
                payload=payload,
            )
        return PatternClassifierResponse(
            result_type="new_pattern",
            canonical_label=canonical_label,
        )

    raise PatternClassifierInvalidOutputError(
        "Pattern classifier response must be discriminated.",
        payload=payload,
    )


def parse_pattern_duplicate_guard_response(
    payload: dict[str, Any],
) -> PatternDuplicateGuardResponse:
    result_type = payload.get("result_type")
    pattern_id = payload.get("pattern_id")

    if result_type == "create_new_pattern":
        if pattern_id:
            raise PatternClassifierInvalidOutputError(
                "create_new_pattern response must not include pattern_id.",
                payload=payload,
            )
        return PatternDuplicateGuardResponse(result_type="create_new_pattern")

    if result_type == "reuse_existing_pattern":
        if not pattern_id:
            raise PatternClassifierInvalidOutputError(
                "reuse_existing_pattern response must include pattern_id.",
                payload=payload,
            )
        try:
            parsed_pattern_id = uuid.UUID(str(pattern_id))
        except (TypeError, ValueError) as exc:
            raise PatternClassifierInvalidOutputError(
                "reuse_existing_pattern response has invalid pattern_id.",
                payload=payload,
            ) from exc
        return PatternDuplicateGuardResponse(
            result_type="reuse_existing_pattern",
            pattern_id=parsed_pattern_id,
        )

    raise PatternClassifierInvalidOutputError(
        "Pattern duplicate guard response must be discriminated.",
        payload=payload,
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
                    "result_type": {
                        "type": "string",
                        "enum": ["existing_pattern", "new_pattern"],
                    },
                    "pattern_id": {"type": ["string", "null"]},
                    "canonical_label": {"type": ["string", "null"]},
                },
                "required": ["result_type", "pattern_id", "canonical_label"],
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
                },
                "required": ["result_type", "pattern_id"],
            },
        },
    }


def _default_fake_payload(input_payload: dict[str, Any]) -> dict[str, Any]:
    active_patterns = input_payload.get("active_patterns") or []
    if active_patterns:
        return {"result_type": "existing_pattern", "pattern_id": active_patterns[0]["id"]}
    return {"result_type": "new_pattern", "canonical_label": "Recurring operational issue"}


def _is_invalid_response_format_schema_error(exc: BaseException) -> bool:
    if getattr(exc, "param", None) == "response_format":
        return True
    return "Invalid schema" in str(exc)


_ANALYTICS_PATTERN_SYSTEM_PROMPT = """\
Tu classes un Signal opérationnel Houston dans un motif analytique.
Réponds uniquement avec le JSON strict demandé.

Règles:
- Si un motif actif candidat couvre le même phénomène opérationnel, retourne existing_pattern.
- Sinon propose un libellé canonique court avec new_pattern.
- Le libellé doit nommer le phénomène, pas l'établissement, ni les business units.
- Les business units sont du contexte secondaire et ne définissent pas l'identité du motif.
"""


def _system_prompt() -> str:
    return _ANALYTICS_PATTERN_SYSTEM_PROMPT


_ANALYTICS_PATTERN_DUPLICATE_GUARD_SYSTEM_PROMPT = """\
Tu vérifies si un nouveau libellé de motif Analytics est un doublon sémantique.
Réponds uniquement avec le JSON strict demandé.

Règles:
- Réutilise un motif existant seulement si la même identité de phénomène est claire.
- Ignore les business units, l'établissement, le routing et les actions.
- En cas de doute, retourne create_new_pattern.
"""


def _duplicate_guard_system_prompt() -> str:
    return _ANALYTICS_PATTERN_DUPLICATE_GUARD_SYSTEM_PROMPT
