# Phase B — Backend RBAC / membership scope

**Date:** 2026-06-11  
**S0 source:** [`code_scalability_s0_2026-06-11.md`](code_scalability_s0_2026-06-11.md)  
**Status:** Complete

## Implemented

### BE-RBAC01 — Checklist membership validation (P1)

**Action:** Implemented.

Replaced checklist-local `_is_active_membership` (membership status only) with establishments `_is_valid_membership` (active user, org, establishment, membership, valid role).

**Files:**
- `apps/api/houston/checklists/permissions.py`
- `apps/api/houston/checklists/tests/test_permissions.py`

**Tests added:** inactive/deactivated membership, non-active establishment (draft/deactivated), non-active organization (suspended/archived), non-active user.

---

## Review-only decisions

### BE-RBAC02 — Signal detail scope vs feed BU scope (P1)

| Field | Value |
|-------|-------|
| **Current behavior** | `signal_feed_queryset` applies `build_signal_feed_scope_q_v2` for manager/staff in `personal` view mode (affected **or** responsible BU). `get_signal_for_detail` / `_can_view_signal_detail` only checks `can_view_signal_feed(membership)` — any valid establishment member can read feed-visible signal detail by ID, regardless of BU scope. |
| **Product rationale (from code)** | Inline comment in `signals/selectors.py`: *"any feed-capable member may read feed-visible signal detail (pin/urgency gated separately)"*. Supports deep-linking and shared operational context without re-filtering detail reads through feed list scope. |
| **Recommendation** | **Keep** — intentional divergence between list scope and detail access. |
| **Owner** | Product |
| **Patch** | None without product sign-off. If changed later: apply `signal_visible_in_membership_scope` (or equivalent) in `_can_view_signal_detail` and add `signals/tests/test_permissions.py`. |
| **Domain docs** | Propagated 2026-06-12 — [`signal_domain.md`](../product/domains/signal_domain.md) §7, [`rbac_permissions_domain.md`](../product/domains/rbac_permissions_domain.md) §7, [`feed_domain.md`](../product/domains/feed_domain.md) §7. |

---

### BE-RBAC03 — Checklist management vs establishments management (P2)

| Field | Value |
|-------|-------|
| **Current behavior** | `can_access_checklist_management` = any `_is_valid_membership` (all roles: owner, director, manager, staff). `can_manage_memberships` = owner/director only. |
| **Rationale** | Checklists are operational tooling for all field roles; membership administration is restricted to leadership. |
| **Recommendation** | **Keep** — different capability domains by design. |
| **Owner** | Product |
| **Patch** | None unless product confirms checklist admin should be leadership-only. |

**Matrix:**

| Capability | Owner | Director | Manager | Staff |
|------------|-------|----------|---------|-------|
| Checklist management API (`can_access_checklist_management`) | ✓ | ✓ | ✓ | ✓ |
| Membership management (`can_manage_memberships`) | ✓ | ✓ | — | — |

---

### BE-RBAC04 — Execution feed permission class (P1)

| Field | Value |
|-------|-------|
| **Current behavior** | `ExecutionFeedView` uses `HasActiveMembership` only. `SignalFeedView` adds `CanViewSignalFeed`, which calls `can_view_signal_feed` → `_is_valid_membership` on the establishment-scoped membership resolved in the view. |
| **Assessment** | No proven RBAC gap. Execution feed resolves establishment-scoped membership via `resolve_observation_actor_membership`; `None` → 404. Feed content is further scoped in `build_execution_feed_page` / selectors (actions + checklists). `CanViewSignalFeed` is redundant with `_is_valid_membership` on the same resolved membership for signal feed; adding a parallel class to execution feed would duplicate that check without closing a new hole. |
| **Recommendation** | **Keep** — defer dedicated permission class unless `resolve_observation_actor_membership` is shown to return memberships that fail `_is_valid_membership`. |
| **Owner** | Engineering (revisit if uploads access layer changes in Phase C) |
| **Patch** | None. |

---

### BE-RBAC05 — Duplicated role constants (P2)

| Field | Value |
|-------|-------|
| **Current behavior** | `_ADMIN_ROLES` / `_MANAGEMENT_ROLES` defined independently in `checklists/permissions.py`, `signals/permissions.py`, `actions/permissions.py`, `chat/permissions.py`, and `establishments/permissions.py`. |
| **Recommendation** | **Defer to S1** — document only; no export/dedup in Phase B. |
| **Owner** | Engineering (S1) |
| **Patch** | S1: single shared constants module after grep-based audit. |

---

### BE-RBAC06 — Checklist BU scope vs signal/action scope (P2)

| Field | Value |
|-------|-------|
| **Current behavior** | Checklist visibility (`build_checklist_visibility_scope_q`) filters executions by snapshot `business_unit_id` in membership scope. Signals/actions use affected **or** responsible BU (`build_signal_feed_scope_q_v2`, `build_action_visibility_scope_q` in `membership_scope.py`). |
| **Rationale** | Checklist executions are assigned to a single BU snapshot; signals/actions can span affected + responsible units. |
| **Recommendation** | **Keep** — document semantic difference; measure query impact in Phase L if needed. |
| **Owner** | Product / Engineering (L) |
| **Patch** | None in B. L may baseline `scope_links` prefetch cost (DB-05). |

---

## Validation

```bash
cd apps/api && uv run pytest houston/checklists/tests/test_permissions.py -q
cd apps/api && uv run pytest houston/checklists/tests/ -q
make lint
```

## Rollback

Revert `checklists/permissions.py` and new tests; this decision doc remains for traceability.

## Stop condition for Phase C

- BE-RBAC01 implemented and tested ✓
- BE-RBAC02 / BE-RBAC04 documented with keep/defer recommendations ✓
- Checklist permission regression suite green (pending CI/local run)
