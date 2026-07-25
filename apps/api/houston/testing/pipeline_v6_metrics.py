"""Operational metric definitions A–J and lot acceptance mapping for pipeline V6."""

from __future__ import annotations

from typing import Any

METRIC_IDS: tuple[str, ...] = tuple("ABCDEFGHIJ")

METRIC_SPECS: dict[str, dict[str, str]] = {
    "A": {
        "name": "preconditions_etablissement",
        "layer": "precondition",
        "measures": "Précondition établissement / pôles actifs respectée avant LLM",
    },
    "B": {
        "name": "detection_segmentation",
        "layer": "llm_understanding",
        "measures": "candidate precision/recall, segmentation, signal loss",
    },
    "C": {
        "name": "comprehension_operationnelle",
        "layer": "llm_understanding",
        "measures": "signal_kind, expected_action, canonical_object",
    },
    "D": {
        "name": "resolution_affected",
        "layer": "resolver",
        "measures": "affected correct ; mauvaise instance",
    },
    "E": {
        "name": "resolution_responsible_subject",
        "layer": "resolver",
        "measures": "responsible + subject corrects",
    },
    "F": {
        "name": "coherence_subject_responsible",
        "layer": "resolver",
        "measures": "invariant subject.business_unit = responsible",
    },
    "G": {
        "name": "persistance_routing_partiel",
        "layer": "persistence",
        "measures": "unassigned / partial persistés ; pas de perte de fait",
    },
    "H": {
        "name": "agregation_backend",
        "layer": "aggregation",
        "measures": (
            "agrégation resolved-only exacte ; pas de legacy_fallback ; "
            "pas de fausse agrégation ; politique expected_action D3"
        ),
    },
    "I": {
        "name": "qualification_manuelle",
        "layer": "qualification",
        "measures": "qualify réutilise resolver ; collision / fusion",
    },
    "J": {
        "name": "erreurs_techniques",
        "layer": "errors",
        "measures": "codes techniques séparés de routing_status ; JSON valide",
    },
}

# Truth-table sections contribute these metrics for orphan coverage.
SECTION_DEFAULT_METRICS: dict[str, tuple[str, ...]] = {
    "precondition": ("A", "J"),
    "resolver": ("D", "E", "F"),
    "persistence": ("G",),
    "aggregation": ("H",),
    "errors": ("J",),
    "context": ("C", "D", "E"),
}

LOT_IDS: tuple[str, ...] = tuple(f"lot{i}" for i in range(0, 11))

LOT_ACCEPTANCE: dict[str, dict[str, Any]] = {
    "lot0": {
        "criteria": [
            "corpus_valid",
            "unique_ids",
            "observed_v5_recorded",
            "metrics_a_j_referenced",
            "truth_tables_valid",
            "v6_tests_explicitly_pending",
        ],
        "case_ids": [],
        "truth_row_ids": [],
        "notes": "Artefacts d'acceptation uniquement ; aucun runtime V6.",
    },
    "lot1": {
        "criteria": [
            "routing_status_persistable",
            "partial_and_resolved_coexist",
            "no_permanent_default_on_routing_status",
        ],
        "case_ids": ["S15-03", "S15-04", "S15-18"],
        "truth_row_ids": ["PERS-01", "PERS-02", "PERS-04"],
    },
    "lot2": {
        "criteria": [
            "precondition_active_bu_not_snapshot_ready",
            "no_llm_call_on_precondition_fail",
            "technical_codes_stable",
        ],
        "case_ids": ["S15-01", "S15-02", "S15-04", "S15-D1"],
        "truth_row_ids": ["PRE-01", "PRE-02", "PRE-03", "PRE-04", "ERR-01", "PERS-03"],
    },
    "lot3": {
        "criteria": [
            "active_business_units_includes_non_routable",
            "routing_taxonomy_routable_only",
            "author_and_action_plan_context",
        ],
        "case_ids": ["S15-08", "S15-09", "S15-10", "S15-15", "S15-16", "S15-17", "S15-D1"],
        "truth_row_ids": [
            "CTX-01",
            "CTX-02",
            "CTX-03",
            "CTX-04",
            "CTX-05",
            "CTX-06",
            "CTX-07",
            "CTX-08",
        ],
    },
    "lot4": {
        "criteria": [
            "provider_contract_v6_fake_ci",
            "nullable_routing_keys",
            "no_backend_only_fields_in_llm_schema",
            "truth_table_provider_errors_green",
            "no_aggregate_into_signal_id_in_contract",
        ],
        "case_ids": ["S15-05", "S15-06", "S15-07", "S15-11", "S15-12", "S15-14"],
        "truth_row_ids": ["ERR-02", "ERR-03"],
    },
    "lot5": {
        "criteria": [
            "partial_routing",
            "subject_imposes_responsible",
            "invalid_key_does_not_drop_candidate",
            "explicit_keys_only_no_capability_auto_resolve",
            "truth_table_resolver_green",
        ],
        "case_ids": [
            "S15-03",
            "S15-04",
            "S15-05",
            "S15-10",
            "S15-18",
            "S15-19",
            "S15-20",
            "S15-D1",
        ],
        "truth_row_ids": ["RES-01", "RES-02", "RES-03", "RES-04", "RES-05", "ERR-04"],
    },
    "lot6": {
        "criteria": [
            "no_auto_aggregate_unassigned",
            "resolved_exact_aggregate",
            "no_legacy_fallback",
            "expected_action_policy_d3",
            "truth_table_aggregation_green",
        ],
        "case_ids": [],
        "truth_row_ids": ["AGG-01", "AGG-02", "AGG-03", "AGG-04"],
    },
    "lot7": {
        "criteria": [
            "qualify_reuses_resolver",
            "collision_merge_or_reject_documented",
            "staff_denied_qualify",
        ],
        "case_ids": ["S15-19"],
        "truth_row_ids": [],
    },
    "lot8": {
        "criteria": [
            "unassigned_visibility_h5",
            "qualify_hints_separated_from_feed_view",
            "pin_cancel_resolve_do_not_alter_routing_status",
        ],
        "case_ids": ["S15-03"],
        "truth_row_ids": [],
    },
    "lot9": {
        "criteria": [
            "qualify_ui_adaptive_h2",
            "precondition_error_banner_copy",
            "merge_redirect_ux",
        ],
        "case_ids": ["S15-03", "S15-19"],
        "truth_row_ids": [],
        "notes": "UI ; critères checklist + cas unassigned / qualify.",
    },
    "lot10": {
        "criteria": [
            "corpus_green_against_v6_runtime",
            "business_smoke_provider_signed_off",
            "v5_paths_removed",
            "docs_aligned",
        ],
        "case_ids": [
            "S15-01",
            "S15-02",
            "S15-05",
            "S15-11",
            "S15-12",
            "S15-14",
            "S15-D1",
        ],
        "truth_row_ids": [],
        "notes": "Cutover ; smoke métier hors CI.",
    },
}


def list_cases_for_metric(metric_id: str, cases: list[dict[str, Any]]) -> list[str]:
    metric = metric_id.strip().upper()
    return [case["id"] for case in cases if metric in case.get("metrics", [])]


def list_cases_for_lot(lot_id: str, cases: list[dict[str, Any]]) -> list[str]:
    return [case["id"] for case in cases if lot_id in case.get("lots", [])]


def list_truth_rows_for_lot(
    lot_id: str,
    truth_tables: dict[str, Any],
) -> list[str]:
    row_ids: list[str] = []
    for section_rows in truth_tables.get("sections", {}).values():
        for row in section_rows:
            if row.get("owning_lot") == lot_id:
                row_ids.append(row["id"])
    return row_ids


def metrics_referenced_by_corpus(cases: list[dict[str, Any]]) -> set[str]:
    referenced: set[str] = set()
    for case in cases:
        for metric in case.get("metrics", []):
            referenced.add(str(metric).upper())
    return referenced


def metrics_referenced_by_truth_tables(truth_tables: dict[str, Any]) -> set[str]:
    referenced: set[str] = set()
    for section_name, rows in truth_tables.get("sections", {}).items():
        referenced.update(SECTION_DEFAULT_METRICS.get(section_name, ()))
        for row in rows:
            for metric in row.get("metrics", []):
                referenced.add(str(metric).upper())
    return referenced
