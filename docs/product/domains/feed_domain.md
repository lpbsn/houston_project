# Feed Domain

Status: authoritative
Last reviewed: 2026-09-29
Implementation status: operational Signal and Action Plan Execution feeds, pins, bounded reading, and History live. The Feed contracts & pagination chantier (Lots 0–7) and its final hardening (PR1–PR5D) are closed. Measured PR5 query rewrites were not applied.

## 1. Purpose

Feed is a backend-authorized **read projection**, not business truth. It owns authorized collection membership, filtering, ordering, counts, cursor pagination, and safe list representations for operational Signal and Execution feeds. History is the consultative projection of currently terminal Signals and executions.

It does not own lifecycle transitions, pins writes, Notification Center, realtime transport, RBAC policy, AI, or Observation persistence. Domain services perform mutations; feed and history selectors project the resulting persisted state.

## 2. Scope

In: authorized establishment and explicit Cross reads; safe items (no raw Observation text or signed media URLs); operational P/L collections; counts and scheduled summaries; History; cursor pagination; client refresh/reconciliation.

Current HTTP families are `signal-feed/`, `action-plan-execution-feed/`, `history/signals/`, and `history/executions/`, each with establishment routes and explicit Cross routes. Dedicated Cross pin continuation routes are `cross/signal-feed-pins/` and `cross/action-plan-execution-feed-pins/`. Exact request and response shapes: [`apps/api/schema.yml`](../../../apps/api/schema.yml).

Out: feed as truth; lifecycle from feed state; frontend-only authorization; saved views; drag-and-drop mutation; AI ranking; public/cross-tenant feeds; a universal feed engine.

## 3. Invariants

Backend authorization applies before filtering, exclusion, count, or LIMIT. Frontend tabs and permission hints never grant visibility or commands. Cross is the authorized union of resolved management memberships and remains read-only for this surface.

For a fixed authorized scope and filter, P is the eligible pinned collection and L the eligible non-pinned collection. They are disjoint: all matching P rows are excluded from L before pagination, including Cross pins not yet loaded in the preview. Counts describe their documented complete authorized collection, not loaded cards.

L pages default to 25 and accept at most 50. `has_more` uses `limit + 1`, never a total. Establishment first pages and Signal Cross bootstrap responses carry P with their metadata; Execution Cross fetches its P preview separately. L continuations carry only `items`, `next_cursor`, and `has_more`. P has a separate continuation where the domain cap does not bound the authorized Cross collection.

## 4. Signal Feed

Operational statuses are `open`, `in_progress`, and `interesting`; `resolved` and `canceled` leave the feed immediately and remain accessible through History and authorized detail.

Status selection is `all`, `open`, `in_progress`, or `interesting`. L is one global cursor collection, not independently paginated sections. Under `all`, ordering is `open` → `in_progress` → `interesting`, then `last_activity_at DESC`, `created_at DESC`, `id DESC`. Counts for the three statuses describe L and ignore the selected status while retaining the other active filters; `pinned` describes filtered P.

Signal P is collective:

- eligible statuses: `open` and `interesting`;
- cap: five per establishment across filters, views, and devices;
- order: `pinned_at DESC`, `id DESC`;
- `open → interesting` keeps the pin; `in_progress`, `resolved`, and `canceled` remove it atomically;

The pin zone follows the active filter and is absent under `in_progress`. Establishment first pages can return the complete capped P. Cross unions all authorized establishment pins, has no extra global cap, returns an initial bounded page, and continues through the dedicated pins endpoint. Signal services own pin commands, cap enforcement, explicit replacement, and lifecycle cleanup; see [`signal_domain.md`](signal_domain.md) §3.

Signal Ma vue / générale and command rules: [`signal_domain.md`](signal_domain.md) §5 and [`rbac_permissions_domain.md`](rbac_permissions_domain.md). Feed subscriptions remain deferred: [`feed_subscription_domain.md`](feed_subscription_domain.md).

## 5. Execution Feed

| Mode | Who sees what |
| --- | --- |
| `personal` | Owner/Director: all feed-visible establishment executions. Manager/Staff: assignee, Manager scope via execution teams, or **mention on an execution comment**. |
| `general` | Owner/Director: all. Manager: scoped BUs + own assignments. Staff: own assignments only. |

Mention grants read + thread participation (`action_plan_execution_readable_to_membership`), not operational commands.

L contains only operational `pending_validation` and `in_progress` executions. Selection is `all`, `pending_validation`, `overdue`, or `in_progress`. `pending_validation` takes priority; overdue means `in_progress` with `end_at < as_of`; the remaining in-progress items are split between dated and undated ordering.

Ordering is:

- À valider: `marked_done_at ASC NULLS LAST`, `id ASC`;
- En retard and dated En cours: `end_at ASC`, then `last_activity_at DESC`, `created_at DESC`, `id DESC`;
- undated En cours: `last_activity_at DESC`, `created_at DESC`, `id DESC`.

The first cursor freezes `as_of` for overdue classification throughout that traversal. `as_of` stays inside the opaque cursor.

Execution P is personal to membership and establishment, capped at three, ordered `pinned_at ASC`, `id ASC`, and filtered by category. Category counts include P+L; `pinned` is a subtotal and must not be added to workflow totals. Action Plan services own cap enforcement, explicit replacement, and terminal cleanup; see [`action_plan_domain.md`](action_plan_domain.md) §4.

Cross returns a three-pin preview and loads the rest progressively through the dedicated pins endpoint. It does not add a global cap and exposes no pin mutation. `scheduled` is outside P/L and summarized on page 1 as `{ count, next: { id, start_at, title } | null }`. The read path may perform the bounded lazy materialization described in [`action_plan_domain.md`](action_plan_domain.md).

## 6. Cursors, refresh, realtime, and memory

Signal, Execution, and History cursors are opaque versioned server tokens. They bind collection, sort tuple, filters/view, establishment or Cross scope, and an authorization fingerprint derived from live memberships, roles, status, and BusinessUnit scopes. Execution L also binds `as_of`. A mismatch returns HTTP 400 `cursor_context_mismatch`; clients discard the traversal and restart at page 1.

Operational feeds auto-load near the end with one continuation in flight. Empty-plus-`has_more` or a non-advancing cursor stalls locally and exposes retry instead of looping. Mobile web and Capacitor support pull-to-refresh at the top. Desktop Execution feeds and establishment Signal feeds expose an accessible refresh button. Desktop Signal Cross currently has no always-visible refresh button; it can refresh from the updates banner when present or from retry controls after failure. Refresh keeps scope/filter, starts a new generation at the top, and replaces P, L, counts, summaries, and ordering. A failed refresh preserves displayed data.

Realtime carries invalidation hints, not feed state. While the user reads away from the top, reorder-only changes are deferred behind “Mises à jour disponibles”. Items known to have become terminal are removed from the hydrated collection immediately; authorized refetch remains the source of truth. Reconnect force-invalidates establishment and Cross feeds plus upcoming execution queries.

Operational feed memory is bounded by [`feed-reading-window.ts`](../../../apps/web/src/lib/feed-reading-window.ts): retained page 1, at most two focused continuation slots, one replaceable cursor behind, and ids only for hydrated slots. Return-from-detail state is O(1) (anchor, neighbor, resume cursor, authorization fingerprint). Traversal depth is not capped: evicted regions are refetched on demand.

## 7. History

History is available from `/general/history` with Observations/Signals and Executions views. It inherits the current establishment or explicit Cross terrain scope. Without terrain scope, it uses the active establishment when present, otherwise asks for a local establishment selection; it never infers Cross.

Periods `7`, `30`, and `90` are Europe/Paris civil days ending today, inclusive. Custom ranges are `[from 00:00, day-after-to 00:00)` in Europe/Paris; `all` is unbounded. Default period is 30 days. Status and `view_mode` remain cursor context.

Terminal ordering is `terminal_at DESC`, `id DESC`; the client groups by Paris civil day across page boundaries. Terminal date source is:

1. Signals: `resolved_at` or `canceled_at`; executions: `canceled_at`, `validated_at`, or `marked_done_at` for done executions not requiring validation;
2. otherwise the latest reliable matching resolved/canceled/validated/marked-done lifecycle event;
3. otherwise unknown.

Each item exposes the terminal-date source plus the stored termination origin and actor when demonstrable; absent actors do not imply an automatic origin. Undated terminals are included at the end of `period=all` under “Date inconnue”. Bounded periods exclude them from items but first-page `undated_count` makes the exclusion explicit. History is current-terminal-state consultation, not an exhaustive lifecycle timeline. Authorized detail access remains independent from operational-feed eligibility.

## 8. HTTP and related owners

OpenAPI: [`apps/api/schema.yml`](../../../apps/api/schema.yml). Shared pagination rules: [`api_pagination_standard.md`](../../engineering/api_pagination_standard.md). Lifecycle and detail routes belong to [`signal_domain.md`](signal_domain.md) and [`action_plan_domain.md`](action_plan_domain.md). Realtime delivery: [`realtime_domain.md`](realtime_domain.md).

Inspect selectors, tests, and `schema.yml` before changing collection membership, ordering, metadata, or cursor context. A compatible JSON shape can still be a breaking feed contract change.
