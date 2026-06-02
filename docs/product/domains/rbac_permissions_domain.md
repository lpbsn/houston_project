# RBAC / Permissions Domain

Status: authoritative
Last reviewed: 2026-05-29
Implementation status: implemented for Phase 1

## 1. Purpose

This domain defines what an authenticated user can see and do inside an establishment after identity and membership have already been resolved.

Identity, organization, establishment, membership lifecycle, and membership selection rules belong to [identity_membership_domain.md](/Users/leobsn/Desktop/houston_project/docs/product/domains/identity_membership_domain.md). RBAC builds on that model and uses active `EstablishmentMembership` as the authorization root.

## 2. MVP Scope

- Backend-enforced authorization for establishment-scoped product access.
- Membership-backed roles: `owner`, `director`, `manager`, `staff`.
- Membership-backed operational domain scope through `MembershipScope` rows.
- Establishment visibility checks, action permission checks, and domain access checks.
- Backend permission enforcement for API reads, writes, command endpoints, feeds, realtime subscriptions, signed media access, notifications, comments, and chat access.
- Frontend permission hints as convenience only, never as security authority.

## 3. Out of Scope

- External policy engines.
- User-defined custom roles or permission builder UI.
- Cross-establishment access granted from a global `User` alone.
- UI-only authorization as a security boundary.
- Organization-wide super-admin product UX unless later validated.
- Exhaustive endpoint-by-endpoint permission matrix unless separately validated.
- Chat moderation workflows or advanced delegated admin hierarchy unless later validated.

## 4. Core Invariants

- Default deny. If membership, role, domain scope, or resource visibility is not valid, access is denied.
- Every establishment-scoped operation requires an active membership plus an active user, active establishment, and active organization.
- Backend validates authorization on every request. Frontend visibility never grants access.
- Object-level authorization is mandatory for both reads and writes.
- Establishment isolation is mandatory. Product APIs must not expose data outside authorized establishments.
- Role and operational domain data in responses are UI hints, not security authority.
- `owner` and `director` still require valid active membership; broad authority is never global.
- **`MembershipScope`** is the source of truth for manager/staff operational RBAC (`scope_type`: `module`, `domain`, or `subject`; `scope_id`: taxonomy UUID). No label-based inference. Parent scopes are explicit only (module/domain rows are not expanded into child subjects in the database).
- **`MembershipDomain`** is legacy/historical and must not be used as an active RBAC model. Authorization root is `MembershipScope` rows.
- `operational_domains` is onboarding proposal context (taxonomy selection), not the RBAC source of truth used by authorization checks.
- **`MembershipFeedSubscription`** (future Phase 4) personalizes **Ma vue** only — see [`feed_subscription_domain.md`](feed_subscription_domain.md). It must not be used as a security boundary or mixed with RBAC checks.
- Notifications and realtime events do not grant access.
- Signed media URLs require backend authorization before generation.
- Raw Observation text must not leak through feeds, notifications, realtime payloads, signed media flows, or unauthorized detail views.

## 5. Main Objects

- Role
  - Product role attached to `EstablishmentMembership`.
  - Current validated roles are `owner`, `director`, `manager`, and `staff`.

- Permission / Capability
  - Backend decision about whether a member may view a resource or perform a command.
  - Current helper truth lives in `apps/api/houston/establishments/permissions.py`.

- EstablishmentMembership
  - Authorization root for establishment access.
  - Carries role and membership status; access fails closed if membership is missing or inactive.

- MembershipScope assignment
  - Explicit module/domain/subject scope rows scope manager/staff action and visibility inside an establishment.
  - `can_access_domain` / `can_access_subject` evaluate scope coverage; owner/director retain broad access without scope rows.

- Resource visibility
  - Backend decision about whether a resource is visible at all inside the authorized establishment scope.
  - Visibility and actionability are related but not identical.

- Command authorization
  - Separate backend check for state-changing actions such as creating or validating work.
  - A visible resource does not automatically imply action permission.

## 6. Lifecycle / Statuses

Not applicable in MVP. RBAC evaluates current `User`, `EstablishmentMembership`, role, membership status, `MembershipScope` rows, establishment status, organization status, and resource state.

Permission outcomes are:
- allowed
- denied
- not visible / outside scope

## 7. Permissions

- Non-member or inactive member
  - No product access for the establishment.
  - A global `User` alone never grants product access.

- Active member
  - Base establishment access comes from active membership only.
  - Current implemented helpers allow active members to access the app, view the signal feed, and create observations.

- Owner
  - Broad Organization-level authority in.
  - Current implemented helpers allow managing establishment settings, memberships, runtime context, action creation, and action validation.

- Director
  - Broad establishment-level operational authority in MVP.
  - Current implemented helpers match owner authority for most validated helper sets.
  - Membership management is narrower than owner authority: directors may manage manager and staff memberships only; they cannot manage owner memberships.

- Manager
  - Management and action authority, mainly inside assigned operational domains.
  - Current implemented helpers allow action creation and validation, but not establishment settings or membership management.
  - Domain/subject access requires matching `MembershipScope` coverage (or owner/director broad access).

- Staff
  - Reporting and execution role, not management authority.
  - Current implemented helpers allow app access, signal-feed access, and observation creation, but not action creation or action validation.
  - Domain/subject access requires matching `MembershipScope` coverage (or owner/director broad access).

- Visibility vs actionability
  - Seeing a resource does not automatically allow acting on it.
  - Adjacent product docs validate that some cross-domain visibility may be broader than action rights. Treat exact per-resource behavior as candidate unless confirmed by current code and `apps/api/schema.yml`.
  - When adjacent product rules allow a manager outside the matching domain to see or comment on a visible resource, action rights still remain denied unless domain-compatible or explicitly authorized.

- Boundary rules
  - Feed visibility is backend-owned.
  - Comments inherit parent-resource visibility and must not bypass RBAC.
  - Chat is establishment-scoped and independent in MVP; it must not bypass structured workflow permissions.
  - Notifications may target authorized recipients, but they never create access.
  - Realtime may invalidate or trigger refetch only; it does not carry business truth or permission authority.

## 8. Events

No implemented RBAC-specific event contract is validated in current code or `apps/api/schema.yml`.

Candidate events only:
- `PermissionDenied` candidate
- `MembershipRoleChanged` candidate
- `MembershipScopeChanged` candidate
- `ResourceAccessDenied` candidate

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented RBAC-relevant endpoints confirmed in `apps/api/schema.yml`:

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

- Auth responses and bootstrap expose backend-approved `memberships`.
- `active_membership` is present when `UserSession.selected_establishment` resolves to a valid active membership.
- Login and refresh currently auto-select the sole active establishment on `UserSession` when exactly one active membership exists.
- Membership payloads include `role`, `scopes`, and `scope_summary` for UI context (not authoritative for security).
- Membership-management endpoints reuse bearer-session access context and DRF permission classes backed by `UserSession.selected_establishment`.
- Membership-management list endpoints are tenant-filtered at selector/queryset level before serialization.
- Current implemented membership-management authority is `owner` and `director`; `manager` and `staff` are denied.
- The current active establishment context must match the path `establishment_id`.
- Scoped user search reuses bearer-session access context and requires a valid active membership in the current selected establishment.
- Scoped user search is tenant-filtered at selector/queryset level before serialization and does not expose cross-establishment users.
- Scoped user search response fields are intentionally minimal and do not expose broader user profile or tenant metadata.

Candidate endpoints only:

- Role assignment or operational-domain assignment endpoints.
- Permission introspection endpoints.
- Signal, action, checklist, comment, notification, chat, feed, and signed-media endpoints whose RBAC behavior is described in product docs but not present in `apps/api/schema.yml`.

Target API convention from active product docs, not yet confirmed by current public resource endpoints:

- `401` for unauthenticated access.
- `403` for action not allowed on a visible resource.
- `404` for not visible / outside-scope resources.

## 10. Frontend Expectations

- Frontend receives membership, role, and scope context (`scopes`, `scope_summary`) from backend auth/bootstrap responses.
- Frontend may use backend-provided role or permission context to hide or show UI affordances, but must still submit commands to the backend for validation.
- TanStack Query owns server state and refetch behavior.
- Frontend must handle `401` as unauthenticated and should be prepared for `403` and `404` according to the target API convention above.
- Frontend must not infer real authorization from raw role or domain data alone.
- Frontend must not rely on websocket payloads as business truth; realtime should trigger invalidation and REST refetch.
- Frontend must not persist permission-sensitive business data outside the validated auth/session design.

## 11. AI Agent Notes

- Inspect current permission helpers before changing RBAC behavior.
- Inspect `apps/api/schema.yml` before listing endpoints or claiming a permission-bearing API is implemented.
- Inspect [identity_membership_domain.md](/Users/leobsn/Desktop/houston_project/docs/product/domains/identity_membership_domain.md) before changing membership assumptions.
- Do not move role or operational-domain scope onto `User`.
- Do not treat the UI as the authorization authority.
- Do not expose cross-establishment resources.
- Do not add a giant permission matrix unless explicitly requested and separately validated.
- Do not introduce an external policy engine in MVP.
- Do not claim candidate endpoints or events are implemented.
- Do not use old-stack terminology.
- When adding new permission-bearing endpoints later, update backend authorization, OpenAPI, generated clients, and tests together.
