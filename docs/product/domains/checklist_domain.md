# Checklist Domain

Status: authoritative
Last reviewed: 2026-05-27
Implementation status: not_started

## 1. Purpose

Checklist owns Houston's routine execution structure:
- reusable shared checklist templates for establishment routines
- runtime checklist executions and task executions
- private personal checklist work

Checklist is a routine domain. It is not Action, Signal, or Observation.

Checklist does not own:
- Signal creation or Action lifecycle
- feed sorting, filtering, pagination, or projection rules
- notification routing
- realtime transport
- comments behavior
- RBAC internals
- raw Observation privacy policy

## 2. MVP Scope

- Shared checklist templates.
- Shared Checklist Template lifecycle: `active` / `inactive`.
- Checklist task templates.
- Checklist executions.
- Shared Checklist Execution lifecycle: `assigned`, `in_progress`, `done`, `canceled`.
- Checklist task executions.
- ChecklistTaskExecution statuses include `pending`, `done`, `skipped`, and `observation_created`.
- Personal checklists.
- Backend-authorized task completion and skip behavior.
- Task-triggered Observation creation through the normal Observation flow.
- No Checklist comments in MVP.
- Done shared Checklist Executions disappear from the active Execution Feed by default.
- Safe checklist execution surfaces without raw Observation text.
- Target MVP direction: checklist work may appear in Execution Feed, while feed behavior remains owned by the Feed domain.

Current truth:
- `apps/api/houston/checklists/` contains only the Django app stub today.
- `apps/api/schema.yml` contains no checklist endpoints today.

## 3. Out of Scope

- Treating Checklist or `ChecklistTaskExecution` as an Action.
- Direct task-to-Signal or task-to-Action creation.
- Frontend-only lifecycle authority.
- Frontend-only completion or cancellation behavior.
- Recurrence automation.
- Manager validation gate for checklist completion.
- Multi-assignee single checklist execution.
- Proof or photo evidence workflow.
- Shared-by-default personal checklists.
- Checklist comments in MVP.
- `draft` / `archived` shared template lifecycle unless later validated.
- `open` / `completed` ChecklistExecution naming unless later validated.
- Advanced scheduling, analytics, workflow-builder, or public checklist behavior.

## 4. Core Invariants

- Template and execution are separate concepts.
- A template is reusable structure; an execution is runtime state.
- Checklist is a routine domain, not an Action, Signal, or Observation.
- Shared Checklist Templates are either `active` or `inactive` in MVP.
- Personal checklist work is private by default.
- Personal Checklists are private to their `created_by`.
- All active establishment members can create Personal Checklists.
- Shared checklist execution is single-assignee in MVP direction; multiple assignees require multiple executions.
- Shared Checklist Executions start as `assigned`, not `open`.
- A ChecklistExecution becomes `in_progress` when at least one task is completed.
- A ChecklistExecution becomes `done` when all task executions are `done` or `skipped`.
- `observation_created` is a ChecklistTaskExecution status.
- `observation_created` is a ChecklistTaskExecution status. It is not terminal for ChecklistExecution completion unless later converted to `done` or `skipped`.
- Only the user who assigned a shared ChecklistExecution can cancel it, unless later RBAC rules explicitly extend this.
- Backend owns lifecycle transitions and authorization.
- Observation-from-task must go through the Observation domain flow.
- Checklist does not create Actions directly in MVP.
- Checklist has no comments in MVP.
- Checklist must not expose raw Observation text in detail, feed, notification, realtime, or normal log surfaces.
- Notifications and realtime do not grant access and do not carry business truth.

## 5. Main Objects

- `ChecklistTemplate`
  - Reusable routine structure.
  - Shared templates are establishment-scoped and managed by authorized roles.
  - Shared Checklist Template lifecycle is `active` or `inactive` in MVP.

- `ChecklistTaskTemplate`
  - Reusable task definition inside one template.
  - Ordering is target behavior, but exact storage is not validated in current code.

- `ChecklistExecution`
  - Runtime instance assigned to one user.
  - Initial status is `assigned`.
  - Done executions are removed from the active Execution Feed by default.

- `ChecklistTaskExecution`
  - Runtime state for one task inside one execution.
  - Runtime status can be `pending`, `done`, `skipped`, or `observation_created`.
  - `observation_created` means the task has produced an Observation through the normal Observation flow.

- `PersonalChecklist`
  - Private personal routine concept.
  - Not shared by default and not a shared template unless later validated.

- `ChecklistOriginContext`
  - Candidate checklist context passed into Observation creation.
  - Must not bypass Observation validation or privacy boundaries.

## 6. Lifecycle / Statuses

Shared Checklist Template lifecycle:
- `active`
- `inactive`

Shared ChecklistExecution lifecycle:
- `assigned`
- `in_progress`
- `done`
- `canceled`

ChecklistTaskExecution lifecycle:
- `pending`
- `done`
- `skipped`
- `observation_created`

Transition rules:
- create shared execution -> `assigned`
- first completed task -> `in_progress`
- task completed -> task status `done`
- task skipped -> task status `skipped`
- task creates Observation -> task status `observation_created`
- `observation_created` does not count as `done` unless a later backend rule explicitly converts it.
- all task executions are `done` or `skipped` -> execution status `done`
- user who assigned the checklist cancels execution -> `canceled`

Current code does not implement Checklist APIs or models yet; the above lifecycle is validated product target behavior, not current code truth.

## 7. Permissions

- Checklist visibility and commands must be establishment-scoped and backend-authorized.
- Current code validates only general establishment role helpers in `apps/api/houston/establishments/permissions.py`, not checklist-specific object permissions.
- Owner, Director, and Manager can create and assign shared checklists, subject to backend authorization.
- Shared Checklist Executions can be seen by Managers whose operational domains intersect with the checklist execution operational domains.
- Owner and Director follow broader shared-checklist visibility through RBAC.
- The assignee can execute assigned shared ChecklistExecution tasks.
- The user who assigned the shared ChecklistExecution can cancel it.
- Personal Checklists are visible only to their `created_by`.
- All active establishment members can create Personal Checklists.
- Notifications and realtime events do not grant Checklist access.
- Checklist permissions must not expose raw Observation text.

## 8. Events

No implemented checklist event contract is validated in current code or in `apps/api/schema.yml`.

Candidate events only:
- `ChecklistTemplateCreated`
- `ChecklistTemplateUpdated`
- `ChecklistTemplateActivated`
- `ChecklistTemplateDeactivated`
- `ChecklistExecutionCreated`
- `ChecklistExecutionAssigned`
- `ChecklistExecutionProgressed`
- `ChecklistExecutionDone`
- `ChecklistExecutionCanceled`
- `ChecklistTaskCompleted`
- `ChecklistTaskSkipped`
- `ChecklistTaskObservationCreated`
- `PersonalChecklistCreated`
- `PersonalChecklistStarted`
- `PersonalChecklistDone`

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented checklist endpoints confirmed in `apps/api/schema.yml`:
- none

Candidate endpoints only:
- list, create, or update shared checklist templates
- activate or deactivate shared checklist templates
- create, update, delete, or reorder checklist task templates
- create checklist execution from a template
- fetch checklist execution detail
- mark checklist task done
- skip checklist task
- create Observation from checklist task
- cancel checklist execution
- list or create a personal checklist

Do not treat any checklist endpoint as implemented until it exists in `apps/api/schema.yml`.

## 10. Frontend Expectations

- Separate template management from execution work.
- Treat checklist lifecycle changes as backend commands, not local UI authority.
- Use generated OpenAPI clients only for implemented routes present in `apps/api/schema.yml`.
- TanStack Query owns checklist server state when checklist APIs exist.
- Shared Checklist Execution status shown to users should use `assigned`, `in_progress`, `done`, or `canceled`.
- Done shared Checklist Executions disappear from the active Execution Feed by default.
- No Checklist comment UI in MVP.
- Assignee receives notification when a shared ChecklistExecution is assigned.
- The user who assigned the checklist receives notification when the ChecklistExecution is done.
- Checklist-origin Observation should open the reporting flow with checklist context rather than creating a Signal or Action directly in the client.
- Checklist UI must not display raw Observation text.
- Execution Feed representation, notification behavior, and realtime refresh behavior must follow their owning domains.
- Realtime should invalidate/refetch checklist execution and Execution Feed views for authorized users, including Managers whose operational domains intersect with the checklist execution operational domains.
- Realtime and notification payloads must not be treated as complete checklist state.

## 11. AI Agent Notes

- Inspect `apps/api/houston/checklists/` before claiming checklist models, services, statuses, commands, or events exist.
- Inspect `apps/api/schema.yml` before claiming any checklist API is implemented.
- Inspect [action_domain.md](action_domain.md), [feed_domain.md](feed_domain.md), [observation_domain.md](observation_domain.md), [rbac_permissions_domain.md](rbac_permissions_domain.md), and [security_rgpd_domain.md](security_rgpd_domain.md) before changing checklist boundaries.
- Do not make Checklist or `ChecklistTaskExecution` an Action.
- Do not use `open` or `completed` as ChecklistExecution MVP status names unless explicitly changed later.
- Use `assigned`, `in_progress`, `done`, and `canceled` for Shared ChecklistExecution product target status names.
- Do not add a shared ChecklistExecution start command; `in_progress` begins when at least one task is completed.
- Do not treat `observation_created` as only a transient outcome; it is a ChecklistTaskExecution status.
- Do not treat `observation_created` as terminal for execution completion unless explicitly validated later.
- Do not add Checklist comments in MVP.
- Do not use `detected_domains` naming for Checklist unless separately validated; prefer checklist operational domains or `associated_operational_domains`.
- Do not use `archived` as a Shared Checklist Template MVP status; use `active` / `inactive`.
- Do not keep done shared ChecklistExecutions in the active Execution Feed unless later validated.
- Do not add recurrence automation, manager validation of checklist completion, frontend-only lifecycle transitions, or shared-by-default personal checklists unless separately validated.
- Do not expose raw Observation text through checklist surfaces.
- When checklist APIs are added later, update backend authorization, OpenAPI, generated clients, tests, and this document together.
