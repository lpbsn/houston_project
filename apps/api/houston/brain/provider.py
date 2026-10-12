"""Local fake provider. Lot 3 does not call a network and does not send a client file."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Protocol

from houston.brain.errors import BrainWorkError


class BrainProviderUnavailable(BrainWorkError):
    def __init__(self):
        super().__init__(
            code="provider_unavailable",
            message="Le fournisseur d'analyse est indisponible.",
        )


@dataclass(frozen=True)
class ProviderCallResult:
    output: dict
    truncated: bool
    input_tokens: int | None
    output_tokens: int | None


class BrainProvider(Protocol):
    def complete(
        self,
        *,
        analysis_id: str,
        lot_key: str,
        payload: dict,
        timeout_seconds: int,
    ) -> ProviderCallResult: ...


class FakeBrainProvider:
    """Orchestration stand-in. Hold and failure modes are local and never open a socket."""

    def complete(
        self,
        *,
        analysis_id: str,
        lot_key: str,
        payload: dict,
        timeout_seconds: int,
    ) -> ProviderCallResult:
        del analysis_id, timeout_seconds
        hold = _env_int("HOUSTON_BRAIN_FAKE_HOLD_SECONDS")
        if hold > 0:
            time.sleep(hold)
        mode = os.environ.get("HOUSTON_BRAIN_FAKE_MODE", "ok").strip() or "ok"
        if mode == "unavailable":
            raise BrainProviderUnavailable()
        section_keys = [
            section.get("text") or section.get("header")
            for section in payload.get("sections") or []
            if isinstance(section, dict)
        ]
        output = {"lot_key": lot_key, "section_markers": section_keys}
        if mode == "truncated":
            return ProviderCallResult(
                output=output,
                truncated=True,
                input_tokens=None,
                output_tokens=1,
            )
        if mode == "omit_output_tokens":
            return ProviderCallResult(
                output=output,
                truncated=False,
                input_tokens=1,
                output_tokens=None,
            )
        if mode == "omit_input_usage":
            return ProviderCallResult(
                output=output,
                truncated=False,
                input_tokens=None,
                output_tokens=1,
            )
        return ProviderCallResult(
            output=output,
            truncated=False,
            input_tokens=None,
            output_tokens=1,
        )


def _env_int(name: str) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0
