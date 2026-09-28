# Feed contracts & pagination - Lot 0 measurement

Measured on 2026-09-27 at 16:01 UTC against local Docker database `houston`.

Repository state:

- Branch: `main`
- Commit: `08ac2605c06fe66f99ca56d36642144f6e7f665d`
- Scope constraints: `docs/cadrage/SPORE_Feed_contracts_pagination_cadrage_v1.md` and `docs/plans/feed_contracts_plan_017155e4.plan.md`
- No product code, schema, generated contract, or data mutation was changed for this lot.

## Method

Measurements were run through Django inside the local `api` container, using the current selectors and models rather than hand-written substitutes.

- Inventory counts used ORM aggregates on `Signal`, `SignalLifecycleEvent`, `ActionPlanExecution`, `ActionPlanExecutionLifecycleEvent`, and `ActionPlanExecutionFeedPin`.
- EXPLAIN used PostgreSQL `EXPLAIN (FORMAT JSON, COSTS)` through Django `QuerySet.explain`.
- EXPLAIN was intentionally run without `ANALYZE`; costs and planned rows are planner estimates, not runtime timings.
- Representative establishment EXPLAIN sample: active manager membership `01edd494-8c3e-4542-9274-3f29b1e1705b` in establishment `48140b58-45e1-48dc-89c6-bac3b310e846`.

## Dataset Snapshot

- Active memberships: 62
- Signals total: 420
- Signals in current feed statuses: 420
- Action plan executions total: 441
- Executions in current cursor feed statuses: 292

## Pins Inventory

Execution pins:

- Total rows: 0
- Memberships over the target cap of 3: 0
- Max pins for one membership: 0
- Scheduled pins: 0
- Terminal pins: 0
- Pins outside remaining-work statuses (`in_progress`, `pending_validation`): 0
- Membership/execution establishment mismatches: 0

Signals pins:

- Total pinned signals: 2
- Pinned by status: `open=2`
- Target-ineligible pinned signals, status not `open` or `interesting`: 0
- Current-service-ineligible pinned signals, status not `open`: 0
- Pinned signals missing `pinned_at`: 0
- Pinned signals missing `pinned_by_membership`: 0

## Terminal Dates And Orphans

Signals:

- `resolved`: total 359; direct `resolved_at` present 359; missing field with reliable lifecycle event 0; orphans 0.
- `canceled`: total 8; direct `canceled_at` present 8; missing field with reliable lifecycle event 0; orphans 0.

Executions:

- `done`: total 227; `validated_at` present 227; `marked_done_at` only 0; any direct terminal field present 227; missing direct field with reliable lifecycle event 0; orphans 0.
- `canceled`: total 22; direct `canceled_at` present 22; missing field with reliable lifecycle event 0; orphans 0.

No terminal orphan was found in the measured local dataset.

## Cancel Origin Inventory

- Canceled executions by origin: `manual=19`, `schedule_sync=3`
- Canceled executions with null origin: 0
- Canceled executions with atypical origin: 0
- Non-canceled executions with a non-null origin: 0

## Lifecycle Event Inventory

Signals lifecycle events:

- `signal.created`: 420
- `signal.history_baseline`: 420
- `signal.marked_interesting`: 10
- `signal.moved_in_progress`: 200
- `signal.moved_open`: 16
- `signal.resolved`: 359
- `signal.canceled`: 8

Execution lifecycle events:

- `action_plan_execution.created`: 441
- `action_plan_execution.history_baseline`: 440
- `action_plan_execution.started`: 288
- `action_plan_execution.marked_done`: 244
- `action_plan_execution.validated`: 227
- `action_plan_execution.canceled`: 22
- `action_plan_execution.reopened`: 4
- `action_plan_execution.deadline_changed`: 1

Factual discrepancy observed: execution baseline events are 440 for 441 executions. This did not create terminal-date orphans in the current dataset.

## EXPLAIN Inventory

Establishment Signals feed, current first GET behavior:

- Current code runs one limited section query per requested status.
- All measured section plans include explicit sort work over the feed sort keys.
- `open`: top `Limit`, planned rows 26, cost 373.57, scans `Index Scan=2`, `Seq Scan=9`, sorts `Incremental Sort=1`, `Sort=1`.
- `in_progress`: top `Limit`, planned rows 24, cost 353.67, scans `Index Scan=2`, `Seq Scan=9`, sorts `Incremental Sort=1`, `Sort=1`.
- `interesting`: top `Limit`, planned rows 13, cost 235.52, scans `Index Scan=4`, `Seq Scan=7`, sorts `Incremental Sort=1`, `Sort=1`; planner uses `signal_feed_sort_idx`.
- `resolved`: top `Limit`, planned rows 26, cost 422.54, scans `Index Scan=4`, `Seq Scan=7`, sorts `Incremental Sort=1`, `Sort=1`.
- `canceled`: top `Limit`, planned rows 8, cost 181.02, scans `Index Scan=4`, `Seq Scan=7`, sorts `Incremental Sort=1`, `Sort=1`; planner uses `signal_feed_sort_idx`.
- Recurrent scanned relations include `signals_signal`, `signals_signalsourceobservation`, `action_plans_actionplanexecution`, establishment dimension tables, and membership tables.

Establishment Execution feed, current first page:

- Top `Limit`, planned rows 26, cost 2325.24.
- Sort nodes: `Sort=1`.
- Scan nodes: `Index Scan=9`, `Seq Scan=9`, `Bitmap Heap Scan=1`, `Bitmap Index Scan=1`.
- Planner uses pin-related indexes including `ap_exec_feed_pin_idx` and `uniq_action_plan_execution_feed_pin`.
- Recurrent scanned relations include `action_plans_actionplanexecution`, `action_plans_actionplanexecutionfeedpin`, `action_plans_actionplanexecutionteam`, `action_plans_actionplanassignee`, membership/user tables, establishment dimension tables, and `signals_signal`.

Execution scheduled preview:

- Top `Limit`, planned rows 50, cost 208.02.
- Sort nodes: `Sort=1`.
- Scan nodes: `Index Scan=8`, `Seq Scan=9`.
- The current preview still plans a 50-row object preview query, matching the plan's note that later lots must replace it with slim scheduled metadata.

## Cross Measurement Limit

No official Cross multi-establishment scope was available in the measured local database:

- Users with more than one active membership: 0
- Official `resolve_management_memberships_for_scope(user)` sample with more than one membership: none

Because of that, the requested Cross UUID-materialization EXPLAIN could not be measured against a real accessible Cross scope in this environment. The current implementation was still inspected: `cross_signal_feed_queryset` materializes UUIDs per membership through `signal_feed_queryset(...).values_list("id", flat=True)` before building a final `id__in` queryset.

## Factual Deviations For Later Lots

- No execution pins need demo trimming in this measured dataset.
- No Signal pins are currently ineligible under either the current service rule (`open`) or the target rule (`open`, `interesting`).
- No terminal history orphan repair decision is forced by the measured dataset.
- Cross performance remains unmeasured in this environment because there is no real multi-establishment management scope.
- One execution lacks a `history_baseline` lifecycle event while all 441 executions have `created` lifecycle events.
