# Feed contracts & pagination — baseline post-Lots 0–7

Captured on 2026-09-28 against the local Docker PostgreSQL database.

Reference state:

- Branch: `main`
- Commit: `f9406bce07c3d3a82e5b5848b617d60ef2d47ea2`
- Baseline schemas: `feed_hardening_baseline_v2`, `feed_frontend_baseline_v2`,
  `feed_browser_baseline_v2`
- No feed contract, selector, index, cache behavior, or product code was changed before capture.
- Raw local artifacts:
  - `.artifacts/feed-hardening-baseline/post-lots-0-7-backend.json`
  - `.artifacts/feed-hardening-baseline/post-lots-0-7-frontend.json`
  - `.artifacts/feed-hardening-baseline/post-lots-0-7-browser.json`

The raw artifacts are intentionally gitignored. This report, the deterministic seed command,
and the frontend instrumentation are the durable comparison point.

## Protocol

Backend instrumentation lives in
`apps/api/houston/core/feed_hardening_baseline.py` and is exposed by
`benchmark_feed_hardening_baseline`. It is guarded by `assert_local_dev_environment`,
deletes only its `T36 Feed Hardening Baseline` namespace, and requires `--confirm` before
rebuilding data.

The representative profile deterministically creates:

- 20 establishments in one organization;
- one owner user with 20 active memberships, providing real Cross scope;
- 5,000 Signals, 100 pins, 10,000 linked source observations, and 114 terminal
  orphans without a field or lifecycle event;
- 3,600 regular seeded executions, 60 pins, 3,600 assignees, 10,800 tasks, and 195
  terminal orphans; the isolated read-catch-up fixture adds one due execution for
  lifecycle promotion and materializes one scheduled execution, producing 3,602 executions
  and 3,601 assignees after the measured catch-up;
- one high-active establishment, one high-history/low-active establishment, and
  eighteen mixed establishments;
- Cross first-page samples at 1, 5, and 20 memberships;
- direct terminal dates distributed over 120 days;
- dated overdue/current and undated execution buckets.

Durable synthetic IDs and distributions are derived from seed 36. Time-sensitive values use
the recorded temporal anchor so their relative lifecycle semantics remain stable. The
single catch-up schedule also includes that anchor in its UUID, preventing a stale local
worker task from a prior run from consuming the new fixture.

Backend timing uses one warmup and seven isolated wall-clock samples. Query diagnostics run
separately through Django's execution wrapper. Payload size is compact serialized JSON.
Selector/serializer paths and authenticated Django HTTP first/continuation paths are
reported separately; HTTP figures include routing, authentication, permission resolution
and rendering, but not network transport.
Materialization/lifecycle catch-up is a dedicated one-shot diagnostic; the pin write runs in
a rollback-only transaction. Every timing and query diagnostic completes before any
`EXPLAIN`, preventing plan replay from warming later scenarios. The two slowest distinct
SELECTs per scenario are then replayed with `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` and
identified by a stable SQL-shape hash.

Deterministic frontend instrumentation simulates 20 pages of 25 items with production cache
and invalidation functions. The browser harness renders 50 real Signal cards and 50 real
Execution cards through 20 generations under React `Profiler`.

## Reproduction commands

Backend full capture:

```bash
REFERENCE_COMMIT="$(git rev-parse HEAD)"
docker compose exec -T api sh -lc '
  cd /app/apps/api &&
  uv run python manage.py benchmark_feed_hardening_baseline \
    --profile representative \
    --reference-commit '"$REFERENCE_COMMIT"' \
    --confirm \
    --iterations 7 \
    --explain-limit 2 \
    --archive \
    --archive-dir /app/.artifacts/feed-hardening-baseline \
    --archive-filename post-lots-0-7-backend.json
'
```

Use `--confirm` for the complete comparable capture because it includes the one-shot
read-catch-up fixture. `--skip-seed` is suitable only for additional warm nominal reads.

Frontend structural capture:

```bash
cd apps/web
FEED_BASELINE_REFERENCE_COMMIT="$(git rev-parse HEAD)" \
FEED_BASELINE_OUTPUT="../../.artifacts/feed-hardening-baseline/post-lots-0-7-frontend.json" \
npx vitest run src/baseline/feed-hardening-baseline.test.ts --maxWorkers=1
```

Browser capture:

```bash
cd apps/web
VITE_FEED_BASELINE_REFERENCE_COMMIT="$(git rev-parse HEAD)" \
npm run dev -- --host 127.0.0.1 --port 4173 --strictPort
```

Open `http://127.0.0.1:4173/baseline.html` in a fresh tab of the documented Chromium version
with a
644 × 818 CSS-pixel viewport and DPR 2. Wait for
`document.body.dataset.baselineComplete === "true"`, then export
`window.__FEED_BROWSER_BASELINE__`. Disable/re-enable the Performance domain immediately
before reloading the fixed-size tab, then record `Performance.getMetrics`. Keep browser
version, viewport, device pixel ratio, anchor, and commit with the result in
`post-lots-0-7-browser.json`.

## Backend results

Environment:

- Python 3.13.13, PostgreSQL 17.10, `shared_buffers=128MB`;
- Linux aarch64 Docker under OrbStack;
- database size after seed and measured catch-up: 56 MB;
- Django debug enabled.

Inventory anchor: `2026-09-28T17:13:11+00:00`. Final Signal statuses are 2,544 open,
938 in progress, 469 interesting, 773 resolved, and 276 canceled. Final Execution statuses
are 1,937 in progress, 531 pending validation, 567 done, 387 canceled, and 180 scheduled.

Establishment Signals:

- first page: p50 97.6 ms, p95 129.1 ms, 9 queries, 42,547 bytes;
- continuation: p50 87.1 ms, p95 103.2 ms, 5 queries, 35,252 bytes.

Cross Signals:

- first page at 1/5/20 establishments: p50 138.0/184.2/356.1 ms, p95
  254.8/225.5/399.2 ms, 9 queries each, 42,716/50,238/50,239 bytes;
- 20-establishment continuation: p50 274.8 ms, p95 372.6 ms, 5 queries,
  35,391 bytes;
- pins continuation: p50 60.3 ms, p95 69.0 ms, 5 queries, 14,636 bytes.

Establishment Execution:

- materialization/lifecycle catch-up: 1,572.0 ms wall, 904.8 ms SQL, 93 queries
  (72 SELECT, 11 writes, 10 transaction/control);
- post-catch-up pre-warm read: 860.5 ms wall, 654.0 ms SQL, 20 SELECTs;
- warm first page: p50 847.5 ms, p95 892.6 ms, 20 queries, 84,276 bytes;
- continuation: p50 368.7 ms, p95 411.9 ms, 9 queries, 73,822 bytes.

Cross Execution:

- first page at 1/5/20 establishments: p50 578.5/1,682.7/5,525.3 ms, p95
  720.0/1,913.3/5,760.2 ms, 16/48/168 queries, 75,654/75,519/75,236 bytes;
- 20-establishment continuation: p50 848.3 ms, p95 1,047.4 ms, 66 queries,
  75,673 bytes;
- pins first page: p50 887.4 ms, p95 1,420.7 ms, 66 queries, 29,622 bytes.

Cross History:

- Signals all-time: p50 40.4 ms, p95 48.0 ms, 2 queries, 10,270 bytes;
- Signals 90-day: p50 58.9 ms, p95 78.1 ms, 3 queries, 10,290 bytes;
- Execution all-time: p50 52.7 ms, p95 157.9 ms, 2 queries, 10,265 bytes;
- Execution 90-day: p50 95.6 ms, p95 214.2 ms, 3 queries, 10,285 bytes.

Write and authenticated HTTP paths:

- pin replacement: p50 28.7 ms, p95 48.8 ms, 12 queries (8 SELECT, 2 writes,
  2 transaction/control);
- HTTP Signal establishment first/continuation: p50 218.5/170.6 ms, p95
  350.7/250.1 ms, 13/9 queries, 42,222/35,026 bytes;
- HTTP Signal Cross first/continuation: p50 671.6/311.9 ms, p95 988.5/527.8 ms,
  16/12 queries, 49,839/35,165 bytes;
- HTTP Execution establishment first/continuation: p50 951.7/365.7 ms, p95
  1,022.2/457.1 ms, 24/13 queries, 84,276/73,822 bytes;
- HTTP Execution Cross first/continuation: p50 5,697.3/911.3 ms, p95
  6,119.4/1,070.7 ms, 175/73 queries, 75,236/75,673 bytes.

## Query-plan observations

These are baseline facts, not optimization decisions.

- Signal establishment first-page principal shape `f324cd55c4b48110` returns 26 rows
  through `Limit`: 14.9 ms executor time and 324 shared-buffer hits.
- Signal Cross first-page principal shape `eea84d0a858afab2` rises from 10.5 ms at one
  membership to 41.0 ms at five and 168.6 ms at twenty, with 742 shared-buffer hits for
  26 rows at twenty. The 20-membership continuation shape `f9be3488d0cf5e7b` takes
  172.9 ms and 669 hits.
- Execution establishment principal feed shape `44870820a315dd2f` returns 26 rows in
  10.8 ms with 163 hits, but has 273.8 ms planning time in this replay. End-to-end cost is
  dominated by the wider read path, related-object prefetches, metadata queries,
  serialization, and query planning.
- Execution Cross first page has an O(memberships) query multiplier: 16/48/168 queries at
  1/5/20 memberships. Its 20-membership principal shape `15b53c4b6ec2fb22` returns 26
  rows in 111.7 ms with 2,624 hits, while total SQL diagnostic time is 4,628.8 ms.
- History remains bounded in this dataset: all-time Signal and Execution principal page
  plans return 26 rows in 4.9 ms and 8.1 ms respectively. The 90-day forms add the orphan
  count query and use 3 queries each.
- All plans were warm-buffer runs (`shared_read=0` in the summarized principal plans).
  They must be compared under the same local protocol after PR1–3.

## Frontend structural results

Runtime: Node 24.15.0 on Darwin. The synthetic session loads 20 pages of 25 items.

- Both reading windows retain page one plus two focus pages: 75 hydrated items and 50
  rendered items after eviction.
- Signals additionally stores 50 projected item references alongside its hydrated window;
  serialized state is 142,785 bytes with contract-complete synthetic items.
- Execution serialized state is 87,376 bytes without a second projected list.
- Eight Signal and eight Execution filter/view cache entries produce 16 QueryClient entries
  and 1,841,305 serialized bytes with this synthetic shape.
- Forced Signal invalidation issues 3 prefix invalidations.
- Forced Execution feed invalidation issues 5 prefix invalidations.

## Browser render results

Captured in a fresh Cursor Chromium 148 / Electron 42.10 tab at 644 × 818 CSS pixels and
device pixel ratio 2. React StrictMode remained enabled. Synthetic card dates are anchored
at page load so relative-time labels remain equivalent when PR4 replays the harness.

- Signal cards: 20 profiler commits, 187.5 ms total actual duration, 9.375 ms mean,
  23.1 ms maximum.
- Execution cards: 40 profiler commits, 917.7 ms total actual duration, 22.942 ms mean,
  41.7 ms maximum. The extra commits are part of the current card-time behavior and are
  intentionally retained in the baseline.
- Harness heap proxy: 27,599,891 bytes at start and 65,440,467 bytes after the session.
- CDP after completion: 17,484,188 bytes JS heap used, 19,562,496 bytes JS heap total,
  3,119 nodes, 3,458 layout objects, and 256 JS event listeners.

The two heap readings come from different Chromium instruments and must not be compared to
each other. Future runs compare each field only with the same instrument and browser setup.

## Comparison guardrails

- Reuse the same profile, seed, commit capture, warmups, iterations, browser, viewport, and
  worker count. Avoid concurrent builds, tests, or other database workloads during timing.
- Compare query count and query shape before interpreting latency.
- Keep selector timing separate from read-path side effects and serialization.
- Do not change query-count ceilings, add indexes, or accept a query rewrite from this
  baseline alone. PR4 re-measures after PR1–3 and decides which PR5 candidates are justified.
- Do not use Mama Nice or an establishment-only account as a substitute for the 20-scope
  Cross profile.
