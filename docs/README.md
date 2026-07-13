# Houston documentation

Status: authoritative  
Last reviewed: 2026-07-13

Git is the only history. There is no `archive/` or `audits/` folder in active docs.

## Start here

1. Root [`README.md`](../README.md) — repository entry
2. [`product/current_state.md`](product/current_state.md) — what is implemented today
3. [`engineering/local_development.md`](engineering/local_development.md) — daily workflow
4. Nearest [`AGENTS.md`](../AGENTS.md) (root, `apps/api`, `apps/web`) for coding agents
5. [`apps/api/schema.yml`](../apps/api/schema.yml) — HTTP API contract

## Product

| Doc | Purpose |
|-----|---------|
| [`product/mvp_scope.md`](product/mvp_scope.md) | Pilot boundaries |
| [`product/product_principles.md`](product/product_principles.md) | Principles |
| [`product/product_operating_model.md`](product/product_operating_model.md) | Operating model |
| [`product/decisions/action_plan.md`](product/decisions/action_plan.md) | Action plan §26 + schedules |
| [`product/domains/`](product/domains/) | Domain specs (16 files) |

## Architecture & engineering

| Doc | Purpose |
|-----|---------|
| [`architecture/authentication_charter.md`](architecture/authentication_charter.md) | Auth rules |
| [`architecture/api_error_contract.md`](architecture/api_error_contract.md) | API errors |
| [`engineering/local_development.md`](engineering/local_development.md) | Local workflow |
| [`engineering/frontend_architecture.md`](engineering/frontend_architecture.md) | React / PWA map |
| [`engineering/testing.md`](engineering/testing.md) | Test strategy |
| [`engineering/api_pagination_standard.md`](engineering/api_pagination_standard.md) | Pagination |

## Deploy

| Doc | Purpose |
|-----|---------|
| [`deploy/smoke_checklist.md`](deploy/smoke_checklist.md) | Smoke (local + Railway) |
| [`deploy/prod_test_runbook.md`](deploy/prod_test_runbook.md) | Operator runbook |
| [`deploy/railway_deploy_contract.md`](deploy/railway_deploy_contract.md) | Deploy contract |
| [`deploy/railway_architecture.md`](deploy/railway_architecture.md) | Railway topology |
| [`deploy/railway_variables.md`](deploy/railway_variables.md) | Env matrix |
| [`deploy/railway_security.md`](deploy/railway_security.md) | Security notes |

## Policy

[`00_ai_documentation_policy.md`](00_ai_documentation_policy.md) — how to write and maintain docs.

## Data (not prose docs)

- [`catalogue/`](catalogue/) — CSV import for global catalog (`make import-catalog`)
- [`../contracts/`](../contracts/) — machine contracts (realtime invalidation)
