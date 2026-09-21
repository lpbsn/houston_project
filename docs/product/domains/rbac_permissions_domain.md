# RBAC / Permissions Domain

Status: authoritative
Last reviewed: 2026-09-21
Implementation status: live (tenant RBAC; Platform is a separate context)

Tenant authorization after identity and membership are resolved. Root: active `EstablishmentMembership`. Identity/lifecycle: [`identity_membership_domain.md`](identity_membership_domain.md). Action Plan matrices: [`action_plans/permissions.py`](../../../apps/api/houston/action_plans/permissions.py) and [`decisions/action_plan.md`](../decisions/action_plan.md). HTTP: [`apps/api/schema.yml`](../../../apps/api/schema.yml).

**Platform is a separate authorization context** (`IsActivePlatformOperator` on `/api/v1/platform/*` only). Do not weaken tenant selectors or `HasActiveMembership` for it. Tenant domain code must not import Platform permissions.

## Invariants

- Default deny. Invalid membership, role, BusinessUnit scope, or resource visibility → denied.
- Authorization is layered and must not be collapsed:
  - **PostgreSQL** — a `MembershipScope` row cannot link a membership to a BusinessUnit of another establishment (`establishment_id` stamped from the membership, composite FKs).
  - **Domain services** — business matrices (active BusinessUnit, Owner/Director without scope rows, invite/manage rules). A DB constraint does not replace those checks.
  - **DRF** — omit `permission_classes` and `DenyByDefault` refuses access, including for an authenticated bearer. Intentionally unauthenticated routes opt in with `AllowAny`; the closed public allowlist is the urlconf inventory test, not a second permission registry.
  - **Surface permissions** — HTTP entry for a given context. Path-scoped establishment/organization admin is decided **once** per request (`decide_active_establishment_admin_access` / `decide_organization_admin_access`). `HasActiveMembership` is a coarse session gate, not object rules.
- Every establishment-scoped operation requires an active membership plus active user, establishment, and organization. A `User` alone never grants product access.
- Backend validates on every request. Frontend visibility never grants access. Role and BusinessUnit payloads are UI hints.
- **`MembershipScope`** is the source of truth for manager/staff operational RBAC (`scope_type`: `business_unit` only; `scope_id`: active BusinessUnit UUID). ActivitySubject is never an RBAC scope. No label-based inference.
- **`MembershipFeedSubscription` is deferred.** Today Ma vue uses `MembershipScope`. Subscriptions are never a security boundary. See [`feed_subscription_domain.md`](feed_subscription_domain.md).
- Notifications and realtime events do not grant access. Signed media URLs require backend authorization before generation. Raw Observation text must not leak through feeds, notifications, realtime, signed media, or unauthorized detail.

## Roles

Helpers live in `apps/api/houston/establishments/permissions.py` unless a domain owns its matrix.

- **Non-member / inactive** — no product access for the establishment.
- **Active member** — app access, signal feed, observation create (when helpers allow).
- **Owner** — organization-level authority: settings, memberships, runtime, action create/validate. May invite `owner`, `director`, `manager`, `staff`. Owner invite fans out across draft/active establishments. `PATCH` cannot assign destination `owner`/`director` and cannot modify an existing owner. Director may be demoted to manager/staff with required scopes.
- **Director** — establishment-level operational authority. Invite `director`, `manager`, `staff` on an **active** establishment (multi-director allowed post-activation). Cannot invite `owner`. May manage manager and staff only; not owner or peer director memberships.
- **Manager** — authority mainly inside assigned BusinessUnit scopes. Action create/validate; invite **staff** within BU coverage. Not establishment settings. Scope coverage required (or owner/director broad access).
- **Staff** — reporting and execution. Cannot invite. Action plan create follows `can_create_action_plan` / `can_create_action`. Cannot create **signal-linked** plans when role denies it. Cannot validate executions when `can_validate_action` excludes them. Scope coverage required for visibility and free-action create (or owner/director broad access).

## Signal Feed — list vs detail

Validated product decision (keep unless explicitly reopened):

- **Ma vue** (`view_mode=personal`): Manager/Staff see Signals where affected **or** responsible BusinessUnit is in `MembershipScope`. Owner/Director see all feed-visible establishment Signals.
- **Vue générale** (`view_mode=general`): all feed-visible establishment Signals for every role — no BU filter on the list.
- **Detail**: any member passing `can_view_signal_feed` may read feed-visible Signal detail by ID, including deep-links outside Ma vue BU scope (`get_signal_for_detail` / `_can_view_signal_detail`).
- Command authorization (pin, urgency, cancel, resolve, create linked action) remains scope-aware for Manager/Staff.

Seeing a resource does not imply acting on it.

## Other surfaces

- Comments inherit parent-resource visibility.
- Chat V1 is establishment-scoped and independent of `MembershipScope`. Participant-only: Owner/Director have no read access outside participation. Group delete on the product API requires an active **admin participant**. Staff may create DMs, not groups; Manager/Director/Owner may create groups.
- Feed visibility: [`feed_domain.md`](feed_domain.md). Signal: [`signal_domain.md`](signal_domain.md).

## Frontend

Use bootstrap role/scope to hide or show affordances. Submit commands to the backend. Treat `401` as unauthenticated; expect `403` (action denied on a visible resource) and `404` (not visible / outside scope). Do not persist permission-sensitive data outside the auth/session design.

## Agent notes

- Inspect current permission helpers and `schema.yml` before changing RBAC.
- Do not move role or BusinessUnit scope onto `User`.
- Do not implement Platform as a super-membership or `is_staff` check on tenant views.
- Do not add an endpoint-by-endpoint matrix here.
