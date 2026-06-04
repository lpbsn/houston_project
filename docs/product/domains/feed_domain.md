# Feed Domain

Status: authoritative
Last reviewed: 2026-06-04
Implementation status: partial (Execution Feed Phase 5; Signal Feed Phase 4)

## 1. Purpose

Feed owns Houston's authorized operational read projections:
- `SignalFeed` for structured Signal summaries.
- `ExecutionFeed` for structured execution summaries.
- safe feed items, backend-applied filters, backend-applied sorting, pagination, and optional permission hints.

Feed does not own:
- Signal, Action, or candidate Checklist lifecycle rules.
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
- `GET execution-feed/` implemented (Phase 5, Actions only) with required `view_mode=personal|general`.
- Response envelope: `items`, `next_cursor`, `has_more`.
- Execution Feed **Vue globale** for Staff: created/assigned Actions only (not scope-based); **Ma vue** uses the same rule for Staff.

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
  - Includes Action items and candidate checklist-derived execution items only when separately validated.

- `FeedItem`
  - Safe summary of a visible domain object.
  - Signal Feed item = structured Signal summary, never raw Observation text.
  - Execution Feed item = structured execution summary for Action and candidate checklist work.

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

Not applicable as a business lifecycle in MVP. Feed reflects authorized read state from Signal, Action, and candidate Checklist domains.

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
- `MembershipFeedSubscription` is **out of scope Phase 4** (`feed_subscription_domain.md`).
- RBAC (`MembershipScope`) governs actionability; feed Ma vue uses the same scope rows for filtering in Phase 4.
- Visibility does not imply actionability.
- Notifications and realtime events do not grant access.
- Permission hints do not grant access.

### Signal Feed vs Execution Feed — personal view (validated)

| Feed | Ma vue (`view_mode=personal`) | Vue générale (`view_mode=general`) |
| --- | --- | --- |
| **Signal Feed** | Active Signals matching **`MembershipScope`** (Owner/Director: all active). Empty if manager/staff has no scopes. | All active establishment Signals. RBAC feed access only. |
| **Execution Feed** | Active Actions where the user is **`created_by` or `assigned_to`** (all roles). Owner/Director **personal** is not all establishment Actions (unlike Signal Feed). **Not** driven by feed subscriptions. | **Owner/Director:** all active establishment Actions. **Manager:** personal set plus Actions in **`MembershipScope`**. **Staff:** same as personal (created/assigned only). **Not** subscription-based. |

Feed subscriptions personalize **Signal Feed Ma vue only**. They are not permissions and do not filter Execution Feed.

## 8. Events

No implemented Feed business event contract is confirmed in current code or `apps/api/schema.yml`.

Candidate events only:
- `FeedViewed` for analytics.
- `FeedFilterChanged` for frontend analytics.
- `FeedInvalidated` for internal or realtime coordination.

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented endpoints confirmed today:
- none

Candidate endpoints only:
- `GET /api/v1/establishments/:id/signal_feed`
- `GET /api/v1/establishments/:id/execution_feed`

Candidate API expectations:
- Signal Feed target filters: `view_mode`, `domains`, `statuses`, `urgency`, candidate `search`.
- Execution Feed target filters: `view_mode`, `item_types`, `statuses`, `domains`, `requires_my_action`, candidate `search`.
- Cursor pagination is preferred for feeds, but remains candidate until implemented.
- Candidate response-shape elements include `next_cursor`, `has_more`, `applied_filters`, and counts.
- Candidate Signal Feed ordering includes active-status prioritization, urgency emphasis, and pinned visibility rules.
- Candidate Execution Feed ordering includes grouping by execution state or required action.
- Candidate feed item fields may include permission hints, related Signal summaries, `media_count`, and `thumbnail_media_id`.
- Detail routes belong to owning domains, not Feed.

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
- Do not claim candidate APIs are implemented.
- When feed APIs are added later, update backend authorization, OpenAPI, generated clients, tests, and this document together.

## 12. Future test scenarios (Phase 4 — documentation only)

Do **not** implement these tests before Signal model, feed selectors, and feed API exist. They define the acceptance matrix for Phase 4 implementation.

### Signal Feed API

| Scenario | Expected behavior |
| --- | --- |
| Active member requests `view_mode=personal` with subscriptions | Returns only active Signals (`open`, `in_progress`) whose module/domain/subject matches at least one subscription |
| Active member requests `view_mode=personal` without subscriptions | Returns empty list (not an error) |
| Active member requests `view_mode=general` | Returns all active establishment Signals; **no** subscription filter |
| Resolved / canceled / archived Signals | Excluded from active feed results |
| Cross-establishment access | 404 when establishment does not match session membership |
| Inactive membership | 403 / no feed access |

### Feed selector matching

| Subscription kind | Signal triplet | Match |
| --- | --- | --- |
| Module `hotel` | `operational_module=hotel` | Yes |
| Domain `hotel__hebergement` | `operational_domain=hotel__hebergement` | Yes |
| Subject `hotel__hebergement__proprete_des_chambres` | `operational_subject=…` | Yes only at subject level |
| Domain subscription | Signal in same module but different domain | No |

### Role scenarios (Ma vue)

| Role | Subscriptions | Expected Ma vue |
| --- | --- | --- |
| Directeur | Module `hotel` | All hotel Signals |
| Gouvernante | Domain `hotel__hebergement` | Hebergement Signals only |
| Femme de chambre | Subject `hotel__hebergement__proprete_des_chambres` | That subject only |
| Technicien | Domain maintenance-related subject | Matching domain/subject Signals only |

Vue générale for each role above must still return **all** active establishment Signals (RBAC access only).

### Response contract

- Feed items expose safe structured summaries only (no raw Observation text).
- Items include module/domain/subject keys for UI badges.
- OpenAPI, generated TypeScript client, selector unit tests, and API integration tests must be added together when implemented.
