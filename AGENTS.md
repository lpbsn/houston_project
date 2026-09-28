# AGENTS.md

**Spore** is the product. **Houston** is the repository and backend technical name.

Spore is a multi-tenant field-operations application with one shared React product tree serving Native/Capacitor mobile and Web desktop surfaces, backed by a Django modular monolith. It is not a PWA.

Core loop:

Observation → Signal → Action Plan → Execution → Validation → Feed update

Feature-specific lifecycle, permissions, statuses, contracts, and implementation details belong to their owning code, tests, and scoped documentation.

## Sources of truth

For current behavior, prefer:

1. owning implementation
2. owning tests
3. generated or published contracts
4. stable agent policies
5. living architecture/product documentation
6. Git history

Do not substitute documentation or agent instructions for inspection of the implementation when behavior matters.

## Engineering principles

- Fix root causes at the owning layer instead of accumulating patches, exceptions, flags, or parallel paths around a broken concept.
- Prefer the smallest **coherent** solution, not necessarily the smallest diff. Correct a directly affected abstraction when evidence shows it is the source of the problem; do not expand into unrelated cleanup.
- Reuse code when it owns the same responsibility. Factor only when the current change demonstrates a stable shared responsibility; resemblance alone is not enough.
- Design for realistic Spore growth in tenants, users, operational records, feeds, conversations, and history. Performance and bounded data access are part of design, not deferred cleanup.
- Avoid speculative hyperscale, generic abstractions, compatibility layers, migration paths, dual behavior, rollout machinery, or infrastructure unless an existing consumer, persisted data, deployment constraint, public contract, or explicit task demonstrates the need.
- Keep one owner for each truth. Backend owns business rules, authorization, lifecycle, visibility, and durable integrity. Client state, realtime, async work, caches, and AI outputs must not become competing business truth.
- Existing code is evidence, not proof of correctness. Challenge patterns that create fragile ownership, unnecessary complexity, poor scalability, or maintenance cost.
- Optimize for long-term maintainability: clear ownership, explicit data flow, bounded responsibilities, and as few special cases as reasonably possible.
- Do not modify unrelated user work or weaken security, tenant isolation, data integrity, lifecycle guards, or meaningful tests to make a change easier.
- AI output is untrusted derived input. Business invariants remain in deterministic application code.

## Exploration and decisions

Explore proportionally to the realistic blast radius. Follow ownership and dependencies rather than directory breadth.

Inspect meaningful consumers before changing a shared abstraction.

Resolve non-blocking technical ambiguity from repository evidence. Ask the human only when a genuine product or architectural decision cannot be resolved safely.

Validated product and architectural decisions are constraints unless new evidence makes them inconsistent or impossible.

## Scoped guidance

Read the closest applicable `AGENTS.md` before changing an area:

- Backend: [`apps/api/AGENTS.md`](apps/api/AGENTS.md)
- Frontend: [`apps/web/AGENTS.md`](apps/web/AGENTS.md)

Use specialized documentation only when the task requires it. Documentation is supporting context, not a substitute for inspecting the owning implementation and tests.

Explicit human workflows live under `.agents/skills/`. Cursor-specific scoped rules live under `.cursor/rules/`.

Use the workflow requested by the human. Do not silently substitute another workflow.
