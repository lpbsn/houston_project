# AGENTS.md

Houston is a mobile-first, event-driven operational PWA.

Core loop:
Observation -> Signal -> Action -> Execution -> Validation -> Feed update

## Source of truth

- Django owns business rules, permissions, lifecycle transitions, feed visibility, and API contracts.
- PostgreSQL is the persisted business source of truth.
- Redis is temporary technical state only.
- React is the UI layer.
- TanStack Query owns frontend server state.
- OpenAPI/generated types define the frontend/backend contract.
- Docs may be stale; verify behavior in code and tests first.

## Architecture

Use a modular monolith.

Prefer:
- explicit services/selectors/permissions
- small safe changes
- behavior-focused tests
- generated API contracts
- event-driven side effects

Avoid:
- unrelated refactors
- frontend business logic
- hidden side effects
- generic abstractions
- manual edits to generated files
- business truth in Redis or WebSocket payloads

## Event-driven rule

Business tables remain source of truth.
Events trace significant business/technical facts.
State change first, event second.
Consumers handle notification, realtime, audit, analytics, and async side effects.
Do not introduce event sourcing unless explicitly requested.

## Security

Never leak:
- secrets or tokens
- raw Observation text
- private media paths
- sensitive business payloads in logs, broker messages, WebSocket payloads, or frontend persistent storage

Backend authorization is mandatory for reads, writes, signed URLs, realtime subscriptions, notifications, and async jobs.

## API contract

If API shape changes:
- update backend serializer/view/tests
- update OpenAPI schema
- regenerate frontend types
- update frontend callers and query invalidation

Generated files must not be manually edited.

## Scope

Do not:
- move files or reorganize modules unless requested
- add dependencies without approval
- upgrade framework versions unless requested
- mix feature, refactor, cleanup, and formatting
- Ne jamais lancer directement des commandes docker compose complexes si une commande Makefile existe.

## Nested instructions

Use nested files:
- `apps/api/AGENTS.md` for backend work
- `apps/web/AGENTS.md` for frontend work

Use `.cursor/rules/` for Cursor-specific persistent rules.
Use `.cursor/commands/` for repeated workflows.