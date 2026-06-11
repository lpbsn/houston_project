# Code Scalability Audit — Phase S0

**Date:** 2026-06-11  
**Mode:** read-only orientation  
**Scope:** full stack (backend, frontend, API, DB, async, fixtures, tests)  
**Prerequisite:** Phase A (CI) validated  
**Next roadmap order:** B → C → D → K → L → M → P → E → F → G → H → I → S1

Events, production/staging readiness, and generic realtime platform are **out of scope** (deferred).

---

## 1. Executive summary

**Overall scalability posture:** Medium. Core domains use explicit services/selectors/permissions with strong API test coverage. Risk concentrates in **hot feed paths** (N+1, full-table counts, read-path writes), **permission model drift**, **frontend bundle/invalidation breadth**, **uploads opacity**, and **test gaps** (no query-count tests, missing permission unit files).

### Top 5 scalability risks

| # | Risk | Evidence | Phase |
|---|------|----------|-------|
| 1 | Execution feed materializes on every GET + full counts | `actions/execution_feed.py` L33–43 | G, L |
| 2 | Signal feed full `queryset.count()` + serializer N+1 | `signals/api/views.py` L157–158; `signals/api/serializers.py` L71–74 | E, L |
| 3 | Chat conversation list N+1 (latest message per row) | `chat/api/views.py` L176–206 | L, S1 |
| 4 | RBAC scope drift (checklist vs establishment; signal detail vs feed scope) | `checklists/permissions.py` L29–30; `signals/selectors.py` L130–138 | B |
| 5 | Frontend monolithic bundle + broad query invalidation | `App.tsx` static imports; `index-*.js` 733 kB; `actions/hooks.ts` invalidates `signalsQueryKeys.all` | P, H |

### Top 5 quick wins (post-S0)

1. Fix signal feed serializer to use prefetched links/media — **E**
2. Align checklist `_is_active_membership` → `_is_valid_membership` — **B**
3. Lazy-load terrain route pages — **P**
4. Batch chat list latest-message fetch — **L** or **S1**
5. Mechanical deprecated `terrain-card` import codemod — **H** / **S1**

---

## 2. Methodology

| Dimension | Commands / technique |
|-----------|---------------------|
| Backend structure | Read views, services, selectors, permissions across 7 domains |
| Frontend structure | `wc -l features/**/pages/*.tsx`; grep imports, invalidation, casts |
| API contract | Compare `schema.yml`, bootstrap serializer, CI drift gate (Phase A) |
| Database | Grep `select_related`/`prefetch_related`; model `Meta.indexes`; feed view count patterns |
| Async | Grep `tasks.py`, `on_commit`, `CELERY_BEAT_SCHEDULE`, retry config |
| FE performance | `npm run build` chunk output |
| Fixtures/dev | `Makefile` bootstrap/shared-dev targets; guard scripts |
| Tests | Inventory `test_permissions.py`; grep `assertNumQueries`, `@pytest.mark.slow` |

**Not verified:** `houston/uploads/` (`.cursorignore`-blocked); runtime EXPLAIN; load tests; live shared-dev DB contents.

---

## 3. Findings by dimension

### 3.1 Backend structure

| ID | Pri | Finding | Files | Phase |
|----|-----|---------|-------|-------|
| BE-S01 | P2 | Establishments views module ~1,726 lines; inline exception→HTTP mapping | `establishments/api/views.py` | S1 |
| BE-S02 | P2 | Chat list serialization in view, not selector | `chat/api/views.py` L176–207, L288–304 | S1 |
| BE-S03 | P2 | Checklist template list queryset shaping in view | `checklists/api/views.py` L182–188 | S1 |
| BE-S04 | P2 | Assignment create bypasses selector with direct ORM | `checklists/api/views.py` L648–655 | S1 |
| BE-S05 | P2 | Cross-domain service edges (actions↔signals, checklist→observations) | `actions/services.py`, `signals/services.py`, `checklists/services.py` | S1 (document) |
| BE-S06 | P1 | `create_registered_checklist_template` multi-write without outer `@transaction.atomic` | `checklists/services.py` L867–909 | G, S1 |

**Positive:** Signals/actions command views, observations submit, and most checklist mutations follow thin-view → service pattern.

---

### 3.2 Serializer weight & representation hot paths

| ID | Pri | Finding | Files | Phase |
|----|-----|---------|-------|-------|
| BE-SER01 | P1 | Signal feed item: per-row `source_observation_links…first()` + `media_items.count()` despite prefetch | `signals/api/serializers.py` L62–74 | E |
| BE-SER02 | P1 | Signal detail repeats same extra queries | `signals/api/serializers.py` L117–143 | E |
| BE-SER03 | P2 | Permission hints evaluated in serializer hot path | `signals/api/serializers.py`, `actions/api/serializers.py`, `checklists/permission_hints.py` | D, S1 |
| BE-SER04 | P2 | Checklist feed item fallback: 2 COUNT queries when annotations missing | `checklists/feed_serializers.py` L42–51 | G |

---

### 3.3 RBAC & permission consistency

| ID | Pri | Finding | Files | Phase |
|----|-----|---------|-------|-------|
| BE-RBAC01 | P1 | Checklist uses `_is_active_membership` (status only) vs establishments `_is_valid_membership` (org/estab/user active) | `checklists/permissions.py` L29–30 vs `establishments/permissions.py` | B |
| BE-RBAC02 | P1 | Signal detail: `_can_view_signal_detail` checks feed capability only, not manager BU scope applied in feed | `signals/selectors.py` L104–108 vs L130–138 | B |
| BE-RBAC03 | P1 | Checklist management = any active member; establishments membership management = owner/director | `checklists/permissions.py` L80–81 vs `establishments/permissions.py` L44–45 | B |
| BE-RBAC04 | P1 | Execution feed: only `HasActiveMembership`; signal feed has `CanViewSignalFeed` | `actions/api/views.py` L94–97 vs `signals/api/views.py` | B |
| BE-RBAC05 | P2 | Duplicated `_ADMIN_ROLES` / `_MANAGEMENT_ROLES` in checklists, signals, actions, chat | `checklists/permissions.py` L13–26; `signals/permissions.py`; `actions/permissions.py` | B, S1 |
| BE-RBAC06 | P2 | Checklist visibility scope filters `business_unit_id` on executions; signals/actions use affected **or** responsible BU | `checklists/permissions.py` L64–77 vs `membership_scope.py` | B, L |

---

### 3.4 API contract & bootstrap

| ID | Pri | Finding | Files | Phase |
|----|-----|---------|-------|-------|
| API-01 | P2 | Bootstrap lacks `permission_hints` / `chat_available` — FE infers via extra calls | `accounts/api/serializers.py`; `App.tsx` chat gating | D |
| API-02 | P1 | Signal feed `next_cursor` in schema always `None`; `has_more` via full count | `signals/api/views.py` L157–158; `schema.yml` | E |
| API-03 | P1 | Execution feed `next_cursor` hardcoded `None`; merge pagination not true merge-sort | `actions/api/views.py`; `execution_feed.py` L55–68 | E, G |
| API-04 | P2 | Unbounded list endpoints: checklist templates/assignments, membership roster, chat conversations | `checklists/api/views.py`; `establishments/api/views.py`; `chat/api/views.py` | L, S1 |
| API-05 | P1 | Upload endpoints in schema; module un-auditable, no dedicated tests | `schema.yml`; `houston/uploads/` (blocked) | C |
| API-06 | P2 | FE unsafe casts concentrated in onboarding/auth API (~44 `as` usages) | `onboarding/api.ts`, `auth/api.ts` | H, S1 |

**Positive:** Phase A CI now enforces `schema.yml` drift via `spectacular` + `git diff`.

---

### 3.5 Database & query performance

| ID | Pri | Finding | Files | Phase |
|----|-----|---------|-------|-------|
| DB-01 | P0 | Execution feed: `ensure_visible_executions_materialized` on every read + 2× full `count()` | `actions/execution_feed.py` L33–43 | G, L |
| DB-02 | P1 | Signal feed: full `queryset.count()` for `has_more` | `signals/api/views.py` L158 | E, L |
| DB-03 | P1 | Chat conversation list: `get_latest_message(conversation.id)` per row; participants iterated twice | `chat/api/views.py` L181–206 | L, S1 |
| DB-04 | P1 | Signal serializer N+1 (see BE-SER01) despite good selector prefetch | `signals/selectors.py` L22–32 | E |
| DB-05 | P2 | Checklist permissions: `membership.scope_links.all()` without prefetch on hot paths | `checklists/permissions.py` L40–45 | B, L |
| DB-06 | P2 | Missing composite indexes for manager BU scope on checklist models | `checklists/models.py` L64–67, L233–238 | L |
| DB-07 | P3 | `EstablishmentMembership` list: no composite `(establishment, status, role)` index | `establishments/models.py` L383–388 | L |

**Positive:** Chat messages use cursor pagination; signal/action/checklist selectors use `select_related`/`annotate` at queryset layer.

---

### 3.6 Async / Celery

| ID | Pri | Finding | Files | Phase |
|----|-----|---------|-------|-------|
| ASYNC-01 | P0 | Stuck `PROCESSING` if worker dies mid-pipeline; no stale-state recovery | `signals/services.py` L464–488 | M, K |
| ASYNC-02 | P0 | Upload TTL setting exists; no Celery beat purge task found | `settings.py` L117; `CELERY_BEAT_SCHEDULE` | C, M |
| ASYNC-03 | P1 | No `time_limit` / `soft_time_limit` / `acks_late` on any task | All `tasks.py`; `settings.py` Celery block | M |
| ASYNC-04 | P1 | Checklist/chat tasks declare `max_retries=3` but never call `self.retry()` | `checklists/tasks.py`, `chat/tasks.py` | M |
| ASYNC-05 | P1 | Observations `on_commit` enqueue lacks rollback test (chat has one) | `observations/tests/test_submit_on_commit_enqueue.py` | M, K |
| ASYNC-06 | P2 | `bootstrap-dev` / `shared-dev-up` omit `celery-beat` — scheduled jobs silent | `Makefile` L16–18, L60, L75 | I, M |

**Positive:** Observation pipeline idempotency via `select_for_update` + status gate; chat purge task + beat entry; checklist materialization idempotent via uniqueness.

---

### 3.7 Frontend structure & performance

| ID | Pri | Finding | Files | Phase |
|----|-----|---------|-------|-------|
| FE-01 | P1 | No route lazy loading — 24 static page imports in `App.tsx` | `App.tsx` L19–55 | P |
| FE-02 | P1 | Main JS chunk **733 kB** (Vite warns >500 kB) | `npm run build` → `dist/assets/index-*.js` | P |
| FE-03 | P1 | Broad TanStack invalidation: action mutations invalidate all signals; checklist mutations invalidate all actions | `actions/hooks.ts`, `checklists/hooks.ts`, `signals/hooks.ts` | H, P |
| FE-04 | P1 | 4 pages >300 lines; `app-page` (421) and `report-page` (424) mix orchestration + UI | See §3.8 page table | H |
| FE-05 | P1 | Duplicated `getErrorMessage` ×8 pages; `toRoleEnum` ×3 copies | 8 terrain pages; `profile-page`, `team-invite-page`, `checklist-hub-page` | H, S1 |
| FE-06 | P2 | FE RBAC matrices duplicate backend rules | `invitation-rbac.ts`, `membership-rbac.ts`, `operational-config-access.ts`, `app-page.tsx` `MANAGEABLE_ROLES` | D, H |
| FE-07 | P3 | 11 files still import deprecated `@/components/layout/terrain-card` | Checklist cluster + `profile-page.tsx` | H, S1 |
| FE-08 | P2 | `App.tsx` itself 576 lines — routing shell not decomposed | `App.tsx` | H, S1 |

**Positive:** Checklists use centralized `resolveChecklistErrorMessage`; newer domains (signals/actions/checklists API) use typed client + `parseStandardApiError`; chat hooks scope invalidation to establishment.

---

### 3.8 Frontend page sizes (lines)

| Lines | File |
|------:|------|
| 424 | `features/observations/pages/report-page.tsx` |
| 421 | `features/auth/pages/app-page.tsx` |
| 326 | `features/onboarding/pages/onboarding-page.tsx` |
| 315 | `features/actions/pages/action-create-page.tsx` |
| 291 | `features/checklists/pages/checklist-execution-detail-page.tsx` |
| 281 | `features/checklists/pages/checklist-template-create-page.tsx` |

23 page files total; 4 exceed 300-line threshold.

---

### 3.9 Fixtures & dev ergonomics

| ID | Pri | Finding | Files | Phase |
|----|-----|---------|-------|-------|
| DEV-01 | P1 | `catalog-check` hardcodes 14 BUs / 134 subjects in Makefile shell — duplicated from import tests | `Makefile` L57–58, L95–96 | I |
| DEV-02 | P1 | Fresh bootstrap does not start celery-beat; horizon/purge jobs won't run until `make up-scheduler` | `Makefile` | I |
| DEV-03 | P2 | Observations API tests reimplement `create_user`/`create_establishment` instead of `testing/factories.py` | `observations/tests/test_observation_api.py` L26–53 | I, S1 |
| DEV-04 | — | Shared-dev guards strong (remote DB, no local postgres in worker stack) | `assert-shared-dev-compose.sh`, `assert-local-dev-db.sh` | — |

---

### 3.10 Test coverage gaps

| ID | Pri | Finding | Files | Phase |
|----|-----|---------|-------|-------|
| TST-01 | P1 | **Zero** `assertNumQueries` / query-count tests repo-wide | Entire `apps/api` | E, G, L, K |
| TST-02 | P1 | No dedicated `test_permissions.py` for signals, chat, observations | `signals/permissions.py`, `chat/permissions.py` | B, K, S1 |
| TST-03 | P1 | Enqueue tests patch `_enqueue_observation_processing` helper — skip real `on_commit` + `.delay()` chain | `observations/tests/test_submit_on_commit_enqueue.py` | M, K |
| TST-04 | P2 | Only **1** `@pytest.mark.slow` usage; golden pipeline tests unmarked | `chat/tests/test_ws_ticket_api.py` L129 | S1 |
| TST-05 | P2 | Chat purge: service tested, Celery task wrapper not | `chat/tests/test_purge.py` vs `chat/tasks.py` | M |
| TST-06 | P2 | No test that double pipeline run on PROCESSED observation is no-op | `signals/services.py` | M, K |

**Positive:** ~100 backend / ~53 frontend test modules; root `conftest.py` fake AI guard; establishments/checklists/actions have permission unit tests.

---

## 4. Priority matrix

| Priority | Count | Themes |
|----------|------:|--------|
| **P0** | 4 | Read-path materialization; stuck PROCESSING; missing upload purge; (execution feed scale) |
| **P1** | 28 | Feed N+1/counts; RBAC drift; pagination; async timeouts; FE bundle/invalidation; test gaps |
| **P2** | 22 | Fat views; serializer hints; indexes; casts; factory duplication; dev brittleness |
| **P3** | 5 | Deprecated imports; minor index tuning; overdue helper duplication |

---

## 5. Phase routing (S0 → hardening phases)

Each finding maps to the **recommended implementation phase** from the hardening roadmap.

| Phase | Address from S0 |
|-------|-----------------|
| **B** | BE-RBAC01–06: membership validation, signal detail scope, execution feed permission class, role constant dedup |
| **C** | API-05, ASYNC-02: uploads audit, TTL purge, dedicated upload tests |
| **D** | API-01, BE-SER03, FE-06: bootstrap `permission_hints`, reduce FE RBAC duplication |
| **K** | ASYNC-01 diagnostics, pipeline failure visibility, ASYNC-05 rollback test |
| **L** | DB-01–07: query-count baselines, EXPLAIN on hot feeds, indexes, unbounded lists |
| **M** | ASYNC-01–05: stuck PROCESSING recovery, Celery timeouts, retry config, on_commit tests |
| **P** | FE-01–03: lazy routes, chunk budget, narrow invalidation |
| **E** | BE-SER01–02, API-02, DB-02–04: signal feed N+1, cursor/count fix |
| **F** | (WS session revalidation — see `chat_v1_technical_debt`; not re-audited in depth here) |
| **G** | DB-01, BE-SER04, BE-S06, API-03: checklist materialization cost, feed merge pagination |
| **H** | FE-03–08, API-06, FE-05–07: helpers, hooks extraction, casts, terrain imports |
| **I** | DEV-01–03, ASYNC-06: bootstrap determinism, factory reuse, scheduler docs |
| **S1** | BE-S01–05, remaining P2/P3 cleanup, TST-04, unbounded list pagination, chat list batching |

### Recommended execution order (unchanged from roadmap)

```
A ✓ → S0 ✓ → B → C → D → K → L → M → P → E → F → G → H → I → S1
```

S0 does **not** reorder phases; it confirms B/C/D and feed perf (E/G/L) as highest-value tranches after CI.

---

## 6. Cross-reference to prior audits

| Doc | Relationship |
|-----|--------------|
| `docs/audit/chat_v1_technical_debt_2026-06-09.md` | F phase: WS session binding, bootstrap `chat_available` |
| `docs/audit/checklist_audit_2026-06-09.md` | SUPERSEDED — G/H items partially overlap S0 checklist findings |
| `.cursor/plans/houston_full_audit_a969d0b9.plan.md` | Parent roadmap; S0 satisfies orientation deliverable |

---

## 7. Definition of Done (Phase S0)

- [x] Concrete findings with file + function references
- [x] Priority list P0–P3
- [x] Files impacted per finding
- [x] Recommended target phase per finding
- [x] No application code diffs

---

**Changed:** `docs/audit/code_scalability_s0_2026-06-11.md` (this document only).  
**Validated:** Read-only exploration across 8 audit dimensions; build chunk baseline (733 kB main bundle); grep-backed query-count and permission test inventory.  
**Risks / not verified:** `houston/uploads/` implementation; runtime EXPLAIN; whether signal detail scope gap is intentional product choice vs bug; full CI green after Phase A on GitHub Actions.
