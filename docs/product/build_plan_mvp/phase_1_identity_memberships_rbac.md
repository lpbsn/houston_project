# Phase 1.0 — Identity / Memberships / RBAC

Status: active Phase 1 source of truth  
Last reviewed: 2026-05-28  
Authority order: current code -> tests -> apps/api/schema.yml -> domain docs -> this file

## Phase 1.0 objective

Freeze the Phase 1 contract for:

- authenticated identity
- establishment memberships
- backend RBAC foundations
- tenant-scoped bootstrap context

This phase exists to stabilize the auth, membership, and permission baseline before deeper product features are added.

## Already implemented

- Auth model is API-first token auth:
  - opaque bearer access token
  - rotating refresh token in HttpOnly cookie
  - backend `UserSession`, `AccessToken`, and `SessionRefreshToken`
- Public auth API currently implemented in `apps/api/schema.yml`:
  - `GET /api/v1/auth/csrf/`
  - `POST /api/v1/auth/login/`
  - `POST /api/v1/auth/refresh/`
  - `POST /api/v1/auth/logout/`
  - `GET /api/v1/auth/bootstrap/`
  - `POST /api/v1/auth/switch_establishment/`
- Public membership-management API currently implemented in `apps/api/schema.yml`:
  - `GET /api/v1/establishments/{establishment_id}/memberships/`
  - `GET /api/v1/establishments/{establishment_id}/memberships/{membership_id}/`
  - `PATCH /api/v1/establishments/{establishment_id}/memberships/{membership_id}/`
  - `POST /api/v1/establishments/{establishment_id}/memberships/{membership_id}/deactivate/`
- Public scoped user search API currently implemented in `apps/api/schema.yml`:
  - `GET /api/v1/establishments/{establishment_id}/users/search/?q=`
- `bootstrap` is authenticated-only:
  - unauthenticated => `401`
  - authenticated => `BootstrapResponse`
- Identity and tenancy models already exist:
  - `User`
  - `Organization`
  - `Establishment`
  - `EstablishmentMembership`
  - `OperationalDomain`
  - `MembershipDomain`
- Active bootstrap memberships are already filtered by:
  - active user
  - active membership
  - active establishment
  - active organization
- `active_membership` now resolves from `UserSession.selected_establishment` when valid.
- Login and refresh auto-select the sole active establishment on `UserSession` when exactly one active membership exists.
- Current permission helpers already define the validated MVP role baseline:
  - `owner`
  - `director`
  - `manager`
  - `staff`
- Current public membership-management authority is:
  - `owner` and `director` can manage memberships
  - `manager` and `staff` cannot manage memberships
- Current selected-establishment public API authority is `UserSession.selected_establishment`.
- Reusable API access context and DRF permission classes now exist for bearer-session-backed Phase 1 endpoints.
- Scoped user search is establishment-scoped, active-only, and selector-filtered before serialization.

## Phase 1 implementation notes

### 1A. Auth/session contract hardening

- Keep current auth API as the public contract unless code and schema are intentionally changed together.
- Preserve CSRF enforcement on login, refresh, and logout.
- Preserve generic login failure behavior and no sensitive auth metadata in responses.

### 1B. Membership and bootstrap contract freeze

- Treat bootstrap membership payload as the frontend identity source of truth for Phase 1.
- Keep membership visibility backend-filtered.
- Keep membership-management endpoints documented and synchronized with backend code and OpenAPI.

### 1C. RBAC foundation freeze

- Keep backend permission enforcement as the authority.
- Keep current validated role capabilities from `houston.establishments.permissions` as the minimum Phase 1 baseline.
- Keep operational-domain access membership-scoped.

### 1D. Selected establishment public contract

- `POST /api/v1/auth/switch_establishment/` is implemented.
- The public API authority is `UserSession.selected_establishment`, not Django `request.session`.
- `request.session["current_establishment_id"]` remains legacy/internal compatibility only.

## Explicit out of scope for Phase 1.0 documentation freeze

- Any code behavior change
- Invitations
- Password reset
- Public signup
- `me` or `logout_all` endpoints
- Observation
- Signal
- Action
- Feed
- Realtime
- Notification
- Checklist
- Chat

## Implementation rules

- Current code, tests, and `apps/api/schema.yml` are authoritative.
- Do not recreate any obsolete auth or membership endpoint.
- `bootstrap` is authenticated-only. Do not document an unauthenticated bootstrap payload.
- Do not claim Django `request.session` is the public selected-establishment authority.
- Do not move authorization authority to the frontend.
- Do not treat membership, role, or operational domain data in React as security authority.
- Keep establishment scoping backend-enforced.
- List endpoints must be tenant-filtered at selector/queryset level before serialization. DRF permissions alone are not enough to protect list responses.
- Keep `active_membership` semantics exactly as currently implemented through `UserSession.selected_establishment`.
- If a future API contract changes, update backend code, tests, OpenAPI, generated client, and product docs together.

## Test/check commands

Run from repository root unless stated otherwise.

- `cd apps/api && uv run pytest houston/accounts/tests/test_auth_api.py`
- `cd apps/api && uv run pytest houston/accounts/tests/test_services.py`
- `cd apps/api && uv run pytest houston/establishments/tests/test_access.py`
- `cd apps/api && uv run pytest houston/establishments/tests/test_permissions.py`
- `cd apps/api && uv run python manage.py check`
- `cd apps/api && uv run ruff check .`
- `make schema`

## Codex notes

- Read `docs/architecture/authentication_charter.md` before changing auth behavior.
- Read `docs/product/domains/identity_membership_domain.md` and `docs/product/domains/rbac_permissions_domain.md` before changing Phase 1 scope.
- When docs and code diverge, fix the docs or raise the mismatch before changing behavior.

## Definition of Done

Phase 1.0 is done only when:

- Both docs reflect current code, tests, and schema truth.
- No code or schema files changed.
- Requested wording corrections are present.
- No obsolete Phase 1.0 wording remains.
