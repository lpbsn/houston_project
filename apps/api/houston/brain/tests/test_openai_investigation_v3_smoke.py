"""One live OpenAI call for the V3 investigation schema. Opt-in, not the default suite.

The default Brain run excludes ``openai_smoke``. This test also skips unless
``HOUSTON_RUN_BRAIN_INVESTIGATION_SMOKE`` is ``1``. It sends one synthetic
reading through ``OpenAIBrainProvider`` with ``investigation_response_schema``
and ``investigation_prompt``. It does not admit an analysis and does not touch
a tenant.

Launch from the API container, without the default marker filter::

    HOUSTON_RUN_BRAIN_INVESTIGATION_SMOKE=1 \\
    HOUSTON_BRAIN_SMOKE_MODEL=gpt-5-mini \\
    uv run pytest -m openai_smoke -q -s \\
    houston/brain/tests/test_openai_investigation_v3_smoke.py

``OPENAI_API_KEY`` must already be in the process environment. The model must
be one the investigation budget can count (o200k: gpt-4o, gpt-4.1, gpt-5-mini).
The call uses the production timeout and output ceiling. Token counts and
duration are written under ``.artifacts/brain-investigation-v3-smoke/``.
The API does not return a monetary price; those counts are the cost basis.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import pytest
from django.conf import settings
from pydantic import ValidationError

from houston.brain.errors import BrainWorkError
from houston.brain.integration import _provider
from houston.brain.investigation import (
    DEEPENING_MENU,
    PER_CALL_OUTPUT_TOKENS,
    PROVIDER_TIMEOUT_SECONDS,
)
from houston.brain.investigation_contract import (
    SCHEMA_VERSION,
    InvestigationReading,
    investigation_call_tokens,
)
from houston.brain.provider import BrainProviderUnavailable

_ENV = "HOUSTON_RUN_BRAIN_INVESTIGATION_SMOKE"
_MODEL_ENV = "HOUSTON_BRAIN_SMOKE_MODEL"
_CANARY = "SYNTHETIC_SECRET_DO_NOT_LOG_7f3a9c"
_ARCHIVE = Path(__file__).resolve().parents[5] / ".artifacts" / "brain-investigation-v3-smoke"
logger = logging.getLogger("houston.brain.tests.investigation_smoke")


def _payload() -> dict:
    return {
        "contract": SCHEMA_VERSION,
        "reading": 1,
        "proposed_subjects": [
            {
                "key": "couverts-synthetiques",
                "label": "Couverts du service fictif",
                "unit": "couvert",
                "scope": "service",
            }
        ],
        "reporting": {
            "title": "Reporting synthétique",
            "period": "2026-W01",
            "note": _CANARY,
        },
        "series": [
            {
                "series_key": "couverts-synthetiques",
                "label": "Couverts du service fictif",
                "unit": "couvert",
                "scope": "service",
                "points": [
                    {"item_id": "mesure-avant", "value": "40", "at": "2026-01-01"},
                    {"item_id": "mesure-apres", "value": "36", "at": "2026-01-08"},
                ],
            }
        ],
        "objectives": [],
        "examined": [],
        "contradictions": [],
        "discovered_not_examined": [],
        "deepening_menu": sorted(DEEPENING_MENU),
        "deepenings_remaining": 2,
        "limits": [],
        "memory": [],
    }


def _assert_unlogged(caplog, *secrets: str) -> None:
    text = caplog.text
    for secret in secrets:
        if secret and secret in text:
            pytest.fail("donnée sensible présente dans les logs")


def _archive(body: dict, *secrets: str) -> None:
    _ARCHIVE.mkdir(parents=True, exist_ok=True)
    text = json.dumps(body, indent=2, sort_keys=True) + "\n"
    for secret in secrets:
        if secret and secret in text:
            pytest.fail("donnée sensible présente dans l'archive du smoke")
    (_ARCHIVE / "latest.json").write_text(text, encoding="utf-8")


@pytest.mark.openai_smoke
def test_live_openai_accepts_brain_investigation_v3(caplog):
    if os.environ.get(_ENV) != "1":
        pytest.skip(
            f"{_ENV}=1, {_MODEL_ENV} (o200k) et OPENAI_API_KEY sont requis. "
            "make backend-test exclut ce marqueur."
        )
    model = os.environ.get(_MODEL_ENV, "").strip()
    api_key = str(settings.OPENAI_API_KEY or "").strip()
    missing = [
        name
        for name, value in ((_MODEL_ENV, model), ("OPENAI_API_KEY", api_key))
        if not value
    ]
    if missing:
        pytest.fail("prérequis manquant: " + ", ".join(missing))

    payload = _payload()
    try:
        local_tokens = investigation_call_tokens(payload, provider="openai", model=model)
    except BrainWorkError as exc:
        pytest.fail(f"modèle inutilisable pour le budget: {exc.code}")

    provider = _provider(
        {"provider": "openai", "model": model},
        {
            "provider_timeout_seconds": PROVIDER_TIMEOUT_SECONDS,
            "per_call_output_tokens": PER_CALL_OUTPUT_TOKENS,
        },
    )
    if provider is None:
        pytest.fail("prérequis manquant: fournisseur OpenAI non construit")

    caplog.set_level(logging.INFO)
    started = time.perf_counter()
    try:
        result = provider.complete(
            analysis_id="smoke-synthetique",
            lot_key="lecture:1",
            payload=payload,
            timeout_seconds=PROVIDER_TIMEOUT_SECONDS,
        )
    except BrainProviderUnavailable as exc:
        cause = exc.__cause__
        provider_error = type(cause).__name__ if cause is not None else type(exc).__name__
        _assert_unlogged(caplog, _CANARY, api_key)
        _archive(
            {
                "passed": False,
                "failure_code": "provider_unavailable",
                "provider_error": provider_error,
                "schema_version": SCHEMA_VERSION,
                "model": model,
            },
            _CANARY,
            api_key,
        )
        pytest.fail(f"OpenAI est indisponible: provider_error={provider_error}")
    except BrainWorkError as exc:
        cause = exc.__cause__
        provider_error = type(cause).__name__ if cause is not None else ""
        _assert_unlogged(caplog, _CANARY, api_key)
        _archive(
            {
                "passed": False,
                "failure_code": exc.code,
                "provider_error": provider_error,
                "schema_version": SCHEMA_VERSION,
                "model": model,
            },
            _CANARY,
            api_key,
        )
        pytest.fail(
            "OpenAI a refusé la requête: "
            f"failure_code={exc.code} provider_error={provider_error}"
        )
    elapsed = time.perf_counter() - started

    _assert_unlogged(caplog, _CANARY, api_key)
    if result.truncated or result.output.get("schema_version") != SCHEMA_VERSION:
        _archive(
            {
                "passed": False,
                "failure_code": "response_invalid",
                "truncated": result.truncated,
                "schema_version": SCHEMA_VERSION,
                "model": model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "elapsed_seconds": round(elapsed, 3),
            },
            _CANARY,
            api_key,
        )
        pytest.fail("réponse structurée inexploitable: schéma refusé ou sortie tronquée")
    try:
        reading = InvestigationReading.model_validate(result.output)
    except ValidationError as exc:
        kinds = ",".join(sorted({item["type"] for item in exc.errors()}))
        _archive(
            {
                "passed": False,
                "failure_code": "response_invalid",
                "validation_errors": exc.error_count(),
                "validation_types": kinds,
                "schema_version": SCHEMA_VERSION,
                "model": model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "elapsed_seconds": round(elapsed, 3),
            },
            _CANARY,
            api_key,
        )
        pytest.fail(
            "réponse structurée inexploitable: "
            f"{exc.error_count()} erreurs ({kinds})"
        )
    if not isinstance(result.input_tokens, int) or not isinstance(result.output_tokens, int):
        pytest.fail("usage réel absent de la réponse fournisseur")
    if result.input_tokens < 1 or result.output_tokens < 1 or elapsed <= 0:
        pytest.fail("usage réel ou durée absents de la réponse fournisseur")

    report = {
        "passed": True,
        "schema_version": reading.schema_version,
        "model": model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "local_input_tokens": local_tokens,
        "elapsed_seconds": round(elapsed, 3),
        "subjects": len(reading.subjects),
    }
    logger.info(
        "brain_investigation_v3_smoke model=%s input_tokens=%s output_tokens=%s "
        "local_input_tokens=%s elapsed_seconds=%s",
        model,
        result.input_tokens,
        result.output_tokens,
        local_tokens,
        report["elapsed_seconds"],
    )
    _assert_unlogged(caplog, _CANARY, api_key)
    _archive(report, _CANARY, api_key)
