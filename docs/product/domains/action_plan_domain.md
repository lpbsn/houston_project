# Action Plan Domain

Status: authoritative
Implementation status: catalog, executions, schedules, planning, lazy materialization, Signal sync; Execution Feed read is in [`feed_domain.md`](feed_domain.md)

## 1. Purpose

Action Plan is Houston's **write** surface for operational work: catalog templates, scheduled and ad-hoc executions, task progress, and validation. It sits after Signal and before Feed update.

Owns: catalog identity and reuse, execution lifecycle, schedules and occurrence materialization, planning submission writes, linked-Signal side effects (`source_signal_id`).

Does not own: Signal lifecycle meaning (except the sync hooks below), Execution Feed query/sort/pagination, comments, notifications delivery, realtime transport, RBAC internals, Observation intake.

## 2. Scope

In: reusable catalog (`is_reusable`, `catalog_status` `active` / `inactive`); one-shot plans; executions; schedules (`active` / `inactive`); tasks (max 10); assignees / execution teams; planning engine writes.

Out: feed as business truth; frontend-owned transitions; treating catalog as an execution; treating comments as lifecycle; public/cross-tenant plans.

HTTP: [`apps/api/schema.yml`](../../../apps/api/schema.yml). Execution list reads: [`feed_domain.md`](feed_domain.md).

## 3. Ownership

| Concern | Owner |
| --- | --- |
| Catalog template | `ActionPlan` — `houston/action_plans/services.py`, `template_deletion_*` |
| Execution write / lifecycle | `ActionPlanExecution` — `services.py`, `execution_update.py`, `lifecycle_promotion.py` |
| Schedule + occurrences | `ActionPlanSchedule` — `schedule_services.py`, `materialization.py` |
| Planning submission | `planning_services.py` |
| Execution Feed read | selectors / `execution_feed.py` — documented in Feed, not here |

`source_signal_id` lives on the **execution**, not the catalog row.

## 4. Execution lifecycle

Statuses: `scheduled` → `in_progress` → `pending_validation` → `done`, or `canceled`.

- `scheduled` — materialized or planned ahead of `start_at`. Beat / tick promotes to `in_progress` when due. Preview on the feed via `scheduled_items`; not a cursor item.
- `in_progress` — operational work. Mark done: if `requires_validation`, go to `pending_validation`; else `done`.
- `pending_validation` — validator (`can_validate_action` + pilot-pole management or Owner/Director) validates → `done`, or reopens → `in_progress`.
- `done` — **terminal**. No reopen from `done`.
- `canceled` — from `scheduled`, `in_progress`, or `pending_validation`. Future schedule occurrences may be reactivated by schedule sync (`cancel_origin=schedule_sync`); that is not a general product reopen.

Tasks: `pending` / `done` / `skipped` / `observation_created`. Task observation handoff is an execution-task command, not a public Observation create extension — [`observation_domain.md`](observation_domain.md).

Write-side `ActionPlanExecutionLifecycleEvent` is insert-only in the transition transaction (`metadata_safe` allowlist). Not a product timeline API.

## 5. Permissions (structuring)

Establishment-scoped. Hints are UX only. Matrices: `action_plans/permissions.py`.

- Catalog create: management roles. Catalog delete (reusable templates): Owner/Director.
- Standard execution create: establishment `can_create_action`; Staff is excluded from this path.
- Staff may create a **self-assigned** feed execution: own pilot BU in scope, no `requires_validation`, no cross-pole tasks.
- Cross-pole task definition: Owner/Director only.
- Linked create (`source_signal_id`): Staff excluded; Signal must be active; Manager needs signal access / actionability (null responsible is a triage path).
- Mark done: Owner/Director, Manager of the pilot pole, or pilot-pole assignee.
- Validate / reopen / cancel **active** executions: establishment `can_validate_action` plus Owner/Director or Manager of the pilot pole.
- Cancel `scheduled`: creator, Owner/Director, or Manager of the pilot pole.
- Mention on an execution comment grants **read** (and thread participation), not operational commands.

## 6. Planning and materialization

Planning writes go through `planning_services.py` (idempotent submission), not through views.

Schedule materialization (`materialization.py`):

- Celery beat horizon: 14 days.
- Execution Feed **read path**: lazy horizon **3 days**, skip if `last_materialized_at` is fresher than **30 minutes** and visible occurrences already exist.

Inspect those constants before changing windows. Feed inclusion of `scheduled` vs cursor statuses: [`feed_domain.md`](feed_domain.md).

## 7. Signal integration

Linked create is `POST …/action-plans/` with optional `signal_id` — not a nested Signal resource. [`signal_domain.md`](signal_domain.md) owns Signal statuses.

- Pilot BU must equal `responsible_business_unit` when that FK is set. When responsible is null, create may qualify the Signal (pilot + routing / `issue_focus` rules in services).
- Linked create from a terminal Signal is rejected.
- Blocking executions (`scheduled`, `in_progress`, `pending_validation`) hold Signal in `in_progress` and block `sync_signal_after_execution_change`.
- Sync (Action Plan → Signal): no blockers + ≥1 `done` → auto-resolve (`resolution_origin=action_plan`); all linked `canceled` → Signal `open`.
- Reopen from `pending_validation` while the Signal is `resolved` moves it back to `in_progress`.
- Manual Signal resolve from `open` cancels blocking linked executions.

Do not copy the Signal lifecycle here.

## 8. Frontend / agent notes

Inspect `houston/action_plans/` and `schema.yml` before listing endpoints. Tests of record: `tests/test_execution_services.py`, `test_signal_sync_services.py`, `test_materialization_services.py`, `test_permissions.py`.

Feed read and `+` menu: [`feed_domain.md`](feed_domain.md). Visibility: [`rbac_permissions_domain.md`](rbac_permissions_domain.md).
