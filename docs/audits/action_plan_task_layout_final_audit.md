# Action plan task layout final audit

Date: 2026-07-06  
Scope: final spacing and column layout fix for shared task detail rows (execution + template read-only).

## Files inspected

- `apps/web/src/features/action-plans/components/action-plan-task-detail-layout.tsx`
- `apps/web/src/features/action-plans/components/action-plan-execution-task-row.tsx`
- `apps/web/src/features/action-plans/components/action-plan-task-read-only-row.tsx`

## Tests inspected

- `action-plan-task-detail-layout.test.tsx`
- `action-plan-execution-task-row.test.tsx`
- `action-plan-task-read-only-row.test.tsx`

## Docs / rules inspected

- `docs/audits/action_plan_task_detail_harmonization_audit.md`
- `docs/audits/action_plan_execution_task_layout_audit.md`

## Assumptions

- Deadline always renders in the right `metaStack` column, even without assignee or pole.
- Creation draft editor remains out of scope.
- Terminal status label stays under deadline in `metaStack`.

## Findings

| ID | Severity | Category | Problem | Resolution |
|----|----------|----------|---------|------------|
| APTF-01 | P0 | structure | Menu `h-10` in title flex inflated grid row height | Actions moved to dedicated column 4 |
| APTF-02 | P0 | ambiguity | Deadline under title instead of under assignee/pole meta | `metaStack` column with stacked meta + deadline |
| APTF-03 | P1 | structure | `mt-2` gap before description too small | `mt-4` on description |
| APTF-04 | P1 | structure | Menu in title flex caused premature wrapping | Isolated actions column with `self-center` |
| APTF-05 | P2 | tests | Layout tests asserted obsolete DOM structure | Updated layout/read-only/execution tests |
| APTF-06 | P2 | tests | No coverage for deadline without meta | Added read-only + layout tests |
| APTF-07 | P3 | maintainability | Dynamic `descriptionRowStart` logic fragile | Explicit 4-column grid |
| APTF-08 | P3 | ambiguity | Terminal status placement unclear | Status under deadline in `metaStack` |
| APTF-09 | P3 | docs | Prior harmonization audit did not cover spacing bug | This audit closes the gap |
| APTF-10 | P3 | structure | Wrapper rows unchanged | Layout-only fix |

## Product decisions (confirmed)

- Deadline left-aligned under assignee/pole meta on the right.
- Without meta, deadline still appears in the right column.
- Blank line before description (`mt-4`).
- Menu vertically centered in row 1 without forcing title/meta wrap.

## Resolution

Implemented per plan `task_layout_final_fix`:

- `ActionPlanTaskDetailLayout` refactored to `grid-cols-[2.5rem_minmax(0,1fr)_auto_2.5rem]`.
- Title in column 2; meta/deadline/status stacked in column 3; actions in column 4.
- Description spans columns 2–3 with `mt-4`.

## Explicit exclusions

- `action-plan-task-draft-editor.tsx`

## Top 3 fixes (done)

1. APTF-01 + APTF-04 — actions column isolation
2. APTF-02 — deadline under meta stack
3. APTF-03 — description spacing

## Not worth fixing now

- Harmonizing creation draft editor layout
- Reserving actions spacer when menu hidden on terminal tasks
