# Action plan task enrichment audit

Date: 2026-07-06  
Scope: enriched action plan tasks (description, deadline, assignee, pole accordion), create/update, execution display, assignee merge.

## Files inspected

- Backend: `models.py`, `services.py`, `materialization.py`, `api/serializers.py`, `api/views.py`, `permissions.py`, `constants.py`
- Frontend: `action-plan-task-draft-editor.tsx`, `action-plan-create-page.tsx`, `action-plan-template-detail-page.tsx`, `action-plan-execution-task-row.tsx`, `action-plan-create-payload.ts`, `assignee-section.tsx`, planning components
- Tests: `test_models.py`, `test_execution_services.py`, `test_action_plans_api.py`, `test_materialization_services.py`, frontend action-plans tests

## Tests inspected

- Create/use/materialization assignees; task text snapshot; lifecycle task commands
- Missing before implementation: update tasks, enriched fields, task→plan assignee merge, template task edit UI

## Docs/rules inspected

- `AGENTS.md`, `apps/api/AGENTS.md`, `apps/web/AGENTS.md`, `.cursor/rules/10-backend-django-drf.mdc`

## Assumptions

- `deadline_at` is informational only; feed sort stays on `execution.end_at`
- Task assignee merge into plan assignees is skipped for staff (display snapshot only)
- Plan PATCH `tasks` replaces the full task list
- In-flight executions are not retroactively updated after template edit

## Findings

| ID | Severity | Category | Evidence | Problem | Recommended fix | Tests | Size |
|----|----------|----------|----------|---------|-----------------|-------|------|
| APT-01 | P0 | API contract | `ActionPlanTask` only `task`+`business_unit` | Cannot persist description/deadline/assignee | Migration + fields on template and execution task | `test_models.py` | M |
| APT-02 | P0 | API contract | `update_action_plan` metadata only | Template task edit impossible | `replace_action_plan_tasks` + PATCH `tasks` | `test_action_plans_api.py` | M |
| APT-03 | P1 | ambiguity | Informational assignee vs merge | Merge makes assignee operational | Document; staff = display only | merge tests | M |
| APT-04 | P1 | structure | Three materialization entry points | Divergence risk | Central `_merge_task_assignees_into_validated_assignees` | execution + materialization tests | M |
| APT-05 | P1 | security | Staff self-assign only | Third-party task assignee + merge breaks RBAC | Skip merge for staff; UI hides third-party picker | staff tests | S |
| APT-06 | P2 | maintainability | Task draft editor growth | God-component / picker collisions | Extract `ActionPlanTaskDraftCard` | component test | M |
| APT-07 | P2 | API contract | Template detail read-only tasks | Missing edit surface | Reuse editor + extended update mutation | template page test | M |
| APT-08 | P2 | structure | `AssigneeSection` single mode unused | Unproven in production | `ActionPlanTaskAssigneeSheet` wrapper | sheet test | S |
| APT-09 | P3 | performance | New FK on tasks | Possible N+1 | `select_related` on execution detail | selector test | S |
| APT-10 | P3 | ambiguity | Task deadline vs execution end_at | Product confusion | Doc: task deadline is UI hint only | doc | S |

## Top 3 fixes

1. APT-01 — Model + migration + read serializers
2. APT-04 — Centralized assignee merge with shared chronology
3. APT-06/07 — Enriched task editor (create + template edit)

## Quick wins

- Reuse `ACTION_PLAN_DESCRIPTION_MAX_LENGTH` for task description
- `formatActionPlanTaskMetaLine()` formatter
- Reuse `PlanningDateTimeRow` / `PlanningOptionRow`

## Structural backlog

- `useActionPlanTaskDraftEditor` hook to slim create page
- Shared assignee validation module (execution vs schedule)

## Not worth fixing now

- Feed task preview enrichment
- Task deadline in feed sort
- Per-task PATCH by ID

## Resolution

Implementation delivered per plan phases 1–8 (see git history).
