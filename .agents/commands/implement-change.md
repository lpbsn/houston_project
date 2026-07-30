# Implement change

Read `AGENTS.md`, relevant nested `AGENTS.md`, and existing code/tests before editing.
Smallest safe patch only — no refactor, format, or scope creep unless requested.
Contexte : Its a solo dev project. The prod environment has no real user or real data. We don't need safe implementation

## Layer detection

Apply only matching sections:
- `apps/api/**` → Si backend
- status transitions in services → Si lifecycle
- `permissions.py`, membership → Si RBAC
- `broadcast.py`, consumers, WebSocket, Celery side effects → Si event/realtime
- `apps/web/**` → Si frontend
- serializers/views/schema/generated types → Si API contract

## Si backend

- Writes in services; reads in selectors; views thin
- `make backend-test ARGS='path/to/test.py::test_name'`
- See [`apps/api/AGENTS.md`](../../apps/api/AGENTS.md)

## Si lifecycle

- Transitions in services only; test valid, forbidden, side effects

## Si RBAC

- Backend enforces security; test allowed/forbidden/inactive/wrong establishment
- See [`80-security-data-integrity.mdc`](../rules/80-security-data-integrity.mdc)

## Si event/realtime

- Persist state first; after-commit side effects; minimal payloads
- Runtime hubs: Event-driven section in `apps/api/AGENTS.md`
- No event sourcing unless requested

## Si frontend

- TanStack Query; generated API types; no fetch in components
- See [`apps/web/AGENTS.md`](../../apps/web/AGENTS.md)

## Si API contract

- **Use [`api-contract-change`](./api-contract-change.md)** — do not skip schema/types chain

## Si mobile shell / iOS keyboard

- **Use [`mobile-pwa-debug`](./mobile-pwa-debug.md)** before layout fixes

## Validation

- Targeted tests first; gate wide checks only when justified
- Docker/Make: [`30-local-infra.mdc`](../rules/30-local-infra.mdc)

Final: Changed · Validated · Risks
