# Backend AGENTS.md

Applies to `apps/api/**`.

## Stack

Python, Django, DRF, PostgreSQL, Redis, Celery, Django Channels, Daphne, Pydantic, OpenAPI.

Do not upgrade backend framework versions unless explicitly requested.

## Ownership

- Domain **services** modules: writes, workflows, lifecycle transitions, event publication. Some domains split `*_services.py` rather than a single `services.py`.
- **selectors**: reusable reads, feeds, permission-scoped lists.
- **permissions**: authorization helpers and RBAC checks.
- `api/` views: HTTP orchestration only.
- `api/` serializers: request validation and response representation only.
- **models**: fields, constraints, indexes, simple invariants.
- `core/`: shared infrastructure only — no product workflows.

Do not put business workflows in views, serializers, models, Django signals, Celery tasks, or `core/`.

### Observation → AI → Signal

App-level ownership (inspect current services and tasks before changing it):

- `observations` — intake, processing status, enqueue after commit
- `ai` — provider adapter, prompt/input, structured parse, usage metadata (not a public HTTP contract)
- `signals` — pipeline orchestration, signal create/aggregate, recovery sweeps

Cross-app enqueue after submit is intentional. Exact function names belong in code.

## Business rules

Backend owns permissions, establishment isolation, membership status/scope, lifecycle transitions, feed visibility/sorting, and API contracts. Frontend hints are UX only.

## Events, async, realtime

Persist valid business state first. Side effects after commit. Consumers must be retry-safe and reasonably idempotent. Events are traces and triggers, not business truth. Do not invent a separate event bus.

Celery: pass durable IDs, reload from the database, handle missing records, bound retries. Do not pass raw Observation text or other sensitive payloads as task arguments.

Redis: cache, rate limit, Channels, and Celery infra only — never business or authorization truth.

Channels: consumers stay thin; validate user, membership, and establishment access. Generic realtime sends invalidation only. Chat uses a dedicated WebSocket protocol and a REST-issued ticket.

AI output is untrusted external input. Keep business invariants in backend code. Minimize provider payloads. Distinguish provider failure, invalid output, and business validation failure.

## Transactions and schema

Use `transaction.atomic` for multi-write workflows, lifecycle transitions with side effects, aggregation, permissions-relevant writes, and event publication. Do not wrap simple selectors.

Design schema changes for integrity and realistic growth. Preserve existing data only when current data or deployment constraints require it; otherwise prefer the simplest direct migration compatible with actual constraints.

## API contracts

The HTTP `api/` package is the usual owner of external request/response shape. Services, models, or permissions can still change external semantics. If they do, consider the full contract chain regardless of which file triggered the change. Do not regenerate schema or frontend types when the external contract is unchanged. Do not invent missing generation commands.

Canonical: `make schema` then `make web-api-generate`.

## Security

Never log or expose secrets/tokens, raw Observation text, comments content, photo/audio content, full AI prompts/outputs, or other sensitive business payloads.

## Tests and commands

Procedure: [`docs/engineering/testing.md`](../../docs/engineering/testing.md).

Test product risk at the owning layer. Check existing coverage before adding. Do not re-prove the same permission rule in unit and API tests. Shared helpers live in `houston/testing/` or domain `tests/helpers.py` — never import from `test_*.py`.

Run from repo root via Make (Docker stack required):

- `make backend-test ARGS='path -q'`
- `make backend-lint`
- `make backend-migrations-check`
- `make backend-check`

Do not run `cd apps/api && uv run pytest` on the host — use Make targets or `docker compose exec api`.
