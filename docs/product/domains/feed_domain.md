# Feed Domain

Status: authoritative
Implementation status: Signal Feed + Action Plan Execution Feed live.

## 1. Purpose

Feed is a backend-authorized **read projection** (not business truth): `SignalFeed` and `ExecutionFeed`, with filters, sort, pagination, and optional permission hints.

It does not own Signal or Action Plan lifecycle, Notification Center, realtime transport, RBAC policy, AI, or Observation persistence.

## 2. Scope

In: authorized list reads; safe items (no raw Observation text, no signed media URLs); `needs_qualification` on Signal Feed; cursor pagination; realtime invalidation/refetch only.

Current HTTP: `GET signal-feed/` and `GET action-plan-execution-feed/` with required `view_mode=personal|general`. Envelope `{ items, next_cursor, has_more }` (Signal Feed may include `applied_filters`). Execution items: `item_type: "action_plan_execution"`. Lazy materialization on Execution Feed read: [`action_plan_domain.md`](action_plan_domain.md) (3-day horizon, 30 min stale guard). Execution Feed `+` (Plan ponctuel / Catalogue) when `can_create_action_plan` — same domain.

Out: feed as truth; lifecycle from feed state; frontend-only auth; saved views; drag-and-drop mutation; AI ranking; public/cross-tenant feeds.

## 3. Invariants

Backend authorization before any item. Establishment-scoped. Frontend tabs do not grant visibility. Hints are UX only. Commands go to owning domains. Realtime refetches; it does not carry full feed state.

## 4. Signal Feed vs Execution Feed (personal)

Signal Ma vue / générale and command vs list rules: [`signal_domain.md`](signal_domain.md) §5 and [`rbac_permissions_domain.md`](rbac_permissions_domain.md). Default statuses: `FEED_SIGNAL_STATUSES`. Subscriptions deferred: [`feed_subscription_domain.md`](feed_subscription_domain.md).

**Execution Feed**

| Mode | Who sees what |
| --- | --- |
| `personal` | Owner/Director: all feed-visible establishment executions. Manager/Staff: assignee, Manager scope via execution teams, or **mention on an execution comment**. |
| `general` | Owner/Director: all. Manager: scoped BUs + own assignments. Staff: own assignments only. |

Mention grants read + thread participation (`action_plan_execution_readable_to_membership`), not operational commands.

Cursor items: `EXECUTION_FEED_CURSOR_STATUSES` (`scheduled` is preview-only via `scheduled_items`). `visible_from` gates cursor items and Planifiées. Terminal `done` / `canceled` stay in the list. Overdue `end_at` does not drop items.

Sort (backend): personal pins first (`ActionPlanExecutionFeedPin`, per membership — not Signal’s establishment pin), then `pending_validation` → `in_progress` → `done` → `canceled`, then overdue/upcoming/`end_at` rules. UI: pinned block unlabeled; Terminés / Annulés collapsed. Cursor freezes `as_of`. Pin HTTP: `POST …/action-plan-executions/{id}/pin/` and `…/unpin/`.

Realtime: `action_plan_execution.*` — [`realtime_domain.md`](realtime_domain.md).

## 5. HTTP

[`apps/api/schema.yml`](../../../apps/api/schema.yml). Pagination: [`api_pagination_standard.md`](../../engineering/api_pagination_standard.md). Detail routes belong to owning domains.

## 6. Frontend / agent notes

Signal Feed is a scannable structured stream. Execution Feed is grouped by state (Kanban-like visibility, not drag-and-drop authority). Query key: `['action-plans', 'action-plan-execution-feed', establishmentId, viewMode]`. Component: `action-plan-execution-feed-card.tsx`.

Inspect selectors and `schema.yml` before changing item rules. Execution inclusion and `+` menu: [`action_plan_domain.md`](action_plan_domain.md) and `action_plans/selectors.py`.
