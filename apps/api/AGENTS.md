# Backend AGENTS.md

Applies to `apps/api/**`.

## Stack

Python, Django, DRF, PostgreSQL, Redis, Celery, Django Channels, Daphne, Pydantic, OpenAPI.

Do not upgrade backend framework versions unless explicitly requested.

## Ownership

- `services.py`: writes, workflows, lifecycle transitions, event publication.
- `selectors.py`: reusable reads, feeds, permission-scoped lists.
- `permissions.py`: authorization helpers and RBAC checks.
- `api/views.py`: HTTP orchestration only.
- `api/serializers.py`: request validation and response representation only.
- `models.py`: fields, constraints, indexes, simple invariants.

Do not put business workflows in views, serializers, models, Django signals, Celery tasks, or `core/`.

## Business rules

Backend owns:
- permissions
- establishment isolation
- membership status/scope
- lifecycle transitions
- feed visibility/sorting
- API contracts

Frontend hints are UX only.

## Event-driven

For significant state changes:
- persist valid business state first
- emit minimal non-sensitive event after valid transition
- prefer after-commit behavior when transaction safety matters
- consumers handle notification, realtime, audit, analytics, async jobs
- consumers must be retry-safe/idempotent where applicable

Events are traces and triggers, not business source of truth.

## Transactions

Use `transaction.atomic` for multi-write workflows, lifecycle transitions with side effects, aggregation, permissions-relevant writes, and event publication.

Do not wrap simple selectors in transactions.

## API / OpenAPI

If API shape changes:
- update serializer/view/service tests
- update schema using project command
- regenerate frontend types using project command
- update frontend callers

Do not invent missing schema/type generation commands. Report missing commands.

## Async

Celery:
- pass IDs only
- reload records from DB
- handle missing records
- keep tasks idempotent when retryable
- do not pass raw Observation text or sensitive payloads

Redis:
- cache/rate limit/locks/Channels only
- never business truth or authorization truth

Channels:
- consumers stay thin
- validate user, membership, establishment access
- generic realtime sends invalidation only
- Chat V1 uses dedicated WS protocol and REST-issued ticket

## Security

Never log or expose:
- secrets/tokens
- raw Observation text
- comments content
- photo/audio content
- full AI prompts/outputs
- sensitive business payloads

## Tests

Add/update focused tests for:
- service behavior
- permissions
- tenant scoping
- lifecycle transitions
- API shape
- emitted events
- Celery/Channels behavior
- sensitive data exposure

Prefer behavior tests over fragile internal mocks.

## Commands

Run from repo root unless needed:

- lint: `cd apps/api && uv run ruff check .`
- format check: `cd apps/api && uv run ruff format --check .`
- tests: `cd apps/api && uv run pytest`
- migrations check: `cd apps/api && uv run python manage.py makemigrations --check --dry-run`

Use project-defined schema/catalog commands if they exist. Do not invent missing commands.