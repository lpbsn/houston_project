# Business unit catalogue seed

Status: authoritative  
Last reviewed: 2026-10-13

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

Expected seed counts today: **19** `CatalogBusinessUnit`, **161** `CatalogActivitySubject` (driven by CSV length / `catalog_seed_counts.py`).

Optional management flags: `--dry-run`, `--strict`, `--regenerate-from-source`.

`suggestion_source.csv` stays a historical Excel trace (`Pole d'activité` and `Sujets` only). `--regenerate-from-source` rebuilds the normalized CSVs from that trace: descriptions are emptied, sort orders follow source order, and `unit_type` is `transversal` only for `maintenance`, `communication`, `rh`, and `evenements_privatisations`. Every other pole becomes `dedicated`, and subject keys are slugs of the source labels. That is not a faithful reconstruction of the normalized catalogue. It cannot preserve the descriptions in the normalized CSVs, the `transversal` type of `produit_numerique`, `developpement_logiciel`, `commercial`, `relation_client`, and `gestion_entreprise`, or explicit keys that differ from a label slug (`relation_client__adoption`, `produit_numerique__validation_impact`, `developpement_logiciel__architecture_qualite`, `relation_client__deploiement_configuration`, `gestion_entreprise__conformite_donnees`, and `gestion_entreprise` itself). Import reads `business_units.csv` and `activity_subjects.csv` only. Do not regenerate those files from the historical source.

Railway and prod-test do not import the catalogue during deploy or migrate. Run `import_business_unit_catalog` after migrate, and again after a catalogue change, to upsert the normalized CSV into PostgreSQL (see [`docs/deploy/prod_test_runbook.md`](../deploy/prod_test_runbook.md)). Publishing the CSV does not update the database.

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
