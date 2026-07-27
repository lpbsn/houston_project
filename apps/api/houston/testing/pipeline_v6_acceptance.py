"""Loaders and strict validation for pipeline V6 Lot 0 acceptance artefacts."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from houston.testing.pipeline_golden_v4 import list_pipeline_golden_v4_case_ids
from houston.testing.pipeline_v6_metrics import (
    LOT_ACCEPTANCE,
    LOT_IDS,
    METRIC_IDS,
    metrics_referenced_by_corpus,
    metrics_referenced_by_truth_tables,
)

CORPUS_PATH = Path(__file__).with_name("pipeline_v6_acceptance_corpus.json")
TRUTH_TABLES_PATH = Path(__file__).with_name("pipeline_v6_truth_tables.json")

CORPUS_SCHEMA_VERSION = "pipeline_v6_acceptance_corpus_v1"
TRUTH_TABLES_SCHEMA_VERSION = "pipeline_v6_truth_tables_v1"

REQUIRED_CASE_IDS: tuple[str, ...] = tuple(f"S15-{i:02d}" for i in range(1, 24)) + ("S15-D1",)

TRUTH_SECTIONS: tuple[str, ...] = (
    "precondition",
    "resolver",
    "persistence",
    "aggregation",
    "errors",
    "context",
)

V6_ROUTING_STATUSES = frozenset({"resolved", "unassigned", None})
V6_OUTCOMES = frozenset(
    {
        None,
        "signals_created",
        "signal_aggregated",
        "no_signal_created",
    }
)


class PipelineV6AcceptanceValidationError(ValueError):
    """Raised when Lot 0 acceptance artefacts fail strict validation."""


@lru_cache(maxsize=1)
def load_pipeline_v6_acceptance_corpus() -> dict[str, Any]:
    with CORPUS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_pipeline_v6_truth_tables() -> dict[str, Any]:
    with TRUTH_TABLES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_pipeline_v6_acceptance_case(case_id: str) -> dict[str, Any]:
    for case in load_pipeline_v6_acceptance_corpus()["cases"]:
        if case["id"] == case_id:
            return case
    raise KeyError(f"Unknown pipeline V6 acceptance case: {case_id}")


def list_pipeline_v6_acceptance_case_ids() -> list[str]:
    return [case["id"] for case in load_pipeline_v6_acceptance_corpus()["cases"]]


def iter_truth_table_rows(
    truth_tables: dict[str, Any] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    data = truth_tables if truth_tables is not None else load_pipeline_v6_truth_tables()
    rows: list[tuple[str, dict[str, Any]]] = []
    for section_name, section_rows in data.get("sections", {}).items():
        for row in section_rows:
            rows.append((section_name, row))
    return rows


def list_truth_table_row_ids() -> list[str]:
    return [row["id"] for _, row in iter_truth_table_rows()]


def get_truth_table_row(row_id: str) -> dict[str, Any]:
    for _section, row in iter_truth_table_rows():
        if row["id"] == row_id:
            return row
    raise KeyError(f"Unknown pipeline V6 truth-table row: {row_id}")


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _validate_observed_v5(label: str, observed: Any, errors: list[str]) -> None:
    _require(isinstance(observed, dict), f"{label}: observed_v5 must be an object", errors)
    if not isinstance(observed, dict):
        return
    executable = observed.get("executable")
    _require(
        isinstance(executable, bool),
        f"{label}: observed_v5.executable must be an explicit boolean",
        errors,
    )
    if executable is False:
        reason = observed.get("reason")
        _require(
            isinstance(reason, str) and bool(reason.strip()),
            f"{label}: observed_v5.reason required when executable is false",
            errors,
        )
    aggregation = observed.get("aggregation")
    if aggregation is not None:
        _validate_aggregation(f"{label}.observed_v5", aggregation, errors)


def _validate_aggregation(label: str, aggregation: Any, errors: list[str]) -> None:
    _require(isinstance(aggregation, dict), f"{label}: aggregation must be an object", errors)
    if not isinstance(aggregation, dict):
        return
    _require(
        "should_aggregate" in aggregation,
        f"{label}: aggregation.should_aggregate is required",
        errors,
    )
    if "should_aggregate" in aggregation:
        _require(
            isinstance(aggregation["should_aggregate"], bool),
            f"{label}: aggregation.should_aggregate must be boolean",
            errors,
        )
    if "aggregate_into_ref" in aggregation:
        ref = aggregation["aggregate_into_ref"]
        _require(
            ref is None or isinstance(ref, str),
            f"{label}: aggregation.aggregate_into_ref must be null or string",
            errors,
        )


def _validate_expected_v6(label: str, expected: Any, errors: list[str]) -> None:
    _require(isinstance(expected, dict), f"{label}: expected_v6 must be an object", errors)
    if not isinstance(expected, dict):
        return
    if "routing_status" in expected:
        status = expected["routing_status"]
        _require(
            status in V6_ROUTING_STATUSES,
            f"{label}: expected_v6.routing_status must be resolved|unassigned|null",
            errors,
        )
    if "outcome" in expected:
        _require(
            expected["outcome"] in V6_OUTCOMES,
            f"{label}: expected_v6.outcome invalid: {expected['outcome']!r}",
            errors,
        )
    if "error_code" in expected:
        code = expected["error_code"]
        _require(
            code is None or (isinstance(code, str) and bool(code.strip())),
            f"{label}: expected_v6.error_code must be null or non-empty string",
            errors,
        )
    if "aggregation" in expected:
        _validate_aggregation(f"{label}.expected_v6", expected["aggregation"], errors)
    if "candidates" in expected:
        _require(
            isinstance(expected["candidates"], list),
            f"{label}: expected_v6.candidates must be a list",
            errors,
        )


def validate_pipeline_v6_acceptance_corpus(
    corpus: dict[str, Any] | None = None,
) -> list[str]:
    data = corpus if corpus is not None else load_pipeline_v6_acceptance_corpus()
    errors: list[str] = []
    _require(
        data.get("schema_version") == CORPUS_SCHEMA_VERSION,
        f"corpus schema_version must be {CORPUS_SCHEMA_VERSION}",
        errors,
    )
    cases = data.get("cases")
    _require(
        isinstance(cases, list) and bool(cases),
        "corpus.cases must be a non-empty list",
        errors,
    )
    if not isinstance(cases, list):
        return errors

    golden_ids = set(list_pipeline_golden_v4_case_ids())
    seen_ids: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        _require(isinstance(case_id, str) and bool(case_id), "case missing id", errors)
        if not isinstance(case_id, str):
            continue
        _require(case_id not in seen_ids, f"duplicate corpus case id: {case_id}", errors)
        seen_ids.add(case_id)
        label = f"case {case_id}"

        _require("observed_v5" in case, f"{label}: missing observed_v5", errors)
        _require("expected_v6" in case, f"{label}: missing expected_v6", errors)
        if "observed_v5" in case:
            _validate_observed_v5(label, case["observed_v5"], errors)
        if "expected_v6" in case:
            _validate_expected_v6(label, case["expected_v6"], errors)

        metrics = case.get("metrics")
        _require(isinstance(metrics, list) and bool(metrics), f"{label}: metrics required", errors)
        if isinstance(metrics, list):
            for metric in metrics:
                _require(
                    metric in METRIC_IDS,
                    f"{label}: metric {metric!r} not in A–J",
                    errors,
                )

        lots = case.get("lots")
        _require(isinstance(lots, list) and bool(lots), f"{label}: lots required", errors)
        if isinstance(lots, list):
            for lot in lots:
                _require(
                    lot in LOT_IDS,
                    f"{label}: lot {lot!r} not in LOT_IDS (lot0–lot10 + lot4b)",
                    errors,
                )

        legacy = case.get("legacy_golden_ids", [])
        _require(isinstance(legacy, list), f"{label}: legacy_golden_ids must be a list", errors)
        if isinstance(legacy, list):
            for golden_id in legacy:
                _require(
                    golden_id in golden_ids,
                    f"{label}: unknown legacy_golden_id {golden_id!r}",
                    errors,
                )

        _require("context" in case, f"{label}: missing context", errors)

    for required_id in REQUIRED_CASE_IDS:
        _require(required_id in seen_ids, f"missing required case id: {required_id}", errors)

    return errors


def validate_pipeline_v6_truth_tables(
    truth_tables: dict[str, Any] | None = None,
) -> list[str]:
    data = truth_tables if truth_tables is not None else load_pipeline_v6_truth_tables()
    errors: list[str] = []
    _require(
        data.get("schema_version") == TRUTH_TABLES_SCHEMA_VERSION,
        f"truth tables schema_version must be {TRUTH_TABLES_SCHEMA_VERSION}",
        errors,
    )
    sections = data.get("sections")
    _require(isinstance(sections, dict), "truth_tables.sections must be an object", errors)
    if not isinstance(sections, dict):
        return errors

    for section_name in TRUTH_SECTIONS:
        _require(section_name in sections, f"missing truth-table section: {section_name}", errors)

    seen_ids: set[str] = set()
    for section_name, rows in sections.items():
        _require(
            section_name in TRUTH_SECTIONS,
            f"unknown truth-table section: {section_name}",
            errors,
        )
        _require(isinstance(rows, list) and bool(rows), f"section {section_name} empty", errors)
        if not isinstance(rows, list):
            continue
        for row in rows:
            row_id = row.get("id")
            label = f"truth {section_name}/{row_id}"
            _require(
                isinstance(row_id, str) and bool(row_id),
                f"{section_name}: row missing id",
                errors,
            )
            if isinstance(row_id, str):
                _require(row_id not in seen_ids, f"duplicate truth-table id: {row_id}", errors)
                seen_ids.add(row_id)
            owning_lot = row.get("owning_lot")
            _require(
                owning_lot in LOT_IDS,
                f"{label}: owning_lot {owning_lot!r} not in lot0–lot10",
                errors,
            )
            _require("input" in row, f"{label}: missing input", errors)
            _require("observed_v5" in row, f"{label}: missing observed_v5", errors)
            _require("expected_v6" in row, f"{label}: missing expected_v6", errors)
            if "observed_v5" in row:
                _validate_observed_v5(label, row["observed_v5"], errors)
            if "expected_v6" in row:
                _validate_expected_v6(label, row["expected_v6"], errors)

    return errors


def validate_pipeline_v6_lot_acceptance(
    *,
    corpus: dict[str, Any] | None = None,
    truth_tables: dict[str, Any] | None = None,
) -> list[str]:
    data = corpus if corpus is not None else load_pipeline_v6_acceptance_corpus()
    tables = truth_tables if truth_tables is not None else load_pipeline_v6_truth_tables()
    errors: list[str] = []
    cases = data.get("cases", [])
    case_ids = {case["id"] for case in cases if isinstance(case.get("id"), str)}
    truth_ids = {row["id"] for _, row in iter_truth_table_rows(tables)}

    cases_by_id = {
        case["id"]: case for case in cases if isinstance(case.get("id"), str)
    }
    truth_rows_by_id = {
        row["id"]: row for _, row in iter_truth_table_rows(tables) if isinstance(row.get("id"), str)
    }

    for lot_id in LOT_IDS:
        _require(lot_id in LOT_ACCEPTANCE, f"LOT_ACCEPTANCE missing {lot_id}", errors)
        entry = LOT_ACCEPTANCE.get(lot_id, {})
        criteria = entry.get("criteria", [])
        _require(
            isinstance(criteria, list) and bool(criteria),
            f"LOT_ACCEPTANCE[{lot_id}] criteria must be non-empty",
            errors,
        )
        for case_id in entry.get("case_ids", []):
            _require(
                case_id in case_ids,
                f"LOT_ACCEPTANCE[{lot_id}] unknown case {case_id}",
                errors,
            )
            case = cases_by_id.get(case_id)
            if case is not None:
                _require(
                    lot_id in (case.get("lots") or []),
                    f"LOT_ACCEPTANCE[{lot_id}] case {case_id} missing {lot_id} in lots",
                    errors,
                )
        for row_id in entry.get("truth_row_ids", []):
            _require(
                row_id in truth_ids,
                f"LOT_ACCEPTANCE[{lot_id}] unknown truth row {row_id}",
                errors,
            )
            row = truth_rows_by_id.get(row_id)
            if row is not None:
                _require(
                    row.get("owning_lot") == lot_id,
                    f"LOT_ACCEPTANCE[{lot_id}] truth row {row_id} owning_lot "
                    f"{row.get('owning_lot')!r} != {lot_id}",
                    errors,
                )

    for extra in set(LOT_ACCEPTANCE) - set(LOT_IDS):
        errors.append(f"LOT_ACCEPTANCE has unexpected key: {extra}")

    return errors


def validate_pipeline_v6_orphan_coverage(
    *,
    corpus: dict[str, Any] | None = None,
    truth_tables: dict[str, Any] | None = None,
) -> list[str]:
    data = corpus if corpus is not None else load_pipeline_v6_acceptance_corpus()
    tables = truth_tables if truth_tables is not None else load_pipeline_v6_truth_tables()
    errors: list[str] = []
    cases = data.get("cases", [])

    referenced_metrics = metrics_referenced_by_corpus(cases) | metrics_referenced_by_truth_tables(
        tables
    )
    for metric in METRIC_IDS:
        _require(
            metric in referenced_metrics,
            f"metric {metric} is not referenced by any case or truth-table section",
            errors,
        )

    lots_from_cases: set[str] = set()
    for case in cases:
        lots_from_cases.update(case.get("lots", []))
    lots_from_truth = {
        row.get("owning_lot") for _, row in iter_truth_table_rows(tables) if row.get("owning_lot")
    }
    covered_lots = lots_from_cases | lots_from_truth
    for lot_id in LOT_IDS:
        _require(lot_id in covered_lots, f"lot {lot_id} has no coverage reference", errors)

    for case in cases:
        case_id = case.get("id")
        metrics = case.get("metrics") or []
        lots = case.get("lots") or []
        _require(
            bool(metrics),
            f"orphan case {case_id}: no metrics",
            errors,
        )
        _require(
            bool(lots),
            f"orphan case {case_id}: no lots",
            errors,
        )

    for _section, row in iter_truth_table_rows(tables):
        _require(
            bool(row.get("owning_lot")),
            f"orphan truth row {row.get('id')}: missing owning_lot",
            errors,
        )

    return errors


def validate_all_pipeline_v6_acceptance_artefacts() -> list[str]:
    errors: list[str] = []
    errors.extend(validate_pipeline_v6_acceptance_corpus())
    errors.extend(validate_pipeline_v6_truth_tables())
    errors.extend(validate_pipeline_v6_lot_acceptance())
    errors.extend(validate_pipeline_v6_orphan_coverage())
    return errors


def assert_pipeline_v6_acceptance_artefacts_valid() -> None:
    errors = validate_all_pipeline_v6_acceptance_artefacts()
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise PipelineV6AcceptanceValidationError(
            f"Pipeline V6 Lot 0 acceptance artefacts invalid:\n{joined}"
        )
