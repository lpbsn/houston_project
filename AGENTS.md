Houston is a backend-centric B2B operational workflow app.

Core loop:

Observation -> Signal -> Action -> Execution -> Validation -> Feed update

Django is the business authority.
React is the UI layer.
PostgreSQL is the persisted source of truth.
OpenAPI is the frontend/backend contract.

More specific rules may exist in nested `AGENTS.md` files.
When editing files under a nested directory, follow both this file and the nearest nested `AGENTS.md`.

---

## Repository layout

Backend:

- `apps/api/`
- Django project/apps: `apps/api/houston/`

Frontend:

- `apps/web/`
- Frontend source: `apps/web/src/`

Documentation:

- `docs/`

Do not move files, rename modules, or reorganize directories unless the task explicitly requires it.

---

## Non-negotiable architecture rules

Use a modular monolith.

Prefer:

- explicit code
- boring architecture
- small safe changes
- backend-enforced business rules
- generated API contracts
- behavior-focused tests

Avoid:

- premature abstractions
- clever metaprogramming
- generic frameworks
- unrelated refactors
- frontend business logic
- hidden side effects

The backend owns:

- business workflows
- permissions
- tenant scoping
- status transitions
- feed visibility
- feed sorting
- API contracts

The frontend owns:

- UI rendering
- user interaction
- local UI state
- API consumption through generated clients
- server-state caching through TanStack Query

For any authentication/session/security-related work, read and follow docs/architecture/authentication_charter.md first.

---

## Phase execution gates (taxonomy / onboarding programme)

When working on **Module → Domain → Subject** taxonomy or onboarding runtime:

| Phase | Allowed | Forbidden |
| --- | --- | --- |
| **Phase A** | Documentation in `docs/` only | Application code, migrations, tests, fixtures, `schema.yml`, generated TS clients |
| **Phase B/C** | Onboarding/runtime taxonomy code in `establishments/` (after human Phase A sign-off) | Signal, Signal Feed, `MembershipFeedSubscription`, Execution Feed, Observation pipeline runtime, Action taxonomy independent of Signal |
| **Phase 4/5** | Signal, Signal Feed, subscriptions, Observation pipeline (when explicitly opened) | Premature feed/subscription code before Signal model |

Authoritative closure gate: [`docs/product/phase_a_closure.md`](docs/product/phase_a_closure.md). **Do not restore B/C stashes or regenerate OpenAPI until Phase A is human-validated.**

Key contracts: [`operational_taxonomy_domain.md`](docs/product/domains/operational_taxonomy_domain.md), [`runtime_config_onboarding_domain.md`](docs/product/domains/runtime_config_onboarding_domain.md), [`ai_observation_pipeline_contract.md`](docs/product/domains/ai_observation_pipeline_contract.md), [`feed_subscription_domain.md`](docs/product/domains/feed_subscription_domain.md).

---

## Agent workflow

Before coding:

1. Identify the domain owner.
2. Identify the change type:
   - read
   - write
   - async
   - realtime
   - UI
   - API contract
   - migration
3. Inspect existing code before creating new code.
4. Reuse existing services, selectors, permissions, hooks, and components when possible.
5. Make the smallest safe change.
6. Add or update tests for changed behavior.
7. Run relevant checks.
8. Report changed files, commands run, results, and remaining risks.

For complex, ambiguous, cross-domain, or architecture-impacting tasks:

- produce a short plan before implementation
- list assumptions explicitly
- ask only blocking questions
- do not start broad refactors without approval

---

## Scope control

Do not do unrelated refactors.

Do not change formatting broadly unless the task is formatting-related.

Do not introduce new architecture patterns without approval.

Do not add production dependencies without explicit approval.

Do not upgrade framework versions unless explicitly requested.

Do not modify lockfiles unless dependency changes are in scope.

Do not manually edit generated files.

Do not manually edit migrations unless intentionally correcting a migration.

---

## Cross-cutting security and privacy rules

Forbidden:

- frontend-only authorization
- tenant data access without establishment scoping
- raw Observation text in product feeds
- raw Observation text in logs
- raw Observation text in websocket payloads
- raw Observation text in Celery payloads
- raw Observation text in notifications
- raw Observation text in persistent frontend storage
- sensitive business content in broker messages
- full business payloads over WebSocket
- business truth in Redis
- secret keys in `VITE_*` environment variables
- durable offline storage of sensitive business data
- broad admin-style APIs in product endpoints
- `core/` used as a business dumping ground

Backend authorization is mandatory for:

- read endpoints
- write endpoints
- signed media URLs
- realtime subscriptions
- notifications
- async job execution

---

## API and OpenAPI rules

The backend API is the only source of frontend data.

No frontend endpoint usage without OpenAPI.

API changes must follow this workflow:

1. update backend serializer/input schema
2. update view/service/selector
3. update OpenAPI schema
4. regenerate TypeScript API client
5. update TanStack Query hook
6. update React component
7. update tests

Generated TypeScript API files must not be manually edited.

If generated files are wrong, fix the backend schema/source and regenerate.

If an OpenAPI generation command or API client generation command is missing, do not invent one.
Report it and propose a dedicated setup task.

---

## Realtime rules

REST API remains the source of truth.

WebSockets are only for:

- invalidation
- refetch triggers
- lightweight event notifications
- non-sensitive UI refresh signals

Do not send full business payloads over WebSockets.

Do not build business truth inside realtime consumers.

Do not make WebSocket consumers perform business workflows.

---

## AI rules

AI may propose structured outputs.

Backend code must validate and persist final business truth.

Rules:

- Pydantic validates AI JSON shape
- Django validates business rules
- AI never mutates the database directly
- AI never decides permissions
- AI never decides urgency in MVP
- store only technical AI metadata
- do not store prompts/content in standard logs
- images are not sent to AI in MVP

AI proposes.
Backend validates.
Humans retain operational authority.

---

## Dependency policy

Before adding a dependency, verify:

1. existing project code cannot solve the need simply
2. the dependency is mature and maintained
3. the dependency is compatible with the current stack
4. the dependency does not introduce avoidable complexity
5. the user explicitly approved it

Do not upgrade:

- Python
- Django
- DRF
- React
- Vite
- TypeScript
- major infrastructure libraries

unless explicitly requested.

---

## Root commands

Run commands from the relevant project directory.

Backend rules and commands are in:

```txt
apps/api/AGENTS.md
```

Frontend rules and commands are in:

```
apps/web/AGENTS.md
```

------

## Documentation rules

Use:

- `AGENTS.md` for repository-wide agent rules
- `apps/api/AGENTS.md` for backend-specific agent rules
- `apps/web/AGENTS.md` for frontend-specific agent rules
- `docs/` for long-form product, architecture, security, API, and domain documentation

Do not duplicate long domain documentation in `AGENTS.md`.

If a rule is specific to backend, put it in `apps/api/AGENTS.md`.

If a rule is specific to frontend, put it in `apps/web/AGENTS.md`.

------

## Testing rules

Add or update tests when changing behavior.

Tests must focus on observable behavior, not fragile implementation details.

Do not add brittle tests that mock internals unnecessarily.

Prefer tests that verify:

- permission behavior
- tenant scoping
- state transitions
- API response shape
- database side effects
- user-visible frontend behavior

------

## Definition of Done

A task is done only when:

- requested scope only was changed
- no unrelated refactor was introduced
- ownership rules are respected
- backend business logic remains backend-owned
- frontend server state and UI state are not mixed
- API changes update OpenAPI and generated TypeScript client when applicable
- security and privacy rules are respected
- model changes include migrations
- changed behavior has tests or a clear reason why tests were not added
- relevant checks were run
- command results are reported
- remaining risks or debt are explicitly stated
- generated files were not manually edited
- no unnecessary abstraction was introduced

Final response must include:

1. summary of changes
2. files changed
3. tests/checks run and result
4. risks/debt
5. plain-English explanation