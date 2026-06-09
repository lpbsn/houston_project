## Phase execution rule

Before coding any phase:
1. Read the relevant AGENTS.md files, docs, current code, tests, migrations, and OpenAPI schema.
2. If requirements are clear, summarize the plan and implement.
3. If a blocking ambiguity affects DB schema, API contract, auth, RBAC, tenant isolation, migrations, security, or frontend state ownership, stop and ask up to 5 precise questions.
4. For each question, include the recommended default and the risk of choosing wrong.
5. Do not ask about naming/style details already answered by project conventions.
6. Keep scope strict. Do not implement future phases.
7. Run required checks and report changed files + commands + results.

### Taxonomy (BusinessUnit / ActivitySubject)

Migration v1 → v2 is **COMPLETE** (Lot 6 closed). See [`taxonomy_v1_to_v2_migration.md`](../../docs/product/taxonomy_v1_to_v2_migration.md).

Active product docs (do not use v1 Module/Domain/Subject as truth):

- [`business_unit_taxonomy_domain.md`](../../docs/product/domains/business_unit_taxonomy_domain.md)
- [`runtime_config_onboarding_domain.md`](../../docs/product/domains/runtime_config_onboarding_domain.md) — Manual Onboarding V2 only (AI onboarding removed from product)
- [`ai_observation_pipeline_contract.md`](../../docs/product/domains/ai_observation_pipeline_contract.md) — pipeline v3

RBAC: `MembershipScope` on **BusinessUnit only**. Ma vue Signal Feed today uses `MembershipScope` (not feed subscriptions). Future feed subscription is deferred (BU-only first, then ActivitySubject subscribe/unsubscribe) — do not implement `MembershipFeedSubscription` v1.

[`phase_a_closure.md`](../../docs/product/phase_a_closure.md) is **historical v1 only** — not an active implementation gate.

## Clarification Gate

Before implementing anything, inspect the relevant docs, current code, schema, and tests.

If requirements are clear, proceed without asking questions.

If ambiguity affects data model, API contract, security, RBAC, migrations, authentication, tenant isolation, or user-visible behavior, stop and ask up to 5 precise questions before coding.

Do not ask questions about details already answered in docs, AGENTS.md, existing code, tests, or schema.

For each question, explain:
- why it matters
- the recommended default
- the risk of choosing wrong

Backend stack:

- Python 3.13.13
- Django 5.2 LTS
- Django REST Framework
- PostgreSQL
- Celery
- Redis
- Django Channels
- Pydantic
- OpenAPI

Do not upgrade backend framework versions unless explicitly requested.

------

## Backend principles

Django is the business authority.

PostgreSQL is the persisted source of truth.

Redis is temporary technical state only.

Celery owns async execution only.

Channels owns realtime invalidation only.

Pydantic validates structured AI/technical payloads.

OpenAPI owns the API contract.

Prefer explicit service methods over generic abstractions.

Avoid placing business logic in framework hooks.

------

## Expected Django app structure

Each domain app should follow this structure when relevant:

```
models.py
services.py
selectors.py
permissions.py
api/
  serializers.py
  views.py
  urls.py
tests/
```

Allowed shared technical primitives may live in `core/`.

Forbidden:

- business workflows in `core/`
- domain-specific services in `core/`
- catch-all utilities that hide ownership
- cross-domain shortcuts that bypass service boundaries

------

## Backend ownership rules

Business writes and workflows go in `services.py`.

Examples:

- submit Observation
- create Signal
- aggregate Signal
- create Action
- accept Action
- mark Action done
- validate Action
- reopen Action
- cancel Action
- create Checklist execution
- create notification
- create domain event

Complex reads go in `selectors.py`.

Examples:

- Signal feed
- Execution feed
- filtered domain views
- permission-scoped lists
- detail projections
- dashboard-style query composition

Authorization rules go in `permissions.py`.

Examples:

- can view Signal
- can create Action
- can validate Action
- can cancel Signal
- can access establishment resource
- can access media
- can subscribe to realtime channel

DRF views must stay thin:

1. validate request shape
2. check permission
3. call service or selector
4. return response

Serializers are for API validation and representation only.
Serializers must not orchestrate Houston business workflows.

Models may contain:

- fields
- constraints
- indexes
- simple local invariants
- simple computed properties

Models must not orchestrate workflows.

------

## Status transition rules

All business state transitions must be explicit service methods.

Forbidden:

- generic PATCH status endpoints for business transitions
- status changes from serializers
- status changes from DRF views
- status changes from React
- status changes from Django signals
- hidden transition side effects

Implemented transition endpoints (confirm in `apps/api/schema.yml` before use):

```
POST /actions/:id/accept
POST /actions/:id/mark_done
POST /actions/:id/validate
POST /actions/:id/reopen
POST /actions/:id/cancel

POST /signals/:id/resolve
POST /signals/:id/cancel
POST /signals/:id/pin
POST /signals/:id/unpin
PATCH /signals/:id/urgency/
```

Do not add new transition endpoints without updating OpenAPI and tests.

Legacy `POST /signals/:id/add_domain` and `POST /signals/:id/remove_domain` are **obsolete** for MVP (single BU/AS classification per Signal).

Each transition must:

- check backend permission
- validate current state
- validate establishment scope
- run inside `transaction.atomic` when multiple writes are involved
- emit the expected domain event when applicable
- return the updated resource summary

------

## Transaction rules

Use `transaction.atomic` for critical write workflows.

Use transactions when a service:

- changes status
- creates multiple related records
- writes domain events
- updates feed timestamps
- creates notifications
- creates or updates permissions-relevant data
- performs aggregation
- creates an Action from a Signal

Do not wrap simple read selectors in transactions.

------

## Domain guardrails

### Observation

Rules:

- text input is required
- audio is temporary and only produces editable text
- photos are optional
- photo-only Observation is forbidden
- pipeline receives validated text only
- raw Observation text is never exposed in product APIs

Celery payloads must pass IDs only.
Workers must reload sensitive content server-side.

### Signal

Rules (Phase 4 — **implemented** in codebase; archive Signal and timeline remain candidate):

- created only by backend service
- aggregated only by backend service
- **one primary v3 classification per Signal**: `affected_business_unit`, `responsible_business_unit`, `activity_subject`; optional `operational_unit` (location only)
- **Ma vue** Signal Feed: `MembershipScope` BusinessUnit match (Owner/Director: all active)
- feed visibility and sorting are backend-owned
- `last_activity_at` is maintained by backend

### Action

Phase 5 — **core implemented** (lifecycle + Execution Feed Actions). Phase 7 Checklists — **implemented** (templates, assignments, executions, polymorphic Execution Feed merge). Notifications and comments remain out of scope.

Allowed transitions:

- create
- accept
- mark_done
- validate
- reopen
- cancel
- reassign

Each transition must check backend permission.

Generic status mutation endpoints are forbidden.

### Feeds

Phase 4 Signal Feed and Phase 5/7 Execution Feed — **core implemented** in codebase.

Execution Feed is **polymorphic** (`item_type: action | checklist`). Orchestration lives in `houston/actions/execution_feed.py`; checklist feed querysets in `houston/checklists/selectors.py`; lazy materialization in `houston/checklists/materialization.py`. Checklist items are prioritized in page assembly (checklists first, Actions fill remaining slots).

Backend applies:

- RBAC
- establishment scope
- `view_mode=personal|general` (Signal Feed: personal uses `MembershipScope`; Execution Feed personal uses assigned responsibilities for Actions and checklist rules for Checklists)
- filters (Signal Feed: partial — see `schema.yml`)
- sorting (per-type; see `feed_domain.md` for merge rules)
- pagination (cursor envelope)

Never return unauthorized data and rely on frontend hiding.

Future feed subscription (deferred): personalize Ma vue by BusinessUnit first, then ActivitySubject subscribe/unsubscribe — not implemented.

### AI pipeline

Rules:

- Pydantic validates AI JSON shape
- Django validates business rules
- AI does not mutate the database directly
- AI does not decide permissions
- AI does not decide urgency in MVP
- store only technical AI metadata
- no prompt/content logs in standard logs
- images are not sent to AI in MVP

------

## DRF API rules

Use DRF views/viewsets only as HTTP orchestration.

Views may:

- parse request
- instantiate serializer
- call permission function
- call service or selector
- return response

Views must not:

- implement workflows
- directly mutate business objects
- contain complex query logic
- decide business transitions
- bypass services

Serializers may:

- validate request shape
- validate primitive field constraints
- represent response data

Serializers must not:

- create complex workflows
- perform status transitions
- perform permission checks
- create domain events
- call Celery tasks directly
- create notifications directly

------

## OpenAPI rules

API changes require OpenAPI updates.

If using drf-spectacular or another schema generator, use the project-defined command.

Do not invent OpenAPI generation commands.

If no command exists, report:

```
OpenAPI generation command is not defined yet.
```

and propose a dedicated setup task.

Schema changes must be reflected in generated frontend types.

------

## Authentication foundation rules

Backend auth for Houston uses:

- opaque short-lived bearer access tokens
- rotating opaque refresh tokens
- `UserSession` as the session authority
- `AccessToken` and `SessionRefreshToken` digests only

Mutation auth endpoints that depend on cookies must enforce CSRF:

- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `POST /api/v1/auth/logout/`

Never:

- store raw tokens in the database
- expose token digests in API responses
- make frontend state the authorization authority
- use JWT for MVP auth

Auth throttling for public auth mutation endpoints is implemented via DRF `ScopedRateThrottle` (see [`authentication_charter.md`](../../docs/architecture/authentication_charter.md)).

------

## Celery rules

Celery tasks are execution wrappers, not business services.

Tasks may:

- receive IDs
- load database records
- call services
- handle retry policy
- log technical metadata

Tasks must not:

- receive raw Observation text
- receive sensitive business payloads
- contain business workflows directly
- bypass permissions or establishment scope
- become the source of business truth

Broker messages must stay small and non-sensitive.

Celery Beat (optional `celery-beat` Compose service): `CELERY_BEAT_SCHEDULE` in `config/settings.py` runs `materialize_checklist_assignments_horizon_task` daily (UTC). Checklist horizon materialization also runs eagerly on assignment create and lazily on execution-feed read — Beat is not the only path.

------

## Redis rules

Redis may be used for:

- cache
- rate limit counters
- temporary locks
- short-lived technical state
- Channels layer

Redis must not be used for:

- persisted business truth
- authorization truth
- operational history
- durable workflow state
- sensitive raw content

------

## Channels and realtime rules

Channels consumers must stay thin.

**Chat V1** (`houston/chat/`) is the first WebSocket surface :

- ASGI : `AllowedHostsOriginValidator` + `URLRouter` — **no** `AuthMiddlewareStack`
- Auth : REST ws-ticket consumed in first WS message (see [`authentication_charter.md`](../../docs/architecture/authentication_charter.md))
- Server : Daphne
- Message send : WebSocket only in V1 (no REST message write)
- Delivery : personal membership group `chat_est_{establishment_id}_mbr_{membership_id}` so new conversations deliver without reconnect
- Spec : [`chat_domain.md`](../../docs/product/domains/chat_domain.md)

**Global realtime** (deferred) consumers may:

- authenticate user
- check membership
- check channel subscription permission
- send lightweight invalidation events
- trigger frontend refetch

Consumers must not:

- perform business workflows outside their domain
- send full business payloads on **generic** invalidation channels
- expose sensitive content to unauthorized recipients
- bypass REST API for authoritative reads
- mutate domain state except technical connection state and Chat message persistence path

------

## Logging rules

Logs may contain:

- correlation ID
- request ID
- user ID
- establishment ID
- event type
- error code (see [`api_error_contract.md`](../../docs/architecture/api_error_contract.md) for supported values and response shapes)
- latency
- provider/model metadata
- status

Logs must not contain:

- raw Observation text
- full comments
- audio content
- photo content
- secrets
- tokens
- full AI prompts
- full AI outputs containing business content

------

## Backend commands

Run from repository root unless stated otherwise.

Install dependencies:

```
cd apps/api && uv sync
```

Lint:

```
cd apps/api && uv run ruff check .
```

Format check:

```
cd apps/api && uv run ruff format --check .
```

Tests:

```
cd apps/api && uv run pytest
```

Migration check:

```
cd apps/api && uv run python manage.py makemigrations --check --dry-run
```

BusinessUnit catalogue seed (required after migrate for v2 autocomplete):

```
cd apps/api && uv run python manage.py import_business_unit_catalog
```

OpenAPI generation:

```
Use the project-defined OpenAPI command if it exists.
If missing, do not invent it.
```

------

## Backend testing rules

Add or update tests when changing:

- services
- selectors
- permissions
- APIs
- models
- migrations
- status transitions
- Celery tasks
- Channels consumers
- AI pipeline validation
- uploads
- notifications

Backend tests should verify:

- successful path
- permission denial
- invalid state transition
- establishment scoping
- database side effects
- emitted domain event when applicable
- API response shape
- sensitive data is not exposed

Prefer behavior-focused tests.

Avoid tests that depend on fragile internal mocking.

------

## Backend Definition of Done

Backend work is done only when:

- service/selector/permission ownership is respected
- views remain thin
- serializers do not orchestrate workflows
- status transitions are explicit
- transaction boundaries are correct
- tenant scoping is enforced
- sensitive payload rules are respected
- migrations exist for model changes
- OpenAPI is updated when API shape changes
- tests cover changed behavior
- relevant backend commands were run or a reason is given
- risks/debt are stated
