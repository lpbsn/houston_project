# Runtime Config / Onboarding Domain

Status: authoritative
Last reviewed: 2026-05-27
Implementation status: partial

## 1. Purpose

This domain initializes and later evolves the establishment-scoped runtime structure Houston uses for operational workflows.

Implementation status is `partial`: current code validates `Organization`, `Establishment`, `EstablishmentMembership`, `OperationalDomain`, membership-domain links, establishment lifecycle status, and runtime-management permission helpers, but no public runtime/onboarding API is confirmed in `apps/api/schema.yml`.

Domain boundaries:
- Identity / Membership owns `User`, `Organization`, `Establishment`, and `EstablishmentMembership` lifecycle.
- RBAC / Permissions owns who may configure, validate, activate, or later modify runtime context.
- AI owns provider behavior, schemas, and detailed proposal contracts.
- Runtime Config / Onboarding owns the product workflow and invariants for creating, validating, activating, and evolving initial runtime context.

## 2. MVP Scope

- Initialize the initial `Organization` and `Establishment` context required before operational use, while their core lifecycle remains owned by Identity / Membership.
- Capture a required free-text `EstablishmentActivityDescription` rich enough to guide runtime setup.
- Define the initial establishment runtime structure: operational modules, operational domains, operational units, and optional runtime vocabulary, runtime tags, and routing hints.
- Support AI-generated proposals for runtime structure, with manual fallback if AI is unavailable or fails.
- Require human validation before backend activation of runtime context.
- Allow high-level post-activation runtime edits and AI reruns, subject to RBAC and human validation.

Validated MVP examples kept for reference:
- Operational modules may include `hotel`, `restaurant`, `bar`, `rooftop`, `seminar_rooms`, and `coworking`.
- Operational domains may include `maintenance`, `housekeeping`, `cleaning`, `security`, `guest_experience`, `kitchen`, `restaurant_room`, `pricing`, `event_management`, and `management`.
- Operational units may include `lobby`, `rooms`, `corridors`, `restaurant`, `kitchen`, `bar`, `rooftop`, `seminar_rooms`, `storage`, `technical_rooms`, and `outdoor_areas`.

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
- at least 1 active Owner or Director
- at least 1 active or invited Manager
- operational domains assigned to initial managers

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
  - High-level operational activity present in the establishment.
  - Validated product concept; no current backend model is confirmed.

- `OperationalDomain`
  - Stable operational responsibility axis used across runtime setup, RBAC, signals, actions, feeds, and notifications.
  - Currently the only runtime structure visibly implemented in backend code.

- `OperationalUnit`
  - Physical or contextual area used to localize runtime activity.
  - Validated product concept; no current backend model is confirmed.

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
  - Candidate runtime structure proposed manually or by AI before activation or post-activation review.
  - Product concept only; not validated as an implemented public model.

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

- Onboarding session or proposal statuses
  - Not validated yet as implemented backend statuses.
  - Candidate progression only: started, description submitted, AI processing, proposal ready, sections validated, activated.

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
- validate proposal section
- activate establishment
- update runtime config
- rerun AI proposal
- invite initial manager or director

## 10. Frontend Expectations

- Onboarding should be guided and section-based rather than a raw configuration dump.
- UI must clearly distinguish AI proposals from validated active runtime state.
- UI should support accept, edit, and reject flows for proposal sections when those APIs exist.
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
- Inspect the AI domain docs before changing proposal contracts, provider assumptions, or validation boundaries.
- Do not let AI activate runtime elements directly.
- Do not let AI assign roles or permissions.
- Do not use runtime tags as RBAC inputs.
- Do not turn catalog examples into database models or seed data unless the current phase explicitly requires it.
- Do not add exhaustive rooms or checklist templates to activation minimum.
- When adding runtime/onboarding APIs later, update backend authorization, OpenAPI, generated clients, tests, and this document together.
