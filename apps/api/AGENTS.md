# Backend AGENTS.md

Applies to `apps/api/**`.

Spore's backend is a Django modular monolith. Business rules, authorization, lifecycle, tenant isolation, durable integrity, and external API semantics live here.

## Ownership

- Domain `services*` own writes, workflows, lifecycle transitions, and the decision to trigger domain side effects.
- `selectors*` own reusable reads, feeds, filtering, sorting, and scoped list behavior.
- `permissions*` own authorization and RBAC decisions.
- API views orchestrate HTTP concerns, membership resolution, lookups, and error mapping without becoming owners of business workflows.
- Serializers validate and represent API data; they do not own workflows.
- Models own schema, constraints, indexes, and simple invariants.
- `core/` owns shared infrastructure and technical/local maintenance, not runtime product workflows.

Celery tasks, Django signals, realtime consumers, and infrastructure adapters execute or deliver work; they do not become owners of business workflows.

When a domain already has specialized service or selector modules, extend the narrowest existing owner before adding more responsibility to a large generic module. Do not split files mechanically when no clearer responsibility exists.

## Data, feeds and scale

Design reads for realistic growth in establishments, users, observations, signals, action plans, executions, analytics, conversations, notifications, and history.

Any read whose cost grows with tenant history must have a bounded access strategy.

Use pagination, windows, limits, aggregation, or another bounded strategy justified by the domain contract. Do not force one pagination model everywhere.

For growth-sensitive reads, consider query count, indexes, payload size, and repeated work. Avoid N+1 access, naive full-history reads, unbounded fan-out, and unnecessarily large responses.

Feed behavior is a contract: ordering, inclusion/exclusion, visibility, filtering, pagination, and cursor semantics must remain coherent across selector, API response, realtime invalidation, and frontend consumption.

Do not solve frontend performance by returning unbounded or unnecessarily larger backend payloads.

## Transactions, async and realtime

Persist valid durable state before triggering side effects.

Use transactional boundaries when workflows span related writes, lifecycle transitions, permission-relevant state, aggregation, or after-commit effects.

Run external or asynchronous side effects after commit when they depend on committed state.

When correctness depends on current persisted state, reason about concurrent writes and retry behavior rather than assuming requests execute serially.

Celery tasks should receive durable identifiers, reload current state, tolerate retries, and handle missing or stale records safely.

Redis supports cache, rate limiting, Channels, and Celery infrastructure. It is not business or authorization truth.

Realtime consumers stay thin. Prefer invalidating and recomputing current truth from the database over encoding business truth inside realtime events.

## Contracts, tenant integrity and AI

Establishment and organization scoping must be enforced at the owning read/write boundary, not only filtered at the HTTP edge.

Backend authorization remains authoritative. Permission hints exposed to the frontend are UX projections, not a second permission model.

A compatible JSON shape can still be a breaking contract change when ordering, visibility, filtering, pagination, cursor, lifecycle, or error semantics change.

When external API semantics change, update the owning validation/tests and the published contract chain. Do not regenerate schema or frontend artifacts when the external contract is unchanged.

Do not preserve hypothetical legacy behavior. Once production data exists, schema changes must explicitly account for existing rows and deployment safety.

Backfills, staged migrations, or compatibility paths are justified only by real persisted data, active consumers, deployment constraints, or an explicit requirement.

AI output is untrusted external input. AI may propose classification, extraction, summarization, or interpretation; deterministic backend code owns validation, authorization, lifecycle effects, and persistence decisions.

Provider prompts, schemas, and model outputs are versioned integration surfaces. Do not hide business invariants inside prompts.

Minimize sensitive data sent to providers, tasks, logs, realtime payloads, or other infrastructure.

## Validation

Test product risk at the layer that owns it. Avoid proving the same invariant repeatedly across service, API, and integration tests unless each layer protects a distinct failure mode.

Check existing coverage before adding new tests.

Use targeted validation first, then expand according to the realistic blast radius.

When testing details matter, consult the existing testing procedure rather than duplicating it here.

Canonical local backend validation:

- Targeted tests: `make backend-test ARGS='…'`
- Backend validation: `make backend-check`
- Never run `cd apps/api && uv run pytest` on the host.