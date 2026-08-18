# AGENTS.md

**Spore** is the product. **Houston** is the repository and backend technical name.

Spore is a field-operations app with one integrated React frontend (Web and Native/Capacitor) and a Django modular monolith. It is not a PWA.

## Core loop

Observation → Signal → Action Plan → Execution → Validation → Feed update

Detailed statuses, permissions, and pipeline steps belong in owning backend code and tests — not here.

## Sources of truth

Practical authority order:

1. owning implementation
2. owning tests
3. generated contracts (OpenAPI / published contract files)
4. stable agent policies in this tree
5. living architecture and product docs
6. Git history

Docs and agent configuration must not replace inspection of the real implementation when behavior matters. If they conflict with code or tests, follow the implementation unless a stable human policy says otherwise.

## Exploration

Explore proportionally to blast radius. Follow ownership and dependencies, not directory breadth. Ask the human only when the remaining uncertainty is a real product or architectural decision that cannot be resolved from the repository.

When modifying a shared abstraction, inspect its meaningful current consumers before proposing or implementing changes.

## Architecture

- Modular monolith: domain services own writes/workflows, selectors own reads, permissions own authorization; HTTP views orchestrate; serializers validate/represent.
- Backend owns business rules, RBAC, lifecycle, feed visibility, and data integrity. Frontend permission logic is UX only.
- One frontend codebase. Identify the product surface and shell from the repository before changing UI. Mobile-first is not mobile-only.
- Side effects run after valid committed state. Events and realtime are traces and triggers, not a second business store. Do not invent an event bus.
- Smallest change that fits the existing architecture. Introduce an abstraction only when the current change proves a stable shared responsibility.
- Do not add compatibility layers, dual paths, backfills, or rollout machinery for hypothetical consumers or data. Preserve compatibility only when the repository or the task demonstrates an existing requirement.
- Be scale-aware without speculative hyperscale: avoid N+1 queries, unbounded collections, missing pagination, oversized payloads, unbounded fan-out, and naive full-history loads. Do not introduce replicas, shards, extra caches, or new infrastructure without demonstrated need.

## Security and integrity

Enforce authorization, tenant isolation, and data integrity on the backend. Minimize sensitive data across API, realtime, async jobs, uploads, and AI. Never leak secrets, tokens, raw Observation text, private media paths, or sensitive payloads in logs, broker messages, WebSocket payloads, or frontend persistent storage. Log identifiers and state transitions, not sensitive payloads.

## API contracts

If **external** request/response semantics change, consider the end-to-end chain regardless of which file triggered the change: backend owner → validation/tests → OpenAPI/schema → generated frontend artifacts → affected client/query/hooks → UI/cache. Do not hand-edit generated artifacts. Internal backend changes with an unchanged external contract must not trigger unnecessary schema or client regeneration.

## Change behavior

- Inspect existing code, tests, and patterns in the touched area before editing.
- Smallest coherent patch; no unrelated refactor, format, or dependency changes.
- Do not rename public fields, routes, enums, statuses, or events casually.
- Do not weaken tests, RBAC, tenant isolation, or lifecycle guards.
- Be critical where product, architecture, security, integrity, or scale consequences matter. Do not reopen validated decisions without new evidence from the repository.

## Validation

- Backend: never `cd apps/api && uv run` on the host — use `make backend-*` or `docker compose exec api`.
- Frontend: `cd apps/web && npm …` or `make web-*`.
- Validate the changed behavior first, then the likely blast radius. `make backend-check` / `make verify` only when justified.
- Report: Changed · Validated · Risks / not verified (including manual viewport or native behavior).

## Where to look

| Area | Read first |
|------|------------|
| Backend `apps/api/**` | [`apps/api/AGENTS.md`](apps/api/AGENTS.md) |
| Frontend `apps/web/**` | [`apps/web/AGENTS.md`](apps/web/AGENTS.md) |
| Local stack | [`docs/engineering/local_development.md`](docs/engineering/local_development.md) |
| Testing procedure | [`docs/engineering/testing.md`](docs/engineering/testing.md) |
| Product state | [`docs/product/current_state.md`](docs/product/current_state.md) |

`.cursor` is the canonical agent configuration. `.agents` is a generated mirror of Commands, Rules, and Skills.

Human workflow Commands: `create-plan` · `implement-changes` · `review-changes` · `hygiene-pass` · `test-review` · `docs-review`.
