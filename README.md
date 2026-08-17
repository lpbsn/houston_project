# Houston

Houston is a mobile-first operational app for field teams. Django owns business rules and API contracts; React (Spore UI) consumes OpenAPI-generated types via TanStack Query.

## Start here

| Doc | Purpose |
|-----|---------|
| [`docs/product/current_state.md`](docs/product/current_state.md) | What is implemented today |
| [`docs/engineering/local_development.md`](docs/engineering/local_development.md) | Daily dev workflow |
| [`INSTALL_MAC.md`](INSTALL_MAC.md) | macOS install from scratch |
| [`docs/README.md`](docs/README.md) | Full documentation index |
| [`AGENTS.md`](AGENTS.md) | Agent / contributor contract |

## Stack (summary)

**Backend:** Django 5.2, DRF, PostgreSQL, Redis, Celery, Channels — `apps/api`  
**Frontend:** React, TypeScript, Vite, Tailwind, TanStack Query — `apps/web`  
**Contract:** [`apps/api/schema.yml`](apps/api/schema.yml)

## Quick start (macOS)

```bash
cp .env.example .env
make build-backend
make bootstrap-dev
make web-install
make web-dev
```

- API: http://localhost:8000  
- Frontend: http://localhost:5173  
- Swagger: http://localhost:8000/api/docs/

Details: [`docs/engineering/local_development.md`](docs/engineering/local_development.md).

## Prod-test (Railway)

- Runbook: [`docs/deploy/prod_test_runbook.md`](docs/deploy/prod_test_runbook.md)
- Smoke: [`docs/deploy/smoke_checklist.md`](docs/deploy/smoke_checklist.md)
- Variables: [`docs/deploy/railway_variables.md`](docs/deploy/railway_variables.md)
- Wiring: [`infra/railway/README.md`](infra/railway/README.md)
- Template: [`.env.prod-test.example`](.env.prod-test.example)

## Verification

```bash
make verify
```

Targeted checks: `make backend-check`, `make web-check`, `make test`, `make web-test`.

## OpenAPI workflow

After API changes: `make schema` then `make web-api-generate`. Do not edit generated frontend types manually.

## Documentation policy

Git is the only history — legacy archive and audit doc trees are not kept in the repo. See [`docs/00_ai_documentation_policy.md`](docs/00_ai_documentation_policy.md).
