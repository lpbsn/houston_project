# AGENTS.md

Houston is a mobile-first, event-driven operational PWA for field teams.

## Core loop

Observation → Signal → Action Plan → Execution → Validation → Feed update

## Sources of truth

- **Backend**: Django services, selectors, permissions, PostgreSQL, API tests
- **API contract**: OpenAPI schema + generated frontend types
- **Frontend server state**: TanStack Query + generated types
- **Product state**: [`docs/product/current_state.md`](docs/product/current_state.md)

Docs may be stale — verify behavior in code and tests first.

## Architecture principles

- Modular monolith; explicit services/selectors/permissions
- Backend owns business rules, RBAC, lifecycle, feed visibility
- React is UI only; no duplicated backend logic except UX hints
- Event-driven side effects after valid state transitions
- Small, testable changes; no manual edits to generated files

## Security (summary)

Never leak secrets, tokens, raw Observation text, private media paths, or sensitive payloads in logs, broker messages, WebSocket payloads, or frontend persistent storage.

## API contract (summary)

If API shape changes: update backend serializer/view/tests, regenerate schema and frontend types, update callers and query invalidation.

## Instructions by area

| Area | Read first |
|------|------------|
| Backend `apps/api/**` | [`apps/api/AGENTS.md`](apps/api/AGENTS.md) |
| Frontend `apps/web/**` | [`apps/web/AGENTS.md`](apps/web/AGENTS.md) |
| Local dev / Docker | [`docs/engineering/local_development.md`](docs/engineering/local_development.md) |
| Testing | [`docs/engineering/testing.md`](docs/engineering/testing.md) |

## Cursor

Agent behavior: [`.cursor/rules/00-agent-behavior.mdc`](.cursor/rules/00-agent-behavior.mdc)

Commands (invoke explicitly): `scope` · `implement-change` · `audit` · `review` · `api-contract-change` · `mobile-pwa-debug` · `test-audit`
