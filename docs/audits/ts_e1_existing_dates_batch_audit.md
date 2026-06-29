# TS-E1 — batch `existing_dates` audit (PR #42)

> Date: 2026-06-29  
> Scope: read-path materialization (`ensure_visible_executions_materialized`)  
> Related: ROADMAP-15 (TS-E1), DB-02b, MAT-01 (partial — structural debt remains)

## Files inspected

- `apps/api/houston/checklists/materialization.py` — `_existing_occurrence_dates_for_assignments`, `ensure_visible_executions_materialized`
- `apps/api/houston/actions/execution_feed.py` — `build_execution_feed_page` (materialization call site)
- `apps/api/houston/checklists/tests/test_execution_feed_checklist.py` — TS-E1 N=20 guard
- `apps/api/houston/checklists/tests/test_materialization_services.py` — batch + stale-path tests
- `apps/api/houston/realtime/tests/test_checklist_materialization_invalidation.py` — beat-only WS guard
- `apps/api/houston/testing/query_baseline.py` — `EXECUTION_FEED_TWENTY_CHECKLIST_ASSIGNMENTS_MAX_QUERIES`

## Tests inspected

- `test_execution_feed_query_count_with_twenty_visible_assignments` (TS-E1)
- `test_partial_stale_assignment_queries_existing_dates_once` (DB-02)
- `test_ensure_visible_batches_existing_dates_lookup` (new — DB-02b)
- `test_ensure_visible_skips_recently_materialized_assignments`
- `test_horizon_task_emits_execution_created_for_new_materializations` (beat-only WS)

## Docs / rules inspected

- `AGENTS.md`, `apps/api/AGENTS.md`
- `.cursor/rules/01-agent-guardrails.mdc`, `.cursor/rules/10-backend-django-drf.mdc`
- `docs/audits/phase_2_final_roadmap.md` (ROADMAP-15, ROADMAP-20 MAT-01)

## Assumptions / unknowns

- Query ceilings measured on local Docker PostgreSQL test DB only (no prod p95).
- MAT-01 structural read-path write-on-read intentionally **not** addressed in this lot.

---

## Findings

### F1 — Flaky TS-E1 guard (PR #42)
- **ID:** TS-E1-FLAKY
- **Severity:** P2 | **Category:** tests
- **Evidence:** `test_execution_feed_query_count_with_twenty_visible_assignments` originally used `timezone.now()` + `weekday_names[index % 5]` and `assert len(checklist_items) >= 1`.
- **Problem:** Visible assignment count depended on wall-clock weekday; baseline 12 was a false signal.
- **Why it matters now:** CI guard could pass with far fewer than 20 visible items.
- **Why it will hurt later:** Regressions on materialization scaling would not be caught.
- **Fix applied:** `TS_E1_FIXED_NOW` (2026-06-09 12:00 UTC), all 20 assignments on `tuesday`, `assert len == 20`, pre-materialize inside patched `now`.
- **Tests:** `test_execution_feed_query_count_with_twenty_visible_assignments`
- **Size:** S

### F2 — O(N) `existing_dates` SELECT per feed GET
- **ID:** DB-02b
- **Severity:** P1 | **Category:** performance / scalability
- **Evidence:** `ensure_visible_executions_materialized` loop called `_existing_occurrence_dates_for_assignment` once per visible assignment (pre-fix L409–414).
- **Problem:** Steady-state feed GET with N=20 pre-materialized assignments issued **20 identical-structure SELECTs**.
- **Why it matters now:** Measured **28 queries** on TS-E1 before fix (~8 feed + 20 lookups).
- **Why it will hurt later:** Linear PG load per GET at multi-shift establishments.
- **Fix applied:** `_existing_occurrence_dates_for_assignments` — single `checklist_assignment_id__in` + `occurrence_date__in` batch SELECT; three-phase refactor in `ensure_visible_executions_materialized`. Single-assignment wrapper retained for `_assignment_read_path_materialization_is_fresh` fallback.
- **Tests:** `test_ensure_visible_batches_existing_dates_lookup` (3 assignments → 1 batch call); `test_partial_stale_assignment_queries_existing_dates_once` updated to count batch helper.
- **Size:** S

### F3 — MAT-01 remains open (structural)
- **ID:** MAT-01
- **Severity:** P1 | **Category:** scalability / structure
- **Evidence:** `execution_feed.py` L213 — unconditional `ensure_visible_executions_materialized` on every feed GET.
- **Problem:** Read-path materialization loop still O(N) CPU; writes on stale path unchanged.
- **Why it matters now:** Acceptable at pilot scale after batch fix (9 queries at N=20).
- **Why it will hurt later:** Architectural decouple still needed for large establishments / beat-only strategy.
- **Recommended fix:** ROADMAP-20 MAT-01 (deferred). CL-01a `.exists()` early-exit remains WONT_FIX_NOW.
- **Size:** L

---

## Query-count measurement (TS-E1 N=20)

| Phase | `EXECUTION_FEED_TWENTY_CHECKLIST_ASSIGNMENTS_MAX_QUERIES` | Notes |
|-------|-------------------------------------------------------------|-------|
| Before batch (flaky fix only) | 28 | 8 feed + 20 per-assignment `existing_dates` |
| After batch | **9** | 8 feed + 1 assignments SELECT + 1 batched `existing_dates` |

Measured via `CaptureQueriesContext` on `test_execution_feed_query_count_with_twenty_visible_assignments` (Docker PG, 2026-06-29).

---

## Changed

| File | Change |
|------|--------|
| `apps/api/houston/checklists/materialization.py` | Batch helper + 3-phase `ensure_visible_executions_materialized` |
| `apps/api/houston/checklists/tests/test_materialization_services.py` | `test_ensure_visible_batches_existing_dates_lookup`; stale test targets batch helper |
| `apps/api/houston/checklists/tests/test_execution_feed_checklist.py` | Deterministic `TS_E1_FIXED_NOW`, assert 20 visible |
| `apps/api/houston/testing/query_baseline.py` | Baseline 28 → 9 with before/after comment |
| `docs/audits/ts_e1_existing_dates_batch_audit.md` | This report |

## Validated

```bash
make backend-test PYTEST_ARGS="houston/checklists/tests/test_execution_feed_checklist.py houston/checklists/tests/test_materialization_services.py houston/realtime/tests/test_checklist_materialization_invalidation.py -v --tb=short -q"
# 31 passed

make backend-lint
# All checks passed
```

## Risks / not verified

- **MAT-01:** sync materialization on every feed GET; O(N) CPU loop; stale-path writes unchanged.
- **Large IN clauses:** batch query uses `assignment_id IN (...)` + `occurrence_date IN (...)` — fine at pilot N; monitor at 100+ assignments.
- **Prod latency:** local query ceiling only; no production profiling.
- **Product semantics:** unchanged — same rows read, same freshness gate, same materialization decisions.

---

## Top 3 fixes done

1. Deterministic TS-E1 test (fixed date, 20 visible assignments)
2. Batch `existing_dates` lookup (28 → 9 queries)
3. Regression test proving single batch call for N assignments

## Quick wins (done)

- Batch SELECT cross-assignments
- `test_ensure_visible_batches_existing_dates_lookup`

## Structural issues to plan later

- MAT-01 decouple materialization from feed GET
- INDEX-01 if EXPLAIN shows feed filter gaps

## Not worth fixing now

- CL-01a `.exists()` early-exit on empty assignments
- Skip `existing_dates` when `last_materialized_at` is fresh (risks missing deleted executions)
