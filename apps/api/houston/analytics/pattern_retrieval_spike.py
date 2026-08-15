"""Eval-only Phase 0 spike: oracle retrieval recall for semantic pattern search.

No production runtime, migrations, or pgvector. In-memory cosine only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from django.conf import settings

from houston.analytics.labels import normalize_pattern_label
from houston.testing.analytics_pattern_corpus import (
    AnalyticsPatternCorpusValidationError,
    get_analytics_pattern_scenario,
    list_analytics_pattern_scenario_ids,
    validate_analytics_pattern_corpus,
)

ANALYTICS_PATTERN_RETRIEVAL_SPIKE_OPT_IN_ENV = "HOUSTON_RUN_ANALYTICS_PATTERN_RETRIEVAL_SPIKE"
ANALYTICS_PATTERN_RETRIEVAL_SPIKE_ARCHIVE_DIR = (
    Path(__file__).resolve().parents[2] / ".artifacts" / "analytics-pattern-retrieval-spike"
)

SPIKE_SCHEMA_VERSION = "analytics_pattern_retrieval_spike_v1"
PROJECTION_PHENOMENON_V1 = "phenomenon_v1"
PROJECTION_PLUS_OPERATIONAL_UNIT_V1 = "phenomenon_plus_operational_unit_v1"
PROJECTION_PLUS_BUSINESS_UNITS_V1 = "phenomenon_plus_business_units_v1"
DEFAULT_PROJECTION = PROJECTION_PHENOMENON_V1
K_VALUES = (1, 3, 5, 8)
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
# Architecture gate: oracle recall must be near-perfect at chosen K.
ORACLE_RECALL_SATISFYING_RATE = 0.98

STABLE_FAIL_PAIRS = (
    ("hotel_facilities", "hf_01", "hf_02"),
    ("housekeeping_rooms", "hr_05", "hr_06"),
    ("safety_public_areas", "sp_01", "sp_02"),
)


class EmbeddingProviderError(RuntimeError):
    """Raised when the embedding provider cannot return vectors."""


class EmbeddingProvider(Protocol):
    model: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class FakeHashEmbeddingProvider:
    """Deterministic bag-of-token hash embeddings for CI / plumbing."""

    provider = "fake_hash"
    model = "fake-hash-v1"
    dimensions = 64

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [_hash_embedding(text, dimensions=self.dimensions) for text in texts]


class OpenAIEmbeddingProvider:
    provider = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 30,
    ):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model = model or DEFAULT_EMBEDDING_MODEL
        self.timeout_seconds = timeout_seconds
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise EmbeddingProviderError("OpenAI API key is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise EmbeddingProviderError("OpenAI SDK is not installed.") from exc
        self._client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
        return self._client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self._get_client().embeddings.create(
                model=self.model,
                input=texts,
            )
        except Exception as exc:  # noqa: BLE001 - surface provider failures cleanly.
            raise EmbeddingProviderError(
                f"OpenAI embedding request failed: {exc.__class__.__name__}"
            ) from exc
        by_index = {item.index: list(item.embedding) for item in response.data}
        missing = [index for index in range(len(texts)) if index not in by_index]
        if missing:
            raise EmbeddingProviderError(
                f"OpenAI embedding response missing indexes: {missing}"
            )
        return [by_index[index] for index in range(len(texts))]


@dataclass(frozen=True)
class IndexedAlias:
    alias_id: str
    semantic_label: str
    normalized_semantic_label: str
    terminal_key: str
    source: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class RankedCandidate:
    terminal_key: str
    semantic_label: str
    score: float
    matched_alias_id: str


@dataclass(frozen=True)
class DecisionRetrievalResult:
    scenario_id: str
    signal_ref: str
    decision_kind: str
    expected_terminal_key: str | None
    projection_text: str
    ranked_terminal_keys: tuple[str, ...]
    scores: tuple[float, ...]
    hit_at: dict[str, bool]
    scored: bool
    miss_reason: str = ""


@dataclass
class ProjectionEvalReport:
    projection: str
    embedding_provider: str
    embedding_model: str
    decisions: tuple[DecisionRetrievalResult, ...]
    recall: dict[str, Any]
    stable_fail: dict[str, Any]
    holdout: dict[str, Any]
    by_scenario: dict[str, Any]
    recommended_k: int | None
    phase0_status: str
    errors: tuple[str, ...] = ()


def build_signal_projection_text(
    *,
    signal: dict[str, Any],
    scenario: dict[str, Any],
    projection: str,
) -> str:
    activity_subjects = {
        item["key"]: item["label"] for item in scenario.get("activity_subjects", [])
    }
    operational_units = {
        item["key"]: item["label"] for item in scenario.get("operational_units", [])
    }
    business_units = {
        item["key"]: item["label"] for item in scenario.get("business_units", [])
    }
    parts = [
        signal["title"],
        signal["structured_summary"],
        signal["issue_focus"],
        activity_subjects.get(signal["activity_subject_key"], ""),
    ]
    if projection == PROJECTION_PLUS_OPERATIONAL_UNIT_V1:
        parts.append(operational_units.get(signal.get("operational_unit_key"), "") or "")
    elif projection == PROJECTION_PLUS_BUSINESS_UNITS_V1:
        parts.append(business_units.get(signal["affected_business_unit_key"], ""))
        parts.append(business_units.get(signal["responsible_business_unit_key"], ""))
    elif projection != PROJECTION_PHENOMENON_V1:
        raise ValueError(f"Unknown projection: {projection}")
    return "\n".join(part.strip() for part in parts if part and str(part).strip())


def cosine_similarity(
    left: list[float] | tuple[float, ...],
    right: list[float] | tuple[float, ...],
) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions must match.")
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for left_value, right_value in zip(left, right, strict=True):
        dot += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / math.sqrt(left_norm * right_norm)


def choose_smallest_satisfying_k(
    recall_by_k: dict[int, dict[str, Any]],
    *,
    threshold: float = ORACLE_RECALL_SATISFYING_RATE,
) -> int | None:
    for k in K_VALUES:
        metric = recall_by_k.get(k)
        if metric is None:
            continue
        rate = metric.get("rate")
        if rate is not None and rate >= threshold:
            return k
    return None


def evaluate_analytics_pattern_retrieval_spike(
    *,
    scenario_ids: list[str] | None = None,
    projection: str = DEFAULT_PROJECTION,
    provider_name: str = "fake",
    embedding_model: str | None = None,
    archive: bool = False,
    archive_dir: Path | None = None,
    also_run_ablations: bool = False,
) -> dict[str, Any]:
    validation_errors = validate_analytics_pattern_corpus()
    if validation_errors:
        raise AnalyticsPatternCorpusValidationError("; ".join(validation_errors))

    selected = _selected_scenario_ids(scenario_ids)
    provider = _provider_for_name(provider_name, embedding_model=embedding_model)
    if provider_name == "openai":
        _assert_openai_spike_enabled()

    projections = [projection]
    if also_run_ablations and projection == PROJECTION_PHENOMENON_V1:
        projections.extend(
            [
                PROJECTION_PLUS_OPERATIONAL_UNIT_V1,
                PROJECTION_PLUS_BUSINESS_UNITS_V1,
            ]
        )

    reports = [
        _evaluate_projection(
            scenario_ids=selected,
            projection=projection_name,
            provider=provider,
        )
        for projection_name in projections
    ]
    primary = reports[0]
    payload = {
        "schema_version": SPIKE_SCHEMA_VERSION,
        "metric_name": "oracle_retrieval_recall",
        "metric_definition": (
            "Scorable only when a correct terminal target already exists. "
            "Expected creates inject expected_new_pattern_label into the in-memory "
            "index after the decision so subsequent signals can retrieve siblings. "
            "This isolates retriever quality and is not an end-to-end proof."
        ),
        "k_values": list(K_VALUES),
        "satisfying_rate_threshold": ORACLE_RECALL_SATISFYING_RATE,
        "primary_projection": projection,
        "reports": [_projection_report_to_dict(report) for report in reports],
        "recommended_k": primary.recommended_k,
        "phase0_status": primary.phase0_status,
        "phase1_allowed": primary.phase0_status == "pass",
    }
    if archive:
        write_retrieval_spike_archive(report=payload, archive_dir=archive_dir)
    return payload


def format_retrieval_spike_report(payload: dict[str, Any]) -> str:
    lines = [
        "Analytics pattern retrieval spike (Phase 0 — oracle retrieval recall)",
        f"schema={payload['schema_version']}",
        f"phase0_status={payload['phase0_status']} recommended_k={payload['recommended_k']}",
        "",
    ]
    for report in payload["reports"]:
        lines.append(f"projection={report['projection']} model={report['embedding_model']}")
        for k in K_VALUES:
            metric = report["recall"][str(k)]
            rate = metric["rate"]
            rendered = "n/a" if rate is None else f"{rate:.3f}"
            lines.append(
                f"  recall@{k}: {metric['passed']}/{metric['total']} rate={rendered}"
            )
        lines.append(
            f"  stable_fail pairs with perfect recall@chosen: "
            f"{report['stable_fail'].get('summary', {})}"
        )
        if report["errors"]:
            for error in report["errors"]:
                lines.append(f"  error: {error}")
        lines.append("")
    if payload["phase0_status"] == "pass":
        lines.append(
            f"Phase 1 allowed with frozen K={payload['recommended_k']} "
            f"on projection={payload['primary_projection']}."
        )
    else:
        lines.append(
            "Phase 1 blocked: diagnose projection/embedding before any resolver runs."
        )
    return "\n".join(lines).rstrip() + "\n"


def write_retrieval_spike_archive(
    *,
    report: dict[str, Any],
    archive_dir: Path | None = None,
) -> Path:
    target_dir = archive_dir or ANALYTICS_PATTERN_RETRIEVAL_SPIKE_ARCHIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = target_dir / f"analytics-pattern-retrieval-spike-{stamp}.json"
    body = {"archived_at": stamp, **report}
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _evaluate_projection(
    *,
    scenario_ids: list[str],
    projection: str,
    provider: EmbeddingProvider,
) -> ProjectionEvalReport:
    decisions: list[DecisionRetrievalResult] = []
    errors: list[str] = []
    for scenario_id in scenario_ids:
        try:
            decisions.extend(
                _evaluate_scenario(
                    scenario=get_analytics_pattern_scenario(scenario_id),
                    projection=projection,
                    provider=provider,
                )
            )
        except Exception as exc:  # noqa: BLE001 - keep spike resilient per scenario.
            errors.append(f"{scenario_id}: {exc.__class__.__name__}: {exc}")

    recall = _recall_metrics(decisions)
    recommended_k = choose_smallest_satisfying_k(recall)
    phase0_status = "pass" if recommended_k is not None and not errors else "fail"
    return ProjectionEvalReport(
        projection=projection,
        embedding_provider=getattr(provider, "provider", provider.__class__.__name__),
        embedding_model=getattr(provider, "model", ""),
        decisions=tuple(decisions),
        recall={str(k): recall[k] for k in K_VALUES},
        stable_fail=_stable_fail_metrics(decisions, recommended_k=recommended_k),
        holdout=_holdout_metrics(decisions),
        by_scenario=_by_scenario_metrics(decisions),
        recommended_k=recommended_k,
        phase0_status=phase0_status,
        errors=tuple(errors),
    )


def _evaluate_scenario(
    *,
    scenario: dict[str, Any],
    projection: str,
    provider: EmbeddingProvider,
) -> list[DecisionRetrievalResult]:
    index: list[IndexedAlias] = []
    initial_texts = [
        raw["label"] for raw in scenario.get("initial_patterns", [])
    ]
    initial_embeddings = provider.embed_texts(initial_texts) if initial_texts else []
    for raw, embedding in zip(
        scenario.get("initial_patterns", []),
        initial_embeddings,
        strict=True,
    ):
        index.append(
            IndexedAlias(
                alias_id=f"initial:{raw['pattern_key']}",
                semantic_label=raw["label"],
                normalized_semantic_label=normalize_pattern_label(raw["label"]),
                terminal_key=raw["pattern_key"],
                source="initial",
                embedding=tuple(embedding),
            )
        )

    oracle_keys_by_normalized: dict[str, str] = {
        normalize_pattern_label(raw["label"]): raw["pattern_key"]
        for raw in scenario.get("initial_patterns", [])
    }
    results: list[DecisionRetrievalResult] = []

    for signal in scenario["signals"]:
        projection_text = build_signal_projection_text(
            signal=signal,
            scenario=scenario,
            projection=projection,
        )
        query_embedding = provider.embed_texts([projection_text])[0]
        ranked = _rank_terminals(index=index, query_embedding=query_embedding)

        expected_pattern_key = signal.get("expected_pattern_key")
        expected_new_label = signal.get("expected_new_pattern_label")
        if expected_pattern_key is not None:
            expected_terminal_key = expected_pattern_key
            decision_kind = "attach_existing"
            scored = True
        elif expected_new_label:
            normalized_new = normalize_pattern_label(expected_new_label)
            if normalized_new in oracle_keys_by_normalized:
                expected_terminal_key = oracle_keys_by_normalized[normalized_new]
                decision_kind = "attach_oracle_sibling"
                scored = True
            else:
                expected_terminal_key = None
                decision_kind = "oracle_create"
                scored = False
        else:
            raise ValueError(
                f"Signal {signal['ref']} missing expected_pattern_key/"
                "expected_new_pattern_label"
            )

        hit_at = {
            f"@{k}": (
                expected_terminal_key is not None
                and expected_terminal_key
                in {candidate.terminal_key for candidate in ranked[:k]}
            )
            for k in K_VALUES
        }
        miss_reason = ""
        if scored and not hit_at["@8"]:
            miss_reason = _miss_reason(
                expected_terminal_key=expected_terminal_key,
                index=index,
                ranked=ranked,
            )
        results.append(
            DecisionRetrievalResult(
                scenario_id=scenario["id"],
                signal_ref=signal["ref"],
                decision_kind=decision_kind,
                expected_terminal_key=expected_terminal_key,
                projection_text=projection_text,
                ranked_terminal_keys=tuple(
                    candidate.terminal_key for candidate in ranked[: max(K_VALUES)]
                ),
                scores=tuple(candidate.score for candidate in ranked[: max(K_VALUES)]),
                hit_at=hit_at,
                scored=scored,
                miss_reason=miss_reason,
            )
        )

        if decision_kind == "oracle_create" and expected_new_label:
            oracle_key = f"oracle:{normalize_pattern_label(expected_new_label)}"
            embedding = provider.embed_texts([expected_new_label])[0]
            index.append(
                IndexedAlias(
                    alias_id=oracle_key,
                    semantic_label=expected_new_label,
                    normalized_semantic_label=normalize_pattern_label(expected_new_label),
                    terminal_key=oracle_key,
                    source="oracle_create",
                    embedding=tuple(embedding),
                )
            )
            oracle_keys_by_normalized[
                normalize_pattern_label(expected_new_label)
            ] = oracle_key

    return results


def _rank_terminals(
    *,
    index: list[IndexedAlias],
    query_embedding: list[float],
) -> list[RankedCandidate]:
    """Score aliases, remap to terminal keys, keep best score per terminal."""
    best_by_terminal: dict[str, RankedCandidate] = {}
    for alias in index:
        score = cosine_similarity(query_embedding, alias.embedding)
        current = best_by_terminal.get(alias.terminal_key)
        candidate = RankedCandidate(
            terminal_key=alias.terminal_key,
            semantic_label=alias.semantic_label,
            score=score,
            matched_alias_id=alias.alias_id,
        )
        if current is None or (
            candidate.score,
            candidate.semantic_label,
            candidate.terminal_key,
        ) > (
            current.score,
            current.semantic_label,
            current.terminal_key,
        ):
            best_by_terminal[alias.terminal_key] = candidate
    return sorted(
        best_by_terminal.values(),
        key=lambda item: (-item.score, item.semantic_label, item.terminal_key),
    )


def _miss_reason(
    *,
    expected_terminal_key: str | None,
    index: list[IndexedAlias],
    ranked: list[RankedCandidate],
) -> str:
    if expected_terminal_key is None:
        return "no_expected_target"
    if not any(alias.terminal_key == expected_terminal_key for alias in index):
        return "target_missing_from_index"
    if not ranked:
        return "empty_index"
    return "projection_or_embedding_miss"


def _recall_metrics(decisions: list[DecisionRetrievalResult]) -> dict[int, dict[str, Any]]:
    scored = [decision for decision in decisions if decision.scored]
    metrics: dict[int, dict[str, Any]] = {}
    for k in K_VALUES:
        passed = sum(1 for decision in scored if decision.hit_at[f"@{k}"])
        total = len(scored)
        metrics[k] = {
            "passed": passed,
            "total": total,
            "rate": None if total == 0 else passed / total,
            "misses": [
                {
                    "scenario_id": decision.scenario_id,
                    "signal_ref": decision.signal_ref,
                    "expected_terminal_key": decision.expected_terminal_key,
                    "ranked_terminal_keys": list(decision.ranked_terminal_keys[:k]),
                    "miss_reason": decision.miss_reason,
                }
                for decision in scored
                if not decision.hit_at[f"@{k}"]
            ],
        }
    return metrics


def _stable_fail_metrics(
    decisions: list[DecisionRetrievalResult],
    *,
    recommended_k: int | None,
) -> dict[str, Any]:
    by_ref = {
        (decision.scenario_id, decision.signal_ref): decision for decision in decisions
    }
    pairs = []
    for scenario_id, first_ref, second_ref in STABLE_FAIL_PAIRS:
        first = by_ref.get((scenario_id, first_ref))
        second = by_ref.get((scenario_id, second_ref))
        pair_payload = {
            "scenario_id": scenario_id,
            "pair": [first_ref, second_ref],
            "signals": {},
        }
        for ref, decision in ((first_ref, first), (second_ref, second)):
            if decision is None:
                pair_payload["signals"][ref] = {"present": False}
                continue
            pair_payload["signals"][ref] = {
                "present": True,
                "scored": decision.scored,
                "decision_kind": decision.decision_kind,
                "expected_terminal_key": decision.expected_terminal_key,
                "hit_at": decision.hit_at,
                "ranked_terminal_keys": list(decision.ranked_terminal_keys),
                "miss_reason": decision.miss_reason,
            }
        if recommended_k is not None and first is not None and second is not None:
            pair_payload["both_hit_at_recommended_k"] = bool(
                first.scored
                and second.scored
                and first.hit_at[f"@{recommended_k}"]
                and second.hit_at[f"@{recommended_k}"]
            )
        pairs.append(pair_payload)
    return {
        "pairs": pairs,
        "summary": {
            "recommended_k": recommended_k,
            "pairs_both_hit": sum(
                1 for pair in pairs if pair.get("both_hit_at_recommended_k") is True
            ),
            "pair_count": len(pairs),
        },
    }


def _holdout_metrics(decisions: list[DecisionRetrievalResult]) -> dict[str, Any]:
    holdout = [
        decision
        for decision in decisions
        if decision.scenario_id.endswith("_holdout") and decision.scored
    ]
    return {
        str(k): {
            "passed": sum(1 for decision in holdout if decision.hit_at[f"@{k}"]),
            "total": len(holdout),
            "rate": (
                None
                if not holdout
                else sum(1 for decision in holdout if decision.hit_at[f"@{k}"])
                / len(holdout)
            ),
        }
        for k in K_VALUES
    }


def _by_scenario_metrics(decisions: list[DecisionRetrievalResult]) -> dict[str, Any]:
    scenario_ids = sorted({decision.scenario_id for decision in decisions})
    payload: dict[str, Any] = {}
    for scenario_id in scenario_ids:
        subset = [
            decision
            for decision in decisions
            if decision.scenario_id == scenario_id and decision.scored
        ]
        payload[scenario_id] = {
            str(k): {
                "passed": sum(1 for decision in subset if decision.hit_at[f"@{k}"]),
                "total": len(subset),
                "rate": (
                    None
                    if not subset
                    else sum(1 for decision in subset if decision.hit_at[f"@{k}"])
                    / len(subset)
                ),
            }
            for k in K_VALUES
        }
    return payload


def _projection_report_to_dict(report: ProjectionEvalReport) -> dict[str, Any]:
    return {
        "projection": report.projection,
        "embedding_provider": report.embedding_provider,
        "embedding_model": report.embedding_model,
        "recall": report.recall,
        "stable_fail": report.stable_fail,
        "holdout": report.holdout,
        "by_scenario": report.by_scenario,
        "recommended_k": report.recommended_k,
        "phase0_status": report.phase0_status,
        "errors": list(report.errors),
        "decisions": [
            {
                "scenario_id": decision.scenario_id,
                "signal_ref": decision.signal_ref,
                "decision_kind": decision.decision_kind,
                "expected_terminal_key": decision.expected_terminal_key,
                "projection_text": decision.projection_text,
                "ranked_terminal_keys": list(decision.ranked_terminal_keys),
                "scores": list(decision.scores),
                "hit_at": decision.hit_at,
                "scored": decision.scored,
                "miss_reason": decision.miss_reason,
            }
            for decision in report.decisions
        ],
    }


def _provider_for_name(
    provider_name: str,
    *,
    embedding_model: str | None,
) -> EmbeddingProvider:
    normalized = provider_name.strip().lower()
    if normalized == "fake":
        return FakeHashEmbeddingProvider()
    if normalized == "openai":
        return OpenAIEmbeddingProvider(model=embedding_model or DEFAULT_EMBEDDING_MODEL)
    raise ValueError("provider must be 'fake' or 'openai'")


def _selected_scenario_ids(raw_scenario_ids: list[str] | None) -> list[str]:
    known = list_analytics_pattern_scenario_ids()
    if not raw_scenario_ids:
        return known
    unknown = [scenario_id for scenario_id in raw_scenario_ids if scenario_id not in known]
    if unknown:
        raise ValueError(
            f"Unknown Analytics pattern scenario id(s): {', '.join(unknown)}. "
            f"Known: {', '.join(known)}"
        )
    return list(raw_scenario_ids)


def _assert_openai_spike_enabled() -> None:
    if os.environ.get(ANALYTICS_PATTERN_RETRIEVAL_SPIKE_OPT_IN_ENV) != "1":
        raise RuntimeError(
            "OpenAI retrieval spike is opt-in only. Set "
            f"{ANALYTICS_PATTERN_RETRIEVAL_SPIKE_OPT_IN_ENV}=1."
        )
    if not (settings.OPENAI_API_KEY or "").strip():
        raise RuntimeError("OPENAI_API_KEY is not configured.")


def _hash_embedding(text: str, *, dimensions: int) -> list[float]:
    tokens = normalize_pattern_label(text).split()
    values = [0.0] * dimensions
    if not tokens:
        values[0] = 1.0
        return values
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for offset in range(0, min(len(digest), dimensions * 4), 4):
            index = (offset // 4) % dimensions
            raw = struct.unpack_from(">i", digest, offset)[0]
            values[index] += (raw % 1000) / 1000.0
    norm = math.sqrt(sum(value * value for value in values))
    if norm <= 0.0:
        values[0] = 1.0
        return values
    return [value / norm for value in values]
