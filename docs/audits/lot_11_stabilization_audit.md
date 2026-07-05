# Lot 11 — Stabilization post-purge Action/Checklist

Status: completed  
Date: 2026-07-05  
Scope: test hygiene, code micro-fixes, doc alignment — **no API contract changes**

## Files inspected

- Backend: `action_plans/`, `comments/`, `notifications/`, `signals/api/views.py`, `schema.yml`
- Frontend: `action-plans/`, `execution/`, `realtime/`, `query-invalidation.ts`, generated `types.ts`
- Tests: `report-page.test.tsx`, `hooks.mutations.test.ts`, `test_scheduling_failure_logging.py`, `auth/api.test.ts`, `api-user-search.test.ts`
- Docs: `feed_domain.md`, signal/observation/realtime/notification/comments/RBAC domains, README, Makefile, `api_pagination_standard.md`

## Tests inspected

- Parity tests (`query-invalidation-parity`, `operational-invalidation-contract`) — already correct pre-Lot 11
- Fragile fixtures updated (see findings below)

## Docs/rules inspected

- Product domain docs (7 files rewritten/aligned)
- Operator docs (README, INSTALL_MAC, Makefile, `shared_dev_database.md`)
- Agent commands (`.cursor/commands/domain-lifecycle-change.md`, `test-audit.md`)
- Archive banners (`event_catalogue_v0.1.md`, `notification_matrix_v0.2.md`)

## Assumptions

- `comment.execution.*` remains the live realtime contract for `action_plan_execution` comments (not renamed)
- `can_create_action()` establishment helper kept as live alias for action plan permissions (rename deferred)

---

## Findings — resolved

| ID | Severity | Action taken | Evidence |
|----|----------|--------------|----------|
| F11-03 | P2 | Removed dead `useChecklistReportSubmitMutation` mock | `report-page.test.tsx`; `rg` — hook absent from `hooks.ts` |
| F11-04 | P2 | Notification fixtures → `action_plan.execution.created` / `action_plan_execution` | `hooks.mutations.test.ts`, `test_scheduling_failure_logging.py` |
| F11-05 | P2 | Auth cache test → `['action-plans', 'detail', …]` | `auth/api.test.ts` |
| F11-06 | P2 | Signal resolve copy → "linked action plans" | `signals/api/views.py` L436 |
| F11-07 | P2 | Archive banners on event catalogue + notification matrix | `event_catalogue_v0.1.md`, `notification_matrix_v0.2.md` |
| F11-08 | P3 | Scheduler wording → action-plan schedule horizon | README, INSTALL_MAC, Makefile, `shared_dev_database.md` |
| F11-09 | P3 | Removed unused `scheduleDetail` query key | `rg scheduleDetail` → 1 hit (definition only) before removal |
| F11-01 | P1 | Rewrote `feed_domain.md` §4–§12 for plan-only feed | Aligned with `schema.yml` |
| F11-02 | P1 | Aligned 6 domain docs with `schema.yml` | signal, observation, realtime, notification, comments, RBAC |
| F11-10 | P3 | Documented `comment.execution.*` in realtime/comments domains | Emitters unchanged |

## Findings — declined (out of scope)

| Item | Reason |
|------|--------|
| Rename `can_create_action` → `can_create_action_plan` | Cross-cutting; establishment helper still used by `action_plans/permissions.py` |
| Rename `comment.execution.*` → `comment.action_plan_execution.*` | Working live contract; explicit guardrail to preserve |
| Bulk archive `docs/audits/*` | Banner in `docs/audits/README.md` only |
| Component/file renames (`action-detail-tabs`, `signal-create-action.ts`) | Cosmetic; no functional drift |

## Confirmed stable (no changes needed)

- No `houston/actions` or `houston/checklists` apps
- OpenAPI + generated types: ActionPlan-only surface
- Production query keys, realtime contract, notification enums — action_plan scoped
- Execution feed page + backend selector — plan-only

## API contract checklist

| Check | Result |
|-------|--------|
| `schema.yml` modified by Lot 11 | **No** |
| `generated/types.ts` modified by Lot 11 | **No** (Lot 11 edits did not touch this file) |
| `make schema` / `web-api-generate` run | **No** |

## Validations executed

```bash
cd apps/web && npm run typecheck          # pass
cd apps/web && npm test -- report-page api.test hooks.mutations api-user-search  # 25 tests pass
docker compose exec -T api uv run pytest houston/notifications/tests/test_scheduling_failure_logging.py -q  # 1 pass
```

## `scheduleDetail` gate

Pre-removal: `rg scheduleDetail` → 1 occurrence (`action-plans/api.ts` definition). Removed.

## `comment.execution.*` preserved

Live emitters in `comments/services.py`; contract in `contracts/operational-realtime-invalidation.json`; frontend handler in `apply-operational-invalidation.ts`. Documented in `realtime_domain.md` and `comments_domain.md`.

---

## Top 3 fixes delivered

1. Test hygiene — dead mocks and legacy enum fixtures removed
2. Code micro-fixes — signal copy, `scheduleDetail` removal, aria-label
3. Doc alignment — feed + domain docs + operator docs

## Risks / not verified

- Full `make verify` not run
- Signal resolve copy change is user-visible HTTP `detail` text only (no new error code)
- Older `docs/audits/*` files still contain pre-Lot 10 paths — use `docs/audits/README.md` guardrail
