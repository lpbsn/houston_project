# Signal Domain

Status: authoritative
Last reviewed: 2026-06-03
Implementation status: partial (feed, detail, pin, urgency, cancel, resolve implemented; Phase 5 core Action side effects implemented; archive, timeline not implemented)

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
- Routing through **BusinessUnit / ActivitySubject classification** per Signal: `affected_business_unit`, `responsible_business_unit`, `activity_subject` (optional `operational_unit` for structured location; `location_text` for free text).
- Human-controlled urgency.
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
- **One primary v3 classification per Signal** (`affected_business_unit`, `responsible_business_unit`, `activity_subject`). Legacy Module/Domain/Subject FKs are removed (Lot 6).
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
  - v3 classification: affected/responsible BusinessUnit + ActivitySubject FKs on the Signal row.
  - Optional operational unit for physical location only.

- ~~`SignalDomain` / `detected_domains`~~ — removed from MVP; classification is BU/AS only.
- `SignalUrgency`
  - Human-controlled urgency state for the supervised situation.
  - Separate from status.

- `SignalAggregation`
  - Backend decision that a candidate Signal belongs to an existing active Signal instead of creating a new one.
  - Exact stored recurrence/count shape is not validated yet.

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

- `in_progress`
  - Active situation with linked execution work underway.
  - Exact automatic transition rule is not validated in code yet, but current product direction ties this state to Action activity.

- `resolved`
  - Situation considered operationally handled.
  - Manual resolution is available via backend command `POST .../signals/{id}/resolve/` from active statuses (`open`, `in_progress`).
  - Automatic resolution when all linked Actions are terminal is implemented in Phase 5 (Action services).
- `POST .../resolve/` returns **409** `business_conflict` when linked Actions are still active.

- `canceled`
  - Situation intentionally closed as no longer relevant to pursue.
  - **MVP cancellation does not require a category, reason, or justification payload.** The command is `POST .../signals/{id}/cancel/` with no mandatory request body.

- `archived`
  - Historical state outside the active operational feed by default.
  - Exact archival delay or archival trigger is not validated yet.

Validated target transition rules:
- Signal is created as `open`.
- A candidate Signal may aggregate only into an active Signal.
- Aggregation must not target `resolved`, `canceled`, or `archived` Signals.
- A recurring issue after a closed Signal should create a new Signal rather than silently reuse the closed one.
- `archived` is out of the active Signal feed by default.

Validated in current code:
- Manual cancel and resolve from `open` or `in_progress` only (active statuses).
- Default Signal Feed includes `open`, `in_progress`, and `resolved`; `canceled` and `archived` are excluded.
- Feed sorting places all active Signals before any `resolved` Signal (`status_group_rank` before pin/urgency).
- `resolved` Signals are readable on detail (read-only via `permission_hints`); `canceled` and `archived` are not exposed on detail by default.
- Resolve transition forces unpin (clears pin fields) and resets `high` urgency to `normal` (model has `normal` / `high` only).

Not validated yet:
- exact automatic transition from `open` to `in_progress`
- exact automatic transition from active states to `resolved` via Action completion
- exact reopen behavior
- exact archival timing
- exact stored representation of confidence scores
- exact recurrence/count field name

## 7. Permissions

- Signal visibility is establishment-scoped and backend-authorized.
- RBAC baseline defines establishment membership, role, and BusinessUnit scope authority. Signal command helpers exist for implemented APIs.
- Owner and Director target behavior: broad establishment-level Signal visibility and actionability, subject to RBAC.
- Manager target behavior: actionability requires RBAC (`MembershipScope` BusinessUnit coverage) and Signal BU classification.
- Ma vue (`view_mode=personal`) filters by **`MembershipScope`** (Owner/Director: all feed-visible establishment Signals).
- Vue générale (`view_mode=general`) shows all feed-visible establishment Signals without subscription filter.
- Visibility does not imply actionability.
- Resolving Signals, canceling Signals, changing urgency, and pinning require backend command authorization (implemented). Creating Actions from Signals remains a separate workflow.
- **Cancel and resolve** (implemented): Owner and Director may act on any active Signal in the establishment; Manager may act only when `MembershipScope` covers the Signal taxonomy; **Staff are denied** cancel and resolve.
- Notifications and realtime events do not grant Signal access.
- Raw Observation text is not exposed through Signal permissions.

API responses expose `permission_hints` (`can_pin`, `can_set_urgency`, `can_cancel`, `can_resolve`, `can_create_action`) for UI display; backend permission checks on command endpoints remain authoritative. `can_create_action` is signal-scoped: it indicates whether the current membership may create a linked Action from this Signal (aligned with `can_create_linked_action`). `POST /actions/` enforcement remains the final authority.

## 8. Events

No Signal-specific event contract is implemented in current code or confirmed in `apps/api/schema.yml`.

Candidate events only:
- `SignalCreated`
- `SignalAggregated`
- `SignalStatusChanged`
- `SignalResolved`
- `SignalCanceled`
- `SignalArchived`
- `SignalUrgencyChanged`
- `SignalPinned`
- `SignalUnpinned`
- `SignalActionCreated`
- `SignalCommentAdded`

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented in `apps/api/schema.yml` (establishment-scoped under `/api/v1/establishments/{establishment_id}/`):
- `GET signal-feed/` — feed-visible Signals (`view_mode=personal|general`); optional filters `statuses` (open, in_progress, resolved), `business_unit_keys`, `activity_subject_ids` (comma-separated); response includes `applied_filters`
- `GET signals/{signal_id}/` — active Signal detail
- `POST signals/{signal_id}/pin/`
- `POST signals/{signal_id}/unpin/`
- `PATCH signals/{signal_id}/urgency/` — body `{ "urgency": "normal" | "high" }`
- `POST signals/{signal_id}/cancel/` — **no mandatory body**; sets status `canceled`
- `POST signals/{signal_id}/resolve/` — **no mandatory body**; sets status `resolved`

Not implemented in current schema:
- archive Signal
- fetch Signal timeline or events

Action creation is via `POST .../actions/` with optional `signal` (Phase 5 core implemented), not a nested Signal sub-resource.

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
- Urgency and pinned UI must respect backend rules.
- TanStack Query owns server state for implemented Signal APIs.
- Frontend must use generated OpenAPI clients only for routes present in `apps/api/schema.yml`.

## 11. AI Agent Notes

- Inspect current Signal code before claiming models, services, selectors, events, commands, or endpoints exist.
- Inspect `apps/api/schema.yml` before listing any Signal API as current.
- Inspect `observation_domain.md` before changing raw input or linked Observation assumptions.
- Inspect `ai_domain.md` before changing candidate Signal or aggregation assumptions.
- Inspect the Action domain source of truth before changing Action creation or resolution assumptions.
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

| Status | In active Signal Feed |
| --- | --- |
| `open`, `in_progress` | Yes |
| `resolved`, `canceled`, `archived` | No (default) |

### Aggregation (when pipeline exists)

| Scenario | Expected behavior |
| --- | --- |
| Candidate matches active Signal | Aggregate into existing Signal |
| Candidate matches resolved Signal | Create new Signal |
| Aggregation target closed/archived | Rejected |

Tests must use BU/AS runtime taxonomy keys from onboarding, not legacy flat domain keys.
