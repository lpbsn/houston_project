# DB Scalability — Phase L Baselines

**Date:** 2026-06-11  
**Phase:** L (query-count baselines + index evidence notes)  
**Prerequisite:** Phases A, S0, B, C, D, K complete  
**Parent:** [`code_scalability_s0_2026-06-11.md`](code_scalability_s0_2026-06-11.md)

Phase L establishes **fixture-scale query-count ceilings** for hot read endpoints before feed optimizations (E/G). No application query changes, no blind index migrations, no EXPLAIN in CI.

---

## 1. Methodology

| Item | Detail |
|------|--------|
| Tool | `django.test.utils.CaptureQueriesContext` via `houston.testing.query_baseline` |
| DB | PostgreSQL test database (`make backend-test` / Docker `api` service) |
| Auth | Full APIClient request (Bearer token + CSRF), same as existing API tests |
| Fixture scale | Small deterministic datasets (1–3 rows per list) |
| Assertions | Upper-bound `assert_query_count_at_most` + optional 1→3 scaling delta caps |
| Constants | `houston/testing/query_baseline.py` (single source for test ceilings) |

**Not in CI:** `EXPLAIN ANALYZE` — manual/dev only (see §4).

---

## 2. Measured baselines (fixture-scale)

| Endpoint | Fixture | Queries | Test | S0 IDs |
|----------|---------|--------:|------|--------|
| `GET .../signals/feed/?view_mode=general` | Owner, 2 signals | **11** | `test_signal_feed_query_count_baseline_two_items` | DB-02, DB-04, TST-01 |
| Same (1→3 items delta) | +2 signals | **≤2** extra | `test_signal_feed_query_count_grows_with_item_count` | BE-SER01 |
| `GET .../execution-feed/?view_mode=general` | Owner, empty feed | **9** | `test_execution_feed_query_count_baseline_empty` | DB-01 |
| `GET .../execution-feed/?view_mode=personal` | Staff, 1 checklist execution | **13** | `test_execution_feed_checklist_query_count_baseline` | DB-01, G prep |
| `GET .../chat/conversations/` | 3 DMs, 1 message each | **12** | `test_chat_conversations_list_query_count_baseline` | DB-03 |
| Same (1→3 conv delta) | +2 conversations | **≤2** extra | `test_chat_conversations_list_query_count_grows_with_list_size` | DB-03 |
| `GET .../conversations/{id}/messages/` | 1 message, default page | **10** | `test_chat_messages_list_query_count_baseline` | DB-03 |

### Known hot-path costs (unchanged in L)

1. **Signal feed** — `queryset.count()` for `has_more` (`signals/api/views.py`); serializer per-row `source_observation_links` + `media_items.count()` (`signals/api/serializers.py`).
2. **Execution feed** — `ensure_visible_executions_materialized` on every GET; `action_qs.count()` + `checklist_qs.count()` (`actions/execution_feed.py`).
3. **Chat conversations** — `get_latest_message(conversation.id)` per row; participants iterated twice (`chat/api/views.py` `_serialize_conversation_list_item`).

---

## 3. Unbounded list endpoints (API-04)

Documented for S1 pagination decisions. Threshold guidance: investigate pagination when typical establishment exceeds **~50 rows** per list under normal ops.

| Endpoint | Module | Pagination today | Risk |
|----------|--------|------------------|------|
| `GET .../checklists/templates/` | `checklists/api/views.py` | None (full list) | Grows with template catalog per establishment |
| `GET .../checklists/assignments/` | `checklists/api/views.py` | None | Grows with active assignments |
| `GET .../memberships/` (roster) | `establishments/api/views.py` | None | Grows with team size |
| `GET .../chat/conversations/` | `chat/api/views.py` | None | Grows with DM/group count; compounds DB-03 N+1 |
| `GET .../chat/eligible-memberships/` | `chat/api/views.py` | None | Grows with active memberships |

**Paginated (reference):** signal feed (`page_size` + cursor), execution feed (`page_size` only — cursor gap P0), chat messages (`page_size` + cursor).

**Pagination standard (2026-06-13):** Full classification and tickets — [`pagination_audit_2026-06-13.md`](pagination_audit_2026-06-13.md), [`api_pagination_standard.md`](../engineering/api_pagination_standard.md).

---

## 4. Index candidates (DB-06, DB-07) — EXPLAIN evidence notes

**No migrations in Phase L.** Run locally via `make shell` when validating:

```sql
EXPLAIN ANALYZE <query>;
```

### DB-06 — Checklist manager BU scope

**Context:** `build_checklist_visibility_scope_q` filters `ChecklistExecution` with `business_unit_id__in=bu_ids` (`checklists/permissions.py`). Feed queryset uses `checklist_exec_feed_idx` on `(establishment, status, visible_from, last_activity_at)` but not `business_unit_id`.

**Candidate index (evidence pending):**

```text
ChecklistExecution: (establishment_id, business_unit_id, status, visible_from)
```

**Manual check:** With manager membership scoped to 1–3 BUs and 100+ executions, compare seq scan vs bitmap index scan on `business_unit_id` filter combined with `visible_from <= now()`.

**Related:** `membership.scope_links.all()` in `_scope_business_unit_ids` (DB-05) — prefetch on membership before permission checks may reduce repeated scope queries; not measured as feed-hot in L fixtures.

### DB-07 — Establishment membership roster

**Context:** Roster/list endpoints filter `EstablishmentMembership` by `establishment` + often `status` + `role`. Current indexes are single-column (`membership_est_idx`, `membership_status_idx`, `membership_role_idx`).

**Candidate index (evidence pending):**

```text
EstablishmentMembership: (establishment_id, status, role)
```

**Manual check:** `EXPLAIN` on active-membership roster query for an establishment with 50+ members.

---

## 5. BE-RBAC06 / checklist BU scope (measurement note)

Checklist visibility uses **snapshot `business_unit_id` on executions only** (not affected/responsible dual scope like signals/actions). At fixture scale, checklist execution feed baseline (**13 queries**) is dominated by materialization + dual `count()`, not scope-link iteration.

**Follow-up:** If manager scoped to many BUs shows feed latency, profile `_scope_business_unit_ids` + `business_unit_id__in` filter under realistic assignment volume (Phase G/S1).

---

## 6. Phase L definition of done

- [x] Query-count baselines for all four hot endpoint groups (signal feed, execution feed, checklist-in-feed, chat list + messages)
- [x] Scaling delta tests document per-item N+1 where present
- [x] EXPLAIN/index notes for DB-06, DB-07 (evidence-only)
- [x] API-04 unbounded list inventory
- [x] No feed optimizations, no index migrations, no EXPLAIN in CI

**Commands:**

```bash
docker compose exec api uv run pytest \
  houston/signals/tests/test_signal_feed_api.py \
  houston/actions/tests/test_execution_feed_api.py \
  houston/checklists/tests/test_execution_feed_checklist.py \
  houston/chat/tests/test_rest_api.py -q -k query_count
make backend-migrations-check
```

**Rollback:** Revert test assertions and `query_baseline.py` constants; delete this doc if abandoning baselines.

---

**Changed:** `houston/testing/query_baseline.py`; query-count tests in signal/action/checklist/chat test modules; this audit appendix.  
**Validated:** Targeted pytest `-k query_count` (Docker api).  
**Risks / not verified:** Runtime `EXPLAIN ANALYZE` on production-like row counts; CI query-count gate not yet added to GitHub workflow (deferred from Phase A).
