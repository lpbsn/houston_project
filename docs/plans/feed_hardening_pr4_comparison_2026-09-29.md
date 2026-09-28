# Feed hardening PR4 — comparative measurement after PR1–3

Captured on 2026-09-29 against the local Docker PostgreSQL database.

Reference states:

- before: `main` at `f9406bce07c3d3a82e5b5848b617d60ef2d47ea2`;
- after PR1–3: `main` at `50a266b668a7229aa5a484494b5f8672e64e85b2`;
- frozen baseline: `docs/plans/feed_contracts_post_lots_0_7_baseline_2026-09-28.md`;
- raw after artifacts:
  - `.artifacts/feed-hardening-baseline/post-pr1-3-backend.json`;
  - `.artifacts/feed-hardening-baseline/post-pr1-3-frontend.json`;
  - `.artifacts/feed-hardening-baseline/post-pr1-3-browser.json`.

No query shape, queryset, index, external contract, runtime behavior, or query-count
budget was changed for PR4. `apps/api/schema.yml` and
`apps/web/src/api/generated/types.ts` are unchanged between the two reference commits.

## Protocol and comparability

The representative profile, seed 36, volumes, scenarios, one warmup, seven timing
iterations, two `EXPLAIN (ANALYZE, BUFFERS)` replays, frontend 20-page session, browser
20-generation session, Chromium version, 644 × 818 viewport, and DPR 2 are the same as
the frozen baseline.

The first literal replay happened after midnight in Europe/Paris. At that time, the
fixture's 08:00 occurrence was not yet visible and the read path exercised lifecycle
promotion without schedule materialization: 3,601 executions, 42 queries and 3 writes.
That run was rejected because it did not reproduce the frozen catch-up scenario.

The retained backend capture freezes `django.utils.timezone.now()` to the baseline
temporal anchor, `2026-09-28T17:13:11+00:00`, while invoking the same seed and benchmark
functions. It reproduces the exact inventory after catch-up: 3,602 executions, 3,601
assignees, 93 queries, 11 writes, 5,000 Signals, 100 Signal pins, 10,000 source
observations, 60 Execution pins, and 10,800 tasks.

Environment stayed equivalent: Python 3.13.13, PostgreSQL 17.10,
`shared_buffers=128MB`, Linux aarch64 under OrbStack, Django debug enabled. Database size
was 56 MB before and 57 MB after.

Latency deltas below are observations, not causal gains from PR1–3. SQL shape hashes and
query counts are stable while most timings improve substantially, including untouched
History and card rendering. The captures therefore show meaningful absolute bottlenecks
and absence of regression, but do not prove that PR1–3 caused the timing reductions.

Payload deltas of 0.3–0.5% on live feeds come from temporal/cursor values produced at the
two capture points. History and write payload sizes are byte-identical, and the published
contract files are unchanged.

## Pure read / selector and serializer paths

These are warm nominal reads after the dedicated catch-up has completed. They invoke the
owning page builder and serializer without routing, authentication, network transport, or
write-side catch-up.

| Scenario | p50 before → after | p95 before → after | Queries | Payload before → after |
| --- | ---: | ---: | ---: | ---: |
| Signal establishment first | 97.6 → 85.8 ms (-12.0%) | 129.1 → 102.3 ms (-20.7%) | 9 → 9 | 42,547 → 42,327 B (-0.5%) |
| Signal establishment continuation | 87.1 → 28.2 ms (-67.6%) | 103.2 → 28.9 ms (-72.0%) | 5 → 5 | 35,252 → 35,067 B (-0.5%) |
| Signal Cross first, 1 establishment | 138.0 → 58.1 ms (-57.9%) | 254.8 → 67.8 ms (-73.4%) | 9 → 9 | 42,716 → 42,497 B (-0.5%) |
| Signal Cross first, 5 establishments | 184.2 → 127.4 ms (-30.8%) | 225.5 → 151.5 ms (-32.8%) | 9 → 9 | 50,238 → 49,984 B (-0.5%) |
| Signal Cross first, 20 establishments | 356.1 → 235.8 ms (-33.8%) | 399.2 → 290.6 ms (-27.2%) | 9 → 9 | 50,239 → 49,985 B (-0.5%) |
| Signal Cross continuation, 20 establishments | 274.8 → 164.6 ms (-40.1%) | 372.6 → 207.0 ms (-44.4%) | 5 → 5 | 35,391 → 35,207 B (-0.5%) |
| Signal Cross pins continuation | 60.3 → 43.2 ms (-28.3%) | 69.0 → 58.8 ms (-14.8%) | 5 → 5 | 14,636 → 14,566 B (-0.5%) |
| Execution establishment first | 847.5 → 504.6 ms (-40.5%) | 892.6 → 724.8 ms (-18.8%) | 20 → 20 | 84,276 → 84,061 B (-0.3%) |
| Execution establishment continuation | 368.7 → 200.8 ms (-45.5%) | 411.9 → 217.0 ms (-47.3%) | 9 → 9 | 73,822 → 73,628 B (-0.3%) |
| Execution Cross first, 1 establishment | 578.5 → 332.9 ms (-42.5%) | 720.0 → 383.6 ms (-46.7%) | 16 → 16 | 75,654 → 75,460 B (-0.3%) |
| Execution Cross first, 5 establishments | 1,682.7 → 943.2 ms (-43.9%) | 1,913.3 → 993.2 ms (-48.1%) | 48 → 48 | 75,519 → 75,325 B (-0.3%) |
| Execution Cross first, 20 establishments | 5,525.3 → 2,949.2 ms (-46.6%) | 5,760.2 → 3,072.3 ms (-46.7%) | 168 → 168 | 75,236 → 75,042 B (-0.3%) |
| Execution Cross continuation, 20 establishments | 848.3 → 442.5 ms (-47.8%) | 1,047.4 → 480.2 ms (-54.2%) | 66 → 66 | 75,673 → 75,479 B (-0.3%) |
| Execution Cross pins first, 20 establishments | 887.4 → 359.6 ms (-59.5%) | 1,420.7 → 398.6 ms (-71.9%) | 66 → 66 | 29,622 → 29,499 B (-0.4%) |
| Signal History all-time | 40.4 → 19.9 ms (-50.6%) | 48.0 → 21.5 ms (-55.1%) | 2 → 2 | 10,270 → 10,270 B |
| Signal History 90-day | 58.9 → 30.3 ms (-48.6%) | 78.1 → 50.7 ms (-35.1%) | 3 → 3 | 10,290 → 10,290 B |
| Execution History all-time | 52.7 → 22.2 ms (-57.9%) | 157.9 → 46.9 ms (-70.3%) | 2 → 2 | 10,265 → 10,265 B |
| Execution History 90-day | 95.6 → 34.2 ms (-64.2%) | 214.2 → 38.7 ms (-81.9%) | 3 → 3 | 10,285 → 10,285 B |
| Execution pin replacement | 28.7 → 13.1 ms (-54.3%) | 48.8 → 34.1 ms (-30.2%) | 12 → 12 | 18 → 18 B |

## Complete authenticated HTTP paths

These figures add routing, authentication, permission resolution and response rendering,
but not network transport. Execution reads are warm and nominal here; the one-shot
materialization/lifecycle path is measured separately in the next section.

| Scenario | p50 before → after | p95 before → after | Queries | Payload before → after |
| --- | ---: | ---: | ---: | ---: |
| HTTP Signal establishment first | 218.5 → 90.7 ms (-58.5%) | 350.7 → 130.2 ms (-62.9%) | 13 → 13 | 42,222 → 42,002 B (-0.5%) |
| HTTP Signal establishment continuation | 170.6 → 57.9 ms (-66.1%) | 250.1 → 84.5 ms (-66.2%) | 9 → 9 | 35,026 → 34,841 B (-0.5%) |
| HTTP Signal Cross first | 671.6 → 269.2 ms (-59.9%) | 988.5 → 285.5 ms (-71.1%) | 16 → 16 | 49,839 → 49,585 B (-0.5%) |
| HTTP Signal Cross continuation | 311.9 → 203.2 ms (-34.8%) | 527.8 → 217.4 ms (-58.8%) | 12 → 12 | 35,165 → 34,981 B (-0.5%) |
| HTTP Execution establishment first | 951.7 → 497.0 ms (-47.8%) | 1,022.2 → 534.3 ms (-47.7%) | 24 → 24 | 84,276 → 84,061 B (-0.3%) |
| HTTP Execution establishment continuation | 365.7 → 221.0 ms (-39.6%) | 457.1 → 348.9 ms (-23.7%) | 13 → 13 | 73,822 → 73,628 B (-0.3%) |
| HTTP Execution Cross first | 5,697.3 → 2,915.1 ms (-48.8%) | 6,119.4 → 3,117.3 ms (-49.1%) | 175 → 175 | 75,236 → 75,042 B (-0.3%) |
| HTTP Execution Cross continuation | 911.3 → 477.1 ms (-47.6%) | 1,070.7 → 608.3 ms (-43.2%) | 73 → 73 | 75,673 → 75,479 B (-0.3%) |

## Complete Execution catch-up / materialization path

This one-shot diagnostic runs on the disposable namespaced dataset and deliberately
includes schedule materialization, lifecycle promotion, notifications and related writes.
It is not mixed into the warm selector or HTTP timing distributions.

| Diagnostic | Wall before → after | SQL before → after | Queries before → after |
| --- | ---: | ---: | ---: |
| Materialization + lifecycle catch-up | 1,572.0 → 990.6 ms (-37.0%) | 904.8 → 475.2 ms (-47.5%) | 93 → 93: 72 SELECT, 11 writes, 10 control |
| Immediate post-catch-up pre-warm read | 860.5 → 471.6 ms (-45.2%) | 654.0 → 370.3 ms (-43.4%) | 20 → 20 SELECT |

The unchanged 93-query shape is the important result. The path still performs substantial
repeated work for one materialized execution and one promoted execution. The lower wall
and SQL times are favorable but, like the nominal timing reductions, are not attributable
to a PR1–3 query or index change.

## EXPLAIN ANALYZE BUFFERS

The table compares identical principal SQL-shape hashes. `Rows` is the top plan node's
actual row count. Buffers are warm (`shared_read=0` throughout). Temp blocks are shown as
read/written. Planning time is included where it materially dominates execution.

| Scenario / shape | Rows | Execution before → after | Shared hits before → after | Temp read/write before → after | Planning before → after |
| --- | ---: | ---: | ---: | ---: | ---: |
| Signal establishment first `f324cd55c4b48110` | 26 → 26 | 14.9 → 7.5 ms | 324 → 324 | 0/0 → 0/0 | 36.4 → 25.8 ms |
| Signal Cross first, 20 `eea84d0a858afab2` | 26 → 26 | 168.6 → 144.9 ms | 742 → 743 | 560/561 → 560/561 | 69.2 → 36.6 ms |
| Signal Cross continuation, 20 `f9be3488d0cf5e7b` | 26 → 26 | 172.9 → 103.2 ms | 669 → 670 | 865/866 → 865/866 | 67.2 → 47.7 ms |
| Execution establishment first `44870820a315dd2f` | 26 → 26 | 10.8 → 5.8 ms | 163 → 168 | 0/0 → 0/0 | 273.8 → 128.4 ms |
| Execution Cross first, 20 `15b53c4b6ec2fb22` | 26 → 26 | 111.7 → 66.2 ms | 2,624 → 2,769 | 0/0 → 0/0 | 488.3 → 171.9 ms |
| Execution Cross continuation, 20 `f3a228a986735c42` | 26 → 26 | 108.9 → 77.9 ms | 2,995 → 3,073 | 0/0 → 0/0 | 305.1 → 207.3 ms |
| Signal History all-time `e42bd716add9fd35` | 26 → 26 | 4.9 → 2.2 ms | 473 → 472 | 0/0 → 0/0 | 1.6 → 0.8 ms |
| Execution History all-time `55cef8af4cb173af` | 26 → 26 | 8.1 → 3.9 ms | 744 → 900 | 0/0 → 0/0 | 1.4 → 0.7 ms |
| Execution History 90-day `610dc2a6a9f0f0da` | 26 → 26 | 10.3 → 5.6 ms | 3,434 → 3,437 | 0/0 → 0/0 | 1.7 → 0.9 ms |

Relevant row/filter observations are also stable for the establishment and continuation
shapes: Signal establishment removes 25 rows; Signal Cross first/continuation remove
1,567/1,592 rows; Execution establishment removes 572 rows; Execution Cross continuation
removes 142 before and 143 after. Execution Cross first changed from 117 to 1,635 rows
removed despite identical SQL and inventory, alongside a different warm plan execution
profile. That reinforces the guardrail against attributing its latency delta to PR1–3.

The durable findings are:

- Signal Cross still spills temporary blocks for only 26 returned rows.
- Execution planning remains much larger than executor time, especially on establishment
  and Cross reads.
- Execution Cross still touches roughly 2.8–3.1k shared buffers on its principal page
  queries and compounds that with membership-linear auxiliary queries.
- History remains bounded and inexpensive enough that PR5 work is not justified there.

## Frontend structural metrics

The same synthetic session loads 20 pages of 25 contract-complete items into eight Signal
and eight Execution cache entries.

| Metric | Before → after | Delta |
| --- | ---: | ---: |
| Signal hydrated / rendered items | 75 / 50 → 75 / 50 | unchanged |
| Signal projected references stored in parallel | 50 → 0 | removed |
| Signal serialized state | 142,785 → 85,424 B | -57,361 B (-40.2%) |
| Execution serialized state | 87,376 → 87,376 B | unchanged |
| QueryClient entries | 16 → 16 | unchanged |
| QueryClient serialized data | 1,841,305 → 1,382,417 B | -458,888 B (-24.9%) |
| Forced Signal invalidations | 3 → 3 | unchanged |
| Forced Execution invalidations | 5 → 5 | unchanged |

PR3 therefore achieves its intended structural result: Signals no longer stores a second
projected item list, while window depth, rendered items, cache keys and invalidation
fan-out stay stable.

## Browser render and memory metrics

The browser version and harness geometry match exactly:
Cursor 3.22.7, Chromium 148.0.7778.280, Electron 42.10.0, 644 × 818 CSS pixels,
DPR 2, development mode, React StrictMode enabled.

| Metric | Before → after | Delta |
| --- | ---: | ---: |
| Signal profiler commits | 20 → 20 | unchanged |
| Signal total actual duration | 187.5 → 148.7 ms | -20.7% |
| Signal mean / maximum duration | 9.375 / 23.1 → 7.435 / 17.0 ms | -20.7% / -26.4% |
| Execution profiler commits | 40 → 40 | unchanged |
| Execution total actual duration | 917.7 → 776.0 ms | -15.4% |
| Execution mean / maximum duration | 22.942 / 41.7 → 19.4 / 30.8 ms | -15.4% / -26.1% |
| Harness heap proxy, start | 27,599,891 → 44,126,944 B | +59.9% |
| Harness heap proxy, end | 65,440,467 → 44,306,122 B | -32.3% |
| CDP JS heap used / total | 17,484,188 / 19,562,496 → 17,510,248 / 19,300,352 B | +0.1% / -1.3% |
| CDP nodes / layout objects / listeners | 3,119 / 3,458 / 256 → 3,119 / 3,458 / 256 | unchanged |

The stable CDP heap and exact DOM/listener counts show no browser-memory or render-shape
regression. The harness heap start/end pair is sensitive to garbage collection and initial
tab state; its much smaller within-session growth after PR3 is encouraging but is not
used as standalone proof. The card components did not change in PR1–3, so profiler timing
improvements are treated as run variance rather than a PR3 effect.

## Query budgets

No budget changes are justified:

- all retained backend query counts are identical before/after;
- establishment Execution remains at 20 selector queries and 24 authenticated HTTP
  queries on the representative first page;
- Cross Execution remains membership-linear rather than receiving a structural reduction;
- the complete catch-up remains 93 queries with the same SELECT/write/control split.

`apps/api/houston/testing/query_baseline.py` is therefore unchanged.

## PR5 candidates selected on evidence

1. **Batch the Cross Execution per-membership read preparation and scheduled summaries.**
   This is the highest-priority candidate. First-page selector counts scale
   16 → 48 → 168 for 1/5/20 establishments, equivalent to `8 × memberships + 8`;
   authenticated HTTP reaches 175 queries and p50 2.9 s at 20 establishments.
   Continuation and pins still use 66 selector queries at 20 establishments.

2. **Reduce repeated Execution query construction/planning and evaluate a single section
   aggregate.** The principal establishment query plans for 128.4 ms but executes in
   5.8 ms; Cross first plans for 171.9 ms and executes in 66.2 ms. Any rewrite must retain
   P-before-L exclusion, category semantics, cursor tie-breakers, RBAC and scheduled
   metadata. Compare total request SQL, not only the principal statement.

3. **Evaluate the Signal Cross sort/annotation order and a narrowly justified supporting
   index.** The 20-establishment first/continuation plans return 26 rows but still execute
   in 144.9/103.2 ms and spill 560/561 and 865/866 temporary blocks. A candidate is valid
   only if it removes the spill or materially lowers work without changing cursor order,
   pin exclusion, visibility or counts.

4. **Reduce repeated materialization/lifecycle work on the complete Execution read path.**
   One schedule materialization plus one lifecycle promotion still costs 93 queries,
   990.6 ms wall and 475.2 ms SQL. Preserve the GET catch-up guarantee and compare the
   write/control split, emitted side effects and resulting inventory.

5. **Keep single pin replacement verification as a low-priority control candidate only.**
   It remains 12 queries but is 13.1 ms p50 in this profile. There is no evidence to
   prioritize a rewrite ahead of Cross fan-out, planning, Signal spill or catch-up work.

Not selected for PR5: History query/index changes, establishment Signal changes, frontend
virtualization, cache-key changes, invalidation changes, or query-budget relaxation. Their
measured costs and stable structures do not justify added complexity.

## PR5 acceptance gate

For each retained candidate, rerun this same anchored representative profile and require:

- unchanged result contract, query ordering, cursor semantics, RBAC and inventory;
- a lower relevant query count or materially lower executor/planning/buffer/temp work;
- lower p50 and p95 on the owning selector and authenticated HTTP path;
- no displaced cost into writes, another page, another membership, or catch-up;
- a focused contract test and a query budget only when the optimized structure establishes
  a lower stable ceiling.
