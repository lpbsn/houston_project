# Identity / Membership Domain

Status: authoritative
Last reviewed: 2026-05-27
Implementation status: implemented for Phase 1

## 1. Purpose

This domain defines global user identity and how Houston derives establishment access from active establishment memberships.

It covers the MVP relationship between `User`, `Organization`, `Establishment`, and `EstablishmentMembership`. Authentication mechanics stay high-level here; detailed session and token rules belong to `docs/architecture/authentication_charter.md`. Detailed RBAC rules belong to `docs/product/domains/rbac_permissions_domain.md`.
This domain owns global user identity, organization and establishment membership, membership status, and establishment context selection. It does not own detailed RBAC matrices, token or session internals, or domain-specific business permissions.

## 2. MVP Scope

- Global `User` identity.
- `Organization` as the parent business container.
- `Establishment` as the operational tenant context.
- `EstablishmentMembership` as the access link between a user and an establishment.
- Membership-scoped role and membership status.
- Membership-scoped operational RBAC through `MembershipScope` rows (`module`, `domain`, or `subject` taxonomy IDs).
- Backend-enforced establishment access based on active membership, active user, active establishment, and active organization.
- Bootstrap-facing identity and membership context through the current auth API.
- Mono-establishment default UX.
- Multi-establishment selection through backend-owned auth-session state.
- Establishment-scoped membership management for the current active establishment context.
- Establishment-scoped active-user search for the current active establishment context.

## 3. Out of Scope

- SSO.
- MFA, unless current code explicitly proves otherwise.
- Billing ownership details.
- Advanced organization hierarchy.
- Complex multi-establishment workspace UX.
- Fine-grained RBAC matrices.
- Arbitrary admin browsing across tenants.
- Cross-tenant access.
- Invitation flows.
- Password reset flows.
- Public signup.
- Old-stack implementation assumptions or terminology.

## 4. Core Invariants

- A `User` alone never grants establishment access.
- Access requires an active `EstablishmentMembership`.
- Membership access also depends on an active `User`, active `Establishment`, and active `Organization`.
- Backend enforces establishment scoping and all access checks.
- Frontend state cannot grant permissions.
- Role and operational périmètre (`MembershipScope`) are membership-scoped, not global user attributes.
- No product API may expose data outside establishments visible through valid memberships.
- Establishment switching must not bypass backend authorization.
- A selected establishment context must always be backed by a valid active membership.

## 5. Main Objects

- `User`
  - Global identity for authentication.
  - Supports `identity_type` values `email` and `username`.
  - Has validated status values in code and does not carry establishment role or domain authority.
- `Organization`
  - Parent business container.
  - Owns one or more establishments.
- `Establishment`
  - Operational tenant context for Houston workflows.
  - Belongs to one organization.
- `EstablishmentMembership`
  - Joins a user to an establishment.
  - Carries membership role and membership status.
  - Operational périmètre is attached through `MembershipScope` rows (explicit taxonomy UUIDs), not on `User`.

## 6. Lifecycle / Statuses

- `User`: `pending`, `active`, `suspended`, `anonymized`
- `Organization`: `active`, `suspended`, `archived`
- `Establishment`: `draft`, `active`, `deactivated`
- `EstablishmentMembership`: `invited`, `active`, `deactivated`

Validated MVP access implications:

- Access resolution uses only active user + active membership + active establishment + active organization.
- `invited` memberships do not count as active access.
- Deactivated memberships are excluded from access resolution and bootstrap results.
- Current code validates access state, but this document does not define additional lifecycle workflows or transition APIs beyond what is implemented.

## 7. Permissions

- Active members may access establishment context only through backend validation.
- Membership management is restricted to authorized establishment leadership roles. Current backend helpers must be checked before changing this rule.
- Current public membership-management API is restricted to the current active establishment context selected on `UserSession`.
- Membership role and operational domain data inform backend authorization, but detailed action matrices do not belong here.
- Detailed RBAC rules belong to `docs/product/domains/rbac_permissions_domain.md`.

## 8. Events

No identity or membership domain events are validated in current code or in `apps/api/schema.yml`.

Candidate events only:

- `UserCreated` candidate
- `EstablishmentMembershipCreated` candidate
- `EstablishmentMembershipUpdated` candidate
- `EstablishmentMembershipDeactivated` candidate
- `EstablishmentSwitched` candidate

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented endpoints confirmed in `apps/api/schema.yml`:

- `GET /api/v1/auth/csrf/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/bootstrap/`
- `POST /api/v1/auth/switch_establishment/`
- `GET /api/v1/establishments/{establishment_id}/memberships/`
- `GET /api/v1/establishments/{establishment_id}/memberships/{membership_id}/`
- `PATCH /api/v1/establishments/{establishment_id}/memberships/{membership_id}/`
- `POST /api/v1/establishments/{establishment_id}/memberships/{membership_id}/deactivate/`
- `GET /api/v1/establishments/{establishment_id}/users/search/?q=`

Implemented response truths:

- Login and bootstrap responses include `memberships`.
- Login and refresh currently auto-select the sole active establishment on `UserSession` when exactly one active membership exists.
- Current bootstrap behavior: `active_membership` resolves from `UserSession.selected_establishment` when valid.
- If `selected_establishment` is stale, inactive, or outside active memberships, it is cleared safely and `active_membership` becomes `null`.
- Membership-management endpoints are establishment-scoped and require the path `establishment_id` to match the current active auth-session context.
- Membership-management list and detail responses are tenant-filtered before serialization.
- Role updates and operational-domain assignment updates use `PATCH`; deactivation is a separate command endpoint.
- The last active owner cannot be deactivated.
- The last active owner cannot be demoted to another role.
- The last-active-owner invariant is enforced in the service layer.
- If another active owner exists, demotion is allowed.
- Directors cannot patch, deactivate, or reassign owner memberships.
- Directors may manage manager and staff memberships when they hold membership-management authority.
- Owners may manage director, manager, and staff memberships subject to the last-active-owner invariant.
- Any active member may read `GET /api/v1/establishments/{establishment_id}/workspace-summary/` for the current active establishment context.
- Scoped user search is establishment-scoped and requires the path `establishment_id` to match the current active auth-session context.
- Scoped user search returns active users with active memberships in the same active establishment only.
- Scoped user search response fields are limited to `id`, `display_name`, `username`, `email`, `role`, and `membership_id`.
- Establishment invitation acceptance: `POST /api/v1/invitations/{token}/accept/` (password setup, session creation; CSRF required).
- Onboarding Director invite with token: `POST /api/v1/onboarding-sessions/{session_id}/director-invitations/` returns `invitation_token` for manual sharing (no email delivery in MVP).
- Post-onboarding staff/manager invite with token: `POST /api/v1/establishments/{establishment_id}/membership-invitations/` returns `invitation_token` for manual sharing (no email delivery in MVP).

Candidate endpoints only:

- Password reset endpoints
- Current-user endpoints beyond the implemented bootstrap contract

## 10. Frontend Expectations

- Frontend reads auth/bootstrap state from backend APIs.
- TanStack Query owns auth/bootstrap server state.
- Frontend auth and session mechanics follow `docs/architecture/authentication_charter.md`.
- Frontend must not derive authorization from role or operational domain data.
- Mono-establishment users should not see unnecessary establishment switch UI.
- Multi-membership users may require simple selection UI through the validated `switch_establishment` auth endpoint.
- Frontend must handle unauthenticated, inactive user, no active memberships, single active membership, and multiple active memberships with no selected context yet.
- Frontend must not persist selected establishment outside the backend auth session design.

## 11. AI Agent Notes

- Inspect current models before changing this domain or related code.
- Inspect `apps/api/schema.yml` before listing or changing endpoints.
- Do not move role or operational domain scope onto `User`.
- Do not add detailed RBAC matrices here.
- Do not place detailed authorization rules in this document; use `rbac_permissions_domain.md` for permission behavior.
- Do not claim invitations, password reset, membership management, or switch endpoints are implemented without schema proof.
- Do not document Django `request.session["current_establishment_id"]` as public auth-session authority.
- Do not introduce old-stack terminology.
- For auth and session mechanics, read `docs/architecture/authentication_charter.md`.
