# Signal Domain

Status: authoritative
Last reviewed: 2026-07-29
Implementation status: partial (feed, detail, pin, mark interesting, archive, cancel, resolve implemented; Phase 5 core Action side effects implemented; pipeline **v6** aggregation on normalized `issue_focus` for `routing_status=resolved` only; Signal lifecycle actor fields + append-only `SignalLifecycleEvent` journal implemented write-side; user-facing timeline API not implemented)

## 1. Purpose

This domain defines Houston's structured operational situation boundary.

Signal owns:
- the structured operational situation created or enriched from backend-validated Observation pipeline output
- the business identity of the supervised situation shown in Signal Feed
- the Signal lifecycle and high-level state meaning
- routing and operational scope through validated BU/AS classification

Signal does not own:
- raw Observation input or Observation persistence
- AI proposal contracts or provider behavior
- Action execution lifecycle
- Feed query, sorting, or pagination rules
- notification delivery rules
- realtime transport rules
- RBAC internals or security policy details

Signal is the operational object between Observation and Action. It is not the raw report itself and it is not the execution task.

## 2. MVP Scope

- Signal creation from backend-validated candidate Signals proposed from Observation pipeline output.
- Aggregation of a candidate Signal into an existing active Signal when backend validation decides it matches an ongoing situation.
- Signal lifecycle statuses: `open`, `in_progress`, `resolved`, `canceled`, `archived`.
- Routing through **BusinessUnit / ActivitySubject classification** per Signal: `affected_business_unit`, `responsible_business_unit`, `activity_subject` (optional `operational_unit` for structured location; `location_text` for free text; **`issue_focus`** for operational focus and aggregation discriminant).
- Candidate pinned-open behavior for important visible Signals.
- Safe Signal summaries for feed and detail surfaces.
- Relationship to linked Actions, contextual comments, safe timeline entries, and linked Observation media context without exposing raw Observation text.
- Establishment-scoped backend authorization for Signal visibility and commands.

This domain describes the validated MVP target behavior. Current code and `apps/api/schema.yml` confirm partial Signal implementation (see §9).

## 3. Out of Scope

- Direct manual Signal creation in MVP.
- A free-floating Signal with no Observation or validated pipeline origin.
- Treating Signal as raw Observation input.
- Treating Signal as an Action, checklist task, or generic ticket.
- AI-decided urgency.
- AI-created Actions.
- Frontend-only Signal lifecycle transitions.
- Public Signal links or cross-tenant Signal visibility.
- Raw Observation text in Signal detail, feed, notifications, realtime payloads, or normal technical logs.
- Arbitrary frontend-driven Signal merging.
- Advanced duplicate-resolution workflow, advanced transfer workflow, or SLA system not separately validated.
- Image AI analysis.

## 4. Core Invariants

- Signal is the central structured operational situation.
- Signal is not Observation.
- Signal is not Action.
- Signal is not a generic ticketing object.
- Only backend-validated proposals may create a new Signal or aggregate into an existing Signal.
- Observation remains a separate persisted record even when its candidate output aggregates into an existing Signal.
- Raw Observation text must not appear in normal Signal surfaces, notifications, realtime payloads, or durable frontend state.
- Signal lifecycle transitions are backend-owned.
- Frontend cannot treat local state as Signal status authority.
- AI does not decide urgency in MVP.
- AI does not create Actions in MVP.
- **One primary BU/AS classification per Signal** (`affected_business_unit`, `responsible_business_unit`, `activity_subject`). Legacy Module/Domain/Subject FKs are removed (Lot 6).
- An Observation describing **multiple distinct problems** produces **multiple CandidateSignals** and, after validation, **multiple Signals** — never multiple categorizations on one Signal.
- Ma vue feed visibility uses **BusinessUnit `MembershipScope`** matching (Owner/Director: all active). RBAC action uses affected/responsible BusinessUnit scopes and role rules. Feed subscription is deferred (future BU-only, then ActivitySubject subscribe/unsubscribe) — not used today.
- Visibility does not imply actionability.
- Realtime and notifications may help refresh attention, but they do not grant access and do not become business truth.

## 5. Main Objects

- `Signal`
  - Structured operational situation visible in Signal Feed.
  - Created or enriched only after backend validation of pipeline output.

- `CandidateSignal`
  - Structured proposal produced before business persistence.
  - Not business truth until backend validation creates or aggregates a Signal.

- `SignalStatus`
  - Lifecycle state such as `open`, `in_progress`, `resolved`, `canceled`, or `archived`.
  - Controls whether the Signal remains part of active operational supervision.

- `SignalCategorization`
  - BU/AS classification: affected/responsible BusinessUnit + ActivitySubject FKs on the Signal row.
  - Optional operational unit for physical location only.
  - Public feed/detail may expose compatibility `*_business_unit_key` / `*_label` (`normalized_specific_name` / `specific_name`) — **never identifiers**; filter/RBAC use UUIDs.

- ~~`SignalDomain` / `detected_domains`~~ — removed from MVP; classification is BU/AS only.

- `SignalAggregation`
  - Backend decision that a candidate Signal belongs to an existing active Signal instead of creating a new one.
  - Match key (pipeline v6): `(affected_bu, responsible_bu, activity_subject, operational_unit | null, normalize(issue_focus))` — **only** when `routing_status=resolved`.
  - No LLM aggregate hint (`aggregate_into_signal_id` removed). `unassigned` Signals are never auto-aggregated.
  - UI filter / badge **« Non classifié »** = `responsible_business_unit_id IS NULL` (distinct from affected / subject).
  - Display dedup Concerné / responsable is **ID-only** (`affected_business_unit_id` vs `responsible_business_unit_id`): same UUID hides the secondary Concerné line; same label with different UUIDs still shows Concerné.

- `LinkedObservationContext`
  - Safe reference to source Observation context.
  - Must not expose raw Observation text in normal product surfaces.

- `SignalTimeline`
  - Safe event, Action, comment, and media summary around the situation.
  - Not a raw dump of internal payloads or Observation content.

## 6. Lifecycle / Statuses

- `open`
  - Active structured situation requiring supervision.
  - Normal creation state for a newly persisted Signal.
  - May carry an associated **SignalResolutionRequest** (`pending`, `approved`, `rejected`, `canceled`) without changing `Signal.status`.
  - A pending resolution request is an associated workflow state, **not** a Signal lifecycle status; no `pending_validation` Signal status exists.

- `interesting`
  - Useful situation kept outside the default operational urgency buckets.
  - Transition `open → interesting` via `POST .../signals/{id}/mark-interesting/`.
  - Not pinnable; marking interesting always clears pin fields (`status == interesting` ⇒ `is_pinned == false`).
  - Cancel and resolve are not allowed.
  - Remains an aggregation target and participates in the active uniqueness constraint with `open` / `in_progress`.
  - Linked Action Plan execution creation transitions `interesting → in_progress` via the same `_activate_linked_signal_on_execution_create` path as `open`.
  - No reverse transition to `open`.
  - User archive: `interesting → archived` via `POST .../signals/{id}/archive/` (Owner/Director/Manager scope-or-unassigned; Staff denied). Feed sheet action only in UI.

- `in_progress`
  - Active situation with linked execution work underway.
  - Automatic transition from `open` or `interesting` when a linked Action Plan execution is created (`create_action_plan_with_execution` with `source_signal_id`).

- `resolved`
  - Situation considered operationally handled.
  - Manual resolution is available via backend command `POST .../signals/{id}/resolve/` from `open` only (`MANUAL_CANCEL_RESOLVE_SIGNAL_STATUSES`; `in_progress` and `interesting` excluded).
  - Manual resolve/cancel on `in_progress` is refused with an explicit business error; resolution must go through linked Action Plan finalization.
  - Automatic resolution when all linked Actions are terminal is implemented in Phase 5 (Action services) via `resolve_signal_from_execution_sync` (allows `open` / `in_progress`).
  - Manual resolve from `open` cancels linked blocking executions (if any), then transitions the Signal to `resolved`.
  - If a pending resolution request exists, a manual or automatic resolve by another authorized actor cancels that request with reason `signal_resolved_elsewhere`.

- `canceled`
  - Situation intentionally closed as no longer relevant to pursue.
  - Manual cancellation is available via `POST .../signals/{id}/cancel/` from `open` only (same eligibility as manual resolve).
  - **MVP cancellation does not require a category, reason, or justification payload.** The command has no mandatory request body.

- `archived`
  - Historical / terminal storage state outside all product surfaces in this version (no feed, no status filter, detail GET → 404).
  - User archive from `interesting` only (`POST .../signals/{id}/archive/`). Does **not** set `merged_into` (distinct from qualify merge archive).
  - Applies the same CREATED_FROM media cleanup policy as cancel/resolve (delete when last active sibling).
  - Releases the active uniqueness / aggregation key so a new identical occurrence creates a new active Signal.
  - Concurrent with linked Action Plan create: Signal row locks in UUID order; archive locks CREATED_FROM sibling set (or self); AP create locks the source Signal only. Winner: AP → `in_progress` and archive refused, or archive → `archived` and AP refused; never `in_progress → archived`.
  - No restore in this version.

Validated target transition rules:
- Signal is created as `open`.
- A candidate Signal may aggregate only into an active Signal (`open`, `in_progress`, `interesting`).
- Aggregation must not target `resolved`, `canceled`, or `archived` Signals.
- A recurring issue after a closed Signal should create a new Signal rather than silently reuse the closed one.
- `archived` is out of the active Signal feed by default.

Validated in current code:
- Manual cancel and resolve from `open` only (`MANUAL_CANCEL_RESOLVE_SIGNAL_STATUSES`). `in_progress` must be resolved via Action Plans.
- Mark interesting from `open` only (Owner/Director/Manager with scope or unassigned triage; Staff denied).
- Archive from `interesting` only (same RBAC shape as pin / mark interesting; Staff denied). Archived Signals are not exposed (feed/detail/filtre); `merged_into` stays null; media cleanup matches cancel/resolve.
- Linked Action Plan creation from an active Signal (`open`, `in_progress`, or `interesting`) transitions `open`/`interesting` → `in_progress` and unpins if pinned; creation is rejected when the Signal is terminal (`resolved`, `canceled`, `archived`). When `source_signal_id` is set: if the Signal has a `responsible_business_unit_id`, `pilot_business_unit_id` must equal it; if responsible is null but an `activity_subject` is present, the pilot must equal the subject's owning BusinessUnit.
- Default Signal Feed includes `open`, `in_progress`, `interesting`, `resolved`, and `canceled`; `archived` is excluded.
- Feed sorting places operational active Signals (`open`/`in_progress`) first, then `interesting`, then `resolved`, then `canceled` (`status_group_rank` before pin). UI section « Intéressants » is dynamic and collapsed by default.
- `resolved`, `canceled`, and `interesting` Signals are readable on detail (action hints accordingly); `canceled` detail requires pole visibility for Manager/Staff; `archived` detail returns 404 (not exposed).
- Resolve transition forces unpin (clears pin fields). Mark interesting also forces unpin. User archive forces unpin defensively.
- Automatic transition from active states to `resolved` when all linked Action Plan executions are terminal and at least one is `done` (triggered by mark-done or validate via `sync_signal_after_execution_change`).

Not validated yet:
- exact reopen behavior
- restore of archived Signals
- exact stored representation of confidence scores
- exact recurrence/count field name

## 7. Permissions

- Signal visibility is establishment-scoped and backend-authorized.
- RBAC baseline defines establishment membership, role, and BusinessUnit scope authority. Signal command helpers exist for implemented APIs.
- Owner and Director target behavior: broad establishment-level Signal visibility and actionability, subject to RBAC.
- Manager target behavior: actionability requires RBAC (`MembershipScope` BusinessUnit coverage) and Signal BU classification.
- Ma vue (`view_mode=personal`) filters by **`MembershipScope`** for Manager/Staff (affected **or** responsible BusinessUnit in scope). Owner/Director: all feed-visible establishment Signals.
- Vue générale (`view_mode=general`) shows all feed-visible establishment Signals for Owner/Director; for Manager/Staff, active and `resolved` Signals are establishment-wide while `canceled` Signals follow pole visibility on the feed list.
- Detail access (implemented): any member who passes `can_view_signal_feed` may read **feed-visible** Signal detail by ID, including deep-links to Signals outside their Ma vue BU scope. Pin, mark interesting, archive, cancel, resolve, and create-action commands remain scope-aware for Manager (see [`rbac_permissions_domain.md`](rbac_permissions_domain.md) §7).
- Visibility does not imply actionability.
- Resolving Signals, canceling Signals, pinning, marking interesting, and archiving require backend command authorization (implemented). Creating Actions from Signals remains a separate workflow.
- **Cancel and resolve** (implemented): Owner and Director may act on any `open` Signal in the establishment; Manager may act only when `MembershipScope` covers the Signal taxonomy (or unassigned triage); **Staff are denied** cancel and resolve. Manual cancel/resolve on `in_progress` is refused (permission hints false; API returns business error).
- **Resolution request workflow** (implemented): Staff may request review from eligible Managers; Managers with current responsible-pole coverage may request review from eligible Directors. A pending request blocks **the requester Manager only** from resolving directly until they cancel the request or a reviewer decides; another authorized resolver may still resolve and auto-cancel the request.
- **Mark interesting** (implemented): same RBAC shape as pin — Owner/Director/Manager (scope or unassigned triage) on `open` only; **Staff denied**. Staff may still view `interesting` Signals in personal and general feed.
- **Archive** (implemented): same RBAC shape as pin — Owner/Director/Manager (scope or unassigned triage) on `interesting` only; **Staff denied**. Archived Signals are not product-exposed.
- Notifications and realtime events do not grant Signal access.
- Raw Observation text is not exposed through Signal permissions.

API responses expose `permission_hints` (`can_pin`, `can_mark_interesting`, `can_archive`, `can_cancel`, `can_resolve`, `can_create_linked_action_plan`, `can_qualify_routing`, `can_request_resolution`, `can_approve_resolution_request`, `can_reject_resolution_request`, `can_cancel_resolution_request`) for UI display; backend permission checks on command endpoints remain authoritative. `can_create_linked_action_plan` is signal-scoped: it indicates whether the current membership may create a linked Action Plan from this Signal. Action Plan create enforcement remains the final authority.

## 8. Events

### Current-state actor fields (on `Signal`)

Detail API exposes (not feed):

- `marked_interesting_by_membership_id` / `marked_interesting_at`
- `resolved_by_membership_id` / `resolved_at` / `resolution_origin` (`manual` | `resolution_request` | `action_plan`)
- `canceled_by_membership_id` / `canceled_at`
- `archived_by_membership_id` / `archived_at`

On `resolved → in_progress` (execution reopen), `resolved_*` and `resolution_origin` are cleared. Prior resolution remains in the journal.

Action-plan auto-resolve: `resolved_by_membership` is null and `resolution_origin=action_plan`.

On `in_progress → open` (all linked executions canceled), the journal records `signal.moved_open`. Actor is the cancel actor when cancel is manual; otherwise null. No event when the Signal is already `open` or remains `in_progress`.

### Append-only journal (`SignalLifecycleEvent`)

Write-only internal journal (no timeline/list API in this ticket). Inserted in the **same transaction** as a valid Signal lifecycle transition that **effectively changes** status.

Invariants:

- insert-only from business services (never update/delete journal rows)
- no event on invalid transition or no-op / idempotent sync replay
- shared timestamp: Signal current `*_at` field and `occurred_at` use the same `now`
- `metadata_safe` allowlists structured ids/statuses/origins only (no Observation text / user free text)
- Resolution-request create/reject/cancel that leave Signal `open` do **not** write journal rows; approve that resolves writes `signal.resolved` with `resolution_origin=resolution_request`

Event types:

- `signal.marked_interesting`
- `signal.archived`
- `signal.resolved`
- `signal.canceled`
- `signal.moved_in_progress`
- `signal.moved_open`

Realtime/notification side effects remain after-commit hubs and are not this journal.

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented in `apps/api/schema.yml` (establishment-scoped under `/api/v1/establishments/{establishment_id}/`):
- `GET signal-feed/` — feed-visible Signals (`view_mode=personal|general`); optional filters `statuses` (open, in_progress, resolved), `business_unit_ids` (UUID, comma-separated), `activity_subject_ids` (comma-separated), `needs_qualification` (true → active Signals with `responsible_business_unit_id IS NULL`); response includes `applied_filters`. Legacy query param `business_unit_keys` is rejected.
- `GET signals/{signal_id}/` — active Signal detail
- `POST signals/{signal_id}/pin/`
- `POST signals/{signal_id}/unpin/`
- `POST signals/{signal_id}/cancel/` — **no mandatory body**; sets status `canceled`
- `POST signals/{signal_id}/resolve/` — **no mandatory body**; sets status `resolved`
- `POST signals/{signal_id}/mark-interesting/` — **no mandatory body**; sets status `interesting`
- `POST signals/{signal_id}/archive/` — **no mandatory body**; `interesting` → `archived` (not exposed afterward)
- `POST signals/{signal_id}/resolution-requests/` — create a pending resolution request; Signal remains `open`
- `POST signals/{signal_id}/resolution-requests/{request_id}/approve/` — approve request and resolve Signal atomically
- `POST signals/{signal_id}/resolution-requests/{request_id}/reject/` — reject request; Signal remains `open`
- `POST signals/{signal_id}/resolution-requests/{request_id}/cancel/` — requester cancels pending request; Signal remains `open`

Not implemented in current schema:
- fetch Signal timeline or `SignalLifecycleEvent` list
- restore archived Signal

Action Plan creation from a Signal is via `POST .../action-plans/` with optional `signal_id` (linked plan), not a nested Signal sub-resource.

Do not treat any Signal route as implemented until it exists in `apps/api/schema.yml`.

## 10. Frontend Expectations

- Signal Feed must show structured Signal cards, not raw Observations.
- Signal detail must show only safe structured summary and authorized related context.
- Frontend must not display raw Observation text in Signal feed, detail, notifications, or realtime-triggered UI.
- Frontend may render backend-provided permission hints, but backend responses remain the authority for allowed commands.
- Frontend must treat Signal lifecycle changes as backend commands, not local UI rules.
- Frontend must render backend BU/AS classification as provided and must not infer alternate primary categorization.
- Realtime remains invalidation and refetch only; it does not carry business truth.
- Notifications and realtime payloads must not be treated as complete Signal state.
- Pinned UI must respect backend rules.
- TanStack Query owns server state for implemented Signal APIs.
- Frontend must use generated OpenAPI clients only for routes present in `apps/api/schema.yml`.

## 11. AI Agent Notes

- Inspect current Signal code before claiming models, services, selectors, events, commands, or endpoints exist.
- Inspect `apps/api/schema.yml` before listing any Signal API as current.
- Inspect `observation_domain.md` before changing raw input or linked Observation assumptions.
- Inspect `ai_domain.md` before changing candidate Signal or aggregation assumptions.
- Inspect [`decisions/action_plan.md`](../decisions/action_plan.md) before changing Action Plan creation or linked-execution assumptions.
- Inspect Feed documentation before changing Signal Feed sorting, filtering, pagination, or detail query behavior.
- Inspect `rbac_permissions_domain.md` before changing visibility or actionability.
- Inspect `security_rgpd_domain.md` before changing raw-text visibility, logging, notification, or realtime boundaries.
- Inspect `upload_media_domain.md` before changing linked media assumptions.
- Do not make Signal a raw Observation, an Action, or a generic ticket.
- Do not introduce a single authoritative `primary_domain`-style fallback for Signal routing, visibility, or actionability in MVP.
- Do not add direct manual Signal creation unless it is separately validated.
- Do not expose raw Observation text in Signal detail, feed, notifications, realtime payloads, or normal technical logs.
- Do not let AI decide urgency or create Actions.
- Do not implement frontend-only Signal lifecycle transitions.
- When Signal APIs are added later, update backend authorization, OpenAPI, generated clients, tests, and this document together.

## 12. Acceptance test matrix (implemented Signal surface)

### Signal creation / validation

| Scenario | Expected behavior |
| --- | --- |
| Valid BU/AS classification same establishment | Signal persisted with FKs |
| BU/AS classification from another establishment | Rejected |
| Optional unit from same establishment | Allowed; orthogonal to categorization |
| Observation with one problem | One CandidateSignal → one Signal after validation |
| Observation with N distinct problems | N CandidateSignals → N Signals (never multi-classification on one row) |

### Categorization invariants

| Scenario | Expected behavior |
| --- | --- |
| Signal row | Exactly one primary BU/AS classification via FKs |
| Legacy `detected_domains[]` shape | Not accepted in MVP |

### Lifecycle (active feed eligibility)

Aligned with `FEED_SIGNAL_STATUSES` in `apps/api/houston/signals/constants.py`.

| Status | In active Signal Feed (default) |
| --- | --- |
| `open`, `in_progress`, `resolved`, `canceled` | Yes |
| `archived` | No |

### Aggregation (when pipeline exists)

| Scenario | Expected behavior |
| --- | --- |
| Candidate `routing_status=resolved` matches active resolved Signal (same aggregation key incl. `issue_focus`) | Aggregate into existing Signal |
| Candidate same taxonomy but different `issue_focus` | Create new Signal |
| Candidate `routing_status=unassigned` (even identical keys) | Always create a new Signal (no auto-aggregation) |
| Candidate matches resolved lifecycle-closed Signal | Create new Signal |
| Aggregation target closed/archived | Rejected |

Tests must use BU/AS runtime taxonomy keys from onboarding, not legacy flat domain keys.
