# Runtime Config / Onboarding Domain

Status: authoritative
Last reviewed: 2026-05-30
Implementation status: **implemented** (onboarding/runtime API — Phase 2 + taxonomy subjects extension)

## 1. Purpose

This domain initializes and later evolves the establishment-scoped runtime structure Houston uses for operational workflows.

Public onboarding/runtime API is **implemented**. Authoritative contract: [`apps/api/schema.yml`](../../../apps/api/schema.yml) (paths under `/api/v1/onboarding-sessions/`). Current code includes catalogue hierarchy (modules, domains, subjects), proposals v2, AI modules-only expansion, item-level mutations, runtime config, activation readiness, and activation.

Domain boundaries:
- Identity / Membership owns `User`, `Organization`, `Establishment`, and `EstablishmentMembership` lifecycle.
- RBAC / Permissions owns who may configure, validate, activate, or later modify runtime context.
- AI owns provider behavior, schemas, and detailed proposal contracts.
- Runtime Config / Onboarding owns the product workflow and invariants for creating, validating, activating, and evolving initial runtime context.

## 2. MVP Scope

- Initialize the initial `Organization` and `Establishment` context required before operational use, while their core lifecycle remains owned by Identity / Membership.
- Capture a required free-text `EstablishmentActivityDescription` rich enough to guide runtime setup.
- Define the initial establishment runtime structure using the **Module → Domain → Subject** hierarchy, plus optional **Units** (orthogonal location), runtime vocabulary, runtime tags, and routing hints.
- Support AI-generated **modules-only** proposals with **backend expansion** of domains and subjects from the catalogue.
- Use proposal schema **`onboarding_proposal_v2`** with explicit `operational_subjects` section.
- Support AI-generated proposals with manual fallback if AI is unavailable or fails.
- Require human validation before backend activation of runtime context.
- Allow high-level post-activation runtime edits and AI reruns, subject to RBAC and human validation.

**Catalogue authority:** `OnboardingCatalogModule` / `OnboardingCatalogDomain` / `OnboardingCatalogSubject` in PostgreSQL (seeded by migration `0007`; 6 modules, 31 domains, 154 subjects). Legacy flat domain keys (`maintenance`, `housekeeping`, …) and removed modules (`bar`, `rooftop`, `seminar_rooms`) are **obsolete** for new proposals.

**AI onboarding contract:** provider returns **`operational_modules` only**; backend expands domains and subjects via catalogue FK tree (`ai_onboarding_v3`). See [`operational_taxonomy_domain.md`](operational_taxonomy_domain.md).

## 3. Out of Scope

- Full org-chart creation during activation.
- Billing, subscription management, or client account administration.
- Exhaustive room or location inventory during onboarding.
- Checklist template setup as part of activation minimum.
- AI-driven activation, role assignment, or permission decisions.
- Advanced analytics or large template/catalog marketplace behavior.
- Detailed multi-establishment onboarding UX or native mobile onboarding flows.
- Full vocabulary, tagging, or routing administration UI beyond MVP runtime setup needs.

## 4. Core Invariants

- Establishment runtime config must be human-validated before activation.
- AI proposes only; humans validate; backend activates.
- Backend activates only validated runtime state.
- Runtime config is establishment-scoped and must not leak across establishments.
- Operational modules and operational domains are required for activation minimum.
- **Operational subjects** are required at activation minimum: ≥1 active subject per active domain that remains after apply (see [`phase_a_closure.md`](../phase_a_closure.md)).
- Runtime vocabulary, runtime tags, and routing hints may be skipped if activation minimum is still met.
- Skipping them must not block establishment activation if the activation minimum is met.
- Runtime tags never grant permissions.
- Routing hints never grant permissions.
- Frontend cannot activate or mutate authoritative runtime state by itself.
- Post-activation destructive runtime changes must be explicit, authorized, and never auto-applied from AI proposals.

Activation minimum:
- organization created
- establishment created
- establishment activity description validated
- at least 1 operational module validated
- at least 3 operational domains validated
- at least 1 operational subject validated per active domain in applied proposal
- at least 1 active Owner or Director
- exactly one active or invited Director membership on a user distinct from the initial Owner (at most one invited/active Director per establishment; deactivated Directors do not satisfy the gate)
- Director invitation during draft onboarding via `POST /api/v1/onboarding-sessions/{session_id}/director-invitations/` (returns one-time `invitation_token` and `invitation_accept_path` for manual sharing)
- Director accepts via `POST /api/v1/invitations/{token}/accept/` (sets password, activates user/membership, creates auth session)

Proposal parent/child coherence (§3.1 in [`operational_taxonomy_domain.md`](operational_taxonomy_domain.md)) applies during manual item edit and validation.

## 5. Main Objects

- `Organization`
  - Parent business container created before an establishment.
  - Identity / Membership owns its lifecycle.

- `Establishment`
  - Operational tenant whose runtime context is initialized by onboarding.
  - Belongs to exactly one organization.

- `EstablishmentActivityDescription`
  - Required free-text onboarding input describing the establishment's operational reality.
  - Used to guide manual setup or AI proposals.

- `OperationalModule`
  - High-level operational activity (catalogue module).
  - Parent of operational domains at runtime.

- `OperationalDomain`
  - Stable operational scope under a module (hierarchical key, e.g. `hotel__hebergement`).
  - Used for manager/staff RBAC (`MembershipScope`) and Signal/Action routing. `MembershipFeedSubscription` (future) is separate from RBAC.

- `OperationalSubject`
  - Finest operational problem type under a domain (hierarchical key, e.g. `hotel__hebergement__proprete_des_chambres`).
  - Required in onboarding proposal v2 and activation minimum.

- `OperationalUnit`
  - Physical or contextual **location** used to localize activity.
  - **Orthogonal** to Module/Domain/Subject; optional on Signals.
  - **Not** used for feed subscriptions in MVP.

- `RuntimeVocabulary`
  - Local terms and aliases that improve interpretation and routing.
  - Optional at activation minimum.

- `RuntimeTag`
  - Flexible contextual labels that enrich runtime interpretation and downstream workflows.
  - Must not be used as a permission mechanism.

- `RoutingHint`
  - Optional guidance that helps later proposal or routing logic interpret recurring patterns.
  - Must not be treated as access control.

- `OnboardingProposal`
  - Candidate runtime structure proposed manually or by AI before activation.
  - Target payload: `schema_version: onboarding_proposal_v2` with sections `operational_modules`, `operational_domains`, `operational_subjects`, optional units/vocabulary/tags/routing_hints.
  - AI path: modules-only from provider → backend expansion + validation.

- `OnboardingProposalItemMutation` (implemented API)
  - `POST /api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/items/` — add/remove module, domain, or subject keys with automatic parent/child coherence.

- `OnboardingValidation`
  - Human approval step for sections of proposed runtime context before backend activation.
  - Product concept only; not validated as an implemented public model.

- `EstablishmentActivation`
  - Backend transition that makes the establishment usable with validated minimum runtime structure.
  - Product concept only beyond the validated `Establishment` status lifecycle.

## 6. Lifecycle / Statuses

- `Establishment`
  - Current code validates `draft`, `active`, and `deactivated`.
  - Onboarding must not treat the establishment as operationally active before backend activation.

- `OnboardingSession` statuses (implemented on `OnboardingSession` model)
  - `started`, `description_submitted`, `configuring_runtime`, `proposal_ready`, `validating_sections`, `ready_for_activation`, `activated`, `failed`, `canceled`
- `OnboardingProposal` statuses (implemented)
  - Includes `draft`, `ready`, `partially_validated`, `validated`, `applied`, `rejected`, `superseded`

- Runtime context sections
  - Validation is expected to happen by section where useful.
  - Exact persisted validation-state models are not validated yet.

## 7. Permissions

- Owner and Director are the product-level actors who validate and activate runtime setup.
- Managers may modify some runtime context post-activation only when RBAC allows it.
- Staff does not configure, validate, or activate onboarding/runtime setup in MVP.
- Backend permission checks are mandatory for validation, activation, rerun, and post-activation mutation.
- Pilot onboarding may be operationally supported by Houston/FloorPower admin plus Owner/Director, but this is not a validated public product permission contract.

## 8. Events

No onboarding event contract is confirmed as implemented in current code or in `apps/api/schema.yml`.

Candidate events only:
- `OrganizationCreated`
- `EstablishmentCreated`
- `OnboardingStarted`
- `EstablishmentDescriptionSubmitted`
- `OnboardingAIInterpretationStarted`
- `OnboardingAIInterpretationSucceeded`
- `OnboardingAIInterpretationFailed`
- `OperationalModulesProposed`
- `OperationalDomainsProposed`
- `OperationalUnitsProposed`
- `RuntimeVocabularyProposed`
- `RuntimeTagsProposed`
- `RoutingHintsProposed`
- `OnboardingProposalValidated`
- `OperationalModuleActivated`
- `OperationalDomainActivated`
- `OperationalUnitActivated`
- `RuntimeVocabularyActivated`
- `EstablishmentActivated`
- `InitialUserInvited candidate, cross-domain with Identity / Membership`
- `MembershipActivated candidate, cross-domain with Identity / Membership`

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented runtime/onboarding endpoints confirmed in `apps/api/schema.yml`:
- None.

Current public schema exposes auth endpoints plus schema/health endpoints, but no public runtime/onboarding API.

Candidate endpoint capabilities only:
- create organization
- create establishment
- submit establishment description
- start AI interpretation
- fetch onboarding proposal
- mutate proposal catalog item (add/remove module, domain, subject)
- validate proposal section
- activate establishment
- update runtime config
- rerun AI proposal
- invite initial director during onboarding (`POST .../director-invitations/`)

## 10. Frontend Expectations

- Onboarding should be guided and section-based rather than a raw configuration dump.
- UI must clearly distinguish AI proposals from validated active runtime state.
- UI should support accept, edit, reject, and **item-level add/remove** for proposal sections when those APIs exist.
- UI must support manual fallback when AI fails or is unavailable.
- UI must not present AI output as already active runtime configuration.
- UI must not treat activation as complete until backend confirmation is returned.
- TanStack Query owns runtime/onboarding server state.
- Frontend must use generated API clients only for endpoints confirmed in OpenAPI.
- Candidate runtime/onboarding endpoints remain future targets only and must not be assumed available.

## 11. AI Agent Notes

- Inspect current code before assuming runtime objects beyond `OperationalDomain` already exist.
- Inspect `apps/api/schema.yml` before claiming any runtime/onboarding endpoint is implemented.
- Inspect `identity_membership_domain.md` before changing `Organization`, `Establishment`, or membership assumptions.
- Inspect `rbac_permissions_domain.md` before changing who can validate, activate, rerun, or edit runtime setup.
- Inspect [`operational_taxonomy_domain.md`](operational_taxonomy_domain.md) before changing hierarchy or keys.
- Inspect the AI onboarding contract (`ai_onboarding_v3`, modules-only) before changing proposal or provider schemas.
- Do not implement Signal, Feed, or Observation pipeline code in onboarding phases.
- Do not let AI activate runtime elements directly.
- Do not let AI assign roles or permissions.
- Do not use runtime tags as RBAC inputs.
- Do not turn catalog examples into database models or seed data unless the current phase explicitly requires it.
- Do not add exhaustive rooms or checklist templates to activation minimum.
- When adding runtime/onboarding APIs later, update backend authorization, OpenAPI, generated clients, tests, and this document together.
