# Runtime Config / Onboarding Domain

Status: authoritative
Last reviewed: 2026-09-21
Implementation status: live — Platform draft/complete (`/api/v1/platform/onboardings/`)

Owns the live workflow that initializes establishment runtime structure (BusinessUnit → ActivitySubject) and the activation gate. Identity owns `User` / `Organization` / `Establishment` / membership lifecycle. RBAC owns who may mutate runtime **after** activation. HTTP: [`apps/api/schema.yml`](../../../apps/api/schema.yml). Taxonomy: [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md).

## Current entry

Onboarding runs only on **Spore Platform**, desktop Web (`/platform`), by an `IsActivePlatformOperator`. The operator runs the wizard. Owner/Director accept invitation and wait (`/pending-onboarding`); they never open the wizard. `/onboarding` is a redirect, not a wizard.

Platform HTTP stays under `/api/v1/platform/*`. Onboarding writes go through authz-free cores called by Platform wrappers. Tenant permissions must not learn about Platform operators.

## Workflow

- Persist incomplete wizard state in `OnboardingDraft`.
- Materialize + invite + activate only in Platform `POST …/complete/` (`complete_onboarding_session_core`): single transaction; validates final draft; materializes BU/AS; maps `client_key → BusinessUnit.id`; creates director + optional manager/staff invites/scopes; checks shared readiness; activates establishment; deletes draft. Idempotent when already activated. Refuses if any BusinessUnit already exists.
- Display `functional_status` (first match wins): `activated`, `error`, `ready_to_complete`, `waiting_acceptance`, `in_progress`. List filters do not include `functional_status`.
- `Organization.has_been_operational` is set at activation only.

## Activation minimum

Backend `compute_activation_readiness` / `_activation_blockers` (not a UI checklist):

- organization `active`; establishment still `draft`; session not terminal
- required activity description, validated, length 10–5000 (`missing_or_invalid_activity_description`)
- at least one active BusinessUnit
- every active BusinessUnit has at least one active ActivitySubject
- at least one **active** Owner or Director (`missing_active_owner_or_director`)
- at least one **active or invited** non-owner Director (`missing_active_or_invited_director`); deactivated Directors do not satisfy the gate
- during draft onboarding, at most one invited/active non-owner Director per establishment (`DirectorInvitationAlreadyExistsError`)

Director invitation during draft: Platform director-invitation path (or from draft complete). Accept remains `POST /api/v1/invitations/accept/`. After the establishment is **active**, additional directors may be invited via establishment membership invitations (onboarding single-director gate does not apply).

Post-activation create uses `create_runtime_business_unit` (core + seed all active catalog subjects). Reactivation is `POST …/business-units/{id}/reactivate/` (`reactivate_business_unit` — no seed, no scope recreation).

## Out of scope

Full org-chart, billing, exhaustive rooms, AI-assisted onboarding (removed), native mobile wizard, director-led wizard, Platform operator as a tenant permission.

## Frontend

Wizard only under Platform on desktop Web (`isDesktopWeb`). UI must not treat activation as complete until the backend confirms. TanStack Query owns server state. Generated clients only for OpenAPI routes.

## Agent notes

- Recoup activation with `complete_onboarding_session_core`, `compute_activation_readiness`, and their tests — not with historical HTTP.
- Do not add Platform checks inside tenant membership permissions.
- Do not add rooms or checklist templates to activation minimum.
