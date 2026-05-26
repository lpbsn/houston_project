# Houston

Houston is currently in Phase 0.2 foundation hardening for the modular monolith backend.

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

## Local Setup

1. Copy `.env.example` to `.env`.
2. Start the stack:

```bash
docker compose up --build
```

3. Run the acceptance checks from another terminal:

```bash
docker compose exec api python --version
docker compose exec api python manage.py check
docker compose exec api pytest
docker compose exec api ruff check .
docker compose exec api python manage.py spectacular --file schema.yml
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/
```

## Make Commands

These commands are thin wrappers around `docker compose`:

```bash
make build
make up
make down
make check
make test
make lint
make schema
make shell
make migrate
```

`make check`, `make test`, `make lint`, `make schema`, `make shell`, and `make migrate` assume the stack is already running.

## Available Endpoints

- `/`: Django template rendering proof
- `/api/v1/health/`: health endpoint
- `/api/schema/`: OpenAPI schema
- `/api/docs/`: Swagger UI

## Phase 0.2 Boundaries

- No business models
- No auth, users, memberships, roles, or permissions
- No `apps/web`
- No React
- No frontend build tooling
- No observation, signal, action, AI, uploads, notifications, or realtime implementation
- Domain apps remain scaffolds only
