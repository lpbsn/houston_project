# Houston documentation

Status: authoritative  
Last reviewed: 2026-09-21

Git is the only history. There is no `archive/`, `audits/`, or `cadrage/` tree in active docs.

## How to keep docs

Prefer deletion, consolidation, and shortening. Do not copy OpenAPI into domain docs (`schema.yml` is the HTTP contract). Do not keep closed Lots, phase tables, or “removed, see Git” notes in living docs. Do not preserve a paragraph only because it already exists. If code, tests, or OpenAPI disagree with a doc, follow the implementation and fix or delete the doc.

## Start here

1. Root [`README.md`](../README.md) — repository entry
2. [`product/current_state.md`](product/current_state.md) — what is implemented today and remaining exclusions
3. [`product/domains/identity_membership_domain.md`](product/domains/identity_membership_domain.md) — Authentication vs Tenant vs Platform
4. The domain you are changing under [`product/domains/`](product/domains/)
5. [`apps/api/schema.yml`](../apps/api/schema.yml) — HTTP API contract
6. [`engineering/local_development.md`](engineering/local_development.md) — daily workflow
7. Nearest [`AGENTS.md`](../AGENTS.md) (root, `apps/api`, `apps/web`) for coding agents

## Product

| Doc | Purpose |
|-----|---------|
| [`product/current_state.md`](product/current_state.md) | Live snapshot + remaining exclusions |
| [`product/product_principles.md`](product/product_principles.md) | Product identity |
| [`product/decisions/action_plan.md`](product/decisions/action_plan.md) | Action plan §26 + schedules |
| [`product/domains/`](product/domains/) | Domain invariants (start with identity) |
| [`product/domains/business_unit_taxonomy_domain.md`](product/domains/business_unit_taxonomy_domain.md) | BU/AS identity, `routing_key`, public shapes |
| [`product/data_inventory.md`](product/data_inventory.md) | Collected data, deletion, store privacy SoT |
| [`product/store_privacy_declarations.md`](product/store_privacy_declarations.md) | Apple / Google privacy worksheet |
| [`product/store_compliance.md`](product/store_compliance.md) | Store compliance hors privacy |
| [`product/store_listing.md`](product/store_listing.md) | Store listing copy pack (FR) |
| [`product/store_review.md`](product/store_review.md) | Store review runbook |
| [`product/store_phase1_gate.md`](product/store_phase1_gate.md) | Store Readiness Phase 1 gate |

## Architecture & engineering

| Doc | Purpose |
|-----|---------|
| [`architecture/authentication_charter.md`](architecture/authentication_charter.md) | Session, tokens, CSRF, transports, WS tickets |
| [`architecture/api_error_contract.md`](architecture/api_error_contract.md) | API errors |
| [`engineering/local_development.md`](engineering/local_development.md) | Local workflow |
| [`engineering/frontend_architecture.md`](engineering/frontend_architecture.md) | React / Vite map |
| [`engineering/testing.md`](engineering/testing.md) | Test strategy |
| [`engineering/api_pagination_standard.md`](engineering/api_pagination_standard.md) | Pagination |

## Deploy

| Doc | Purpose |
|-----|---------|
| [`deploy/native_release.md`](deploy/native_release.md) | Native store bake + signed Android AAB; CI `cap sync` deferred |
| [`deploy/smoke_checklist.md`](deploy/smoke_checklist.md) | Smoke (local + Railway) |
| [`deploy/prod_test_runbook.md`](deploy/prod_test_runbook.md) | Operator runbook |
| [`deploy/railway_deploy_contract.md`](deploy/railway_deploy_contract.md) | Deploy contract |
| [`deploy/railway_architecture.md`](deploy/railway_architecture.md) | Railway topology |
| [`deploy/railway_variables.md`](deploy/railway_variables.md) | Env matrix |
| [`deploy/railway_security.md`](deploy/railway_security.md) | Security notes |

## Data

- [`catalogue/README.md`](catalogue/README.md) — catalogue import policy + Make targets; CSVs in the same folder (`make import-catalog`)
- [`../contracts/`](../contracts/) — machine contracts (realtime invalidation)
