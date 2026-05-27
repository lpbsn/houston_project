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
- REST remains the source of truth. Realtime is for invalidation/refetch signals only.
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
- React/Vite frontend foundation under `apps/web`
- Generated OpenAPI TypeScript client workflow
- TanStack Query, minimal Zustand, and conservative PWA setup

## What Is Not Implemented Yet

- Phase 1 onboarding
- Observations
- Signals
- Actions
- Checklists
- Uploads
- AI pipeline
- Notifications
- Realtime business workflows
- Full React auth shell
- Production-grade frontend feature surface

## Auth Notes

- The backend auth contract now lives under `/api/v1/auth/`.
- Login, refresh, and logout are CSRF-protected mutation endpoints.
- Access tokens are opaque bearer tokens and must remain memory-only on the frontend.
- Refresh tokens rotate and remain readable only by the browser as an HttpOnly cookie.
- `UserSession`, `AccessToken`, and `SessionRefreshToken` are the backend auth source of truth.
- `memberships` in bootstrap responses are already filtered to active backend truth.

The backend still exposes `/login/`, `/logout/`, and `/app/` as temporary legacy scaffolding while the React auth shell is completed. They must not be expanded into product UI.

## Local Setup

1. Copy `.env.example` to `.env`.
2. Start the stack:

```bash
docker compose up --build
```

3. Apply database migrations:

```bash
make migrate
```

4. Generate the backend schema and frontend API types when needed:

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
make up
make down
make shell
```

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
