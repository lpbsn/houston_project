# Signal Domain

Status: authoritative
Last reviewed: 2026-05-29
Implementation status: not_started

## 1. Purpose

This domain defines Houston's structured operational situation boundary.

Signal owns:
- the structured operational situation created or enriched from backend-validated Observation pipeline output
- the business identity of the supervised situation shown in Signal Feed
- the Signal lifecycle and high-level state meaning
- routing and operational scope through validated Signal domains

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
- Routing through **one primary categorization** per Signal: `operational_module`, `operational_domain`, `operational_subject` (optional `operational_unit` for location).
- Human-controlled urgency.
- Candidate pinned-open behavior for important visible Signals.
- Safe Signal summaries for feed and detail surfaces.
- Relationship to linked Actions, contextual comments, safe timeline entries, and linked Observation media context without exposing raw Observation text.
- Establishment-scoped backend authorization for Signal visibility and commands.

This domain describes the validated MVP target behavior. Current code and `apps/api/schema.yml` still show Signal implementation as not started.

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
- **One primary categorization per Signal** (`operational_module`, `operational_domain`, `operational_subject`). Legacy `detected_domains[]` is obsolete.
- An Observation describing **multiple distinct problems** produces **multiple CandidateSignals** and, after validation, **multiple Signals** — never multiple categorizations on one Signal.
- Ma vue feed visibility uses `MembershipFeedSubscription` matching (see `feed_subscription_domain.md`). RBAC action uses `MembershipDomain` and role rules.
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
  - Single primary triplet: operational module, domain, and subject FKs on the Signal row.
  - Optional operational unit for physical location only.

- ~~`SignalDomain` / `detected_domains`~~ — **removed from MVP**; see `operational_taxonomy_domain.md`.
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
  - Exact manual and automatic resolution rules depend on Action lifecycle implementation and are not validated in code yet.

- `canceled`
  - Situation intentionally closed as no longer relevant to pursue.
  - Exact cancellation categories and reasons are not validated yet.

- `archived`
  - Historical state outside the active operational feed by default.
  - Exact archival delay or archival trigger is not validated yet.

Validated target transition rules:
- Signal is created as `open`.
- A candidate Signal may aggregate only into an active Signal.
- Aggregation must not target `resolved`, `canceled`, or `archived` Signals.
- A recurring issue after a closed Signal should create a new Signal rather than silently reuse the closed one.
- `archived` is out of the active Signal feed by default.

Not validated yet:
- exact automatic transition from `open` to `in_progress`
- exact automatic transition from active states to `resolved`
- exact reopen behavior
- exact archival timing
- exact stored representation of multi-domain confidence scores
- exact recurrence/count field name

## 7. Permissions

- Signal visibility is establishment-scoped and backend-authorized.
- RBAC baseline defines establishment membership, role, and operational-domain authority, but Signal-specific permission helpers remain candidate until Signal APIs/services exist.
- Owner and Director target behavior: broad establishment-level Signal visibility and actionability, subject to RBAC.
- Manager target behavior: actionability requires RBAC and `MembershipDomain` intersection with Signal's `operational_domain`.
- Ma vue (`view_mode=personal`) filters by `MembershipFeedSubscription`, not by `MembershipDomain`.
- Vue générale (`view_mode=general`) shows all active establishment Signals without subscription filter.
- Visibility does not imply actionability.
- Creating Actions from Signals, resolving Signals, canceling Signals, changing urgency, pinning, and editing Signal domains require backend command authorization when those workflows are implemented.
- Notifications and realtime events do not grant Signal access.
- Raw Observation text is not exposed through Signal permissions.

Exact per-command Signal permission rules remain candidate until Signal APIs and services exist in current code and in `apps/api/schema.yml`.

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
- `SignalDomainAdded`
- `SignalDomainRemoved`
- `SignalActionCreated`
- `SignalCommentAdded`

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Current schema confirmation:
- no Signal routes are confirmed today

Candidate API capabilities only:
- Signal Feed
- Signal detail
- resolve Signal
- cancel Signal
- pin Signal
- unpin Signal
- set Signal urgency
- add Signal domain
- remove Signal domain
- create Action from Signal
- fetch Signal timeline or events

Do not treat any Signal route as current API truth until it exists in `apps/api/schema.yml`.

## 10. Frontend Expectations

- Signal Feed must show structured Signal cards, not raw Observations.
- Signal detail must show only safe structured summary and authorized related context.
- Frontend must not display raw Observation text in Signal feed, detail, notifications, or realtime-triggered UI.
- Frontend may render backend-provided permission hints, but backend responses remain the authority for allowed commands.
- Frontend must treat Signal lifecycle changes as backend commands, not local UI rules.
- Frontend must not collapse multi-domain Signals into a single primary domain unless a backend-provided display rule later validates that behavior.
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
- Do not introduce a single authoritative `primary_domain` for Signal routing, visibility, or actionability in MVP.
- Do not add direct manual Signal creation unless it is separately validated.
- Do not expose raw Observation text in Signal detail, feed, notifications, realtime payloads, or normal technical logs.
- Do not let AI decide urgency or create Actions.
- Do not implement frontend-only Signal lifecycle transitions.
- When Signal APIs are added later, update backend authorization, OpenAPI, generated clients, tests, and this document together.

## 12. Future test scenarios (Phase 4 — documentation only)

Do **not** implement Signal model, services, fixtures, or tests before Phase 4. These scenarios guide implementation and acceptance.

### Signal creation / validation

| Scenario | Expected behavior |
| --- | --- |
| Valid triplet (module, domain, subject) same establishment | Signal persisted with FKs |
| Module/domain/subject from another establishment | Rejected |
| Optional unit from same establishment | Allowed; orthogonal to categorization |
| Observation with one problem | One CandidateSignal → one Signal after validation |
| Observation with N distinct problems | N CandidateSignals → N Signals (never multi-triplet on one row) |

### Categorization invariants

| Scenario | Expected behavior |
| --- | --- |
| Signal row | Exactly one primary triplet via FKs |
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

Tests must use runtime taxonomy keys from onboarding (e.g. `hotel__hebergement__proprete_des_chambres`), not legacy flat domain keys.
