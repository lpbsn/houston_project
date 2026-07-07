# Action plan task pole UX audit

Date: 2026-07-06  
Scope: task pole Option A (empty default, explicit picker), detail display, execution row layout.

## Files inspected

- `apps/web/src/features/action-plans/components/action-plan-task-draft-editor.tsx`
- `apps/web/src/features/action-plans/pages/action-plan-create-page.tsx`
- `apps/web/src/features/action-plans/pages/action-plan-template-detail-page.tsx`
- `apps/web/src/features/action-plans/components/action-plan-execution-task-row.tsx`
- `apps/web/src/features/action-plans/lib/action-plan-display.ts`
- `apps/web/src/features/action-plans/lib/action-plan-form-validation.ts`
- `apps/web/src/features/action-plans/lib/action-plan-create-payload.ts`
- `apps/web/src/features/action-plans/components/action-plan-pole-section.tsx`

## Tests inspected

- `action-plan-display.test.ts`
- `action-plan-execution-task-row.test.tsx`
- `action-plan-form-validation.test.ts`
- No dedicated draft editor pole UX tests before this fix

## Docs/rules inspected

- `docs/audits/action_plan_task_enrichment_audit.md`
- `AGENTS.md`, `apps/web/AGENTS.md`

## Assumptions

- `business_unit` remains required at persistence; empty is draft-only
- Execution detail groups tasks by pole section header — row meta should not repeat pole
- Staff tasks must stay on pilot pole (existing validation)

## Findings

| ID | Severity | Category | Evidence | Problem | Recommended fix | Tests | Size |
|----|----------|----------|----------|---------|-----------------|-------|------|
| APTP-01 | P1 | ambiguity | draft editor `resolvedBusinessUnitId`; create page `resolvedTasks` backfill | Pilot pole injected silently | Remove fallbacks; use `task.businessUnitId` only | create form validation | S |
| APTP-02 | P1 | structure | draft editor cross-pole branch vs read-only | Non cross-pole cannot pick pole (Option A) | Single `PlanningOptionRow` for all users | draft editor test | M |
| APTP-03 | P2 | maintainability | `formatActionPlanTaskMetaLine` shared across editor/execution/template | One formatter, three UX contexts | Split editor vs detail formatters | display test | S |
| APTP-04 | P2 | structure | execution row menu only on pending | Meta shifts right when done/skipped | Permanent `w-10` spacer column | execution row test | S |
| APTP-05 | P2 | ambiguity | `createActionPlanTaskDraftEditorItem(pilotBusinessUnitId)` | New task pre-fills pilot pole | Add task with empty pole | validation test | S |
| APTP-06 | P2 | security | create page scopes units; template detail passes full tree | Manager may pick out-of-scope poles on template edit | Shared `resolveVisibleBusinessUnits` | util test | S |
| APTP-07 | P2 | tests | no draft editor pole tests | Regression risk on core UX | Add targeted component tests | new test file | M |
| APTP-08 | P3 | ambiguity | API always returns `business_unit`; execution grouped by pole | Pole in execution row redundant | Execution meta without pole | execution row test | S |
| APTP-09 | P3 | structure | assignee sheet uses pilot fallback | Assignee pickable before task pole chosen | Gate assignee on `task.businessUnitId` | draft editor test | S |
| APTP-10 | P2 | API contract | frontend accepts 0 tasks; backend requires task or assignee | Contract drift | Backlog — align validation | — | S |

## Top 3 fixes

1. APTP-01 + APTP-05 — remove pilot fallbacks
2. APTP-02 + APTP-06 — unified picker + scoped business units
3. APTP-04 + APTP-03 + APTP-08 — execution layout + contextual formatters

## Quick wins

- Permanent `w-10` spacer on execution row
- `createActionPlanTaskDraftEditorItem()` without pilot
- Editor meta line without pole

## Structural backlog

- Template save validation (silent filter in `buildTaskPayloads`)
- Align « at least one task » frontend/backend (APTP-10)

## Not worth fixing now

- Nullable `business_unit` backend
- `pole_explicit` DB field
- Feed task preview pole enrichment

## Resolution

Implemented per plan `task_pole_ux_fix` (frontend only, no backend migration).
