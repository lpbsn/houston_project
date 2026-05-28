# Phase 2 — Runtime config / Onboarding

## Status

Active Phase 2 source of truth.

This document was created during a documentation-only task. The documentation task did not implement backend code, frontend code, migrations, OpenAPI changes, generated frontend types, or tests.

Future Phase 2 implementation sub-phases are expected to change code according to the ordered plan below.

## Authority order

1. current code
2. tests
3. `apps/api/schema.yml`
4. active domain docs
5. this file
6. archived reference docs under `docs/archive/codex/`

## Objective

Implement minimal establishment-scoped runtime configuration and onboarding required
before operational use.

Phase 2 must make manual setup work first, while preparing a clean seam for future
AI-assisted onboarding.

Onboarding is a multi-step workflow, not only runtime configuration. Phase 2 therefore
includes a minimal `OnboardingSession` foundation to keep onboarding process state
separate from `Establishment` runtime state.

Core product rule:

```txt
AI proposes. Human validates. Backend activates.
```

## Current implementation baseline

Current repository state confirms these Phase 0/1 foundations are implemented:

- `User` exists in `houston.accounts`.
- `Organization` exists in `houston.organizations`.
- `Establishment` exists in `houston.establishments` with `draft`, `active`, and
  `deactivated` statuses.
- `EstablishmentMembership` exists with `owner`, `director`, `manager`, and `staff`
  roles plus `invited`, `active`, and `deactivated` statuses.
- `OperationalDomain` exists inside `houston.establishments`.
- `MembershipDomain` exists as the membership-scoped operational domain link.
- Auth/session endpoints are implemented and present in `apps/api/schema.yml`:
  - `GET /api/v1/auth/csrf/`
  - `POST /api/v1/auth/login/`
  - `POST /api/v1/auth/refresh/`
  - `POST /api/v1/auth/logout/`
  - `GET /api/v1/auth/bootstrap/`
  - `POST /api/v1/auth/switch_establishment/`
- Membership management endpoints are implemented and present in `apps/api/schema.yml`:
  - `GET /api/v1/establishments/{establishment_id}/memberships/`
  - `GET /api/v1/establishments/{establishment_id}/memberships/{membership_id}/`
  - `PATCH /api/v1/establishments/{establishment_id}/memberships/{membership_id}/`
  - `POST /api/v1/establishments/{establishment_id}/memberships/{membership_id}/deactivate/`
- Scoped user search is implemented and present in `apps/api/schema.yml`:
  - `GET /api/v1/establishments/{establishment_id}/users/search/?q=`
- `CanManageRuntimeContext` exists in `houston.establishments.permissions`.
- The frontend has an auth/workspace shell under `apps/web/src/features/auth`.
- The frontend imports generated OpenAPI types from `apps/web/src/api/generated/types.ts`.
- The frontend uses TanStack Query for auth/bootstrap, membership, mutation, and scoped
  search server state.

Current repository state confirms these Phase 2 data-model foundation items are
implemented:

- `OnboardingSession`
- `EstablishmentActivityDescription`
- `OperationalModule`
- `OperationalUnit`
- `RuntimeVocabulary`
- `RuntimeTag`
- `RuntimeTagDomain`
- `RoutingHint`
- `RoutingHintDomain`

Current repository state confirms these Phase 2 items are not implemented:

- onboarding activation service
- onboarding session API
- runtime config API
- runtime config frontend UI
- activation summary API
- section validation workflow
- default template proposal flow
- onboarding proposal API
- `OnboardingProposal`
- `apply_onboarding_proposal`
- manual/template proposal apply flow
- real AI onboarding provider integration

No runtime/onboarding API endpoint is currently confirmed in `apps/api/schema.yml`.

## Archived reference alignment

The archived onboarding documents are reference inputs, not the Phase 2 source of truth.

Phase 2 adopts from the archived onboarding domain:

- establishment activity description is required
- activity description minimum length = 50 characters
- manual onboarding fallback is required
- default templates are a supported fallback concept
- validation by section is required
- accept-all by section is supported
- modules and domains are required for activation
- vocabulary, tags, routing hints, and units are optional for activation
- activation summary is required before activation
- staff invitations are not required before activation
- initial Owner/Director and Manager setup matters for activation
- manager operational domains are required for activation
- onboarding must stay fast and not model the full organization

Phase 2 adopts from the archived AI onboarding contract:

- AI proposes, human validates, backend activates
- future AI proposals must use allowed module/domain/unit catalogs
- unknown modules/domains/units must never create runtime objects automatically
- future AI proposals must support caps:
  - modules max 10
  - domains max 15
  - units max 15
  - vocabulary max 30
  - runtime_tags max 30
  - routing_hints max 30
- proposals must not assign roles
- proposals must not assign memberships
- proposals must not change billing
- proposals must not generate checklist templates in Phase 2
- proposals must not generate signal examples in Phase 2
- proposals must not activate runtime directly
- manual/template proposals must use the same apply boundary as future AI proposals

Phase 2 defers:

- AI events
- post-activation AI rerun implementation
- `/api/v1/onboarding/:id/...` session endpoints unless the Phase 2 API design
  explicitly chooses them

## AI domains separation

AI Onboarding and AI Observation Pipeline are separate AI domains. They may share
infrastructure later, but they must not share prompt contracts, output schemas,
lifecycle assumptions, or product responsibilities.

Use explicit domain separation:

- `ai_domain = onboarding` is for low-frequency, human-validated bootstrap proposals.
- `ai_domain = observation_pipeline` is for future high-frequency operational
  interpretation.
- onboarding AI and observation pipeline AI may use different prompts, schemas,
  providers, models, costs, latency targets, and evaluation metrics.
- onboarding AI only proposes runtime onboarding structure.
- observation pipeline AI may later support operational processing, but remains
  separate and out of Phase 2.
- the two domains must not be coupled.

## Chosen defaults

- Do not create a new Django app in this phase.
- Keep runtime config implementation inside `houston.establishments` because
  `OperationalDomain`, membership-domain links, and runtime permission helpers already
  live there.
- Phase 2 includes a minimal `OnboardingSession` foundation.
- Phase 2 includes an `OnboardingProposal` foundation.
- Full Phase 2 completion requires both `OnboardingSession` and `OnboardingProposal`.
- If either is deferred, the milestone is only Phase 2A complete, not full Phase 2.
- Do not change Phase 1 active-membership bootstrap semantics.
- Add separate onboarding access for draft/active establishments later.
- Manual onboarding first.
- Manual runtime setup must work before AI assistance.
- Real AI Onboarding provider integration is part of full Phase 2, but only after the
  `OnboardingProposal` foundation exists.
- Real AI provider integration remains out of scope for Sub-phase 3 and earlier
  sub-phases.
- OnboardingProposal structure and manual/template proposal apply flow are part of full
  Phase 2.
- AI Onboarding must store output as `OnboardingProposal` only.
- AI must never mutate runtime configuration directly.
- AI Observation Pipeline remains out of Phase 2.
- Runtime config is establishment-scoped.
- Runtime tags and routing hints never drive permissions.
- Runtime tags and routing hints do not affect RBAC.
- Backend is the source of truth for activation.
- Frontend only reflects backend state and validation errors.
- OpenAPI remains mandatory for every API endpoint.
- Frontend must use generated OpenAPI types only.
- Frontend must use TanStack Query for onboarding/runtime server state.
- React must not own business rules or authorization.

## Critical Phase 1 preservation constraint

Current Phase 1 active membership resolution only includes establishments with status
`active`.

Phase 2 onboarding needs to configure `draft` establishments.

Do not break Phase 1.

Future implementation must add a separate path-scoped onboarding access helper for
active owner/director memberships on `draft` or `active` establishments.

Do not make `draft` establishments appear in the regular active workspace/bootstrap
flow unless a later task explicitly changes that product decision.

## Warning about `CanManageRuntimeContext`

`CanManageRuntimeContext` exists, but future implementation must verify whether it is
suitable for draft onboarding.

If it depends on active-establishment membership resolution, create a separate
onboarding-specific helper instead of changing Phase 1 behavior.

## Activation minimum

An establishment can be activated only if:

- the organization exists and is active
- the establishment exists and is currently `draft`
- the establishment has a validated activity description
- the establishment activity description is at least 50 characters
- the establishment has at least 1 active operational module
- the establishment has at least 3 active operational domains
- the establishment has at least 1 active Owner or Director membership
- the establishment has at least 1 active or invited Manager membership
- initial managers have operational domains assigned
- required sections are validated before activation
- modules and domains are required sections
- vocabulary, tags, routing hints, and units may be skipped for activation
- activation summary is available before activation
- runtime tags, vocabulary, routing hints, and units are optional for activation

Backend must enforce this. Frontend may display helper messages but must not be the
authority.

Staff invitations are not required before activation.

## AI Onboarding integration strategy

AI Onboarding can be integrated in Phase 2 because its scope is limited to onboarding
proposals.

AI Onboarding must use the `OnboardingProposal` boundary:

- AI output must be stored as an `OnboardingProposal`.
- AI output must never directly write active runtime configuration.
- backend must validate the proposal before it can be stored or applied.
- human validation is required before apply.
- only backend services can apply validated proposal data into runtime configuration.
- ensure manual/template proposals use the same apply boundary as future AI proposals

AI Onboarding must:

- use allowed module/domain/unit catalogs
- enforce proposal caps
- validate structured output before storage/application
- produce only onboarding proposal sections:
  - operational modules
  - operational domains
  - operational units
  - runtime vocabulary
  - runtime tags
  - routing hints

AI Onboarding must not generate:

- roles
- memberships
- billing changes
- checklists
- signal examples
- actions
- comments
- operational execution workflows

AI Onboarding must not know or own Signal, Action, Signal lifecycle, Action lifecycle,
feeds, or operational execution workflows.

AI Observation Pipeline remains separate and out of scope for Phase 2.

Strict No-AI-claims rule:

Do not claim AI-assisted onboarding is implemented until a real onboarding provider,
prompt contract, strict JSON schema or structured output contract, retry policy,
timeout policy, AIUsageLog or equivalent usage tracking, and tests exist.

## Proposal payload shape

Candidate payload shape for future proposals:

```json
{
  "operational_modules": [],
  "operational_domains": [],
  "operational_units": [],
  "runtime_vocabulary": [],
  "runtime_tags": [],
  "routing_hints": []
}
```

This is a candidate payload shape, not an implemented API contract yet.

Unknown or invalid values must be rejected or safely ignored by backend validation.
Future AI proposals must use allowed module/domain/unit catalogs. Unknown
modules/domains/units must never create runtime objects automatically.

Proposal validation must enforce these caps:

- modules max 10
- domains max 15
- units max 15
- vocabulary max 30
- runtime_tags max 30
- routing_hints max 30

Proposals must not assign roles. Proposals must not assign memberships. Proposals must
not change billing. Proposals must not generate checklist templates in Phase 2.
Proposals must not generate signal examples in Phase 2. Proposals must not activate
the establishment directly. Activation must remain an explicit backend service path
after human validation and proposal application.

## Final ordered sub-phases

### 1. Phase 2 contract freeze

Objective:

- Create and maintain this Phase 2 source-of-truth build plan from current repository
  state.
- Align with archived onboarding references only where they fit the current repo and
  validated Phase 2 direction.
- Preserve the current Phase 1 contract while documenting the Phase 2 sequence.

Likely files touched:

- `docs/product/build_plan_mvp/phase_2_runtime_config_onboarding.md`

API changes:

- None.

Migration risk:

- None.

Tests required:

- None for this documentation-only sub-phase unless a docs lint command is introduced.

Exact commands to run:

```bash
git status --short
git diff -- docs/product/build_plan_mvp/phase_2_runtime_config_onboarding.md
```

Explicit out of scope:

- Backend code
- Frontend code
- Migrations
- `apps/api/schema.yml`
- Generated frontend types
- Phase 1 docs
- Domain docs
- Archived docs

Definition of Done:

- The Phase 2 build plan exists.
- The document reflects current code, tests, schema, active domain docs, and relevant
  archived references in the correct authority order.
- No candidate model, endpoint, or AI behavior is described as implemented.
- No file other than this Phase 2 build plan changed.

### 2. Backend onboarding + runtime data model foundation — DONE

Status:

- DONE. Sub-phase 2 is implemented and green.

Objective:

- Add minimal onboarding and runtime data models required for complete manual
  onboarding and future AI-readiness.
- Keep onboarding and runtime model foundations inside `houston.establishments`.
- Keep onboarding process state separate from `Establishment` runtime state.

Implemented models:

- `OnboardingSession`
- `EstablishmentActivityDescription`
- `OperationalModule`
- `OperationalUnit`
- `RuntimeVocabulary`
- `RuntimeTag`
- `RuntimeTagDomain`
- `RoutingHint`
- `RoutingHintDomain`

Recommended `OnboardingSession` fields:

- `organization`
- `establishment`
- `started_by`
- `status`
- `source_mode`
- `current_step`
- `ai_attempts`
- `last_error_code`
- `last_error_message`
- `started_at`
- `ready_for_activation_at`
- `activated_at`
- `canceled_at`
- `created_at`
- `updated_at`

Recommended statuses:

- `started`
- `description_submitted`
- `configuring_runtime`
- `proposal_ready`
- `validating_sections`
- `ready_for_activation`
- `activated`
- `failed`
- `canceled`

Recommended `source_mode` values:

- `manual`
- `template`
- `ai`

`ai` may exist as a future-compatible enum value, but no real AI provider is
called in Sub-phase 2.

Database rule:

- An establishment can have only one non-terminal initial onboarding session at a time.
- Historical sessions may exist for audit, fallback, or future rerun flows.
- Use database constraints where appropriate for establishment-scoped uniqueness and
  active/non-terminal session rules.

Terminal OnboardingSession statuses:
- activated
- failed
- canceled

Non-terminal OnboardingSession statuses:
- started
- description_submitted
- configuring_runtime
- proposal_ready
- validating_sections
- ready_for_activation

EstablishmentActivityDescription is the canonical Phase 2 model for validated activity
description unless current code conventions strongly justify a field on Establishment.
Do not duplicate the same description state in both places.

Likely files touched:

- `apps/api/houston/establishments/models.py`
- `apps/api/houston/establishments/migrations/`
- `apps/api/houston/establishments/tests/test_models.py`

API changes:

- None in this sub-phase.

Migration risk:

- New tables and constraints are expected.
- Partial uniqueness for non-terminal onboarding sessions may require careful database
  constraint design.
- Avoid destructive changes to existing Phase 1 tables.
- Do not manually edit generated migrations except to correct intentional migration
  output.

Tests required:

- `OnboardingSession` constraints and terminal/non-terminal behavior.
- Establishment-scoped uniqueness for runtime keys.
- Activity description minimum length validation target.
- Optional runtime objects do not block model creation.
- Runtime tags and routing hints do not grant permissions.
- Draft establishments remain excluded from regular Phase 1 active membership
  resolution.

Exact commands to run:

```bash
make migrations-check
cd apps/api && uv run pytest houston/establishments/tests/test_models.py
cd apps/api && uv run pytest houston/establishments/tests/test_access.py
make check
make lint
```

Explicit out of scope:

- Runtime/onboarding API
- Frontend UI
- Proposal apply flow
- Real AI provider integration
- AIUsageLog, AI events, provider retry policy, and provider timeout policy

Definition of Done:

- `OnboardingSession` foundation exists with database constraints for one non-terminal
  initial onboarding session per establishment.
- Runtime model foundation exists with migrations.
- Existing `OperationalDomain` and `MembershipDomain` behavior remains compatible.
- Runtime tags, routing hints, vocabulary, and units are not permission authorities.
- Relevant model tests pass.

### 3. Onboarding access, selectors, services, and activation readiness

Objective:

- Add backend-owned onboarding session access and activation readiness logic.
- Add selectors and services for onboarding session state, runtime config, section
  validation, activation summary, and backend activation.
- Preserve Phase 1 active workspace/bootstrap behavior.

Must include:

- onboarding-session-specific access helper
- selectors
- services
- activation readiness service
- activation summary service
- section validation service if needed
- preservation of Phase 1 active workspace/bootstrap behavior

Likely files touched:

- `apps/api/houston/establishments/access.py`
- `apps/api/houston/establishments/permissions.py`
- `apps/api/houston/establishments/selectors.py`
- `apps/api/houston/establishments/services.py`
- `apps/api/houston/establishments/tests/test_access.py`
- `apps/api/houston/establishments/tests/test_permissions.py`
- new service tests under `apps/api/houston/establishments/tests/`

API changes:

- None in this sub-phase.

Migration risk:

- None expected unless the onboarding/runtime model foundation needs correction.

Tests required:

- Owner/Director can manage onboarding session.
- Manager/Staff cannot activate onboarding.
- Manager/Staff cannot configure runtime context unless a later explicit rule permits a
  narrower post-activation management path.
- Draft establishments stay excluded from regular workspace/bootstrap.
- Activation minimum is enforced server-side.
- Activation summary reflects backend readiness.
- Section validation state does not equal runtime activation until backend
  apply/activation.
- Inactive users, inactive memberships, deactivated establishments, and inactive
  organizations are denied.
- Activation changes establishment status only through an explicit service.

Exact commands to run:

```bash
cd apps/api && uv run pytest houston/accounts/tests/test_auth_api.py
cd apps/api && uv run pytest houston/accounts/tests/test_services.py
cd apps/api && uv run pytest houston/establishments/tests/test_access.py
cd apps/api && uv run pytest houston/establishments/tests/test_permissions.py
cd apps/api && uv run pytest houston/establishments/tests/
make check
make lint
```

Explicit out of scope:

- Changing bootstrap to include draft establishments.
- Changing regular active workspace selection semantics.
- Frontend authorization decisions.
- Generic status mutation endpoints.
- Real AI provider integration.

Definition of Done:

- Onboarding session access is path-scoped, backend-owned, and tested.
- Activation readiness and activation summary are backend-owned and tested.
- Activation minimum is enforced server-side.
- Manager and Staff cannot activate onboarding.
- Phase 1 active-membership behavior is unchanged.

### 4. Runtime/onboarding API

Objective:

- Expose onboarding session, runtime config, activation summary, and activation through
  explicit DRF endpoints.
- Keep OpenAPI as the frontend/backend contract.

Candidate endpoints:

```txt
POST   /api/v1/onboarding-sessions/
GET    /api/v1/onboarding-sessions/{session_id}/
PATCH  /api/v1/onboarding-sessions/{session_id}/description/
GET    /api/v1/onboarding-sessions/{session_id}/runtime-config/
PUT    /api/v1/onboarding-sessions/{session_id}/runtime-config/
GET    /api/v1/onboarding-sessions/{session_id}/activation-summary/
POST   /api/v1/onboarding-sessions/{session_id}/activate/
```

Optional post-activation endpoint, only if justified by current repository conventions:

```txt
GET    /api/v1/establishments/{establishment_id}/runtime-config/
```

Archived documents mention `/api/v1/onboarding/:id/...` style endpoints, but Phase 2
should prefer the path style that best fits the current repo conventions and OpenAPI
consistency.

Likely files touched:

- `apps/api/houston/establishments/api/serializers.py`
- `apps/api/houston/establishments/api/views.py`
- `apps/api/houston/establishments/api/urls.py`
- `apps/api/houston/establishments/tests/`
- `apps/api/schema.yml` generated by the schema command

API changes:

- Add onboarding-session-scoped runtime config read/write endpoints.
- Add description submission/update endpoint with 50-character minimum validation.
- Add activation summary endpoint.
- Add activation command endpoint.
- Response and request serializers must be the source of OpenAPI truth.
- Activation must be a command endpoint, not a generic status patch.

Migration risk:

- None expected in this sub-phase if model foundation is complete.

Tests required:

- `401` for unauthenticated access.
- `403` for authenticated users without onboarding authority.
- `404` for sessions outside the actor's onboarding scope.
- Owner/Director can read and update onboarding runtime config through backend services.
- Owner/Director can activate only when activation minimum passes.
- Manager/Staff cannot activate.
- Tenant filtering happens before serialization.
- Description shorter than 50 characters is rejected.
- Activation summary reflects backend readiness and blockers.
- OpenAPI includes the implemented endpoints.

Exact commands to run:

```bash
cd apps/api && uv run pytest houston/establishments/tests/
make schema
make migrations-check
make check
make lint
```

Explicit out of scope:

- Frontend implementation.
- Manual edits to `apps/api/schema.yml`.
- Real AI onboarding calls.
- WebSocket or realtime behavior.
- Archived `/api/v1/onboarding/:id/...` paths unless explicitly selected by the API
  implementation.

Definition of Done:

- Onboarding/runtime endpoints exist in backend code and generated OpenAPI.
- Endpoints use backend services/selectors instead of embedding business workflows in
  serializers or views.
- Endpoint tests cover permissions, tenant isolation, response shape, description
  validation, activation summary, and activation.

### 5. OnboardingProposal foundation / manual-template proposal apply boundary

Objective:

- Prepare the AI Onboarding boundary without integrating a real AI provider yet.
- Add an onboarding proposal foundation that supports manual/template proposals using
  the same apply path future AI proposals will use.
- Ensure proposal apply is human-validated and backend-validated.

Recommended model:

- `OnboardingProposal`

Recommended fields:

- `onboarding_session`
- `establishment`
- `source`
- `status`
- `payload`
- `created_by`
- `validated_by`
- `validated_at`
- `applied_at`

Recommended sources:

- `manual`
- `template`
- `ai_proposed`

Recommended statuses:

- `draft`
- `ready`
- `partially_validated`
- `validated`
- `applied`
- `rejected`
- `failed`

Recommended service:

- `apply_onboarding_proposal(proposal, actor)`

Likely files touched:

- `apps/api/houston/establishments/models.py`
- `apps/api/houston/establishments/services.py`
- `apps/api/houston/establishments/selectors.py`
- `apps/api/houston/establishments/api/serializers.py` if proposal APIs are added
- `apps/api/houston/establishments/api/views.py` if proposal APIs are added
- `apps/api/houston/establishments/api/urls.py` if proposal APIs are added
- `apps/api/houston/establishments/tests/`
- `apps/api/schema.yml` generated by the schema command if proposal APIs are added

API changes:

- Proposal endpoints are optional until explicitly implemented.
- If implemented, every proposal endpoint must be present in OpenAPI and consumed by
  generated frontend types.

Migration risk:

- Likely, if proposal persistence is added.
- Avoid storing raw prompts or raw AI content in standard logs or unnecessary fields.

Proposal validation must cover:

- allowed module/domain/unit catalogs
- modules max 10
- domains max 15
- units max 15
- vocabulary max 30
- runtime_tags max 30
- routing_hints max 30
- unknown values rejected or safely ignored
- no role assignment
- no membership assignment
- no billing changes
- no checklist template generation
- no signal examples
- no direct activation
- human validation before apply
- backend apply boundary shared by manual/template/future AI proposals

Tests required:

- Proposal payloads are not active runtime state until applied.
- Human validation is required before apply.
- Backend validates every proposed runtime object before persistence.
- Unknown or invalid proposal values are rejected or safely ignored according to the
  implemented serializer/service contract.
- Proposals cannot assign roles.
- Proposals cannot assign memberships.
- Proposals cannot change billing.
- Proposals cannot generate checklist templates.
- Proposals cannot generate signal examples.
- Proposals cannot activate an establishment directly.
- `manual` and `template` sources can be represented without a real provider.
- `ai_proposed` can be represented as a future source without calling a real provider.

Exact commands to run:

```bash
cd apps/api && uv run pytest houston/establishments/tests/
make schema
make migrations-check
make check
make lint
```

Explicit out of scope:

- OpenAI or external provider integration.
- Provider prompt contract implementation.
- Strict provider JSON schema implementation.
- Provider retry policy.
- Provider timeout policy.
- `AIUsageLog`.
- AI events.
- Post-activation AI rerun implementation.
- Claiming AI onboarding is implemented.

Definition of Done:

- `OnboardingProposal` exists and can support manual/template proposals using the same
  apply path future AI proposals will use.
- Proposal foundation is tested.
- Proposal apply flow uses backend services and activation rules.
- Proposals remain inactive until human validation and backend apply.
- No external AI provider is called.
- No real AI behavior is claimed.
- Full Phase 2 completion requires this proposal foundation. If this foundation is
  deferred, the milestone must be called Phase 2A complete, not full Phase 2 complete.

### 6. AI Onboarding provider integration

Objective:

- Integrate real AI Onboarding as a backend-only provider flow that produces
  `OnboardingProposal` records, without directly mutating runtime configuration.

Likely files touched:

- `apps/api/houston/establishments/services.py`
- `apps/api/houston/establishments/selectors.py`
- possibly `apps/api/houston/establishments/ai_onboarding.py` or equivalent module if
  repo conventions allow
- `apps/api/houston/establishments/tests/`
- provider config/settings only if required by current repo conventions
- AI usage logging module only if implemented in this sub-phase
- no frontend unless explicitly part of a later sub-phase

Required backend services to plan:

- `build_ai_onboarding_input(session)`
- `run_ai_onboarding_interpretation(session, actor)`
- `validate_ai_onboarding_output(raw_output)`
- `store_ai_onboarding_proposal(session, sanitized_output, actor)`
- `fallback_to_template_proposal(session, actor)`

Names may differ if repo conventions require it.

Input contract:

AI Onboarding input must include only:

- `organization_name`
- `establishment_name`
- `establishment_activity_description`
- `allowed_module_catalog`
- `allowed_domain_catalog`
- `allowed_unit_catalog`
- `locale`
- `prompt_version`

AI Onboarding input must exclude:

- nominative user data
- emails
- phone numbers
- assignments
- roles nominative data
- exact address/location
- billing
- subscription
- observations
- signals
- actions
- comments

Output contract:

AI output must produce proposal payload sections:

- `operational_modules`
- `operational_domains`
- `operational_units`
- `runtime_vocabulary`
- `runtime_tags`
- `routing_hints`

Required validation:

- parseable JSON / structured output
- `schema_version`
- allowed outcome
- section separation
- catalog validation
- caps validation:
  - modules max 10
  - domains max 15
  - units max 15
  - vocabulary max 30
  - runtime_tags max 30
  - routing_hints max 30
- at least 3 valid domains for a generated AI proposal
- unknown modules/domains/units rejected or safely ignored
- no role assignment
- no membership assignment
- no billing changes
- no checklist generation
- no signal examples
- no direct activation

Provider constraints:

- Use structured output / JSON schema if the chosen provider supports it.
- Use `prompt_version`.
- Use `schema_version`.
- Use timeout policy.
- Use retry policy.
- Use safe technical errors.
- Do not log full raw prompts.
- Do not store unnecessary raw AI content outside the approved proposal/usage retention
  strategy.
- No user-facing claim that AI succeeded unless a proposal was validated and stored.

`AIUsageLog`:

If AI provider integration is implemented in Phase 2, `AIUsageLog` or equivalent usage
tracking is required.

It must track at minimum:

- establishment
- `ai_domain = onboarding`
- provider
- model
- prompt_version
- status
- latency_ms
- input_tokens
- output_tokens
- cost estimate if available
- error_code
- correlation_id
- created_at

If `AIUsageLog` is deferred, then the AI provider integration sub-phase is not complete.

Tests required:

- builds input without nominative user data
- rejects too-short description before provider call
- provider output is stored as `OnboardingProposal`, not active runtime
- invalid JSON / invalid structured output fails safely
- unknown catalog values rejected or ignored safely
- caps enforced
- fewer than 3 valid domains fails or falls back to template
- provider failure uses retry/fallback behavior
- no direct runtime mutation from AI output
- no roles/memberships/billing/checklists/signal examples accepted
- usage log created for provider calls
- no full raw prompt logged

Exact commands to run:

```bash
cd apps/api && uv run pytest houston/establishments/tests/
make schema
make migrations-check
make check
make lint
```

Explicit out of scope:

- Observation Pipeline AI
- Signal candidate generation
- Action suggestions
- automatic runtime activation
- automatic user/membership assignment
- frontend AI UX unless later sub-phase explicitly implements it

Definition of Done:

- AI Onboarding provider can generate a validated `OnboardingProposal`.
- AI output never mutates runtime directly.
- Backend validation protects catalogs, caps, and excluded sections.
- `AIUsageLog` or equivalent exists.
- Fallback template path exists.
- Tests pass.
- Observation Pipeline AI remains untouched.

### 7. Frontend generated types + onboarding/runtime API hooks

Objective:

- Regenerate frontend OpenAPI types after onboarding/runtime and proposal API endpoints
  exist.
- Add typed API wrappers and TanStack Query hooks for onboarding/runtime server state.

Must use:

- generated OpenAPI types
- TanStack Query for server state
- no manual generated type edits
- no Zustand for onboarding/runtime server state

Likely files touched:

- `apps/web/src/api/generated/types.ts`
- onboarding/runtime feature API and hooks under `apps/web/src/features/`
- existing app shell integration only where needed

API changes:

- None. This sub-phase consumes the OpenAPI contract generated from the backend.

Migration risk:

- None.

Tests required:

- Typecheck validates generated type usage.
- Build validates integration.
- Hook behavior keeps server state in TanStack Query, not Zustand.

Exact commands to run:

```bash
make web-api-generate
make web-typecheck
make web-build
```

Explicit out of scope:

- Manual edits to generated frontend types.
- Direct `fetch` calls in feature components.
- Storing onboarding/runtime server state in Zustand.
- Frontend-owned activation rules.

Definition of Done:

- Generated frontend types include onboarding/runtime endpoints.
- Runtime API calls flow through generated client usage.
- Onboarding/runtime server state is handled with TanStack Query.

### 8. Mobile-first onboarding UI minimal

Objective:

- Add a minimal mobile-first UI for manual onboarding, runtime setup, section
  validation, activation summary, and activation readiness.
- Reflect backend state and backend validation errors without making React the authority.
- Do not claim AI-assisted onboarding until the backend AI Onboarding provider can
  validate and store an `OnboardingProposal`.

Must include:

- description form with 50-character minimum feedback
- manual setup path
- template fallback path if available
- section-by-section validation UX
- accept-all by section
- skippable vocabulary/tags/routing hints
- modules/domains required
- activation summary before activation
- backend validation errors surfaced clearly
- no React-owned permission or activation authority

Likely files touched:

- onboarding/runtime feature components under `apps/web/src/features/`
- existing app shell or routing files only where required
- reusable UI/domain components only if reuse is clear

API changes:

- None.

Migration risk:

- None.

Tests required:

- Frontend typecheck and build.
- If frontend test tooling is added or already available at implementation time, cover
  loading, error, empty, editing, save, section validation, activation summary, and
  activation-blocked states.

Exact commands to run:

```bash
make web-typecheck
make web-build
```

Explicit out of scope:

- React-derived real permissions.
- Client-only activation minimum enforcement as authority.
- AI proposal UX that implies real AI has run when no validated proposal exists.
- Desktop-only dense admin UI.

Definition of Done:

- Owner/Director can use a mobile-first UI to configure onboarding/runtime setup.
- UI clearly handles loading, error, empty, and success states.
- UI supports section validation and activation summary.
- Backend validation errors are surfaced plainly.
- Frontend does not claim activation until backend confirms it.

## Assumptions and defaults

- `OnboardingSession` is required for full Phase 2 completion.
- `OnboardingProposal` is required for full Phase 2 completion.
- Real AI Onboarding provider integration is required for full Phase 2 completion,
  after the `OnboardingProposal` foundation exists.
- Real AI provider integration is out of scope for Sub-phase 3 and earlier.
- AI Observation Pipeline is out of scope for Phase 2.
- Runtime config is establishment-scoped.
- Runtime tags and routing hints do not affect RBAC.
- Backend is the source of truth for activation.
- Frontend only reflects backend state and validation errors.
- Manual runtime setup must work before AI assistance.
- Default templates are a supported fallback concept, not a required external dependency.
- OpenAPI is mandatory for every onboarding/runtime API endpoint.
- Frontend must use generated OpenAPI types and TanStack Query for onboarding/runtime
  server state.

## Blocking questions

There is no blocking question if the defaults above are accepted.

If a future implementation task finds a direct contradiction between current code and
this plan, stop and report:

- exact file
- exact code/doc conflict
- recommended resolution
- why proceeding would be risky

## Global Phase Definition of Done

Full Phase 2 is done only when:

- `OnboardingSession` foundation exists
- `OnboardingProposal` foundation exists
- runtime data model exists
- draft onboarding access is backend-owned and tested
- owner/director can configure runtime context
- manager/staff cannot activate onboarding
- activation minimum is enforced server-side
- activation summary exists
- OpenAPI contains onboarding/runtime endpoints
- AI Onboarding provider integration exists and stores validated `OnboardingProposal`
  records
- `AIUsageLog` or equivalent usage tracking exists for AI Onboarding calls
- frontend generated types are updated
- mobile-first onboarding UI exists
- frontend uses TanStack Query for onboarding/runtime server state
- Observation Pipeline AI remains separate and untouched
- backend and frontend checks pass

If `OnboardingSession` or `OnboardingProposal` is deferred, the milestone is only
Phase 2A complete, not full Phase 2 complete.
