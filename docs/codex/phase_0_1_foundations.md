# Codex Task — Phase 0.1 Foundations

Read AGENTS.md first.

## Goal

Implement Houston Phase 0.1 Foundations only.

## Context

Houston is a Django modular monolith for a mobile-first B2B PWA.

The MVP is not a React SPA.

The frontend MVP uses:
- Django Templates
- HTMX
- targeted TypeScript only where needed
- no apps/web

## Scope

Create the backend project under apps/api using:

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

## Expected result

1. Django project bootstrapped under apps/api.
2. Project package named config.
3. Domain package named houston.
4. Initial Django apps created:
   - houston.core
   - houston.accounts
   - houston.organizations
   - houston.establishments
   - houston.observations
   - houston.signals
   - houston.actions
   - houston.checklists
   - houston.comments
   - houston.notifications
   - houston.realtime
   - houston.ai
   - houston.events
   - houston.uploads
5. Docker Compose with:
   - api
   - postgres
   - redis
6. Minimal health endpoint:
   - GET /api/v1/health/
7. Minimal HTML page proof:
   - GET /
   - rendered by Django Template
8. drf-spectacular configured:
   - GET /api/schema/
   - GET /api/docs/
9. pytest configured.
10. Ruff configured.
11. README with local setup commands.
12. No business models yet.
13. No fake domain logic yet.
14. No React.
15. No frontend app folder.

## Constraints

- Keep the diff small.
- Do not implement business models.
- Do not implement auth.
- Do not implement Observation, Signal, Action, AI, uploads, notifications, or realtime.
- Do not create apps/web.
- Do not use React.
- Do not add premature abstractions.

## Acceptance

The following commands must work:

```bash
docker compose up --build
docker compose exec api python manage.py check
docker compose exec api pytest
docker compose exec api ruff check .
docker compose exec api python manage.py spectacular --file schema.yml
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/