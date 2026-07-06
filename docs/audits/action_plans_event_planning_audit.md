# Action plans — event planning audit (correction)

Date: 2026-07-06  
Scope: action-plans event planning, schedules, staff/catalog permissions, bootstrap hints.

## Files inspected

- Backend: `services.py`, `schedule_services.py`, `permissions.py`, `selectors.py`, related tests
- Frontend: `action-plan-event-planning-form.*`, `action-plan-form-validation.ts`, `action-plan-schedule-payload.ts`, `action-plan-create-page.tsx`, `action-plan-use-sheet.tsx`, `action-plan-assignees-sheet.tsx`, `action-plan-management-access.ts`, hooks

## Findings and resolution status

| ID | Severity | Status | Summary |
|----|----------|--------|---------|
| AP-01 | P1 | Fixed | Ruff F841/E501 blocking `make verify` |
| AP-02 | P0 | Fixed | Schedule create/update now call `_validate_actor_can_assign_poles` |
| AP-03 | P1 | Fixed | Create flow validates via `validateActionPlanEventPlanningDraft` |
| AP-04 | P1 | Fixed | Schedule payload propagates `use_shared_chronology` and per-assignee times |
| AP-05 | P2 | Fixed | Shared `_assert_staff_self_assignee_payload` helper |
| AP-06 | P2 | Fixed | `action_plan_has_cross_pole_tasks` + subquery SSoT |
| AP-07 | P2 | Fixed | Catalog create gated by bootstrap `can_create_catalog_action_plan` |
| AP-08 | P2 | Fixed | Tests for assignees sheet, use sheet, schedule mutation, cross-pole coherence |
| AP-09 | P3 | Fixed | Removed unused `pilot_business_unit` from `can_assign_to_execution_business_unit` |
| AP-10 | P3 | Fixed | DB filter for `get_active_started_execution_for_schedule` |

## Top fixes delivered

1. RBAC parity between execution launch and schedule assignee paths
2. Planning validation key alignment on create + repeat
3. Schedule payload chronology contract alignment with UI

## Structural backlog (not in this pass)

- Shared assignee validation module (execution vs schedule payloads)
- Split `action-plan-create-page.tsx` orchestration hook
- Broader `_scope_business_unit_ids` public API cleanup

## Validation

- `make backend-lint`
- `make backend-test` (action_plans focus)
- `cd apps/web && npm run typecheck && npm test -- action-plans`
