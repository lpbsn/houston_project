# Runtime Config / Onboarding Domain

Status: authoritative
Last reviewed: 2026-09-19
Implementation status: **live** — Platform draft/complete (`/api/v1/platform/onboardings/`). Tenant register / `POST /api/v1/establishments/` / tenant `onboarding-sessions` writes are removed. AI onboarding is permanently removed (Lot 6).

**Spore Platform V1 is implemented.** Functional target: [`edb_plateforme_interne_spore_v1-3.md`](../../cadrage/edb_plateforme_interne_spore_v1-3.md). Do not treat removed owner-led HTTP as current product.

## 1. Purpose

This domain initializes and later evolves the establishment-scoped runtime structure Houston uses for operational workflows.

Public onboarding/runtime API **as implemented today**: [`apps/api/schema.yml`](../../../apps/api/schema.yml) (Platform paths under `/api/v1/platform/onboardings/`; catalog suggest remains tenant-authenticated). Runtime onboarding uses BusinessUnit / ActivitySubject draft materialization on complete.

**Current entry (live):** only Spore Platform on desktop Web (`/platform`). Operator runs the entire wizard. Owner/Director only accept invitation and wait; they never open the wizard. Activation remains blocked until at least one Owner or Director membership is `ACTIVE` (`missing_active_owner_or_director`). Functional display states, first match wins: `activated`, `error`, `ready_to_complete`, `waiting_acceptance`, `in_progress`. List filters do not include `functional_status` (display field only). Platform HTTP authz is `IsActivePlatformOperator`, not tenant `HasActiveMembership`. Onboarding writes go through authz-free cores called by Platform wrappers. `Organization.has_been_operational` is set at activation only (default `False`, no historical backfill).

Domain boundaries:
- Identity / Membership owns `User`, `Organization`, `Establishment`, and `EstablishmentMembership` lifecycle.
- RBAC / Permissions owns who may configure, validate, activate, or later modify runtime context.
- Runtime Config / Onboarding owns the product workflow and invariants for creating, validating, activating, and evolving initial runtime context.

## Lot sequencing

| Lot | Scope |
|-----|--------|
| **Lot 1** | `OnboardingDraft`, Platform `GET/PUT …/draft/`, `POST …/complete/` |
| **Lot 2** | Frontend wizard on Platform draft/complete only |
| **Lot 3** | Tenant proposal HTTP / apply wrappers removed; `OnboardingProposal` dropped by a later forward migration (`establishments.0036`) after historical `0004`/`0024` still run on empty databases. |

Live path: persist incomplete wizard state in `OnboardingDraft`; materialize + invite + activate only in Platform `POST …/complete/`. `complete` refuses if any `BusinessUnit` already exists so a session cannot double-materialize.

## 2. MVP Scope

- Initialize the initial `Organization` and `Establishment` context required before operational use, while their core lifecycle remains owned by Identity / Membership.
- Capture a **required** free-text `EstablishmentActivityDescription` (10–5000 chars) as part of activation readiness.
- Define the initial establishment runtime structure using **BusinessUnit → ActivitySubject**.
- Persist incomplete wizard state in `OnboardingDraft`; materialize + invite + activate only in Platform `POST …/complete/`.
- Require human validation before backend activation of runtime context.
- Allow high-level post-activation runtime edits, subject to RBAC and human validation.

**Taxonomy authority:** BusinessUnit / ActivitySubject taxonomy is defined by [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md). Legacy catalogue v1 references are obsolete.

## 3. Out of Scope

- Full org-chart creation during activation.
- Billing, subscription management, or client account administration.
- Exhaustive room or location inventory during onboarding.
- Checklist template setup as part of activation minimum.
- AI-assisted onboarding (removed permanently from Houston scope).
- Non-human-driven activation, role assignment, or permission decisions.
- Advanced analytics or large template/catalog marketplace behavior.
- Detailed multi-establishment onboarding UX or native mobile onboarding flows.
- Full vocabulary, tagging, or routing administration UI beyond MVP runtime setup needs.

## 4. Core Invariants

- Establishment runtime config must be human-validated before activation.
- Platform operators persist draft structure; backend validates the draft on complete and activates when ready.
- Backend activates only validated runtime state.
- Runtime config is establishment-scoped and must not leak across establishments.
- Business units are required for activation minimum.
- **Activity subjects** are required at activation minimum: at least one active subject linked to active business units materialized from the draft.
- Activity description is **required** at activation (length 10–5000); `compute_activation_readiness` includes blocker `missing_or_invalid_activity_description` for `complete`.
- Legacy runtime vocabulary, runtime tags, and routing hints were removed from implementation (migration `0016_drop_legacy_taxonomy`); drafts are BusinessUnit / ActivitySubject only.
- **`complete_onboarding_session_core`**: single transaction; validates final draft; materializes BU/AS; maps `client_key → BusinessUnit.id`; creates director + optional manager/staff invites/scopes; checks shared readiness; activates establishment; deletes draft. Idempotent when already activated. Refuses if any BusinessUnit exists.
- Post-activation destructive runtime changes must be explicit and authorized.
- Post-activation create uses `create_runtime_business_unit` (core + seed all active catalog subjects). Reactivation is a separate `POST …/business-units/{id}/reactivate/` path (`reactivate_business_unit` — no seed, no scope recreation). See [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md).

Activation minimum:
- organization created
- establishment created
- at least 1 business unit validated
- at least 1 activity subject validated from the completed draft
- at least 1 active Owner or Director
- exactly one active or invited Director membership on a user distinct from the initial Owner for **draft activation** (at most one invited/active non-owner Director per establishment during onboarding; deactivated Directors do not satisfy the gate)
- Director invitation during draft onboarding via `POST /api/v1/platform/onboardings/{session_id}/director-invitations/` (or from draft complete); schedules a transactional invitation email when enabled
- Director accepts via `POST /api/v1/invitations/accept/` (bearer in JSON body; sets password, activates user/membership, creates auth session)
- After the establishment is **active**, additional directors may be invited via `POST /api/v1/establishments/{establishment_id}/membership-invitations/` with `role=director` (multi-director allowed; onboarding single-director gate does not apply)

Proposal parent/child coherence follows BU/AS hierarchy rules in [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md).

## 5. Main Objects

- `Organization`
  - Parent business container created before an establishment.
  - Identity / Membership owns its lifecycle.

- `Establishment`
  - Operational tenant whose runtime context is initialized by onboarding.
  - Belongs to exactly one organization.

- `EstablishmentActivityDescription`
  - Optional free-text onboarding input describing the establishment's operational reality.
  - Useful context for manual setup and downstream AI routing when submitted; not required to activate.

- `BusinessUnit`
  - High-level operational scope for runtime structure and RBAC assignment.
  - Parent taxonomy node for activity subjects.

- `ActivitySubject`
  - Finest operational classification under a business unit.
  - Required at activation minimum.

- `OperationalUnit`
  - Physical or contextual **location** used to localize activity.
  - **Orthogonal** to BusinessUnit / ActivitySubject classification; optional on Signals.
  - **Not** used for feed subscriptions in MVP.

- `RuntimeVocabulary`, `RuntimeTag`, `RoutingHint` (removed)
  - Legacy product concepts dropped in migration `0016_drop_legacy_taxonomy`.
  - Not part of draft onboarding or activation minimum.

- `OnboardingDraft`
  - Incomplete wizard state persisted for a Platform onboarding session.
  - Materialized into BusinessUnit / ActivitySubject rows only on Platform `POST …/complete/`.

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
  - Includes live Platform fields (`current_step`, `source_mode`, `last_error_code`, `session_status`) still exposed by the HTTP contract.
- Django still creates `OnboardingProposal` in historical migrations (`0004`, processed by `0024`) then drops it in `establishments.0036`, the same pattern as other retired tables (taxonomy v1). It is not part of the live schema.

- Runtime context sections
  - Validation is expected to happen by section where useful.
  - Exact persisted validation-state models are not validated yet.

## 7. Permissions

**Current implementation:**

- **Platform operator** is the only actor who starts, edits, resumes, or completes the wizard. Completing still requires the shared readiness gate including `missing_active_owner_or_director`.
- **Director** is required for activation minimum (non-owner director membership) but **cannot complete the draft wizard** — invitation accept only.
- Tenant permissions (`resolve_manageable_organization`, `invite_membership_for_establishment` actor membership) **must not** learn about Platform operators. Platform authz stays on `/api/v1/platform/*`.
- Owner/Director invitations during onboarding are onboarding steps, not Platform user admin.
- Managers may modify some runtime context post-activation only when RBAC allows it.
- Staff does not configure, validate, or activate onboarding/runtime setup.
- Backend permission checks are mandatory for validation, activation, and post-activation mutation.
- Informal Houston/FloorPower operational support is **not** a public product permission contract.

Director-led wizard (director fills draft setup) remains **out of product** unless separately recadred.

## 8. Events

No onboarding domain event contract is implemented in current code or `apps/api/schema.yml`.

Future runtime/onboarding events (candidate only — not implemented; validate in a separate product ticket before documenting as active):

- onboarding lifecycle notifications
- BusinessUnit or ActivitySubject activation events

Do not use legacy v1 taxonomy event names (`OperationalModuleActivated`, etc.) in new work.

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented runtime/onboarding endpoints (under `/api/v1/platform/onboardings/`):

- `GET/POST /` — list/start onboarding
- `GET /{session_id}/` — session summary including derived `functional_status`
- `GET/PUT /{session_id}/draft/` — draft payload
- `POST /{session_id}/complete/` — materialize + invite from draft + activate when ready
- `POST /{session_id}/owner-invitations/` — invite organizational Owner
- `POST /{session_id}/director-invitations/` — invite Director (also invited from draft complete when needed)
- `GET /{session_id}/summary/` — activation summary
- `GET /api/v1/catalog/business-units/suggest/` and `…/activity-subjects/suggest/` — catalog autocomplete

Tenant `onboarding-sessions` writes, mark-ready, activate, and proposal apply HTTP are **removed**.

Post-activation establishment runtime mutations (active establishments) under `/api/v1/establishments/{establishment_id}/` — BusinessUnit create/PATCH/reactivate, ActivitySubject create/reactivate, `runtime-config/`, catalogue suggest. Public shapes omit `routing_key` (Lot 5). See `schema.yml` and [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md).

## 10. Frontend Expectations

**Current:** wizard only under Platform on **desktop Web** (`/platform`, `isDesktopWeb`). `/onboarding` redirects to login/landing. Invited Owner/Director use invitation accept then `/pending-onboarding`. List/detail diagnostics show the functional states in §1 (not a list filter).

- Onboarding should be guided and section-based rather than a raw configuration dump.
- UI must not treat activation as complete until backend confirmation is returned.
- TanStack Query owns runtime/onboarding server state.
- Frontend must use generated API clients only for endpoints confirmed in OpenAPI.
## 11. AI Agent Notes

- Inspect current code before assuming runtime objects beyond established BU/AS runtime objects already exist.
- Inspect `apps/api/schema.yml` before claiming any runtime/onboarding endpoint is implemented.
- Inspect `identity_membership_domain.md` before changing `Organization`, `Establishment`, or membership assumptions.
- Inspect `rbac_permissions_domain.md` before changing who can validate, activate, rerun, or edit runtime setup.
- Do not add Platform checks inside tenant membership permissions.
- Inspect `apps/api/schema.yml` for live Platform onboarding APIs.
- Inspect [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md) before changing hierarchy or keys.
- Do not implement Signal, Feed, or Observation pipeline code in onboarding phases.
- Do not let non-authorized clients activate runtime elements directly.
- Do not use runtime tags as RBAC inputs.
- Do not turn catalog examples into database models or seed data unless the current phase explicitly requires it.
- Do not add exhaustive rooms or checklist templates to activation minimum.
- When adding runtime/onboarding APIs later, update backend authorization, OpenAPI, generated clients, tests, and this document together.
