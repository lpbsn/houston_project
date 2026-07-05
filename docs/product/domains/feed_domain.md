# Feed Domain

Status: authoritative  
Last reviewed: 2026-07-05  
Implementation status: implemented (Signal Feed Phase 4 + Action Plan Execution Feed Lot 5/10). Legacy polymorphic Action/Checklist execution feed removed in Lot 10 — archived domain docs: [`action_domain.md`](../../archive/product/domains/action_domain.md), [`checklist_domain.md`](../../archive/product/domains/checklist_domain.md).

## 1. Purpose

Feed owns Houston's authorized operational read projections:
- `SignalFeed` for structured Signal summaries.
- `ExecutionFeed` for structured execution summaries.
- safe feed items, backend-applied filters, backend-applied sorting, pagination, and optional permission hints.

Feed does not own:
- Signal or Action Plan lifecycle rules.
- Notification Center behavior.
- realtime transport.
- RBAC policy definition.
- AI behavior.
- raw Observation persistence or exposure.

Feed is a read/projection domain. It is not business truth.

## 2. MVP Scope

- Backend-authorized `SignalFeed` read projection.
- Backend-authorized `ExecutionFeed` read projection.
- Safe feed items only; no raw Observation text.
- Backend-owned filtering and sorting.
- Pagination suitable for changing operational lists.
- Optional permission hints as UX helpers only.
- Realtime invalidation/refetch boundary only.
- Media summary only; no raw media URLs or signed URLs in feed items.
- Target Signal Feed behavior keeps archived Signals out of feed-visible results by default (`open`, `in_progress`, `resolved`; see [`signal_domain.md`](signal_domain.md) §7).

Current truth:
- `GET signal-feed/` implemented (Phase 4) with required `view_mode=personal|general`.
- **`GET action-plan-execution-feed/`** (Lot 5 Plan d'action, seul feed exécution post-Lot 10) with required `view_mode=personal|general`. Response envelope: `items`, `next_cursor`, `has_more`; each item has `item_type: "action_plan_execution"` and payload `action_plan_execution`.
- Lazy action plan schedule materialization runs on feed read (`ensure_visible_action_plan_executions_materialized`) before querying items on **`action-plan-execution-feed/`** (horizon 3 days, stale guard 30 min).
- **Feed Exécution `+` (cible Lot 10):** menu **Plan ponctuel** / **Catalogue** — voir [`besoin_evolution_action.md`](../../evolution_action/besoin_evolution_action.md) §25.

## 3. Out of Scope

- Feed as business truth.
- Lifecycle transitions from feed state.
- Frontend-only authorization.
- Notification Center ownership.
- Analytics or reporting dashboards.
- Saved views or advanced personalized feed configuration.
- Drag-and-drop lifecycle mutation.
- Raw Observation search.
- Signed media URLs directly inside feed items.
- AI ranking or personalization in MVP.
- Cross-tenant or public feed views.

## 4. Core Invariants

- Feed is a read projection, not a source of business truth.
- Backend authorization runs before returning any feed item.
- Feed items are establishment-scoped.
- Frontend filters, tabs, or view modes do not grant visibility.
- Feed items must not contain raw Observation text.
- Feed items must not contain raw media URLs or signed URLs.
- Permission hints are UX helpers only, not authorization authority.
- Lifecycle changes must happen through owning domain command endpoints.
- Realtime invalidates or refetches feed queries; it does not carry complete feed state.
- Search must not leak raw Observation content.
- Search, if implemented, must search safe indexed summaries only and must not expose raw Observation text.
- Feed items link to owning domain detail routes; Feed does not own detail payloads.
- Feed visibility and action hints must stay consistent with RBAC and domain rules.
- UX direction does not make the frontend authoritative for sorting, filtering, pagination, permissions, or lifecycle commands.

## 5. Main Objects

- `Feed`
  - Backend-authorized operational read projection for work visibility.
  - Covers `SignalFeed` and `ExecutionFeed`.

- `SignalFeed`
  - Structured Signal summary stream for supervision.
  - Never exposes raw Observation text.

- `ExecutionFeed`
  - Structured execution summary view for operational follow-up.
  - **Implemented today:** Action Plan execution items only (`item_type: "action_plan_execution"`). Legacy polymorphic Action/Checklist feed removed in Lot 10 — see archive docs linked in header.

- `FeedItem`
  - Safe summary of a visible domain object.
  - Signal Feed item = structured Signal summary, never raw Observation text.
  - Execution Feed item = structured `ActionPlanExecution` summary (`item_type: "action_plan_execution"`).

- `FeedFilter`
  - Backend query constraints such as `view_mode`, domains, statuses, urgency, or `requires_my_action`.
  - Execution Feed today: required `view_mode=personal|general` only.

- `FeedSort`
  - Backend-defined ordering for visible items.
  - Execution Feed: `last_activity_at desc`, `created_at desc`, `id desc`.

- `FeedCursor`
  - Opaque pagination cursor for stable incremental loading on dynamic feeds.
  - **Implemented** for Signal Feed and Action Plan Execution Feed (`cursor` query param, `next_cursor` response). See [`api_pagination_standard.md`](../../engineering/api_pagination_standard.md).

- `PermissionHint`
  - Candidate backend-provided UI hint such as visible actions or disabled actions.
  - Never grants access by itself.

- `FeedCount`
  - Candidate summary count block returned with feed results.
  - Not implemented API truth today.

## 6. Lifecycle / Statuses

Not applicable as a business lifecycle in MVP. Feed reflects authorized read state from Signal and Action Plan domains.

Frontend display states may include:
- loading
- refreshing
- empty
- error
- paginating

## 7. Permissions

- Feed access is establishment-scoped and backend-authorized.
- Current code proves active members can view Signal Feed through `can_view_signal_feed(...)`. See [`signal_domain.md`](signal_domain.md) §7 for detail access and command scope rules.
- Action Plan Execution Feed applies `view_mode` in selectors before returning items (`action_plan_execution_feed_queryset`).
- **Ma vue** (`view_mode=personal`): executions where the user is an assignee, or (Manager) executions in scoped business units via execution teams.
- **Vue générale** (`view_mode=general`): Owner/Director see all feed-visible establishment executions; Manager sees scoped BUs + own assignments; Staff sees own assignments only.
- Feed subscription is **deferred** (future: BU-only first, then ActivitySubject subscribe/unsubscribe) — see [`feed_subscription_domain.md`](feed_subscription_domain.md). **Today:** Signal Feed Ma vue uses `MembershipScope` only.
- RBAC (`MembershipScope`) governs actionability; feed Ma vue uses the same scope rows for filtering where applicable.
- Visibility does not imply actionability.
- Notifications and realtime events do not grant access.
- Permission hints do not grant access.

### Signal Feed vs Action Plan Execution Feed — personal view (validated)

| Feed | Ma vue (`view_mode=personal`) | Vue générale (`view_mode=general`) |
| --- | --- | --- |
| **Signal Feed** | Feed-visible Signals (`open`, `in_progress`, `resolved`) matching **`MembershipScope`** (Owner/Director: all feed-visible). Empty if manager/staff has no scopes. | All feed-visible establishment Signals (`open`, `in_progress`, `resolved`). RBAC feed access only. |
| **Action Plan Execution Feed** | Executions where user is **assignee**, plus Manager scope via execution teams (`action_plan_execution_personal_feed_q`). Owner/Director Ma vue is not all establishment executions (unlike Signal Feed general). | **Owner/Director:** all feed-visible establishment executions. **Manager:** scoped BUs + own assignments. **Staff:** own assignments only. |

**Action Plan Execution Feed — inclusion rules (implemented):**
- `status IN (in_progress, pending_validation)` (`EXECUTION_FEED_STATUSES`).
- `(visible_from IS NULL OR now >= visible_from)`.
- Terminal `done` / `canceled` excluded from active feed; detail remains accessible.
- `end_at` overdue does not remove items (`is_overdue` indicator only).
- Lazy schedule materialization on feed read (`ensure_visible_action_plan_executions_materialized`) — horizon 3 days, stale guard 30 min. See [`action_plan_materialization.md`](../../evolution_action/action_plan_materialization.md).

**Future** feed subscriptions may personalize Signal Feed Ma vue (not implemented). They would not be permissions and would not filter Execution Feed. **Today:** Signal Feed Ma vue uses `MembershipScope` (BusinessUnit) only.

## 8. Events

No implemented Feed business event contract is confirmed in current code or `apps/api/schema.yml`.

Candidate events only:
- `FeedViewed` for analytics.
- `FeedFilterChanged` for frontend analytics.
- `FeedInvalidated` for internal or realtime coordination.

Realtime invalidation for execution feed uses `action_plan_execution.*` events (see [`realtime_domain.md`](realtime_domain.md)).

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented endpoints (establishment-scoped):

- `GET /api/v1/establishments/{establishment_id}/signal-feed/?view_mode=personal|general` — required `view_mode`; optional `cursor`, `page_size`, `statuses`, `business_unit_keys`, `activity_subject_ids`. **Cursor pagination implemented** (reference).
- `GET /api/v1/establishments/{establishment_id}/action-plan-execution-feed/?view_mode=personal|general` — required `view_mode`; optional `cursor`, `page_size` (default 25, max 50). **Cursor pagination implemented** (single-type feed; opaque cursor).

Response envelope: `{ items, next_cursor, has_more }` (Signal Feed may include `applied_filters`).

Each execution feed item: `{ item_type: "action_plan_execution", action_plan_execution: { ... } }`.

Pagination standard: [`api_pagination_standard.md`](../../engineering/api_pagination_standard.md).

Candidate / not implemented: advanced search, feed counts, saved views.

**Execution Feed `+` menu (implemented):** mobile-first bottom sheet with **Plan d'action** only when `can_create_action_plan` bootstrap hint is true. Routes to action plan create (ponctuel or catalogue). See [`besoin_evolution_action.md`](../../evolution_action/besoin_evolution_action.md) §25.

Detail routes belong to owning domains (`/action-plans/executions/{id}`), not Feed.

## 10. Frontend Expectations

- Frontend renders backend-authorized items only.
- Signal Feed should be described as a structured operational news-feed-like stream: card-based, scannable, priority-aware, and safe.
- Execution Feed should be described as a structured Kanban-style execution view: grouped by execution state or required action, optimized for tracking progress.
- Kanban-style means grouped execution visibility, not drag-and-drop workflow mutation.
- These UX directions must not become business authority.
- Backend remains authoritative for sorting, filtering, pagination, permissions, and lifecycle commands.
- Mobile-first UI may adapt the Kanban representation into columns, grouped sections, tabs, or horizontally scrollable lanes.
- Do not hardcode exact columns, layout, drag-and-drop, animations, or component choices in this domain doc.
- Frontend must use generated OpenAPI clients only for implemented routes.
- TanStack Query owns server state. Query key: `['action-plans', 'action-plan-execution-feed', establishmentId, viewMode]`.
- Frontend may expose filters, search, tabs, or view modes, but backend query remains authority.
- Frontend must not infer visibility from local state.
- Frontend must not display raw Observation text.
- Frontend must not request signed media URLs until an authorized detail or media flow requires them.
- Frontend must not treat notifications or realtime payloads as full feed state.
- Frontend should refetch or invalidate after realtime events (`action_plan_execution.*`).
- Frontend may render permission hints as UX helpers only.
- Mobile-first operational ergonomics matter, but exact layout belongs elsewhere.
- Component: [`action-plan-execution-feed-card.tsx`](../../../apps/web/src/features/execution/components/action-plan-execution-feed-card.tsx).

## 11. AI Agent Notes

- Inspect current code before claiming feed models, selectors, endpoints, filters, or sorting exist.
- Inspect `apps/api/schema.yml` before naming any feed API as implemented.
- Inspect `signal_domain.md` before changing Signal Feed item rules.
- Inspect [`action_plan_materialization.md`](../../evolution_action/action_plan_materialization.md) and `action_plans/selectors.py` before changing Execution Feed item rules.
- Inspect `rbac_permissions_domain.md` before changing visibility or actionability assumptions.
- Inspect `security_rgpd_domain.md` and `observation_domain.md` before changing raw-text, search, media, or logging boundaries.
- Do not make Feed a lifecycle owner.
- Do not expose raw Observation text.
- Do not perform frontend-only authorization.
- Do not include signed media URLs directly in feed items unless separately validated.
- Do not claim candidate APIs are implemented beyond what exists in `schema.yml`.
- Do not reference legacy `/execution-feed/`, `execution-checklist-card.tsx`, or `execution-action-card.tsx` — removed in Lot 10.
- When feed APIs change, update backend authorization, OpenAPI, generated clients, tests, and this document together.

## 12. Acceptance test matrix (implemented feeds)

### Signal Feed API

| Scenario | Expected behavior |
| --- | --- |
| Active member requests `view_mode=personal` with BusinessUnit scopes | Returns feed-visible Signals where affected or responsible BusinessUnit matches scope |
| Active member requests `view_mode=personal` without BusinessUnit scopes | Returns empty list (not an error) for Manager/Staff |
| Owner/Director requests `view_mode=personal` | All feed-visible establishment Signals |
| Active member requests `view_mode=general` | Returns all feed-visible establishment Signals |
| `resolved` Signals | Included in default feed-visible results |
| `canceled` / `archived` Signals | Excluded from default feed-visible results |
| Cross-establishment access | 404 when establishment does not match session membership |
| Inactive membership | 403 / no feed access |

### Ma vue scope matching (current — `MembershipScope`)

| Role | Scopes | Expected Ma vue |
| --- | --- | --- |
| Owner/Director | N/A (broad) | All feed-visible establishment Signals |
| Manager | BusinessUnit `restaurant` | Signals where affected or responsible BU is `restaurant` |
| Staff | BusinessUnit `maintenance` | Signals where affected or responsible BU is `maintenance` |

Vue générale for each role above must still return **all** feed-visible establishment Signals (RBAC feed access only).

### Response contract

- Feed items expose safe structured summaries only (no raw Observation text).
- Signal Feed items expose BusinessUnit / ActivitySubject labels and keys for UI badges.
- Action Plan Execution Feed items expose safe summary: title, progress, assignees, `end_at`, `is_overdue`, business unit labels, status, linked signal summary when present.
