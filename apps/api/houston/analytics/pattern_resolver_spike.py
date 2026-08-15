"""Eval-only Phase 1 spike: semantic retrieval + single GPT-5-mini resolver.

No production runtime, migrations, or pgvector. Uses frozen Phase 0 settings.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from django.conf import settings

from houston.analytics.labels import normalize_pattern_label
from houston.analytics.pattern_retrieval_spike import (
    DEFAULT_EMBEDDING_MODEL,
    K_VALUES,
    PROJECTION_PHENOMENON_V1,
    STABLE_FAIL_PAIRS,
    EmbeddingProvider,
    EmbeddingProviderError,
    FakeHashEmbeddingProvider,
    IndexedAlias,
    OpenAIEmbeddingProvider,
    _rank_terminals,
    build_signal_projection_text,
)
from houston.testing.analytics_pattern_corpus import (
    AnalyticsPatternCorpusValidationError,
    get_analytics_pattern_scenario,
    list_analytics_pattern_scenario_ids,
    validate_analytics_pattern_corpus,
)

ANALYTICS_PATTERN_RESOLVER_SPIKE_OPT_IN_ENV = "HOUSTON_RUN_ANALYTICS_PATTERN_RESOLVER_SPIKE"
ANALYTICS_PATTERN_RESOLVER_SPIKE_ARCHIVE_DIR = (
    Path(__file__).resolve().parents[2]
    / ".artifacts"
    / "analytics-pattern-resolver-spike"
)

SPIKE_SCHEMA_VERSION = "analytics_pattern_resolver_spike_v1"
RESOLVER_PROMPT_VERSION = "analytics_pattern_resolver_spike_v1"
RESOLVER_SCHEMA_VERSION = "analytics_pattern_resolver_spike_v1"
DEFAULT_RESOLVER_MODEL = "gpt-5-mini"
_GPT5_MINI_MODEL_RE = re.compile(r"^gpt-5-mini(?:-\d{4}-\d{2}-\d{2})?$")

MAIN_THRESHOLDS = {
    "false_merge_rate": ("lt", 0.05),
    "acceptable_grouping_rate": ("gte", 0.85),
    "technical_success_rate": ("gte", 0.98),
}

_RESOLVER_SYSTEM_PROMPT = """\
Tu classes un Signal opérationnel Houston dans un motif analytique.
Réponds uniquement avec le JSON strict demandé.

Tu reçois le Signal (champs safe) et une shortlist de candidats locaux c1..cK.
Décide uniquement :
- reuse_candidate: le Signal est le même phénomène opérationnel / la même unité
  managériale qu'un candidat de la shortlist;
- create_pattern: aucun candidat n'est compatible; propose un canonical_label court.

Règles:
- False merge est pire que fragmentation.
- Ne réutilise que si le phénomène, le failure mode, le processus/étape et l'état
  opérationnel sont compatibles.
- Une différence de wording, instance, localisation, SKU ou formulation plus
  spécifique ne justifie pas create_pattern à elle seule si le phénomène est le même.
- Une frontière explicite de processus, failure mode, état ou cause connue impose
  create_pattern.
- Ne déduis pas une cause racine absente du Signal.
- candidate_ref doit être l'un des ids locaux fournis (c1..cK).
- canonical_label: phénomène court, sans établissement/BU, sans détail incident.
"""


class ResolverProviderError(RuntimeError):
    error_code = "resolver_provider_error"


class ResolverInvalidOutputError(ResolverProviderError):
    error_code = "invalid_structured_output"


@dataclass(frozen=True)
class ResolverDecision:
    result_type: str
    candidate_ref: str | None = None
    canonical_label: str | None = None


@dataclass(frozen=True)
class SignalResolverResult:
    scenario_id: str
    signal_ref: str
    technical_success: bool
    assigned_pattern_key: str | None
    assigned_label: str
    expected_pattern_key: str | None
    expected_new_pattern_label: str
    decision_kind: str
    candidate_refs: tuple[str, ...]
    ranked_terminal_keys: tuple[str, ...]
    resolver_result_type: str
    chosen_candidate_ref: str | None
    error_code: str = ""
    retrieval_miss: bool = False
    resolver_create_despite_candidate: bool = False
    wrong_reuse: bool = False


class ResolverProvider(Protocol):
    model: str

    def resolve(self, *, input_payload: dict[str, Any]) -> dict[str, Any]: ...


class FakeResolverProvider:
    provider = "fake"
    model = "fake-resolver"

    def __init__(self, *, scripted: dict[str, dict[str, Any]] | None = None):
        self._scripted = scripted or {}
        self.calls: list[dict[str, Any]] = []

    def resolve(self, *, input_payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(input_payload)
        signal_ref = input_payload.get("signal_ref", "")
        if signal_ref in self._scripted:
            return dict(self._scripted[signal_ref])
        candidates = input_payload.get("candidates") or []
        if candidates:
            return {
                "result_type": "reuse_candidate",
                "candidate_ref": candidates[0]["candidate_ref"],
                "canonical_label": None,
            }
        return {
            "result_type": "create_pattern",
            "candidate_ref": None,
            "canonical_label": "Operational pattern",
        }


class OpenAIResolverProvider:
    provider = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 30,
    ):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model = model or DEFAULT_RESOLVER_MODEL
        self.timeout_seconds = timeout_seconds
        self._client: Any | None = None
        self.calls: list[dict[str, Any]] = []

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ResolverProviderError("OpenAI API key is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ResolverProviderError("OpenAI SDK is not installed.") from exc
        self._client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
        return self._client

    def resolve(self, *, input_payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(input_payload)
        sampling: dict[str, float] = {}
        if not _GPT5_MINI_MODEL_RE.fullmatch((self.model or "").strip()):
            sampling["temperature"] = 0.0
        try:
            response = self._get_client().chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _RESOLVER_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(input_payload, ensure_ascii=False),
                    },
                ],
                response_format=_resolver_response_format(),
                **sampling,
            )
        except Exception as exc:  # noqa: BLE001
            raise ResolverProviderError(
                f"OpenAI resolver request failed: {exc.__class__.__name__}"
            ) from exc
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ResolverInvalidOutputError("OpenAI returned an empty resolver response.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ResolverInvalidOutputError("OpenAI returned invalid resolver JSON.") from exc


def parse_resolver_decision(
    payload: dict[str, Any],
    *,
    allowed_refs: set[str],
) -> ResolverDecision:
    result_type = payload.get("result_type")
    candidate_ref = payload.get("candidate_ref")
    canonical_label = payload.get("canonical_label")
    if set(payload) - {"result_type", "candidate_ref", "canonical_label"}:
        raise ResolverInvalidOutputError("Resolver response has unexpected keys.")
    if result_type == "reuse_candidate":
        if not isinstance(candidate_ref, str) or candidate_ref not in allowed_refs:
            raise ResolverInvalidOutputError("reuse_candidate outside shortlist.")
        if canonical_label not in (None, ""):
            raise ResolverInvalidOutputError(
                "reuse_candidate must not include canonical_label."
            )
        return ResolverDecision(result_type="reuse_candidate", candidate_ref=candidate_ref)
    if result_type == "create_pattern":
        if candidate_ref not in (None, ""):
            raise ResolverInvalidOutputError(
                "create_pattern must not include candidate_ref."
            )
        if not isinstance(canonical_label, str) or not canonical_label.strip():
            raise ResolverInvalidOutputError("create_pattern requires canonical_label.")
        cleaned = canonical_label.strip()
        if len(cleaned) > 255:
            raise ResolverInvalidOutputError("canonical_label is too long.")
        return ResolverDecision(result_type="create_pattern", canonical_label=cleaned)
    raise ResolverInvalidOutputError("Resolver response discriminator invalid.")


def evaluate_analytics_pattern_resolver_spike(
    *,
    scenario_ids: list[str] | None = None,
    runs: int = 4,
    k: int = 1,
    projection: str = PROJECTION_PHENOMENON_V1,
    embedding_provider_name: str = "openai",
    resolver_provider_name: str = "openai",
    embedding_model: str | None = None,
    resolver_model: str | None = None,
    archive: bool = False,
    archive_dir: Path | None = None,
) -> dict[str, Any]:
    validation_errors = validate_analytics_pattern_corpus()
    if validation_errors:
        raise AnalyticsPatternCorpusValidationError("; ".join(validation_errors))
    if k not in K_VALUES:
        raise ValueError(f"k must be one of {K_VALUES}")
    selected = _selected_scenario_ids(scenario_ids)
    if resolver_provider_name == "openai" or embedding_provider_name == "openai":
        _assert_resolver_spike_enabled()

    embedding_provider = _embedding_provider(
        embedding_provider_name,
        embedding_model=embedding_model,
    )
    run_reports = []
    for run_index in range(1, runs + 1):
        resolver_provider = _resolver_provider(
            resolver_provider_name,
            resolver_model=resolver_model,
        )
        run_reports.append(
            _evaluate_run(
                run_index=run_index,
                scenario_ids=selected,
                k=k,
                projection=projection,
                embedding_provider=embedding_provider,
                resolver_provider=resolver_provider,
            )
        )

    aggregate = _aggregate_runs(run_reports)
    payload = {
        "schema_version": SPIKE_SCHEMA_VERSION,
        "resolver_prompt_version": RESOLVER_PROMPT_VERSION,
        "resolver_schema_version": RESOLVER_SCHEMA_VERSION,
        "frozen_from_phase0": {
            "projection": projection,
            "k": k,
            "embedding_model": getattr(embedding_provider, "model", ""),
        },
        "embedding_provider": getattr(embedding_provider, "provider", ""),
        "resolver_provider": resolver_provider_name,
        "resolver_model": resolver_model
        or getattr(_resolver_provider(resolver_provider_name, resolver_model=None), "model", ""),
        "runs": run_reports,
        "aggregate": aggregate,
        "architecture_gate": _architecture_gate(aggregate, run_reports),
        "product_gate": _product_gate(aggregate, run_reports),
    }
    if archive:
        write_resolver_spike_archive(report=payload, archive_dir=archive_dir)
    return payload


def format_resolver_spike_report(payload: dict[str, Any]) -> str:
    lines = [
        "Analytics pattern resolver spike (Phase 1)",
        (
            f"schema={payload['schema_version']} "
            f"projection={payload['frozen_from_phase0']['projection']} "
            f"K={payload['frozen_from_phase0']['k']}"
        ),
        f"resolver_model={payload['resolver_model']}",
        "",
    ]
    for run in payload["runs"]:
        metrics = run["metrics"]
        lines.append(
            f"run{run['run_index']}: grouping="
            f"{metrics['acceptable_grouping_rate']['passed']}/"
            f"{metrics['acceptable_grouping_rate']['total']} "
            f"false_merge={metrics['false_merge_rate']['failing_count']}/"
            f"{metrics['false_merge_rate']['total']} "
            f"tech={metrics['technical_success_rate']['passed']}/"
            f"{metrics['technical_success_rate']['total']}"
        )
    lines.append("")
    agg = payload["aggregate"]
    lines.append(
        f"aggregate grouping={agg['acceptable_grouping_rate']['passed']}/"
        f"{agg['acceptable_grouping_rate']['total']} "
        f"false_merge={agg['false_merge_rate']['failing_count']}/"
        f"{agg['false_merge_rate']['total']}"
    )
    lines.append(f"architecture_gate={payload['architecture_gate']['status']}")
    for reason in payload["architecture_gate"].get("reasons", []):
        lines.append(f"  - {reason}")
    lines.append(f"product_gate={payload['product_gate']['status']}")
    for reason in payload["product_gate"].get("reasons", []):
        lines.append(f"  - {reason}")
    return "\n".join(lines).rstrip() + "\n"


def write_resolver_spike_archive(
    *,
    report: dict[str, Any],
    archive_dir: Path | None = None,
) -> Path:
    target_dir = archive_dir or ANALYTICS_PATTERN_RESOLVER_SPIKE_ARCHIVE_DIR
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = target_dir / f"phase1-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    body = {"archived_at": stamp, **report}
    path = run_dir / "phase1-report.json"
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "SUMMARY.md").write_text(
        format_resolver_spike_report(report),
        encoding="utf-8",
    )
    latest = target_dir / "phase1-latest.json"
    latest.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _evaluate_run(
    *,
    run_index: int,
    scenario_ids: list[str],
    k: int,
    projection: str,
    embedding_provider: EmbeddingProvider,
    resolver_provider: ResolverProvider,
) -> dict[str, Any]:
    signal_results: list[SignalResolverResult] = []
    errors: list[str] = []
    started = time.monotonic()
    for scenario_id in scenario_ids:
        try:
            signal_results.extend(
                _evaluate_scenario(
                    scenario=get_analytics_pattern_scenario(scenario_id),
                    k=k,
                    projection=projection,
                    embedding_provider=embedding_provider,
                    resolver_provider=resolver_provider,
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{scenario_id}: {exc.__class__.__name__}: {exc}")
    metrics = _run_metrics(signal_results)
    return {
        "run_index": run_index,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "resolver_call_count": len(getattr(resolver_provider, "calls", [])),
        "metrics": metrics,
        "stable_fail": _stable_fail_run_summary(signal_results),
        "errors": errors,
        "signals": [_signal_result_to_dict(result) for result in signal_results],
    }


def _evaluate_scenario(
    *,
    scenario: dict[str, Any],
    k: int,
    projection: str,
    embedding_provider: EmbeddingProvider,
    resolver_provider: ResolverProvider,
) -> list[SignalResolverResult]:
    index: list[IndexedAlias] = []
    pattern_keys_by_id: dict[str, str] = {}
    labels_by_key: dict[str, str] = {}

    initial = scenario.get("initial_patterns", [])
    if initial:
        embeddings = embedding_provider.embed_texts([raw["label"] for raw in initial])
        for raw, embedding in zip(initial, embeddings, strict=True):
            key = raw["pattern_key"]
            alias_id = f"initial:{key}"
            index.append(
                IndexedAlias(
                    alias_id=alias_id,
                    semantic_label=raw["label"],
                    normalized_semantic_label=normalize_pattern_label(raw["label"]),
                    terminal_key=key,
                    source="initial",
                    embedding=tuple(embedding),
                )
            )
            pattern_keys_by_id[key] = key
            labels_by_key[key] = raw["label"]

    projection_texts = [
        build_signal_projection_text(
            signal=signal,
            scenario=scenario,
            projection=projection,
        )
        for signal in scenario["signals"]
    ]
    query_embeddings = (
        embedding_provider.embed_texts(projection_texts) if projection_texts else []
    )

    results: list[SignalResolverResult] = []
    for signal, projection_text, query_embedding in zip(
        scenario["signals"],
        projection_texts,
        query_embeddings,
        strict=True,
    ):
        ranked = _rank_terminals(index=index, query_embedding=query_embedding)[:k]
        local_map = {
            f"c{offset}": candidate for offset, candidate in enumerate(ranked, start=1)
        }
        allowed_refs = set(local_map)
        expected_pattern_key = signal.get("expected_pattern_key")
        expected_new_label = signal.get("expected_new_pattern_label", "")
        retrieval_miss = bool(
            expected_pattern_key
            and expected_pattern_key
            not in {candidate.terminal_key for candidate in ranked}
        )

        input_payload = {
            "schema_version": RESOLVER_SCHEMA_VERSION,
            "prompt_version": RESOLVER_PROMPT_VERSION,
            "signal_ref": signal["ref"],
            "signal": {
                "title": signal["title"],
                "structured_summary": signal["structured_summary"],
                "issue_focus": signal["issue_focus"],
                "activity_subject": _activity_label(scenario, signal),
            },
            "candidates": [
                {
                    "candidate_ref": ref,
                    "semantic_label": candidate.semantic_label,
                }
                for ref, candidate in local_map.items()
            ],
        }

        try:
            raw_decision = resolver_provider.resolve(input_payload=input_payload)
            decision = parse_resolver_decision(raw_decision, allowed_refs=allowed_refs)
            if decision.result_type == "reuse_candidate":
                assert decision.candidate_ref is not None
                chosen = local_map[decision.candidate_ref]
                assigned_key = chosen.terminal_key
                assigned_label = labels_by_key.get(assigned_key, chosen.semantic_label)
                decision_kind = "reuse"
                create_despite = False
                if expected_pattern_key and assigned_key == expected_pattern_key:
                    wrong_reuse = False
                elif expected_new_label and not expected_pattern_key:
                    # Reused when a new pattern was expected.
                    wrong_reuse = True
                else:
                    wrong_reuse = assigned_key != expected_pattern_key
                result = SignalResolverResult(
                    scenario_id=scenario["id"],
                    signal_ref=signal["ref"],
                    technical_success=True,
                    assigned_pattern_key=(
                        assigned_key if assigned_key in pattern_keys_by_id else None
                    ),
                    assigned_label=assigned_label,
                    expected_pattern_key=expected_pattern_key,
                    expected_new_pattern_label=expected_new_label or "",
                    decision_kind=decision_kind,
                    candidate_refs=tuple(local_map),
                    ranked_terminal_keys=tuple(
                        candidate.terminal_key for candidate in ranked
                    ),
                    resolver_result_type="reuse_candidate",
                    chosen_candidate_ref=decision.candidate_ref,
                    retrieval_miss=retrieval_miss,
                    resolver_create_despite_candidate=create_despite,
                    wrong_reuse=wrong_reuse,
                )
            else:
                assert decision.canonical_label is not None
                label = decision.canonical_label
                normalized = normalize_pattern_label(label)
                existing = next(
                    (
                        alias
                        for alias in index
                        if alias.normalized_semantic_label == normalized
                    ),
                    None,
                )
                if existing is not None:
                    assigned_key = existing.terminal_key
                    assigned_label = labels_by_key.get(
                        assigned_key, existing.semantic_label
                    )
                else:
                    assigned_key = f"created:{uuid.uuid4()}"
                    assigned_label = label
                    embedding = embedding_provider.embed_texts([label])[0]
                    index.append(
                        IndexedAlias(
                            alias_id=assigned_key,
                            semantic_label=label,
                            normalized_semantic_label=normalized,
                            terminal_key=assigned_key,
                            source="resolver_create",
                            embedding=tuple(embedding),
                        )
                    )
                    labels_by_key[assigned_key] = label
                create_despite = bool(ranked)
                wrong_reuse = False
                result = SignalResolverResult(
                    scenario_id=scenario["id"],
                    signal_ref=signal["ref"],
                    technical_success=True,
                    assigned_pattern_key=(
                        None if assigned_key.startswith("created:") else assigned_key
                    ),
                    assigned_label=assigned_label,
                    expected_pattern_key=expected_pattern_key,
                    expected_new_pattern_label=expected_new_label or "",
                    decision_kind="create",
                    candidate_refs=tuple(local_map),
                    ranked_terminal_keys=tuple(
                        candidate.terminal_key for candidate in ranked
                    ),
                    resolver_result_type="create_pattern",
                    chosen_candidate_ref=None,
                    retrieval_miss=retrieval_miss,
                    resolver_create_despite_candidate=create_despite,
                    wrong_reuse=wrong_reuse,
                )
        except (ResolverProviderError, EmbeddingProviderError) as exc:
            result = SignalResolverResult(
                scenario_id=scenario["id"],
                signal_ref=signal["ref"],
                technical_success=False,
                assigned_pattern_key=None,
                assigned_label="",
                expected_pattern_key=expected_pattern_key,
                expected_new_pattern_label=expected_new_label or "",
                decision_kind="error",
                candidate_refs=tuple(local_map),
                ranked_terminal_keys=tuple(
                    candidate.terminal_key for candidate in ranked
                ),
                resolver_result_type="error",
                chosen_candidate_ref=None,
                error_code=getattr(exc, "error_code", exc.__class__.__name__),
                retrieval_miss=retrieval_miss,
            )
        results.append(result)
    return results


def _run_metrics(signal_results: list[SignalResolverResult]) -> dict[str, Any]:
    by_scenario: dict[str, list[SignalResolverResult]] = {}
    for result in signal_results:
        by_scenario.setdefault(result.scenario_id, []).append(result)

    must_link_passed = 0
    must_link_total = 0
    must_not_failed = 0
    must_not_total = 0
    fragmentation = 0
    for scenario_id, results in by_scenario.items():
        scenario = get_analytics_pattern_scenario(scenario_id)
        by_ref = {result.signal_ref: result for result in results}
        for first, second in scenario.get("must_link", []):
            must_link_total += 1
            if _same_assigned_pattern(by_ref[first], by_ref[second]):
                must_link_passed += 1
            else:
                fragmentation += 1
        for first, second in scenario.get("must_not_link", []):
            must_not_total += 1
            if _same_assigned_pattern(by_ref[first], by_ref[second]):
                must_not_failed += 1

    succeeded = sum(1 for result in signal_results if result.technical_success)
    return {
        "false_merge_rate": _rate_metric(
            passed=must_not_total - must_not_failed,
            total=must_not_total,
            metric_name="false_merge_rate",
            failing_count=must_not_failed,
        ),
        "acceptable_grouping_rate": _rate_metric(
            passed=must_link_passed,
            total=must_link_total,
            metric_name="acceptable_grouping_rate",
        ),
        "technical_success_rate": _rate_metric(
            passed=succeeded,
            total=len(signal_results),
            metric_name="technical_success_rate",
        ),
        "fragmentation_false_separation_count": fragmentation,
        "retrieval_miss_count": sum(
            1 for result in signal_results if result.retrieval_miss
        ),
        "resolver_create_despite_candidate_count": sum(
            1
            for result in signal_results
            if result.resolver_create_despite_candidate
        ),
        "wrong_reuse_count": sum(1 for result in signal_results if result.wrong_reuse),
    }


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
    return {
        "acceptable_grouping_rate": _rate_metric(
            passed=grouping_passed,
            total=grouping_total,
            metric_name="acceptable_grouping_rate",
        ),
        "false_merge_rate": _rate_metric(
            passed=false_total - false_failed,
            total=false_total,
            metric_name="false_merge_rate",
            failing_count=false_failed,
        ),
        "technical_success_rate": _rate_metric(
            passed=tech_passed,
            total=tech_total,
            metric_name="technical_success_rate",
        ),
        "per_run_grouping_passed": per_run_grouping,
        "min_run_grouping_passed": min(per_run_grouping) if per_run_grouping else 0,
        "stable_fail_pair_pass_counts": _stable_fail_pair_pass_counts(run_reports),
    }


def _architecture_gate(
    aggregate: dict[str, Any],
    run_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    false_failed = aggregate["false_merge_rate"].get("failing_count", 0)
    if false_failed:
        reasons.append(f"false_merge_failing_count={false_failed}")
    if any(run["metrics"]["false_merge_rate"].get("failing_count", 0) for run in run_reports):
        reasons.append("false_merge in at least one run")
    pair_counts = aggregate["stable_fail_pair_pass_counts"]
    improved = sum(1 for count in pair_counts.values() if count == len(run_reports))
    if improved < 2:
        reasons.append(
            f"stable_fail improvement insufficient: {improved}/3 pairs perfect across runs"
        )
    baseline_max = 20
    if aggregate["min_run_grouping_passed"] <= baseline_max:
        reasons.append(
            "grouping not significantly better than baseline A "
            f"(min_run={aggregate['min_run_grouping_passed']} <= {baseline_max})"
        )
    tech = aggregate["technical_success_rate"]
    if tech["rate"] is not None and tech["rate"] < 0.98:
        reasons.append("technical_success_rate < 0.98")
    status = "pass" if not reasons else "fail"
    # 22/26 stable with 0 FM remains architectural GO candidate.
    if (
        status == "pass"
        and aggregate["min_run_grouping_passed"] >= 22
        and false_failed == 0
    ):
        note = "architectural_go_candidate"
    elif status == "pass":
        note = "improved_but_review"
    else:
        note = "no_go"
    return {"status": status, "note": note, "reasons": reasons}


def _product_gate(
    aggregate: dict[str, Any],
    run_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    if aggregate["false_merge_rate"].get("failing_count", 0):
        reasons.append("false_merge != 0")
    if aggregate["min_run_grouping_passed"] < 23:
        reasons.append(
            f"min_run_grouping={aggregate['min_run_grouping_passed']} < 23"
        )
    if any(run["metrics"]["false_merge_rate"].get("failing_count", 0) for run in run_reports):
        reasons.append("false_merge in at least one run")
    return {
        "status": "pass" if not reasons else "fail",
        "reasons": reasons,
    }


def _stable_fail_run_summary(signal_results: list[SignalResolverResult]) -> dict[str, Any]:
    by_ref = {
        (result.scenario_id, result.signal_ref): result for result in signal_results
    }
    pairs = []
    for scenario_id, first_ref, second_ref in STABLE_FAIL_PAIRS:
        first = by_ref.get((scenario_id, first_ref))
        second = by_ref.get((scenario_id, second_ref))
        linked = bool(
            first
            and second
            and _same_assigned_pattern(first, second)
        )
        pairs.append(
            {
                "scenario_id": scenario_id,
                "pair": [first_ref, second_ref],
                "linked": linked,
                "first_label": first.assigned_label if first else "",
                "second_label": second.assigned_label if second else "",
            }
        )
    return {"pairs": pairs}


def _stable_fail_pair_pass_counts(run_reports: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        f"{scenario}:{a}/{b}": 0 for scenario, a, b in STABLE_FAIL_PAIRS
    }
    for run in run_reports:
        for pair in run["stable_fail"]["pairs"]:
            key = f"{pair['scenario_id']}:{pair['pair'][0]}/{pair['pair'][1]}"
            if pair["linked"]:
                counts[key] = counts.get(key, 0) + 1
    return counts


def _same_assigned_pattern(
    first: SignalResolverResult,
    second: SignalResolverResult,
) -> bool:
    if not first.technical_success or not second.technical_success:
        return False
    return normalize_pattern_label(first.assigned_label) == normalize_pattern_label(
        second.assigned_label
    )


def _rate_metric(
    *,
    passed: int,
    total: int,
    metric_name: str,
    failing_count: int | None = None,
) -> dict[str, Any]:
    if total == 0:
        return {
            "passed": passed,
            "total": total,
            "rate": None,
            "status": "not_applicable",
        }
    rate = (
        failing_count / total
        if metric_name == "false_merge_rate" and failing_count is not None
        else passed / total
    )
    status = "unscored"
    threshold = MAIN_THRESHOLDS.get(metric_name)
    if threshold is not None:
        operator, value = threshold
        status = "pass" if (
            rate < value if operator == "lt" else rate >= value
        ) else "fail"
    payload = {
        "passed": passed,
        "total": total,
        "rate": rate,
        "status": status,
    }
    if failing_count is not None:
        payload["failing_count"] = failing_count
    return payload


def _signal_result_to_dict(result: SignalResolverResult) -> dict[str, Any]:
    return {
        "scenario_id": result.scenario_id,
        "signal_ref": result.signal_ref,
        "technical_success": result.technical_success,
        "assigned_pattern_key": result.assigned_pattern_key,
        "assigned_label": result.assigned_label,
        "expected_pattern_key": result.expected_pattern_key,
        "expected_new_pattern_label": result.expected_new_pattern_label,
        "decision_kind": result.decision_kind,
        "candidate_refs": list(result.candidate_refs),
        "ranked_terminal_keys": list(result.ranked_terminal_keys),
        "resolver_result_type": result.resolver_result_type,
        "chosen_candidate_ref": result.chosen_candidate_ref,
        "error_code": result.error_code,
        "retrieval_miss": result.retrieval_miss,
        "resolver_create_despite_candidate": result.resolver_create_despite_candidate,
        "wrong_reuse": result.wrong_reuse,
    }


def _activity_label(scenario: dict[str, Any], signal: dict[str, Any]) -> str:
    mapping = {
        item["key"]: item["label"] for item in scenario.get("activity_subjects", [])
    }
    return mapping.get(signal["activity_subject_key"], "")


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


def _resolver_provider(
    provider_name: str,
    *,
    resolver_model: str | None,
) -> ResolverProvider:
    normalized = provider_name.strip().lower()
    if normalized == "fake":
        return FakeResolverProvider()
    if normalized == "openai":
        return OpenAIResolverProvider(model=resolver_model or DEFAULT_RESOLVER_MODEL)
    raise ValueError("resolver provider must be 'fake' or 'openai'")


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


def _assert_resolver_spike_enabled() -> None:
    if os.environ.get(ANALYTICS_PATTERN_RESOLVER_SPIKE_OPT_IN_ENV) != "1":
        raise RuntimeError(
            "OpenAI resolver spike is opt-in only. Set "
            f"{ANALYTICS_PATTERN_RESOLVER_SPIKE_OPT_IN_ENV}=1."
        )
    if not (settings.OPENAI_API_KEY or "").strip():
        raise RuntimeError("OPENAI_API_KEY is not configured.")


def _resolver_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "analytics_pattern_resolver_spike",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "result_type": {
                        "type": "string",
                        "enum": ["reuse_candidate", "create_pattern"],
                    },
                    "candidate_ref": {"type": ["string", "null"]},
                    "canonical_label": {"type": ["string", "null"]},
                },
                "required": ["result_type", "candidate_ref", "canonical_label"],
            },
        },
    }
