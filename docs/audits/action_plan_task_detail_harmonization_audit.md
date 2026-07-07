# Action plan task detail harmonization audit

Date: 2026-07-06  
Scope: shared read-only task detail layout for execution rows and template read-only rows.

## Files inspected

- `apps/web/src/features/action-plans/components/action-plan-task-detail-layout.tsx`
- `apps/web/src/features/action-plans/components/action-plan-execution-task-row.tsx`
- `apps/web/src/features/action-plans/components/action-plan-task-read-only-row.tsx`
- `apps/web/src/features/action-plans/pages/action-plan-template-detail-page.tsx`
- `apps/web/src/features/action-plans/lib/action-plan-display.ts`

## Tests inspected

- `action-plan-task-detail-layout.test.tsx`
- `action-plan-task-read-only-row.test.tsx`
- `action-plan-execution-task-row.test.tsx`
- `action-plan-display.test.ts`

## Docs / rules inspected

- `docs/audits/action_plan_execution_task_layout_audit.md`
- `apps/web/AGENTS.md`

## Assumptions

- Creation draft editor (`action-plan-task-draft-editor.tsx`) intentionally stays on its own layout.
- Deadline display keeps date + time via `formatActionPlanTaskDeadlineLabel`.
- Assignee and pole use ` - ` as separator on harmonized rows.

## Findings

| ID | Severity | Category | Evidence | Problem | Recommended fix | Tests | Size |
|----|----------|----------|----------|---------|-----------------|-------|------|
| APTH-01 | P1 | structure | `ActionPlanTaskReadOnlyRow` in template page | Legacy meta line mixed assignee, pole, deadline | Shared layout component | read-only row test | M |
| APTH-02 | P1 | structure | execution row grid cols 2+3 split | Title/meta/menu not on one flex row | `ActionPlanTaskDetailLayout` | layout test | M |
| APTH-03 | P2 | maintainability | inline `TaskTitleMeta` + `formatActionPlanTaskDetailMetaLine` | Duplicate assignee/pole formatting | `formatActionPlanTaskAssigneePoleLine` | display test | S |
| APTH-04 | P2 | ambiguity | `·` separator on execution row | Diverged from product mockup | ` - ` separator in helper | row tests | S |
| APTH-05 | P2 | tests | no template read-only tests | Regression risk | dedicated row + layout tests | new tests | S |
| APTH-06 | P3 | structure | `formatActionPlanTaskDetailMetaLine` unused in UI | Orphan formatter | mark deprecated | — | S |
| APTH-07 | P2 | maintainability | checkbox / terminal status logic | Must stay execution-specific | slots on layout, logic in row | execution row test | S |
| APTH-08 | P3 | ambiguity | template read-only without checkbox | Visual drift vs execution | fixed-width leading spacer | read-only row test | S |
| APTH-09 | P3 | docs | execution layout audit backlog | Template alignment still open | this audit closes backlog item | — | S |
| APTH-10 | P3 | structure | draft editor layout differs | Intentional product split | document exclusion | — | S |

## Product decisions (confirmed)

- Harmonize execution task rows and template read-only rows only.
- Do not harmonize creation draft editor in this scope.
- Layout target:
  - line 1: leading + title + assignee/pole meta + optional actions menu
  - line 2: deadline under title
  - blank line before description
  - description aligned to the right of the leading column

## Resolution

Implemented per plan `task_detail_harmonization`:

- `formatActionPlanTaskAssigneePoleLine` in `action-plan-display.ts`
- `ActionPlanTaskDetailLayout` shared presentational grid/flex
- `ActionPlanExecutionTaskRow` refactored to use shared layout
- `ActionPlanTaskReadOnlyRow` extracted to dedicated component
- `formatActionPlanTaskDetailMetaLine` marked deprecated for UI usage

## Top 3 fixes (done)

1. APTH-01 + APTH-02 — shared layout
2. APTH-03 + APTH-04 — shared assignee/pole formatter
3. APTH-05 — tests for layout and read-only row

## Quick wins (done)

- APTH-08 — leading spacer on template read-only rows
- APTH-06 — deprecated legacy detail meta formatter

## Structural backlog

- Update `besoin_evolution_action.md` section 16 for flat task list + harmonized row layout.
- Optional: remove deprecated `formatActionPlanTaskDetailMetaLine` once no callers remain.

## Not worth fixing now

- Harmonizing feed card assignee display.
- Harmonizing creation draft editor layout.

## Explicit exclusions

- `apps/web/src/features/action-plans/components/action-plan-task-draft-editor.tsx`
- `formatActionPlanTaskEditorMetaLine`
