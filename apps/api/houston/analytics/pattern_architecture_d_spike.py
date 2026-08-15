"""Eval-only Architecture D spike: classifier + semantic retrieval + duplicate guard.

Replaces token_overlap_v1 shortlisting with phenomenon_v1 dense retrieval.
No production runtime, migrations, or pgvector.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from django.conf import settings
from django.test.utils import override_settings

from houston.analytics.labels import normalize_pattern_label
from houston.analytics.models import OperationalPattern
from houston.analytics.pattern_corpus_eval import (
    ANALYTICS_PATTERN_EVAL_OPT_IN_ENV,
    analytics_pattern_corpus_eval_report_to_dict,
    evaluate_analytics_pattern_corpus,
)
from houston.analytics.pattern_retrieval_spike import (
    ANALYTICS_PATTERN_RETRIEVAL_SPIKE_OPT_IN_ENV,
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingProvider,
    FakeHashEmbeddingProvider,
    IndexedAlias,
    OpenAIEmbeddingProvider,
    PROJECTION_PHENOMENON_V1,
    STABLE_FAIL_PAIRS,
    _rank_terminals,
    evaluate_analytics_pattern_retrieval_spike,
)
from houston.analytics.services import PatternDuplicateGuardCandidate
from houston.signals.models import Signal
from houston.testing.analytics_pattern_corpus import get_analytics_pattern_scenario

ANALYTICS_PATTERN_ARCHITECTURE_D_SPIKE_OPT_IN_ENV = (
    "HOUSTON_RUN_ANALYTICS_PATTERN_ARCHITECTURE_D_SPIKE"
)
ANALYTICS_PATTERN_ARCHITECTURE_D_SPIKE_ARCHIVE_DIR = (
    Path(__file__).resolve().parents[2]
    / ".artifacts"
    / "analytics-pattern-architecture-d-spike"
)

SPIKE_SCHEMA_VERSION = "analytics_pattern_architecture_d_spike_v1"
SHORTLIST_STRATEGY = "semantic_retrieval_phenomenon_v1"
D_K_CANDIDATES = (3, 5)
DEFAULT_CLASSIFIER_MODEL = "gpt-5-mini"

FOCUS_PAIRS = (
    ("hotel_facilities", "hf_01", "hf_02"),
    ("housekeeping_rooms", "hr_05", "hr_06"),
    ("safety_public_areas", "sp_01", "sp_02"),
    ("frontdesk_guest_flow", "fg_05", "fg_06"),
    ("restaurant_stock", "rs_05", "rs_06"),
)

BASELINE_A = {
    "architecture": "A",
    "description": "classifier + token_overlap_v1 + duplicate guard",
    "grouping_per_run": [19, 20],
    "false_merge_per_run": [0, 0],
    "stable_fail_unresolved": ["hf_01/hf_02", "hr_05/hr_06", "sp_01/sp_02"],
}
BASELINE_C = {
    "architecture": "C",
    "description": "embedding + single resolver",
    "grouping_per_run": [24, 22, 23, 22],
    "false_merge_per_run": [1, 1, 0, 1],
    "architecture_gate": "fail",
    "note": "retrieval_miss=0; failures attributed to resolver",
}


@dataclass
class ShortlistCallTrace:
    signal_id: str
    signal_title: str
    projection_text: str
    canonical_label: str
    ranked: list[dict[str, Any]] = field(default_factory=list)


class SemanticRetrievalShortlist:
    """Drop-in replacement for services._duplicate_guard_shortlist (eval-only)."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        k: int,
        projection: str = PROJECTION_PHENOMENON_V1,
    ):
        self.embedding_provider = embedding_provider
        self.k = k
        self.projection = projection
        self._embedding_by_normalized: dict[str, tuple[float, ...]] = {}
        self.calls: list[ShortlistCallTrace] = []

    def __call__(
        self,
        *,
        signal: Signal,
        canonical_label: str,
    ) -> list[PatternDuplicateGuardCandidate]:
        # Query = safe phenomenon projection. Never embed canonical_label alone.
        projection_text = _signal_projection_text(signal, projection=self.projection)
        query_embedding = self.embedding_provider.embed_texts([projection_text])[0]

        organization_id = signal.establishment.organization_id
        patterns = list(
            OperationalPattern.objects.filter(
                organization_id=organization_id,
                status__in=[
                    OperationalPattern.Status.ACTIVE,
                    OperationalPattern.Status.MERGED,
                ],
            )
        )
        if not patterns:
            self.calls.append(
                ShortlistCallTrace(
                    signal_id=str(signal.id),
                    signal_title=signal.title,
                    projection_text=projection_text,
                    canonical_label=canonical_label,
                )
            )
            return []

        index = self._build_index(patterns=patterns, organization_id=organization_id)
        ranked = _rank_terminals(index=index, query_embedding=query_embedding)[: self.k]
        candidates: list[PatternDuplicateGuardCandidate] = []
        ranked_trace: list[dict[str, Any]] = []
        for candidate in ranked:
            try:
                terminal_id = uuid.UUID(candidate.terminal_key)
            except ValueError:
                continue
            pattern = OperationalPattern.objects.filter(
                id=terminal_id,
                organization_id=organization_id,
                status=OperationalPattern.Status.ACTIVE,
            ).first()
            if pattern is None:
                continue
            candidates.append(
                PatternDuplicateGuardCandidate(
                    id=pattern.id,
                    label=pattern.label,
                    normalized_label=pattern.normalized_label,
                    semantic_label=pattern.semantic_label,
                    normalized_semantic_label=pattern.normalized_semantic_label,
                    score=candidate.score,
                )
            )
            ranked_trace.append(
                {
                    "pattern_id": str(pattern.id),
                    "semantic_label": pattern.semantic_label,
                    "score": candidate.score,
                    "matched_alias_id": candidate.matched_alias_id,
                }
            )

        self.calls.append(
            ShortlistCallTrace(
                signal_id=str(signal.id),
                signal_title=signal.title,
                projection_text=projection_text,
                canonical_label=canonical_label,
                ranked=ranked_trace,
            )
        )
        return candidates

    def _build_index(
        self,
        *,
        patterns: list[OperationalPattern],
        organization_id: uuid.UUID,
    ) -> list[IndexedAlias]:
        texts: list[str] = []
        pending: list[OperationalPattern] = []
        for pattern in patterns:
            key = pattern.normalized_semantic_label
            if key not in self._embedding_by_normalized:
                texts.append(pattern.semantic_label)
                pending.append(pattern)
        if texts:
            embeddings = self.embedding_provider.embed_texts(texts)
            for pattern, embedding in zip(pending, embeddings, strict=True):
                self._embedding_by_normalized[pattern.normalized_semantic_label] = tuple(
                    embedding
                )

        index: list[IndexedAlias] = []
        for pattern in patterns:
            terminal = _resolve_terminal_active(
                pattern=pattern,
                organization_id=organization_id,
            )
            if terminal is None:
                continue
            embedding = self._embedding_by_normalized.get(
                pattern.normalized_semantic_label
            )
            if embedding is None:
                continue
            index.append(
                IndexedAlias(
                    alias_id=str(pattern.id),
                    semantic_label=pattern.semantic_label,
                    normalized_semantic_label=pattern.normalized_semantic_label,
                    terminal_key=str(terminal.id),
                    source=(
                        "active"
                        if pattern.status == OperationalPattern.Status.ACTIVE
                        else "merged"
                    ),
                    embedding=embedding,
                )
            )
        return index


def choose_d_shortlist_k(recall_by_k: dict[int, dict[str, Any]]) -> int | None:
    """Pick the smallest K in {3,5} with satisfying oracle recall."""
    for k in D_K_CANDIDATES:
        metric = recall_by_k.get(k)
        if metric is None:
            continue
        rate = metric.get("rate")
        if rate is not None and rate >= 0.98:
            return k
    return None


def evaluate_architecture_d_k_selection(
    *,
    embedding_provider_name: str = "openai",
    embedding_model: str | None = None,
) -> dict[str, Any]:
    """Compare K=3 vs K=5 using Phase 0 oracle retrieval recall (no LLM)."""
    if embedding_provider_name == "openai":
        _assert_architecture_d_spike_enabled()

    previous_retrieval_opt_in = os.environ.get(ANALYTICS_PATTERN_RETRIEVAL_SPIKE_OPT_IN_ENV)
    # D opt-in authorizes reuse of the Phase 0 embedding eval path.
    if embedding_provider_name == "openai":
        os.environ[ANALYTICS_PATTERN_RETRIEVAL_SPIKE_OPT_IN_ENV] = "1"
    try:
        payload = evaluate_analytics_pattern_retrieval_spike(
            scenario_ids=None,
            projection=PROJECTION_PHENOMENON_V1,
            provider_name=embedding_provider_name,
            embedding_model=embedding_model or DEFAULT_EMBEDDING_MODEL,
            also_run_ablations=False,
            archive=False,
        )
    finally:
        if embedding_provider_name == "openai":
            if previous_retrieval_opt_in is None:
                os.environ.pop(ANALYTICS_PATTERN_RETRIEVAL_SPIKE_OPT_IN_ENV, None)
            else:
                os.environ[ANALYTICS_PATTERN_RETRIEVAL_SPIKE_OPT_IN_ENV] = (
                    previous_retrieval_opt_in
                )

    primary = payload["reports"][0]
    recall = {int(k): primary["recall"][str(k)] for k in D_K_CANDIDATES}
    chosen = choose_d_shortlist_k(recall)
    return {
        "schema_version": SPIKE_SCHEMA_VERSION,
        "phase": "d0_k_selection",
        "projection": PROJECTION_PHENOMENON_V1,
        "embedding_provider": primary["embedding_provider"],
        "embedding_model": primary["embedding_model"],
        "recall": {str(k): recall[k] for k in D_K_CANDIDATES},
        "chosen_k": chosen,
        "status": "pass" if chosen is not None else "fail",
        "note": (
            f"Freeze K={chosen} (smallest satisfying among {list(D_K_CANDIDATES)})."
            if chosen is not None
            else "Neither K=3 nor K=5 reached satisfying oracle recall."
        ),
    }


def evaluate_architecture_d_spike(
    *,
    scenario_ids: list[str] | None = None,
    runs: int = 4,
    k: int | None = None,
    embedding_provider_name: str = "openai",
    classifier_provider_name: str = "configured",
    embedding_model: str | None = None,
    classifier_model: str | None = None,
    archive: bool = False,
    archive_dir: Path | None = None,
    skip_k_selection: bool = False,
) -> dict[str, Any]:
    """Run Architecture D: classifier + semantic shortlist + current duplicate guard."""
    if embedding_provider_name == "openai" or classifier_provider_name == "configured":
        _assert_architecture_d_spike_enabled()
    if classifier_provider_name == "configured":
        if os.environ.get(ANALYTICS_PATTERN_EVAL_OPT_IN_ENV) != "1":
            raise RuntimeError(
                "Configured classifier runs also require "
                f"{ANALYTICS_PATTERN_EVAL_OPT_IN_ENV}=1."
            )

    if skip_k_selection and k is not None:
        k_report = {
            "phase": "d0_k_selection",
            "status": "skipped",
            "chosen_k": k,
            "note": f"K={k} provided explicitly; selection skipped.",
            "recall": {},
        }
        frozen_k = k
    else:
        k_report = evaluate_architecture_d_k_selection(
            embedding_provider_name=embedding_provider_name,
            embedding_model=embedding_model,
        )
        frozen_k = k if k is not None else k_report["chosen_k"]
    if frozen_k is None:
        raise RuntimeError("Architecture D blocked: no satisfying K in {3,5}.")

    embedding_provider = _embedding_provider(
        embedding_provider_name,
        embedding_model=embedding_model,
    )
    model = classifier_model or DEFAULT_CLASSIFIER_MODEL
    run_reports: list[dict[str, Any]] = []

    settings_overrides: dict[str, Any] = {
        "HOUSTON_AI_ANALYTICS_PATTERN_MODEL": model,
        "HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MAX_CANDIDATES": frozen_k,
    }

    with override_settings(**settings_overrides):
        for run_index in range(1, runs + 1):
            shortlist = SemanticRetrievalShortlist(
                embedding_provider=embedding_provider,
                k=frozen_k,
                projection=PROJECTION_PHENOMENON_V1,
            )
            with patch(
                "houston.analytics.services._duplicate_guard_shortlist",
                shortlist,
            ):
                report = evaluate_analytics_pattern_corpus(
                    scenario_ids=scenario_ids,
                    provider_name=(
                        "configured"
                        if classifier_provider_name == "configured"
                        else "fake"
                    ),
                    rollback=True,
                    archive=False,
                )
            run_reports.append(
                _run_report_from_corpus(
                    run_index=run_index,
                    report=report,
                    shortlist=shortlist,
                    frozen_k=frozen_k,
                )
            )

    aggregate = _aggregate_runs(run_reports)
    payload = {
        "schema_version": SPIKE_SCHEMA_VERSION,
        "architecture": "D",
        "description": (
            "CURRENT LABEL-FIRST + SEMANTIC RETRIEVAL + CURRENT DUPLICATE GUARD"
        ),
        "shortlist_strategy": SHORTLIST_STRATEGY,
        "projection": PROJECTION_PHENOMENON_V1,
        "k_selection": k_report,
        "frozen_k": frozen_k,
        "embedding_provider": getattr(embedding_provider, "provider", ""),
        "embedding_model": getattr(embedding_provider, "model", ""),
        "classifier_provider": classifier_provider_name,
        "classifier_model": model,
        "duplicate_guard": {
            "prompt_version": "analytics_pattern_duplicate_guard_v2",
            "schema_version": "analytics_pattern_duplicate_guard_v1",
            "replaced": "token_overlap_v1",
            "replacement": SHORTLIST_STRATEGY,
        },
        "baselines": {"A": BASELINE_A, "C": BASELINE_C},
        "runs": run_reports,
        "aggregate": aggregate,
        "focus_pairs": _focus_pairs_across_runs(run_reports),
        "architecture_gate": _architecture_gate(aggregate, run_reports),
        "comparison": _comparison_summary(aggregate),
    }
    if archive:
        write_architecture_d_archive(report=payload, archive_dir=archive_dir)
    return payload


def format_architecture_d_report(payload: dict[str, Any]) -> str:
    lines = [
        "Analytics pattern Architecture D spike",
        f"schema={payload['schema_version']} projection={payload['projection']} "
        f"K={payload['frozen_k']}",
        f"classifier_model={payload['classifier_model']}",
        f"k_selection={payload['k_selection'].get('status')} "
        f"chosen_k={payload['k_selection'].get('chosen_k')}",
        "",
    ]
    for run in payload["runs"]:
        metrics = run["metrics"]
        lines.append(
            f"run{run['run_index']}: grouping="
            f"{metrics['acceptable_grouping_rate']['passed']}/"
            f"{metrics['acceptable_grouping_rate']['total']} "
            f"false_merge={metrics['false_merge_rate'].get('failing_count', 0)}/"
            f"{metrics['false_merge_rate']['total']} "
            f"tech={metrics['technical_success_rate']['passed']}/"
            f"{metrics['technical_success_rate']['total']} "
            f"retrieval_miss_est={run.get('retrieval_miss_estimate', 0)}"
        )
    lines.append("")
    agg = payload["aggregate"]
    lines.append(
        f"aggregate grouping={agg['acceptable_grouping_rate']['passed']}/"
        f"{agg['acceptable_grouping_rate']['total']} "
        f"false_merge={agg['false_merge_rate'].get('failing_count', 0)}/"
        f"{agg['false_merge_rate']['total']}"
    )
    lines.append(f"architecture_gate={payload['architecture_gate']['status']}")
    for reason in payload["architecture_gate"].get("reasons", []):
        lines.append(f"  - {reason}")
    lines.append("focus_pairs:")
    for key, info in payload["focus_pairs"].items():
        lines.append(
            f"  {key}: linked_runs={info['linked_runs']}/{info['total_runs']}"
        )
    lines.append("comparison:")
    for line in payload["comparison"].get("notes", []):
        lines.append(f"  - {line}")
    return "\n".join(lines).rstrip() + "\n"


def write_architecture_d_archive(
    *,
    report: dict[str, Any],
    archive_dir: Path | None = None,
) -> Path:
    target_dir = archive_dir or ANALYTICS_PATTERN_ARCHITECTURE_D_SPIKE_ARCHIVE_DIR
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = target_dir / f"phase-d-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    body = {"archived_at": stamp, **report}
    path = run_dir / "phase-d-report.json"
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "SUMMARY.md").write_text(
        format_architecture_d_report(report),
        encoding="utf-8",
    )
    (target_dir / "phase-d-latest.json").write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _run_report_from_corpus(
    *,
    run_index: int,
    report: Any,
    shortlist: SemanticRetrievalShortlist,
    frozen_k: int,
) -> dict[str, Any]:
    report_dict = analytics_pattern_corpus_eval_report_to_dict(report)
    metrics = report_dict["metrics"]
    signals = []
    for scenario in report_dict["scenarios"]:
        for signal in scenario["signals"]:
            signals.append({**signal, "scenario_id": scenario["scenario_id"]})

    return {
        "run_index": run_index,
        "frozen_k": frozen_k,
        "metrics": {
            "false_merge_rate": metrics["false_merge_rate"],
            "acceptable_grouping_rate": metrics["acceptable_grouping_rate"],
            "technical_success_rate": metrics["technical_success_rate"],
            "duplicate_guard_reuse_count": metrics.get("duplicate_guard_reuse_count"),
            "duplicate_guard_created_count": metrics.get(
                "duplicate_guard_created_count"
            ),
            "duplicate_guard_skipped_count": metrics.get(
                "duplicate_guard_skipped_count"
            ),
            "duplicate_guard_fallback_count": metrics.get(
                "duplicate_guard_fallback_count"
            ),
            "duplicate_guard_reason_code_distribution": metrics.get(
                "duplicate_guard_reason_code_distribution"
            ),
            "fragmentation_false_separation_count": metrics.get(
                "fragmentation_false_separation_count"
            ),
        },
        "evaluation_status": report_dict["evaluation_status"],
        "errors": report_dict["errors"],
        "focus_pairs": _focus_pair_summary(signals),
        "stable_fail": _stable_fail_summary(signals),
        "retrieval_miss_estimate": _estimate_retrieval_misses(
            signals=signals,
            shortlist_calls=shortlist.calls,
            k=frozen_k,
        ),
        "shortlist_call_count": len(shortlist.calls),
        "shortlist_calls": [
            {
                "signal_id": call.signal_id,
                "signal_title": call.signal_title,
                "canonical_label": call.canonical_label,
                "projection_text": call.projection_text,
                "ranked": call.ranked,
            }
            for call in shortlist.calls
        ],
        "signals": signals,
        "scenarios": report_dict["scenarios"],
    }


def _estimate_retrieval_misses(
    *,
    signals: list[dict[str, Any]],
    shortlist_calls: list[ShortlistCallTrace],
    k: int,
) -> int:
    """Count shortlist misses for signals that expected an existing pattern key."""
    misses = 0
    for signal in signals:
        expected_key = signal.get("expected_pattern_key")
        if not expected_key:
            continue
        if (
            signal.get("duplicate_guard_decision") == "skipped"
            and signal.get("duplicate_guard_reason") == "exact_semantic_alias"
        ):
            continue
        title = _corpus_signal_title(signal["scenario_id"], signal["ref"])
        call = next(
            (item for item in shortlist_calls if item.signal_title == title),
            None,
        )
        if call is None:
            continue
        scenario = get_analytics_pattern_scenario(signal["scenario_id"])
        expected_label = next(
            (
                raw["label"]
                for raw in scenario.get("initial_patterns", [])
                if raw["pattern_key"] == expected_key
            ),
            None,
        )
        if expected_label is None:
            continue
        ranked_labels = {
            normalize_pattern_label(item["semantic_label"]) for item in call.ranked[:k]
        }
        if normalize_pattern_label(expected_label) not in ranked_labels:
            misses += 1
    return misses


def _corpus_signal_title(scenario_id: str, ref: str) -> str:
    scenario = get_analytics_pattern_scenario(scenario_id)
    for signal in scenario["signals"]:
        if signal["ref"] == ref:
            return signal["title"]
    return ""


def _focus_pair_summary(signals: list[dict[str, Any]]) -> dict[str, Any]:
    by_ref = {(s["scenario_id"], s["ref"]): s for s in signals}
    out: dict[str, Any] = {}
    for scenario_id, first_ref, second_ref in FOCUS_PAIRS:
        first = by_ref.get((scenario_id, first_ref))
        second = by_ref.get((scenario_id, second_ref))
        linked = _same_label(first, second)
        out[f"{scenario_id}:{first_ref}/{second_ref}"] = {
            "linked": linked,
            "first_label": (first or {}).get("assigned_label", ""),
            "second_label": (second or {}).get("assigned_label", ""),
            "first_guard": (first or {}).get("duplicate_guard_decision", ""),
            "second_guard": (second or {}).get("duplicate_guard_decision", ""),
            "first_reason_code": (first or {}).get("duplicate_guard_reason_code"),
            "second_reason_code": (second or {}).get("duplicate_guard_reason_code"),
        }
    return out


def _stable_fail_summary(signals: list[dict[str, Any]]) -> dict[str, Any]:
    by_ref = {(s["scenario_id"], s["ref"]): s for s in signals}
    pairs = []
    for scenario_id, first_ref, second_ref in STABLE_FAIL_PAIRS:
        first = by_ref.get((scenario_id, first_ref))
        second = by_ref.get((scenario_id, second_ref))
        pairs.append(
            {
                "scenario_id": scenario_id,
                "pair": [first_ref, second_ref],
                "linked": _same_label(first, second),
                "first_label": (first or {}).get("assigned_label", ""),
                "second_label": (second or {}).get("assigned_label", ""),
            }
        )
    return {"pairs": pairs}


def _same_label(first: dict[str, Any] | None, second: dict[str, Any] | None) -> bool:
    if not first or not second:
        return False
    if not first.get("technical_success") or not second.get("technical_success"):
        return False
    return normalize_pattern_label(first.get("assigned_label") or "") == (
        normalize_pattern_label(second.get("assigned_label") or "")
    )


def _focus_pairs_across_runs(run_reports: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [f"{s}:{a}/{b}" for s, a, b in FOCUS_PAIRS]
    out: dict[str, Any] = {}
    for key in keys:
        linked_runs = 0
        for run in run_reports:
            if run["focus_pairs"].get(key, {}).get("linked"):
                linked_runs += 1
        out[key] = {
            "linked_runs": linked_runs,
            "total_runs": len(run_reports),
        }
    return out


def _aggregate_runs(run_reports: list[dict[str, Any]]) -> dict[str, Any]:
    grouping_passed = sum(
        run["metrics"]["acceptable_grouping_rate"]["passed"] for run in run_reports
    )
    grouping_total = sum(
        run["metrics"]["acceptable_grouping_rate"]["total"] for run in run_reports
    )
    false_failed = sum(
        run["metrics"]["false_merge_rate"].get("failing_count", 0) for run in run_reports
    )
    false_total = sum(run["metrics"]["false_merge_rate"]["total"] for run in run_reports)
    tech_passed = sum(
        run["metrics"]["technical_success_rate"]["passed"] for run in run_reports
    )
    tech_total = sum(
        run["metrics"]["technical_success_rate"]["total"] for run in run_reports
    )
    per_run_grouping = [
        run["metrics"]["acceptable_grouping_rate"]["passed"] for run in run_reports
    ]
    per_run_false = [
        run["metrics"]["false_merge_rate"].get("failing_count", 0) for run in run_reports
    ]
    return {
        "acceptable_grouping_rate": {
            "passed": grouping_passed,
            "total": grouping_total,
            "rate": None if grouping_total == 0 else grouping_passed / grouping_total,
        },
        "false_merge_rate": {
            "passed": false_total - false_failed,
            "total": false_total,
            "failing_count": false_failed,
            "rate": None if false_total == 0 else false_failed / false_total,
        },
        "technical_success_rate": {
            "passed": tech_passed,
            "total": tech_total,
            "rate": None if tech_total == 0 else tech_passed / tech_total,
        },
        "per_run_grouping_passed": per_run_grouping,
        "per_run_false_merge": per_run_false,
        "min_run_grouping_passed": min(per_run_grouping) if per_run_grouping else 0,
        "max_run_false_merge": max(per_run_false) if per_run_false else 0,
        "stable_fail_pair_pass_counts": _stable_fail_pair_pass_counts(run_reports),
    }


def _stable_fail_pair_pass_counts(run_reports: list[dict[str, Any]]) -> dict[str, int]:
    counts = {f"{s}:{a}/{b}": 0 for s, a, b in STABLE_FAIL_PAIRS}
    for run in run_reports:
        for pair in run["stable_fail"]["pairs"]:
            key = f"{pair['scenario_id']}:{pair['pair'][0]}/{pair['pair'][1]}"
            if pair["linked"]:
                counts[key] = counts.get(key, 0) + 1
    return counts


def _architecture_gate(
    aggregate: dict[str, Any],
    run_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    if aggregate["max_run_false_merge"] > 0 or aggregate["false_merge_rate"].get(
        "failing_count", 0
    ):
        reasons.append("false_merge != 0 (imperative)")
    baseline_max = 20
    if aggregate["min_run_grouping_passed"] <= baseline_max:
        reasons.append(
            "grouping not better than baseline A "
            f"(min_run={aggregate['min_run_grouping_passed']} <= {baseline_max})"
        )
    tech = aggregate["technical_success_rate"]
    if tech["rate"] is not None and tech["rate"] < 0.98:
        reasons.append("technical_success_rate < 0.98")
    pair_counts = aggregate["stable_fail_pair_pass_counts"]
    improved = sum(
        1 for count in pair_counts.values() if count >= max(1, len(run_reports) // 2)
    )
    if improved < 1 and aggregate["min_run_grouping_passed"] <= baseline_max:
        reasons.append("no structural improvement on former lexical/stable misses")
    status = "pass" if not reasons else "fail"
    return {"status": status, "reasons": reasons, "stable_fail_improved_pairs": improved}


def _comparison_summary(aggregate: dict[str, Any]) -> dict[str, Any]:
    notes = [
        f"A baseline grouping ~{BASELINE_A['grouping_per_run']}/26, FM=0",
        f"C Phase1 grouping {BASELINE_C['grouping_per_run']}/26, "
        f"FM={BASELINE_C['false_merge_per_run']}",
        f"D min_run_grouping={aggregate['min_run_grouping_passed']}/26, "
        f"per_run_FM={aggregate['per_run_false_merge']}",
    ]
    if (
        aggregate["max_run_false_merge"] == 0
        and aggregate["min_run_grouping_passed"] > 20
    ):
        notes.append("D beats A on grouping with FM=0 → architectural candidate vs A.")
    if aggregate["max_run_false_merge"] == 0 and max(BASELINE_C["false_merge_per_run"]) > 0:
        notes.append("D safer than C on false-merge (C had FM>0).")
    return {"notes": notes}


def _signal_projection_text(signal: Signal, *, projection: str) -> str:
    activity = signal.activity_subject.label if signal.activity_subject_id else ""
    parts = [
        signal.title or "",
        signal.structured_summary or "",
        signal.issue_focus or "",
        activity,
    ]
    if projection != PROJECTION_PHENOMENON_V1:
        raise ValueError(f"Architecture D spike only supports {PROJECTION_PHENOMENON_V1}")
    return "\n".join(part.strip() for part in parts if part and str(part).strip())


def _resolve_terminal_active(
    *,
    pattern: OperationalPattern,
    organization_id: uuid.UUID,
) -> OperationalPattern | None:
    if pattern.status == OperationalPattern.Status.ACTIVE:
        return pattern
    if pattern.status != OperationalPattern.Status.MERGED:
        return None
    seen = {pattern.id}
    current = pattern
    for _ in range(5):
        if current.merged_into_id is None:
            return None
        target = OperationalPattern.objects.filter(pk=current.merged_into_id).first()
        if target is None or target.id in seen:
            return None
        seen.add(target.id)
        if target.organization_id != organization_id:
            return None
        if target.status == OperationalPattern.Status.ACTIVE:
            return target
        if target.status != OperationalPattern.Status.MERGED:
            return None
        current = target
    return None


def _embedding_provider(
    provider_name: str,
    *,
    embedding_model: str | None,
) -> EmbeddingProvider:
    normalized = provider_name.strip().lower()
    if normalized == "fake":
        return FakeHashEmbeddingProvider()
    if normalized == "openai":
        return OpenAIEmbeddingProvider(model=embedding_model or DEFAULT_EMBEDDING_MODEL)
    raise ValueError("embedding provider must be 'fake' or 'openai'")


def _assert_architecture_d_spike_enabled() -> None:
    if os.environ.get(ANALYTICS_PATTERN_ARCHITECTURE_D_SPIKE_OPT_IN_ENV) != "1":
        raise RuntimeError(
            "Architecture D OpenAI spike is opt-in only. Set "
            f"{ANALYTICS_PATTERN_ARCHITECTURE_D_SPIKE_OPT_IN_ENV}=1."
        )
    if not (settings.OPENAI_API_KEY or "").strip():
        raise RuntimeError("OPENAI_API_KEY is not configured.")
