# Business unit catalogue seed

Status: authoritative  
Last reviewed: 2026-07-16

Global catalogue CSVs for `CatalogBusinessUnit` and `CatalogActivitySubject`. Domain rules: [`docs/product/domains/business_unit_taxonomy_domain.md`](../product/domains/business_unit_taxonomy_domain.md).

## Files

| File | Role |
| --- | --- |
| [`suggestion_source.csv`](suggestion_source.csv) | Trace of the business Excel export |
| [`business_units.csv`](business_units.csv) | Normalized CatalogBusinessUnit seed |
| [`activity_subjects.csv`](activity_subjects.csv) | Normalized CatalogActivitySubject seed |

## Local commands (Makefile)

From repo root (Docker API; local-dev DB guard):

| Command | Behavior |
| --- | --- |
| `make import-catalog` | `manage.py import_business_unit_catalog` |
| `make catalog-check` | `manage.py verify_catalog_counts` against seed row counts |
| `make bootstrap-dev` | `up-backend` → `migrate` → `import-catalog` → `check` → `catalog-check` |
| `make reset-dev-db` | Destructive: `compose down -v` then `bootstrap-dev` |

Expected seed counts today: **14** `CatalogBusinessUnit`, **134** `CatalogActivitySubject` (driven by CSV length / `catalog_seed_counts.py`).

Optional management flags: `--dry-run`, `--strict`, `--regenerate-from-source` (rebuild normalized CSVs from `suggestion_source.csv`).

Railway / prod-test first import: run `import_business_unit_catalog` once after migrate (see [`docs/deploy/prod_test_runbook.md`](../deploy/prod_test_runbook.md)).

## Import policy

| Situation | Behavior |
| --- | --- |
| Key **present** in CSV | Upsert mutable fields (`label`, `description`, `sort_order`, `unit_type` when allowed, `active` when present); imported rows forced active when upserted |
| Key **absent** from CSV | **No-op** — existing DB row unchanged (not deactivated, not deleted) |
| Deactivation | Explicit operation only (`active=false`); never implied by absence from file |
| Duplicate key in file | Preflight reject (`duplicate_catalog_key`) |
| `CatalogActivitySubject.key` starting with `custom--` | Rejected (`reserved_catalog_key_prefix`); also DB check constraint |
| Immutable field change when referenced | Rejected (`catalog_immutable_field`, `catalog_subject_immutable_business_unit`, …) |

Preflight runs before write; failure is atomic (no partial import).

Codes such as `referenced_catalog_key_missing` are **not** part of the contract: missing file keys are silent no-ops.

## Runtime

- Autocomplete and FK targets read PostgreSQL catalogue models — not CSV at request time.
- Without import, catalogue suggest endpoints return empty.
- Catalogue is not establishment business truth; concrete instances use `specific_name` / `routing_key` (internal).
