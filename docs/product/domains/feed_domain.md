# Feed Domain

Status: authoritative
Last reviewed: 2026-06-09
Implementation status: implemented (Signal Feed Phase 4 + Execution Feed Phase 5/7 — polymorphic Actions + Checklists unifiées). Checklist feed rules alignées sur [`checklist_domain.md`](checklist_domain.md) (Lots 2–7 clos).

## 1. Purpose

Feed owns Houston's authorized operational read projections:
- `SignalFeed` for structured Signal summaries.
- `ExecutionFeed` for structured execution summaries.
- safe feed items, backend-applied filters, backend-applied sorting, pagination, and optional permission hints.

Feed does not own:
- Signal, Action, or Checklist lifecycle rules.
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
- Target Signal Feed behavior keeps archived Signals out of active results by default.

Current truth:
- `GET signal-feed/` implemented (Phase 4) with required `view_mode=personal|general`.
- `GET execution-feed/` implemented (Phase 5 Actions + Phase 7 Checklists) with required `view_mode=personal|general`.
- Response envelope: `items`, `next_cursor`, `has_more`; each item has `item_type: "action" | "checklist"`.
- Execution Feed merge: visible checklist items are **prioritized** — up to `page_size` checklists first (sorted by `last_activity_at desc`), then Actions fill remaining slots (Action sort unchanged). Not a single cross-type `last_activity_at` interleave.
- Lazy checklist materialization runs on feed read (`ensure_visible_executions_materialized`) before querying checklist items.
- Execution Feed **Vue globale** for Staff: created/assigned Actions only (not scope-based); **Ma vue** uses the same rule for Staff. Checklist visibility follows [`checklist_domain.md`](checklist_domain.md) §9 (cible : exécutions assignées + scope ; Flash To-do et lancements depuis modèle selon RBAC).
- **Feed Exécution `+` (cible)** : menu Action / Flash To-do / Checklist — voir [`checklist_domain.md`](checklist_domain.md) §5.16. Flash To-do n'utilise pas la bibliothèque.

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
- Permission hints are UX helpers only, not authorization authority (Action feed items may expose hints; Checklist items use safe summaries without per-item hints in MVP).
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
  - **Implemented today:** polymorphic Action and Checklist execution items (see [`checklist_domain.md`](checklist_domain.md)).

- `FeedItem`
  - Safe summary of a visible domain object.
  - Signal Feed item = structured Signal summary, never raw Observation text.
  - Execution Feed item = structured execution summary for Action or Checklist (`item_type` discriminant).

- `FeedFilter`
  - Backend query constraints such as `view_mode`, domains, statuses, urgency, item type, or `requires_my_action`.
  - Exact supported filter set remains candidate until implemented.

- `FeedSort`
  - Backend-defined ordering for visible items.
  - Exact sort rules remain candidate until implemented.

- `FeedCursor`
  - Candidate pagination cursor for stable incremental loading.
  - Not implemented API truth today.

- `PermissionHint`
  - Candidate backend-provided UI hint such as visible actions or disabled actions.
  - Never grants access by itself.

- `FeedCount`
  - Candidate summary count block returned with feed results.
  - Not implemented API truth today.

## 6. Lifecycle / Statuses

Not applicable as a business lifecycle in MVP. Feed reflects authorized read state from Signal, Action, and Checklist domains.

Frontend display states may include:
- loading
- refreshing
- empty
- error
- paginating

## 7. Permissions

- Feed access is establishment-scoped and backend-authorized.
- Current code proves active members can view Signal Feed through `can_view_signal_feed(...)`.
- `ExecutionFeed` applies `view_mode` in selectors before returning items.
- **Ma vue** (`view_mode=personal`): active Signals matching **`MembershipScope`** (Owner/Director: all active). Empty if manager/staff has no scopes.
- **Vue générale** (`view_mode=general`): all active establishment Signals.
- Feed subscription is **deferred** (future: BU-only first, then ActivitySubject subscribe/unsubscribe) — see [`feed_subscription_domain.md`](feed_subscription_domain.md). **Today:** Ma vue uses `MembershipScope` only.
- RBAC (`MembershipScope`) governs actionability; feed Ma vue uses the same scope rows for filtering.
- Visibility does not imply actionability.
- Notifications and realtime events do not grant access.
- Permission hints do not grant access.

### Signal Feed vs Execution Feed — personal view (validated)

| Feed | Ma vue (`view_mode=personal`) | Vue générale (`view_mode=general`) |
| --- | --- | --- |
| **Signal Feed** | Active Signals matching **`MembershipScope`** (Owner/Director: all active). Empty if manager/staff has no scopes. | All active establishment Signals. RBAC feed access only. |
| **Execution Feed** (Actions + Checklists — implemented) | Active Actions where the user is **`created_by` or `assigned_to`** (all roles). Owner/Director **Ma vue** is not all establishment Actions (unlike Signal Feed). **Not** driven by feed subscriptions. **Checklist items (cible)** : exécutions où l'utilisateur est **`assigned_to`**, plus visibilité élargie Owner/Director/Manager selon [`checklist_domain.md`](checklist_domain.md) §9 (Flash To-do, `template`, `assignment`). | **Owner/Director:** all active establishment Actions + all visible checklist executions. **Manager:** own Actions plus Actions in **`MembershipScope`**, plus checklist executions in scoped BU (+ own assignments). **Staff:** created/assigned Actions + checklist executions **assigned to them** (and scope-visible catalogue usage does not add feed items unless assigned). **Not** subscription-based. |

**Execution Feed — Checklist items (cible post-refonte):** rules in [`checklist_domain.md`](checklist_domain.md) §5.6 and §9. Inclusion requires `status IN (assigned, in_progress)` AND `(visible_from IS NULL OR now >= visible_from)`. **`execution_source = assignment`** : `visible_from = start_at - 1 hour`. **`flash_todo` and `template`** : `visible_from` null (immediate). Terminal `done` / `canceled` excluded from active feed — including Flash To-do. `end_at` overdue does not remove items (`is_overdue` indicator only). Feed cards expose `execution_source` and optional template `badge` (Process/To-do) — **not** shared/personal labels.

**Future** feed subscriptions may personalize Signal Feed Ma vue (not implemented). They would not be permissions and would not filter Execution Feed. **Today:** Signal Feed Ma vue uses `MembershipScope` (BusinessUnit) only.

## 8. Events

No implemented Feed business event contract is confirmed in current code or `apps/api/schema.yml`.

Candidate events only:
- `FeedViewed` for analytics.
- `FeedFilterChanged` for frontend analytics.
- `FeedInvalidated` for internal or realtime coordination.

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented endpoints (establishment-scoped):

- `GET /api/v1/establishments/{establishment_id}/signal-feed/?view_mode=personal|general` — required `view_mode`; optional `statuses`, `business_unit_keys`, `activity_subject_ids`
- `GET /api/v1/establishments/{establishment_id}/execution-feed/?view_mode=personal|general` — required `view_mode`

Response envelope: `{ items, next_cursor, has_more }` (Signal Feed may include `applied_filters`).

Candidate / not implemented: advanced search, feed counts, saved views, stable cross-type cursor pagination.

**Execution Feed page merge (implemented):** checklist items sorted by `last_activity_at desc` among themselves; Actions sorted by existing Action keys (`requires_me_rank`, overdue, status, etc.) among themselves. Page assembly: checklists consume up to `page_size` slots first; Actions fill `page_size - checklist_count` remaining slots. Checklist feed items expose `end_at`, `is_overdue`, `execution_source`, and optional `badge`; overdue does not affect inclusion or sort. Frontend renders checklist cards above grouped Action sections ([`execution-checklist-card.tsx`](../../../apps/web/src/features/execution/components/execution-checklist-card.tsx)). Labels **Flash To-do** / badge Process/To-do — not Partagée/Personnelle.

**Execution Feed `+` menu (cible, Lot 4):** mobile-first bottom sheet with **Action** (Owner/Director/Manager), **Flash To-do** (all roles in scope), **Checklist** (créer ou utiliser enregistrée). See [`checklist_domain.md`](checklist_domain.md) §5.16.

Detail routes belong to owning domains, not Feed.

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
- TanStack Query owns server state.
- Frontend may expose filters, search, tabs, or view modes, but backend query remains authority.
- Frontend must not infer visibility from local state.
- Frontend must not display raw Observation text.
- Frontend must not request signed media URLs until an authorized detail or media flow requires them.
- Frontend must not treat notifications or realtime payloads as full feed state.
- Frontend should refetch or invalidate after realtime events.
- Frontend may render permission hints as UX helpers only.
- Mobile-first operational ergonomics matter, but exact layout belongs elsewhere.

## 11. AI Agent Notes

- Inspect current code before claiming feed models, selectors, endpoints, filters, or sorting exist.
- Inspect `apps/api/schema.yml` before naming any feed API as implemented.
- Inspect `signal_domain.md` before changing Signal Feed item rules.
- Inspect `action_domain.md` before changing Execution Feed Action item rules.
- Inspect checklist source docs before adding checklist items to Execution Feed.
- Inspect `rbac_permissions_domain.md` before changing visibility or actionability assumptions.
- Inspect `security_rgpd_domain.md` and `observation_domain.md` before changing raw-text, search, media, or logging boundaries.
- Do not make Feed a lifecycle owner.
- Do not expose raw Observation text.
- Do not perform frontend-only authorization.
- Do not include signed media URLs directly in feed items unless separately validated.
- Do not claim candidate APIs are implemented beyond what exists in `schema.yml`.
- When feed APIs change, update backend authorization, OpenAPI, generated clients, tests, and this document together.

## 12. Acceptance test matrix (implemented feeds)

### Signal Feed API

| Scenario | Expected behavior |
| --- | --- |
| Active member requests `view_mode=personal` with BusinessUnit scopes | Returns active Signals where affected or responsible BusinessUnit matches scope |
| Active member requests `view_mode=personal` without BusinessUnit scopes | Returns empty list (not an error) for Manager/Staff |
| Owner/Director requests `view_mode=personal` | All active establishment Signals |
| Active member requests `view_mode=general` | Returns all active establishment Signals |
| Resolved / canceled Signals | Excluded from default active feed results |
| Cross-establishment access | 404 when establishment does not match session membership |
| Inactive membership | 403 / no feed access |

### Ma vue scope matching (current — `MembershipScope`)

| Role | Scopes | Expected Ma vue |
| --- | --- | --- |
| Owner/Director | N/A (broad) | All active establishment Signals |
| Manager | BusinessUnit `restaurant` | Signals where affected or responsible BU is `restaurant` |
| Staff | BusinessUnit `maintenance` | Signals where affected or responsible BU is `maintenance` |

Vue générale for each role above must still return **all** active establishment Signals (RBAC feed access only).

### Response contract

- Feed items expose safe structured summaries only (no raw Observation text).
- Signal Feed items expose BusinessUnit / ActivitySubject labels and keys for UI badges.
- Execution Feed Action items expose BU/AS fields per `action_domain.md`.
- Execution Feed Checklist items expose safe summary: title, progress, `execution_source`, optional `badge`, `end_at`, `is_overdue`, `business_unit` label, status per [`checklist_domain.md`](checklist_domain.md) §12.
