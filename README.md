# Houston

Houston is an early-stage backend-centric B2B operational workflow app.

The project currently uses a Django modular monolith as the business authority and a thin React frontend as the UI shell. PostgreSQL is the canonical state store. OpenAPI is the backend/frontend contract.

## Current Stack

### Backend

- Python 3.13.13 for local tooling
- Django 5.2 LTS
- Django REST Framework
- drf-spectacular for OpenAPI
- PostgreSQL
- Celery
- Redis
- Django Channels
- Pydantic
- pytest
- Ruff
- uv

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Zustand for minimal UI state only
- Framer Motion
- PWA foundation via `vite-plugin-pwa`

## Architecture Rules

- Django owns business workflows, permissions, tenant scoping, visibility, and API contracts.
- React owns rendering, interaction, local UI state, and API consumption.
- TanStack Query is the only place for server state in the frontend.
- Zustand is limited to harmless UI state such as panel visibility.
- REST remains the source of truth. Global realtime (deferred) is for invalidation/refetch only. Chat V1 uses a dedicated WebSocket message protocol (see `docs/product/domains/chat_domain.md`).
- OpenAPI-first changes must flow from backend schema to generated frontend types.
- `houston.core` remains for technical primitives, not business workflows.

## Project Layout

- `apps/api` Django project root
- `apps/api/config` Django settings, ASGI, Celery, and URLs
- `apps/api/houston` domain apps
- `apps/web` React/Vite frontend
- `infra/docker/api` API container files
- `infra/docker/web` web container files
- `docs` product, architecture, and implementation notes

## What Is Implemented

- Django project foundation under `apps/api`
- PostgreSQL, Redis, Celery, and Channels wiring
- OpenAPI schema generation at `/api/schema/`
- Swagger UI at `/api/docs/`
- Health endpoint at `/api/v1/health/`
- Backend auth foundation at `/api/v1/auth/` with CSRF bootstrap, opaque access tokens, rotating refresh tokens, and bootstrap payloads
- Phase 0 identity, organization, establishment, and minimal access foundations
- React identity/workspace shell under `apps/web`
- Generated OpenAPI TypeScript client workflow
- TanStack Query, minimal Zustand, and conservative PWA setup
- Authenticated-only bootstrap through `/api/v1/auth/bootstrap/`
- Selected establishment stored on `UserSession.selected_establishment`
- Phase 1 membership management API for owner/director users
- Phase 1 scoped user search for the current active establishment
- Phase 2 runtime config / onboarding minimal ✅ completed
- **Taxonomy v2 and Lot 6 are complete:** BusinessUnit / ActivitySubject product model is authoritative, RBAC is BU-only, manual onboarding V2 and pipeline v3 are live, and legacy Module/Domain/Subject compatibility is removed.
- Observation submission (text + optional validated photo temporary uploads)
- Temporary photo uploads + private media storage (authorized only)
- Audio transcription endpoint (temporary audio deleted after each request)
- Phase 4 AI observation pipeline → Signal feed/detail (Celery + fake/OpenAI providers)
- Signal feed (`/signals`) and detail with pin/unpin/urgency/resolve/cancel commands (no manual Signal CRUD)
- Phase 5 core implemented: Action lifecycle + Execution Feed (`/actions/`, `/execution-feed/`)
- Phase 7 Checklists implemented: templates, assignments, executions, polymorphic Execution Feed (Actions + Checklists)
- Phase 8 Chat V1 core implemented: DM + free groups, REST structure/history/seen/ws-ticket, WebSocket message send/receive, Terrain UI (`/chat`), 7-day purge, membership deactivation hooks — see `docs/product/domains/chat_domain.md`

## What Is Not Implemented Yet
- Notifications
- Global realtime invalidation (Signal/Action/Notifications) — deferred post Chat V1
- Chat post-core product gaps (group management UI, Owner/Director `chat_enabled` toggle UI, `EventEnvelope` events, bootstrap `chat_available`) — see `docs/audit/chat_v1_technical_debt_2026-06-09.md`
- Production-grade frontend feature surface

## Auth Notes

- The backend auth contract now lives under `/api/v1/auth/`.
- Browser login works through the Phase 1 auth API.
- Login, refresh, and logout are CSRF-protected mutation endpoints.
- Access tokens are opaque bearer tokens and must remain memory-only on the frontend.
- Refresh tokens rotate and remain readable only by the browser as an HttpOnly cookie.
- `UserSession`, `AccessToken`, and `SessionRefreshToken` are the backend auth source of truth.
- `bootstrap` is authenticated-only.
- Selected establishment is stored on `UserSession.selected_establishment`.
- `memberships` in bootstrap responses are already filtered to active backend truth.
- Membership management and scoped user search are implemented for the current active establishment context.
- Phase 2 runtime config / onboarding minimal is completed.

Legacy Django `/login/`, `/logout/`, and `/app/` routes still exist outside the Phase 1 product contract. They must not be expanded into product UI.

## Local Setup

**macOS (guide détaillé pour un nouvel arrivant)** : voir [`INSTALL_MAC.md`](INSTALL_MAC.md) — backend Docker + frontend npm local (`make up-backend` + `make web-dev`). Chaque machine a sa propre base Postgres (volume Docker local).

**Fresh install backend** (après `cp .env.example .env` et `make build` sur une machine neuve) :

```bash
make bootstrap-dev
```

Enchaîne migrations, import du catalogue global (`CatalogBusinessUnit` / `CatalogActivitySubject`), `manage.py check` et `catalog-check`. Non destructif — safe après un `git pull`.

**Reset local destructif** (DB + volumes Docker effacés) : `make reset-dev-db` — détails et parcours machine neuve vs reset dans [`INSTALL_MAC.md`](INSTALL_MAC.md). Validation E2E : [`docs/qa/fresh_install_validation.md`](docs/qa/fresh_install_validation.md).

**Workflow quotidien (recommandé macOS / OrbStack)** : `make up-backend` + `make web-dev` — backend dans Docker, frontend npm local.

**Stack complète Docker** : `make up` — démarre `api`, `celery` et le conteneur `web` (port 5173).

**Scheduler optionnel** (matérialisation horizon checklists) : `make up-scheduler` — démarre le backend puis `celery-beat` (profile Compose `scheduler`). La matérialisation lazy sur lecture du execution feed reste disponible sans Beat.

**Frontend local vs conteneur `web`** : ne pas lancer `make up` et `make web-dev` en parallèle (conflit port 5173).

1. Copy `.env.example` to `.env`.
2. Set backend-only onboarding variables in `.env` (never commit real secrets):
   - `HOUSTON_REGISTRATION_INVITE_CODES` — comma-separated codes required for public `/onboarding` registration (empty disables registration).
   - `OPENAI_API_KEY` — server-only OpenAI key for live onboarding AI (optional in dev if you rely on template fallback).
   - `HOUSTON_AI_ONBOARDING_MODEL`, `HOUSTON_AI_ONBOARDING_TIMEOUT_SECONDS`, `HOUSTON_AI_ONBOARDING_USE_STRICT_JSON_SCHEMA` — optional tuning; see `.env.example` for defaults.
   - `HOUSTON_AI_OBSERVATION_PROVIDER` — use `openai` with a valid `OPENAI_API_KEY` for realistic manual Signaler testing (default in `.env.example`). Automated pytest forces `fake` automatically. Do not use `fake` to validate real-world observation understanding (it may produce generic titles like "Structured issue").
   - `HOUSTON_AI_OBSERVATION_MODEL`, `HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS`, `HOUSTON_AI_OBSERVATION_MAX_RETRIES` — optional tuning for observation → signal processing.
   - Do not put API keys or invite codes in `VITE_*` variables.
3. Start the stack:

```bash
docker compose up --build
```

4. Apply database migrations:

```bash
make migrate
```

5. For observation → signal processing (manual Signaler):

- Set in `.env`: `HOUSTON_AI_OBSERVATION_PROVIDER=openai` and `OPENAI_API_KEY=...` (see `.env.example`). Start the API and Celery worker:

```bash
docker compose up -d api celery
```

(`make up` also starts `celery` alongside `api` and `web`.)

- After changing env vars, recreate both containers:

```bash
docker compose up -d --force-recreate api celery
```

Requires Redis (`CELERY_BROKER_URL`). Without the `celery` service, submitted observations stay `queued`. Automated tests use the fake provider via pytest fixtures (no live OpenAI in CI).

Optional checklist horizon materialization (shared assignments): start Beat in addition to the worker. Lazy materialization on execution-feed read still applies without Beat.

```bash
make up-scheduler
```

`docker compose up -d celery-beat` reste techniquement possible avec `--profile scheduler`, mais c’est une commande non recommandée — `make up-scheduler` garantit que le backend et les dépendances nécessaires sont démarrés.

- Poll processing status after submit: `GET /api/v1/establishments/{id}/observations/{observation_id}/processing-status/`

Optional live OpenAI smoke (not CI standard): set `HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1` and run `pytest -m openai_observation_smoke`.

6. Generate the backend schema and frontend API types when needed:

```bash
make schema
make web-api-generate
```

## Docker Compose Usage

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/api/docs/`
- Frontend: `http://localhost:5173`

Core commands:

```bash
make build
make up-backend
make up
make up-scheduler
make down
make shell
```

### Clean archive (no secrets or runtime artifacts)

```bash
git archive --format=zip --output=houston-clean.zip HEAD
```

Excludes `.env`, `private_media`, `node_modules`, caches, and other untracked/gitignored paths automatically.

## Docker security (local)

- **api** and **celery** run as the non-root container user `houston` (see [`infra/docker/api/Dockerfile`](infra/docker/api/Dockerfile)). `chown` in the image applies to `/opt/venv` only; the bind mount `.:/app` uses **host file ownership** — image `chown` on `/app` does not fix runtime permissions.
- **Linux only** — if you get `Permission denied` on the bind mount, use a local `docker-compose.override.yml` (do not commit secrets):

```yaml
services:
  api:
    user: "${UID}:${GID}"
  celery:
    user: "${UID}:${GID}"
```

- **`private_media`** — en Docker, les médias privés sont stockés dans le volume nommé `private_media` (monté sur `/app/apps/api/private_media`). Le dossier local `apps/api/private_media` n’est requis que pour un usage backend hors Docker ou pour du dépannage. Django fails fast at `manage.py check` if the path is not writable (`uploads.E001`). Valider l’écriture après changement de volume (voir post-hardening validation).
- **Runtime volumes** — `postgres_data`, `web_node_modules` (conteneur `web`), `private_media`, `celerybeat_data` (profile `scheduler`).
- **Bind mount risk** — if `.env` exists at the repo root, processes in api/celery can read `/app/.env`. Never commit `.env`.
- **`docker compose config`** may print interpolated secrets — do not paste output into public tickets or CI logs. Do **not** run `docker compose config | grep -E 'OPENAI|SECRET|PASSWORD'` in shareable logs.
- **Postgres (5432)** and **Redis (6379)** are exposed on the host for local dev; tighten before pre-prod.
- **Phase 4** — observation processing needs the celery worker: `docker compose up -d api celery`. After `.env` changes: `docker compose up -d --force-recreate api celery`. Automated pytest does **not** require the Compose celery service (fixtures use the fake provider).

Safe env smoke checks (no secret values):

```bash
docker compose exec api id
docker compose exec celery id
docker compose exec api python -c "import os; print('observation_provider=', os.getenv('HOUSTON_AI_OBSERVATION_PROVIDER',''))"
docker compose exec api python -c "import os; print('broker=', os.getenv('CELERY_BROKER_URL','').split('@')[-1])"
docker compose exec api python manage.py check
```

Post-hardening validation (from repo root):

```bash
docker compose config
docker compose build api celery
docker compose up -d api celery
docker compose exec api id
docker compose exec celery id
docker compose logs celery --tail=100
docker compose exec api python manage.py check
docker compose exec api python manage.py shell -c "
from pathlib import Path
from django.conf import settings
p = Path(settings.HOUSTON_PRIVATE_MEDIA_ROOT) / '.write-test'
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text('ok')
print('write_ok=', p.exists())
p.unlink()
"
docker compose exec api pytest houston/observations houston/signals houston/ai
docker compose exec api ruff check .
cd apps/web && npm run typecheck && npm run lint && npm run build
```

Or run `make docker-verify-security` for a short non-root + `manage.py check` subset.

Pre-prod trajectory (not in local `make up`): host-injected secrets, no app bind mount, optional Docker Secrets / secret manager, internal DB/Redis ports, Redis auth, healthchecks, production image without dev dependency group.

## Backend Commands

Run from the repository root while Docker Compose is available:

```bash
make migrate
make check
make test
make lint
make schema
make migrations-check
```

## Frontend Commands

Run from the repository root:

```bash
make web-install
make web-dev
make web-typecheck
make web-build
make web-api-generate
```

## OpenAPI Workflow

When backend API contracts change:

1. Update the backend serializer, schema, or input type.
2. Update the view/service/selector.
3. Regenerate the backend OpenAPI schema:

```bash
make schema
```

4. Regenerate frontend API types:

```bash
make web-api-generate
```

5. Update the TanStack Query hook or React component that consumes the API.
6. Update tests for the changed behavior.

Do not manually edit generated API types.

## Verification

The intended local verification flow is:

```bash
make build
make up
make migrate
make check
make test
make lint
make schema
make migrations-check
make web-typecheck
make web-build
make verify
```
