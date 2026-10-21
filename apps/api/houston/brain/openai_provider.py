"""OpenAI tool-calling adapter for the investigator.

The analysis worker selects this adapter when the frozen provider is openai.
The API key is not stored on the analysis and is not part of the call payload.
A truncated completion is a technical failure, not a restitution.
"""

from __future__ import annotations

import json

from houston.brain.configuration import canonical_json
from houston.brain.engine import EngineToolCall, EngineTurn
from houston.brain.errors import BrainWorkError
from houston.brain.provider import BrainProviderUnavailable


class OpenAIBrainProvider:
    """One Chat Completions call. The SDK does not retry."""

    provider = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
        max_output_tokens: int,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self._client = None

    def complete(
        self,
        *,
        analysis_id: str,
        messages: list,
        tools: list,
        timeout_seconds: int,
    ) -> EngineTurn:
        del analysis_id
        if not self.api_key:
            raise BrainWorkError(
                code="provider_not_allowed",
                message="Le fournisseur OpenAI n'est pas autorisé pour cette analyse.",
            )
        timeout = timeout_seconds or self.timeout_seconds
        openai_tools = _openai_tools(tools)
        kwargs = {
            "model": self.model,
            "messages": _openai_messages(messages),
            "max_completion_tokens": self.max_output_tokens,
            "timeout": timeout,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools
        else:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            from openai import APIConnectionError, APITimeoutError, BadRequestError
        except ImportError as exc:
            raise BrainProviderUnavailable() from exc
        try:
            response = self._client_for(timeout).chat.completions.create(**kwargs)
        except (APITimeoutError, APIConnectionError) as exc:
            raise BrainProviderUnavailable() from exc
        except BadRequestError as exc:
            raise BrainWorkError(
                code="response_invalid",
                message="Le fournisseur a refusé la demande.",
            ) from exc
        return _turn(response)

    def _client_for(self, timeout: int):
        if self._client is not None:
            return self._client
        from openai import OpenAI

        self._client = OpenAI(api_key=self.api_key, timeout=timeout, max_retries=0)
        return self._client


def _openai_tools(tools: list) -> list[dict]:
    converted = []
    for tool in tools or []:
        if not isinstance(tool, dict) or not tool.get("name"):
            continue
        properties = {
            str(name): {"type": "string", "description": str(description)}
            for name, description in (tool.get("parameters") or {}).items()
        }
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": str(tool.get("description") or ""),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "additionalProperties": False,
                    },
                },
            }
        )
    return converted


def _openai_messages(messages: list) -> list[dict]:
    converted = []
    pending_ids: list[str] = []
    tool_index = 0
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        text = content if isinstance(content, str) else canonical_json(content)
        if role in {"system", "format"}:
            converted.append({"role": "system", "content": text})
            continue
        if role == "assistant":
            tool_calls = []
            pending_ids = []
            for call in message.get("tool_calls") or []:
                if not isinstance(call, dict):
                    continue
                tool_index += 1
                call_id = f"call_{tool_index}"
                pending_ids.append(call_id)
                arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
                tool_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": str(call.get("name") or ""),
                            "arguments": canonical_json(arguments),
                        },
                    }
                )
            converted.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
            continue
        if role == "tool":
            call_id = pending_ids.pop(0) if pending_ids else f"call_{tool_index}"
            converted.append({"role": "tool", "tool_call_id": call_id, "content": text})
            continue
        converted.append({"role": "user", "content": text})
    return converted


def _turn(response) -> EngineTurn:
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", None) if usage is not None else None
    output_tokens = getattr(usage, "completion_tokens", None) if usage is not None else None
    choice = response.choices[0] if getattr(response, "choices", None) else None
    if choice is None:
        raise BrainWorkError(
            code="response_invalid",
            message="Le fournisseur n'a pas renvoyé de réponse.",
        )
    message = choice.message
    if getattr(message, "refusal", None) or choice.finish_reason in {"length", "content_filter"}:
        raise BrainWorkError(
            code="response_invalid",
            message="La réponse du fournisseur est tronquée.",
        )
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        parsed = []
        for call in tool_calls:
            function = getattr(call, "function", None)
            name = str(getattr(function, "name", "") or "")
            raw = getattr(function, "arguments", None) or "{}"
            try:
                arguments = json.loads(raw)
            except json.JSONDecodeError:
                arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            parsed.append(EngineToolCall(name=name, arguments=arguments))
        if not parsed:
            raise BrainWorkError(
                code="response_invalid",
                message="La réponse ne contient ni recherche ni restitution.",
            )
        return EngineTurn(
            tool_calls=tuple(parsed),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    try:
        output = json.loads(message.content or "")
    except json.JSONDecodeError as exc:
        raise BrainWorkError(
            code="response_invalid",
            message="La restitution n'est pas un objet JSON.",
        ) from exc
    if not isinstance(output, dict):
        raise BrainWorkError(
            code="response_invalid",
            message="La restitution n'est pas un objet JSON.",
        )
    return EngineTurn(
        restitution=output,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
