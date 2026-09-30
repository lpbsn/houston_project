# Scalability PR 3 — G-dashboard, G-quota, and certification

Recorded on 2026-09-30 before any dashboard index, cache, or read model, and before any user or establishment admission rate. G-conn and G-transcription stay closed as recorded in [`scalability_pr2_baseline_2026-09-29.md`](scalability_pr2_baseline_2026-09-29.md).

Repository state: PR 1 durable dispatch and PR 2 realtime plus `CONN_MAX_AGE=0` are already in the tree. Live topology remains one API replica, worker concurrency 2 + 1 + 1, one beat.

The analytics harness is the existing `benchmark_analytics_capacity` command. This PR extends it with dashboard 15-day reads, dashboard rankings, and a `rows_scanned` sum of `EXPLAIN` scan nodes. `Actual Rows` is the per-loop average, so the counter multiplies by `Actual Loops`. The figures in the table below were summed before that multiplication. Their dominant scans had `Actual Loops` = 1, so those totals still describe them. The harness runs `ANALYZE` before timing because `COPY` seeding does not refresh planner statistics. Feed traffic is not combined into that harness: doing so would be a second tool. The feed figures below are the already published comparison in [`feed_hardening_pr4_comparison_2026-09-29.md`](feed_hardening_pr4_comparison_2026-09-29.md).

## G-dashboard

Local Docker PostgreSQL 17.10, `shared_buffers=128MB`, Django debug on. Target dataset: 100 establishments, 5,000 patterns, 1,000,000 signals. Timing samples are shorter than the profile default (3 iterations, then 2): the decision uses the single instrumented SQL time as well as p95.

Dashboard and rankings stay on one establishment. Pattern list is organization-scoped, which is the harness scenario.

| Scenario | Before query change | After always evaluating recurrence ids |
| --- | ---: | ---: |
| `dashboard_90d` | p95 1,558 ms, SQL 444 ms, 22 queries | p95 1,855 ms, SQL 520 ms, 22 queries |
| `rankings_90d_recurring` | p95 989 ms, SQL 557 ms | p95 1,508 ms, SQL 615 ms |
| `rankings_90d_new` | p95 1,265 ms, SQL 492 ms | p95 1,636 ms, SQL 495 ms |
| `patterns_90d_page1` | p95 5,893 ms, SQL 5,459 ms, ~3.0M scan rows | p95 6,445 ms, SQL 6,874 ms, ~2.0M scan rows |
| `patterns_30d_page2` | p95 13,172 ms, SQL 12,108 ms, ~6.8M scan rows | p95 4,682 ms, SQL 4,141 ms, ~1.0M scan rows |
| `patterns_30d_recurrent` | p95 15,048 ms, SQL 7,969 ms | p95 4,950 ms, SQL 4,740 ms |

The 90-day dashboard reads one establishment through `signal_est_act_subject_idx` and the assignment unique key. Wall time is about 1.5–1.9 s, SQL about 0.5 s, query count fixed at 22. That does not justify an index, a TTL cache, or a derived table.

The pattern-list blow-up on a cursor page was the recurrence queryset inlined into the select list and into every keyset `OR`. Page 2 scanned the ~950k assignment table about seven times. Evaluating `pattern_recurrence_30d` ids once on a cursor page, and on a recurrent or non-recurrent filter, removes that repetition. Page 2 SQL drops from 12.1 s to 4.1 s. `patterns_30d_recurrent` SQL drops from 8.0 s to 4.7 s.

Always evaluating those ids on the default first page as well added a separate recurrence scan of about 1.0 s. `patterns_90d_page1` SQL moved from 5.5 s to 6.9 s. That 6.9 s is not one aggregation: the page statement stayed about 2.9 s, the new scan about 1.0 s, the existing `COUNT(DISTINCT pattern_id)` about 1.0 s, and the existing page enrichments about 1.2 s. The default first page references membership once, so it keeps the queryset inside the page statement. The 5.5 s figure is that shape. It was not re-timed after making the evaluation conditional. The remaining cost is that organization-wide grouping plus the companion reads. It does not open an index, a TTL cache, or a derived table.

A trial index on `signals_signal (establishment_id, created_at)` was created on this dataset only, then dropped. `patterns_90d_page1` p95 stayed 6.4 s and `dashboard_90d` p95 stayed 1.8 s. The index is not in a migration.

No TTL cache and no read model. Both metrics stay computed at read from PostgreSQL. `resolve_analytics_read_scope` is unchanged.

Feed reads on the published 5,000-signal profile stay in their own band (signal establishment first page p50 85.8 ms / 9 queries; the heaviest execution cross page p95 about 3.1 s). This note does not claim a combined run.

## G-quota

No production admission sample exists. The project has no real user load. The cadrage forbids inventing user or establishment quotas. Observation submit still accepts a valid observation when the provider is slow; the bound is worker concurrency (interactive 2) and the business provider budget, not an HTTP throttle.

Decision: no user throttle and no establishment throttle on either observation submit endpoint or on transcription. Auth throttles stay fail-closed. A down throttle cache makes login return HTTP 500 `internal_error` and does not authenticate. Observation submit and transcription do not consult the throttle cache.

## Canonical metrics

`pattern_recurrence_30d` lives in `houston.analytics.recurrence`. Rolling 30 days, at least 3 occurrences on at least 2 civil days in `establishment.timezone`, canceled signals excluded, read scope unchanged, freshness is OLTP freshness.

`repeated_patterns_in_period` lives in `houston.analytics.dashboard`. Count of signals on the canonical pattern inside the selected dashboard period, included at 2 or more, canceled signals counted, not regrouped by civil day. It is not derived from `pattern_recurrence_30d`.

## Certification

These scenarios are already owned by tests. This PR does not add a second implementation of them.

| Invariant | Proof |
| --- | --- |
| Broker down during submit returns the observation and leaves it recoverable | `test_submit_on_commit_enqueue.py` |
| Same submission key does not create a second observation; a different command conflicts | same file |
| Channels failure does not change the submit HTTP status | `test_api_submit_returns_201_when_channels_send_fails` |
| Worker loss / stuck processing resumes without a second signal | `test_observation_pipeline_recovery.py` |
| Timeout-class provider errors stop at the business attempt ceiling | `test_provider_unavailable_stops_at_business_attempt_ceiling` |
| Invalid output and unexpected provider errors stay inside the classification budget | `test_classification_services.py` |
| `ai_interactive` does not consume `ai_background` | `test_celery_routing.py` |
| API `CONN_MAX_AGE` is 0 | `test_database_settings.py` |
| Beat interruption does not drop durable work; the sweep republishes from PostgreSQL | observation recovery tests and `test_tasks.py` classification sweep |

Not exercised here: a second live API replica, a second worker process, a RabbitMQ process restart, or a combined dashboard-plus-feed load. PgBouncer restart does not apply; PR 2 decided there is no PgBouncer. Horizontal scale remains adding a stateless API replica or one worker class without a code change. Provider call ceilings stay the business counters from PR 1, not a new limiter.
