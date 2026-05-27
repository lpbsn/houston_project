# Codex Task — Phase 0.2 Foundation Hardening

Read AGENTS.md first.

## Goal

Harden the Phase 0.1 Django foundation without adding business features.

This phase improves:
- environment configuration
- Docker/dev ergonomics
- README commands
- project hygiene
- repeatable checks

## Scope

Allowed changes:

1. Environment configuration
   - Ensure Django settings read from environment variables.
   - Add or complete `.env.example`.
   - Keep safe development defaults only where acceptable.
   - Do not introduce production secrets.

2. Docker hygiene
   - Add `.dockerignore` if missing.
   - Ensure Docker build context is clean.
   - Ensure `docker compose up --build` works.

3. Developer commands
   - Add a Makefile with common commands:
     - build
     - up
     - down
     - check
     - test
     - lint
     - schema
     - shell
     - migrate

4. README
   - Document local setup.
   - Document Docker commands.
   - Document validation commands.
   - Document the current stack decision:
     - Python 3.13.13
     - Django 5.2 LTS
     - React + TypeScript + Vite frontend
     - OpenAPI-first backend/frontend contract

5. Tests
   - Keep existing tests green.
   - Add minimal tests only if needed for settings or health behavior.

## Constraints

- Do not create business models.
- Do not implement auth.
- Do not implement users, memberships, roles, permissions.
- Do not implement Observation, Signal, Action, AI, uploads, notifications, realtime.
- Do not create apps/web.
- Do not add React.
- Do not add frontend build tooling yet unless strictly necessary.
- Keep the diff small.
- Do not rename domain apps.

## Acceptance

The following commands must pass:

```bash
docker compose up --build
docker compose exec api python --version
docker compose exec api python manage.py check
docker compose exec api pytest
docker compose exec api ruff check .
docker compose exec api python manage.py spectacular --file schema.yml
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/
make check
make test
make lint
make schema
