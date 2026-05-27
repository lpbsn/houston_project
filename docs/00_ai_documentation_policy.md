# Houston AI Documentation Policy

## Purpose

Documentation must help AI agents build safely without hallucinating or overfitting obsolete specs.

## Authority Order

Use sources in this order:

1. Current source code
2. Generated OpenAPI schema: `apps/api/schema.yml`
3. `AGENTS.md` files
4. Active docs under `docs/`
5. Archived docs only for historical context

If two sources conflict, the higher source wins.

## Documentation Statuses

- `authoritative`: stable decision; follow unless current code proves it obsolete
- `candidate`: target design; not necessarily implemented
- `advisory`: recommendation; adaptable
- `archived`: historical; must not drive implementation

## API Rule

`apps/api/schema.yml` is the current API contract.

Any endpoint documented elsewhere but missing from `apps/api/schema.yml` must be treated as `candidate` only.

## Adaptation Rule

AI agents may adapt implementation details when:

- business invariants remain respected
- backend authority remains respected
- tenant scoping remains enforced
- OpenAPI is updated when API changes
- tests prove behavior
- deviations are reported clearly

## Non-Adaptable Invariants

- backend owns business rules
- PostgreSQL is the source of persisted business truth
- Redis must not store business truth
- permissions are enforced backend-side
- tenant or establishment scoping is mandatory
- OpenAPI is the frontend/backend API contract
- frontend must not own server state
- generated files must not be edited manually
- raw Observation text must not leak into feeds, notifications, websocket payloads, persistent frontend storage, or logs

## Agent Workflow Before Editing

- read the nearest `AGENTS.md`
- inspect the existing code structure
- inspect existing tests
- inspect `apps/api/schema.yml` when touching API docs
- report stale docs found during the work
