# Action plan execution task layout audit

Date: 2026-07-06  
Scope: flat task list on execution detail, task row layout (assignee, pole, deadline, description).

## Files inspected

- `apps/web/src/features/action-plans/pages/action-plan-execution-detail-page.tsx`
- `apps/web/src/features/action-plans/components/action-plan-execution-task-list.tsx`
- `apps/web/src/features/action-plans/components/action-plan-execution-task-row.tsx`
- `apps/web/src/features/action-plans/lib/action-plan-display.ts`
- `apps/web/src/features/action-plans/lib/action-plan-permission-hints.ts`
- `apps/web/src/features/execution/components/action-plan-execution-feed-card.tsx`

## Tests inspected

- `action-plan-execution-task-list.test.tsx`
- `action-plan-execution-task-row.test.tsx`
- `action-plan-execution-detail-page.test.tsx`
- `action-plan-display.test.ts`

## Docs / rules inspected

- `docs/audits/action_plan_task_pole_ux_audit.md` (APTP-08 obsolete)
- `docs/evolution_action/besoin_evolution_action.md` §16 (diverges from new UX)
- `apps/web/AGENTS.md`

## Assumptions

- Pole-level contribution badges and `assignees_by_pole` summary are intentionally dropped from the UI.
- Task order follows global `position`, not alphabetical pole grouping.
- `business_unit` on persisted tasks is always present; row shows `task.business_unit.label` when truthy.
- No backend or OpenAPI changes in this scope.

## Findings

| ID | Severity | Category | Evidence | Problem | Recommended fix | Tests | Size |
|----|----------|----------|----------|---------|-----------------|-------|------|
| APTL-01 | P1 | structure | `buildActionPlanPoleSections`, `ActionPlanPoleSectionView` | Grouping by pole conflicts with flat list UX | Replace with `ActionPlanExecutionTaskList` sorted by `position` | detail-page, task-list | M |
| APTL-02 | P1 | structure | `formatActionPlanTaskDetailMetaLine` on execution row | Assignee and deadline merged in right column | Separate title meta (assignee + pole) and deadline line | task-row | M |
| APTL-03 | P2 | maintainability | Task row flex layout | Description squeezed between checkbox and menu | CSS grid + `col-span-3` description | task-row | S |
| APTL-04 | P2 | ambiguity | `besoin_evolution_action.md` §16 | Product doc still describes pole sections | Backlog doc update | — | S |
| APTL-05 | P2 | structure | `action-plan-pole-section.tsx` | Mixed contribution, plan assignees, tasks | Remove component | detail-page | S |
| APTL-06 | P3 | maintainability | Feed card vs task row | Avatar markup duplicated | Local `TaskAssigneeAvatar` in row | task-row | S |
| APTL-07 | P2 | tests | `action-plan-execution-task-row.test.tsx` | Asserted pole hidden on row | Update for pole + avatar + deadline split | task-row | S |
| APTL-08 | P3 | structure | `ActionPlanContributionBadge`, `shouldShowContributionStatusForPole` | Orphaned after section removal | Delete | — | S |
| APTL-09 | P3 | ambiguity | `buildActionPlanPoleSections` sort | Alphabetical pole order vs global `position` | Sort tasks by `position` only | task-list | S |
| APTL-10 | P3 | docs | `action_plan_task_pole_ux_audit.md` APTP-08 | Prior resolution contradicted new UX | This audit supersedes for execution layout | — | S |

## Product decisions (confirmed)

- Remove dynamic pole sections on execution detail.
- Remove contribution badge and pole-level assignee summary.
- Show assignee (full name + avatar) and task pole on the title line with `flex-wrap`.
- Show task deadline under the title.
- Span description across full card width with symmetric padding.

## Resolution

Implemented per plan `task_detail_layout`:

- `ActionPlanExecutionTaskList` — flat `TerrainCard` list sorted by `position`.
- `ActionPlanExecutionTaskRow` — grid layout, avatar, full name, pole, deadline, full-width description.
- Removed `action-plan-pole-section.tsx`, `action-plan-contribution-badge.tsx`, `buildActionPlanPoleSections`, `shouldShowContributionStatusForPole`.

## Top 3 fixes (done)

1. APTL-01 — flat task list
2. APTL-02 + APTL-03 — row layout refactor
3. APTL-08 — dead code cleanup

## Quick wins (done)

- APTL-07, APTL-09 — test updates
- APTL-06 — local avatar helper

## Structural backlog

- Update `besoin_evolution_action.md` §16 to reflect flat task list.
- Align `ActionPlanTaskReadOnlyRow` on template detail with execution row layout (optional).

## Not worth fixing now

- Global shared avatar component across feed and execution.
- Remove unused `formatContributionStatusLabel` (no caller after badge removal).
- Backend changes to expose per-task overdue flag.
