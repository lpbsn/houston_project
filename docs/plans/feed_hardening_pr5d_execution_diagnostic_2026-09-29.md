# Feed hardening PR5D — Execution read-path diagnostic

Captured on 2026-09-29 against the local Docker PostgreSQL database, before any
change to `materialization.py` or `lifecycle_promotion.py`.

Raw representative artifact:
`apps/api/.artifacts/feed-hardening-baseline/pr5d-representative-before.json`.

## Protocol

- Representative profile, seed 36: 20 establishments, 5,000 Signals, 3,602
  executions after historical catch-up, 3,601 assignees and 10,800 tasks.
- The benchmark freezes `django.utils.timezone.now()` to the dataset temporal
  anchor.
- The historical PR4/PR5B fixture and feed operation are unchanged. New isolated
  fixtures are reset between materialization, availability and promotion.
- Every diagnostic records all SQL shapes with owner/role attribution, SELECT /
  write / control counts, SQL total, wall time, up to ten
  `EXPLAIN (ANALYZE, BUFFERS)` plans, callback scheduling/execution, realtime
  invalidations and persisted business deltas.
- Wall time remains a secondary signal. The gate uses SQL work, planning,
  executor/buffers, required writes/effects and concurrency risk together.

## Diagnostic before modification

Historical combined catch-up:

- 94 queries: 73 SELECT, 11 writes, 10 control.
- 80.7 ms SQL total; 207.7 ms instrumented wall.
- This reproduces the PR5B 94-query shape and remains directly comparable with
  PR4's 93 queries / 475.2 ms SQL and PR5B's approximately 303 ms SQL. Absolute
  timing is lower on this fresh local capture; the stable query shape is the
  durable comparison.
- The two slowest statements belong to the feed read after catch-up, not to a
  removable lifecycle write: shape `45046e8021ec667e` planned for 36.771 ms,
  executed for 0.723 ms and hit 303 shared buffers; shape
  `291ca87df10f79e4` planned for 13.765 ms, executed for 1.375 ms and hit 40
  shared buffers. No explained shape read shared or temp blocks.

Nominal no-op:

- Establishment: 21 SELECT, 53.0 ms SQL, 80.7 ms wall, zero mutation, callback
  or side effect.
- Cross 1: 17 SELECT, 7.0 ms SQL, 22.5 ms wall, zero side effect.
- Cross 5: 33 SELECT, 15.1 ms SQL, 35.5 ms wall, zero side effect.
- Cross 20: 89 SELECT, 46.8 ms SQL, 88.6 ms wall, zero side effect.
- The Cross slope is real, but each establishment owns distinct schedule
  visibility and lifecycle candidates. Removing it safely would require a
  cross-establishment batching/rewrite that is not justified by this local cost
  and would weaken the present per-establishment best-effort boundary.

Isolated real work:

- Materialization only: 56 queries = 41 SELECT / 9 writes / 6 control,
  28.8 ms SQL, 50.0 ms wall.
- Availability only: 23 queries = 15 SELECT / 2 writes / 6 control,
  18.5 ms SQL, 28.9 ms wall.
- Promotion only: 32 queries = 25 SELECT / 3 writes / 4 control,
  19.4 ms SQL, 33.8 ms wall.
- The artifact retains every attributed shape and every plan summary. Repeated
  schedule loads and lifecycle candidate checks exist, but their measured
  executor/buffer contribution is small relative to required structure,
  notification, lifecycle and feed work.

## Persisted effects and callbacks

Historical combined catch-up produced exactly:

- one execution, one team and one assignee;
- one CREATED and two STARTED lifecycle events;
- two availability timestamps and two `scheduled → in_progress` outcomes;
- one CREATED notification;
- one schedule freshness update;
- five callbacks scheduled and executed;
- one `action_plan_execution.created` and one
  `action_plan_execution.started` realtime invalidation;
- no duplicate point transaction.

Materialization-only produced one execution/team/assignee/task, one CREATED and
one STARTED event, one availability timestamp, one CREATED notification, one
freshness update, three callbacks and one created invalidation.

Availability-only produced one availability timestamp and one CREATED
notification, with one callback and no lifecycle/status/realtime change.

Promotion-only produced one status/timestamp/`last_activity_at` transition, one
STARTED event, one STARTED notification, three callbacks and one started
invalidation. The fixture is intentionally not GAM-04 eligible; the concurrency
test covers the eligible award path.

Every no-op scenario produced zero persisted delta and zero callback.

## Concurrency hardening

Added transactional integration coverage with independent database connections:

- two simultaneous read-path materializations;
- Beat horizon materialization concurrent with read catch-up;
- Beat lifecycle tick concurrent with read catch-up.

The tests assert one occurrence, one CREATED/STARTED event pair where applicable,
one availability and STARTED notification, one realtime invalidation and one
eligible GAM-04 point transaction. Existing primitive-level idempotence and lock
tests remain in place.

## Gate

### Materialization: NO-GO

The duplicated schedule/structure reads are visible, but the isolated path costs
28.8 ms SQL while performing nine required writes, six transaction controls,
structure creation, lifecycle journaling, notification and realtime scheduling.
The historical path's dominant planning cost is in the subsequent feed read.
Skipping a freshness reload would also change behavior under concurrent schedule
updates. No safe material gain is demonstrated.

### Lifecycle: NO-GO

Availability and promotion have distinct predicates and ordering. The promotion
recheck/lock guarantees availability before status transition under Beat/read
concurrency. Isolated costs are 18.5 ms and 19.4 ms SQL while producing required
timestamps, events, notifications, realtime and optional gamification. Combining
discoveries or removing the recheck would trade a small local gain for a larger
correctness and rollback risk. No safe material gain is demonstrated.

## Conclusion

PR5D stops at diagnostic hardening. No optimization is applied to
`materialization.py` or `lifecycle_promotion.py`, no query budget changes, and no
contract/schema changes are justified.
