# Local development

Status: authoritative  
Last reviewed: 2026-07-13

Daily workflow for Houston on macOS / OrbStack. Install from scratch: [`INSTALL_MAC.md`](../../INSTALL_MAC.md).

## Recommended stack

- **Backend:** Docker (`make up-backend`) — postgres, redis, api, celery
- **Frontend:** native npm (`make web-dev`) — http://localhost:5173

Do **not** run `make up` (Docker web on 5173) and `make web-dev` at the same time.

## First-time bootstrap

```bash
cp .env.example .env
# Edit DJANGO_SECRET_KEY, HOUSTON_REGISTRATION_INVITE_CODES
make build-backend
make bootstrap-dev
make web-install
make web-dev
```

`make bootstrap-dev` chains: `up-backend` → `migrate` → `import-catalog` → `check` → `catalog-check`.

Catalog CSV: [`docs/catalogue/`](../catalogue/).

Optional scheduler (action plan horizon beat): `make up-scheduler`.

After `.env` changes with stack running: `make recreate-backend` (reloads api/celery env). `make restart-backend` does **not** reload `.env`.

## Daily commands

| Task | Command |
|------|---------|
| Start backend | `make up-backend` |
| Start frontend | `make web-dev` |
| Django shell | `make shell` |
| Migrations | `make migrate` |
| Backend tests | `make test` |
| Full backend check | `make backend-check` |
| Frontend typecheck | `make web-typecheck` |
| Regenerate OpenAPI types | `make schema && make web-api-generate` |
| Full local verify | `make verify` |

## Reset (destructive)

```bash
make reset-dev-db
```

Refused if `.env` points to a remote database (`assert-local-dev-db.sh`). Then `make web-install` if Docker web was used, and `make web-dev`.

## Automatic checks

| Command | Expected |
|---------|----------|
| `make catalog-check` | `14 CatalogBusinessUnit, 134 CatalogActivitySubject` |
| `make check` | Django system check OK |
| `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/health/` | `200` |

## E2E product path (manual)

1. Register/login (`/onboarding` with invite code)
2. Create org + establishment, complete onboarding v2
3. Activate establishment
4. Submit observation (optional photo)
5. Signal appears in feed (celery required)
6. Create action plan from signal
7. Execution visible in execution feed

Smoke checklist: [`../deploy/smoke_checklist.md`](../deploy/smoke_checklist.md).

## Observation pipeline

Requires `celery` service. For realistic AI in manual testing:

```env
HOUSTON_AI_OBSERVATION_PROVIDER=openai
OPENAI_API_KEY=...
```

Automated pytest uses fake provider. After env change: `make recreate-backend`.

## URLs

| Resource | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| API health | http://localhost:8000/api/v1/health/ |
| Swagger | http://localhost:8000/api/docs/ |

## Makefile reference

Run `make` from repo root. Full target list is in the root [`Makefile`](../../Makefile). Common targets: `build-backend`, `up-backend`, `up`, `up-build`, `down`, `migrate`, `test`, `lint`, `schema`, `web-dev`, `web-test`, `verify`, `infra-check`.

## Private media

Docker uses named volume `private_media`. Local `apps/api/private_media` only for non-Docker backend or troubleshooting.
