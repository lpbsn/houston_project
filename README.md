# Houston

Phase 0.1 foundations for the Houston modular monolith.

## Stack

- Python 3.14.2
- Django 5.2 LTS
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Django Channels
- drf-spectacular
- pytest
- Ruff
- uv

## Project Layout

- `apps/api`: Django project root
- `apps/api/config`: Django configuration package
- `apps/api/houston`: domain app package
- `infra/docker/api`: API container build files

## Local Setup

1. Copy `.env.example` to `.env` if you want to override the default local values.
2. Start the stack:

```bash
docker compose up --build
```

3. In another terminal, run the validation commands:

```bash
docker compose exec api python manage.py check
docker compose exec api pytest
docker compose exec api ruff check .
docker compose exec api python manage.py spectacular --file schema.yml
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/
```

## Available Endpoints

- `/`: Django template rendering proof
- `/api/v1/health/`: health endpoint
- `/api/schema/`: OpenAPI schema
- `/api/docs/`: Swagger UI

## Scope Notes

- No React
- No `apps/web`
- No business models
- No auth workflow
- No domain logic for observations, signals, actions, AI, uploads, notifications, or realtime
- Domain apps are scaffolded as empty shells only in this phase
