# Signal Domain

Status: authoritative
Implementation status: partial (feed, detail, pin, mark interesting, cancel, resolve, qualify merge, pipeline **v6** aggregation, write-side `SignalLifecycleEvent` journal; **no** user-facing timeline API)

## 1. Purpose

Signal is Houston's structured operational situation — between Observation and Action Plan. It is not the raw report and not the execution.

Owns: structured situation identity, lifecycle meaning, BU/AS routing, aggregation after backend-validated pipeline output.

Does not own: Observation intake, AI contracts, Action Plan lifecycle, Feed query/sort/pagination, notification delivery, realtime transport, RBAC internals.

## 2. Scope

In: create/aggregate from validated CandidateSignals; statuses `open`, `in_progress`, `interesting`, `resolved`, `canceled`; one primary BU/AS classification per Signal (`affected_business_unit`, `responsible_business_unit`, `activity_subject`; optional `operational_unit`, `location_text`, **`issue_focus`**); safe summaries; establishment-scoped commands.

Out: manual Signal create; free-floating Signal; treating Signal as Observation, Action, or ticket; AI urgency or AI-created plans; frontend-owned transitions; public/cross-tenant links; raw Observation text on product surfaces; frontend merge; image AI.

## 3. Core invariants

- Only backend-validated proposals create or aggregate a Signal. Observation remains a separate row even when aggregated.
- Raw Observation text must not appear on Signal surfaces, notifications, realtime, or durable frontend state.
- Lifecycle is backend-owned. Visibility does not imply actionability.
- **One** primary BU/AS classification per Signal. Multiple problems in one Observation → multiple CandidateSignals / Signals.
- Ma vue uses `MembershipScope` (Owner/Director: all active). Feed subscriptions are deferred — [`feed_subscription_domain.md`](feed_subscription_domain.md).
- Aggregation key (pipeline v6, `routing_status=resolved` only): `(affected_bu, responsible_bu, activity_subject, operational_unit | null, normalize(issue_focus))`. No LLM `aggregate_into_signal_id`. `unassigned` is never auto-aggregated. UI « Non classifié » = `responsible_business_unit_id IS NULL`.

## 4. Lifecycle

- `open` — default create. May carry a **SignalResolutionRequest** (`pending` / `approved` / `rejected` / `canceled`) without changing `Signal.status`. There is no `pending_validation` Signal status.
- `interesting` — `open → interesting` via `mark-interesting`. Not pinnable (always unpins). Cancel allowed; resolve not. Still an aggregation target. Linked Action Plan create → `in_progress`. No reverse to `open`.
- `in_progress` — linked Action Plan execution created from `open` or `interesting`. Manual cancel/resolve refused; resolution goes through Action Plans.
- `resolved` — manual `POST …/resolve/` from `open` only. Auto-resolve when linked executions are terminal with ≥1 `done` (`sync_signal_after_execution_change`; allows `open` / `in_progress`). Manual resolve from `open` cancels blocking linked executions. Another resolver cancels a pending resolution request (`signal_resolved_elsewhere`).
- `canceled` — `POST …/cancel/` from `open` and `interesting`. **No** mandatory body / reason.

Aggregation only into active Signals (`open`, `in_progress`, `interesting`). Closed Signals are not reused for a later recurrence.

Qualify merge on aggregation-key collision absorbs observations then **hard-deletes** the source (retry → 404). Linked plan create from a terminal Signal is rejected. Pilot BU constraints when `source_signal_id` is set: see [`action_plan_domain.md`](action_plan_domain.md).

Default feed includes all `FEED_SIGNAL_STATUSES`. Sort: operational active (`open`/`in_progress`) first, then `interesting`, then `resolved`, then `canceled`. Resolve and mark interesting unpin.

Not a product API yet: reopen semantics as a Signal command; confidence / recurrence field names.

## 5. Permissions

Establishment-scoped. Owner/Director: broad. Manager: `MembershipScope` + classification (or unassigned triage). Staff: no cancel/resolve/mark-interesting.

- Ma vue (`personal`): Manager/Staff — affected **or** responsible BU in scope. Owner/Director — all feed-visible.
- Vue générale (`general`): Owner/Director all; Manager/Staff establishment-wide for active/`resolved`, pole visibility for `canceled` on the list.
- Detail: any member with `can_view_signal_feed` may read feed-visible detail by ID (including outside Ma vue). Commands stay scope-aware for Manager.

Resolution requests: Staff → eligible Managers; Managers with responsible-pole coverage → Directors. A pending request blocks **that requester Manager** from resolving directly.

`permission_hints` are UX only. `can_create_linked_action_plan` is signal-scoped; create enforcement stays in Action Plan.

## 6. Journal (write-side)

Detail (not feed) exposes actor fields: interesting / resolved / canceled (+ `resolution_origin`: `manual` | `resolution_request` | `action_plan`). Auto-resolve from Action Plan: `resolved_by_membership` null, `resolution_origin=action_plan`. `in_progress → open` (all linked executions canceled) writes `signal.moved_open`.

`SignalLifecycleEvent` is insert-only in the same transaction as an effective status change. No timeline/list API. `metadata_safe` allowlists ids/statuses/origins only. Resolution-request create/reject/cancel that leave `open` do not write rows; approve writes `signal.resolved`.

Event types: `signal.marked_interesting`, `signal.resolved`, `signal.canceled`, `signal.moved_in_progress`, `signal.moved_open`.

## 7. HTTP exceptions (not an OpenAPI copy)

Contract: [`apps/api/schema.yml`](../../../apps/api/schema.yml).

Keep these non-obvious query/response rules:

- `GET signal-feed/` — `view_mode=personal|general`; `needs_qualification=true` → active Signals with `responsible_business_unit_id IS NULL`; response may include `applied_filters`; **`business_unit_keys` is rejected**.
- No Signal timeline / `SignalLifecycleEvent` list endpoint.
- Linked Action Plan create is `POST …/action-plans/` with optional `signal_id`, not a nested Signal sub-resource.

## 8. Frontend / agent notes

Feed and detail show structured Signal cards, never raw Observation text. Hints are UX. Realtime is invalidation only.

Inspect Signal code and `schema.yml` before listing endpoints. Linked executions: [`action_plan_domain.md`](action_plan_domain.md). Feed sort/filter: [`feed_domain.md`](feed_domain.md). Visibility: [`rbac_permissions_domain.md`](rbac_permissions_domain.md).
