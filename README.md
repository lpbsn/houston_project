# Houston

Houston is in Phase 0.8, the operational domain normalization slice for the modular monolith backend.

Phase 0.1 through Phase 0.6 are implemented:

- Phase 0.1: Django project foundation under `apps/api`
- Phase 0.2: environment and Docker workflow hardening
- Phase 0.3: core technical primitives
- Phase 0.4: identity and access models
- Phase 0.5: web session authentication and current establishment context
- Phase 0.6: minimal RBAC permission service

Phase 0.8 replaces membership domain JSON storage with relational operational domain tables scoped to establishments. It does not start Phase 1.

## Current Stack Decisions

- Python 3.14.2
- Django 5.2 LTS
- Django Templates + HTMX for the MVP UI
- Django REST Framework for workflow-oriented JSON APIs where needed
- PostgreSQL
- Redis
- Celery
- Django Channels
- drf-spectacular
- pytest
- Ruff
- uv
- No React SPA

## Project Layout

- `apps/api`: Django project root
- `apps/api/config`: Django configuration package
- `apps/api/houston`: domain app package
- `infra/docker/api`: API container build files
- `docs/codex`: scoped implementation briefs

## `houston.core` Guardrail

`apps/api/houston/core` is reserved for shared technical primitives only. It must stay small, stable, and infrastructure-level.

Allowed in `houston.core`:

- abstract base models
- cross-cutting technical primitives
- generic result objects
- generic exceptions
- generic event envelope structures
- temporary health, root, and app shell views
- helpers that are truly shared and non-business

Forbidden in `houston.core`:

- Observation, Signal, Action, Checklist, Notification, Upload, or AI business logic
- establishment-specific RBAC rules
- domain services
- business selectors
- object-level business policies
- code placed there only because it is shared by two modules

Decision rule:

- If code depends on a domain concept, it belongs in that domain app.
- If code is shared across domains but still expresses business rules, put it in the owning domain or a dedicated app, not in `core`.
- If there is doubt, do not put it in `houston.core`.

Any future PR adding code to `houston.core` must explain why that code is framework-level or infrastructure-level rather than domain-level.

## Current Capabilities

The current Phase 0 foundation includes:

- Django project under `apps/api`
- Docker Compose workflow
- PostgreSQL / Redis wiring
- pytest / Ruff / OpenAPI
- core primitives
- custom `User`
- `Organization`
- `Establishment`
- `EstablishmentMembership`
- `OperationalDomain`
- `MembershipDomain`
- web session login/logout
- protected `/app/`
- current establishment context
- minimal RBAC permission service
- capability-level permissions plus domain membership checks

## Local Setup

1. Copy `.env.example` to `.env`.

2. Start the stack:
docker compose up --build

3. Apply database migrations from another terminal
make migrate

4. Run the acceptance checks
docker compose exec api python --version
make check
make test
make lint
make schema
make migrations-check
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/

make migrate, make check, make test, make lint, make schema, and make migrations-check assume the Docker Compose stack is already running.

## Validation Commands


Run from the repository root after the Docker Compose stack is running:
```bash
make migrate
make check
make test
make lint
make schema
make migrations-check

## Make Commands

These commands are thin wrappers around `docker compose`:

make migation check :

```md
make build
make up
make down
make migrate
make check
make test
make lint
make schema
make migrations-check
make shell
```

`make check`, `make test`, `make lint`, `make schema`, `make shell`, and `make migrate` assume the stack is already running.

## Available Endpoints

- `/`: Django template rendering proof
- `/api/v1/health/`: health endpoint
- `/api/schema/`: OpenAPI schema
- `/api/docs/`: Swagger UI
- `/login/`: session login page
- `/logout/`: session logout endpoint
- `/app/`: protected application shell

## Not Implemented Yet

- Phase 1 onboarding
- runtime configuration
- invitations
- signup
- password reset
- JWT
- refresh tokens
- DRF login endpoint
- Observation
- Signal
- Action
- Checklist
- Comments
- Notifications
- Realtime business flows
- AI pipeline
- Upload logic
- React
- TypeScript
- `apps/web`

Scaffold-only Django apps for future domains may exist, but their business logic is intentionally not implemented in Phase 0.

## Domain Access Note

Phase 0.8 replaces `EstablishmentMembership.operational_domains` JSON storage with relational `OperationalDomain` and `MembershipDomain` models.

Current permissions remain limited to capability-level checks plus establishment-scoped domain membership. Object-level Signal, Action, and checklist authorization is not implemented yet.

## Next Phase

Phase 1 — Runtime Config + Minimal Onboarding
