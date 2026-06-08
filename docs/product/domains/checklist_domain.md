# Checklist Domain

Status: authoritative
Last reviewed: 2026-06-08
Implementation status: not_started

Historical reference only (not active product truth): [`docs/archive/codex/houston_checklist_domain.md`](../../archive/codex/houston_checklist_domain.md).

## 1. Purpose

Checklist owns Houston's routine execution structure:
- reusable checklist templates (shared establishment routines and private personal routines)
- shared checklist assignments (scheduled attribution to members)
- runtime checklist executions and task executions
- backend-authorized task completion, skip, and Observation handoff

Checklist is a routine domain. It is not Action, Signal, or Observation.

Checklist does not own:
- Signal creation or Action lifecycle
- feed sorting, filtering, pagination, or projection rules (owned by Feed domain)
- notification routing (deferred — see §4 Hors MVP)
- realtime transport
- comments behavior
- RBAC internals (`MembershipScope` is defined in RBAC domain)
- raw Observation privacy policy

## 2. MVP Scope

- Unified model for Shared and Personal checklists via `checklist_type` (`shared` | `personal`).
- **Separation Template → Assignment → Execution** for shared routines.
- `ChecklistTemplate` lifecycle: `active` | `inactive`.
- `ChecklistAssignment` lifecycle: `active` | `inactive` (shared only).
- `ChecklistExecution` lifecycle: `assigned` | `in_progress` | `done` | `canceled`.
- `ChecklistTaskExecution` lifecycle: `pending` | `done` | `skipped` | `observation_created`.
- `ChecklistTaskTemplate` with required `position` and MVP reorder support.
- Shared templates scoped to a required `business_unit`; Personal templates with nullable `business_unit`.
- Shared scheduling via `ChecklistAssignment`: required `start_at`, required `due_at` (`due_at > start_at`), optional weekly `recurrence_days`.
- Execution materialization from assignments; `visible_from = start_at - 1 hour` on shared executions.
- Personal: no `ChecklistAssignment`, no recurrence, no required `due_at`; one active execution per personal template.
- Snapshot at execution materialization (template + tasks + assignment fields).
- Backend-authorized task transitions: `mark_done`, `skip`, `create_observation_from_task`.
- No `start` endpoint — automatic `assigned` → `in_progress` on first user task event.
- Task-triggered Observation through the normal Observation domain flow (min 10 characters, no shortcut).
- `skipped_reason` optional and nullable on skip.
- Concurrent execution rules: multiple active shared executions allowed; one active personal execution per personal template.
- Inactive template blocks new assignments/executions; existing executions unchanged.
- Empty checklist rules: no activation or execution without at least one task.
- Checklist executions in Execution Feed (Phase 7 target — not implemented today).
- **Profil → Gérer les checklists** for template/assignment management; **Execution Feed `+`** for quick Personal Checklist creation only.
- No Checklist comments in MVP.

Current code truth:
- `apps/api/houston/checklists/` contains only the Django app stub (no `models.py`, no services, no API).
- `apps/api/schema.yml` contains no checklist endpoints.
- `GET execution-feed/` returns Action items only (`item_type: "action"`).
- Frontend has disabled checklist placeholders only (`execution-checklist-placeholder-card.tsx`).
- Profil has no « Gérer les checklists » entry yet ([`profile-page.tsx`](../../../apps/web/src/features/auth/pages/profile-page.tsx)).

## 3. Décisions définitives MVP

### 3.1 Statuts

| Object | MVP statuses | Forbidden names |
| --- | --- | --- |
| `ChecklistTemplate` | `active`, `inactive` | `draft`, `archived` |
| `ChecklistAssignment` | `active`, `inactive` | `draft`, `archived` |
| `ChecklistExecution` | `assigned`, `in_progress`, `done`, `canceled` | `open`, `completed` |
| `ChecklistTaskExecution` | `pending`, `done`, `skipped`, `observation_created` | — |

### 3.2 Complétion

A task is **treated** when its status is `done`, `skipped`, or `observation_created`.

`ChecklistExecution` becomes `done` when **all** task executions are treated.

`observation_created` counts as treated for execution completion. No conversion to `done` is required.

### 3.3 Pas de endpoint `start`

There is no `POST .../start/` or equivalent in MVP.

`ChecklistExecution` passes from `assigned` to `in_progress` on the **first** user task event:
- `mark_done`
- `skip`
- `create_observation_from_task`

### 3.4 Modèle unifié Shared / Personal

Do not create a separate `PersonalChecklist` domain object or model.

Both types share the same object families with `checklist_type`. **Shared** uses Template + Assignment + Execution. **Personal** uses Template + Execution only (no Assignment).

```txt
ChecklistTemplate
  checklist_type = shared | personal
  establishment_id
  created_by
  business_unit          # required if shared; null if personal

ChecklistAssignment          # shared only
  checklist_template
  assigned_to
  assigned_by
  business_unit              # snapshot from template
  start_at                   # required
  due_at                     # required; due_at > start_at
  recurrence_days            # nullable list; empty/null = one-shot
  status = active | inactive

ChecklistExecution
  checklist_template
  checklist_assignment       # nullable; null for personal
  checklist_type
  assigned_to
  assigned_by                # nullable (null for personal self-run)
  business_unit              # snapshot: required if shared; null if personal
  start_at                   # snapshot; nullable for personal
  visible_from               # snapshot; shared = start_at - 1h; null for personal (= visible immediately)
  due_at                     # snapshot; nullable for personal
```

### 3.5 BusinessUnit / RBAC

Use `MembershipScope` on **BusinessUnit** only. Do not use `operational_domains` or legacy domain arrays.

**Shared checklist:**
- `ChecklistTemplate.business_unit` is **required**.
- `ChecklistAssignment.business_unit` and `ChecklistExecution.business_unit` are copied from the template (snapshot).
- Owner and Director: see and manage all shared templates, assignments, and executions in the establishment.
- Manager: see and manage shared templates, assignments, and executions only when `business_unit` is covered by their `MembershipScope`.
- Staff: do **not** see shared template catalogue, assignments, or management UI; may only see and execute shared `ChecklistExecution` items assigned to them.

**Personal checklist:**
- `ChecklistTemplate.business_unit` is **null**.
- `ChecklistExecution.business_unit` is **null**.
- Visible and manageable only by `created_by` / `assigned_to` (same member in MVP).
- A member never sees another member's Personal Checklist Templates.

### 3.6 Scheduling — `start_at`, `due_at`, `visible_from`

**Shared `ChecklistAssignment`:**
- `start_at` is **required**.
- `due_at` is **required** and must satisfy `due_at > start_at`.
- Recurrence is **not** stored on `ChecklistExecution` — only on `ChecklistAssignment`.

**Shared `ChecklistExecution` (materialized):**
- Copies `start_at`, `due_at` from assignment occurrence.
- `visible_from = start_at - 1 hour`.
- Appears in Execution Feed when `now >= visible_from` AND `status IN (assigned, in_progress)`.
- **Overdue rule:** `due_at` does **not** remove an execution from the feed. An overdue execution remains visible while `assigned` or `in_progress`.
- Feed active exclusion: only `done` and `canceled`.

**Personal:**
- No `ChecklistAssignment`.
- No required `due_at` in MVP.
- `visible_from` is **null** (visible immediately on creation).
- `start_at` is **null** (immediate execution).

### 3.7 Récurrence hebdomadaire simple (MVP)

- `recurrence_days` on `ChecklistAssignment`: one or more weekday values (`monday` … `sunday`).
- Empty or null `recurrence_days` ⇒ **one-shot** assignment.
- Non-empty `recurrence_days` ⇒ **weekly simple recurrence** on selected days.
- Each occurrence is a separate materialized `ChecklistExecution` linked to the assignment.
- Deactivating an assignment (`inactive`) stops future materialization; existing executions unchanged.

**Hors MVP:** full RRULE, calendar exceptions, complex end dates, advanced pause.

**Materialization strategy (MVP):** short-horizon materialization (e.g. 14 days) via eager first occurrence on assignment create + periodic Celery job + lazy fallback on feed read. No complex planning engine.

### 3.8 Observation depuis tâche

- A checklist task may create a contextualized Observation.
- Observation text validation remains **10–1,000 characters** (same as direct report). No shorter-text exception for checklist origin in MVP.
- The Observation follows the existing async pipeline (Observation → CandidateSignal → Signal). Checklist never creates Signal or Action directly.
- After valid Observation creation, the task becomes `observation_created`.
- `observation_created` counts as treated for execution completion.
- Raw Observation text must not appear on checklist surfaces.

Handoff target (not implemented): extend `Observation.origin` (e.g. `checklist_task`) and link `checklist_execution_id` / `checklist_task_execution_id`.

### 3.9 Catalogue Staff

Staff cannot browse the shared template catalogue or assignments.

Staff may:
- access **Profil → Gérer les checklists → Mes checklists personnelles** only;
- view and execute shared `ChecklistExecution` assigned to them in Execution Feed;
- create Personal Checklists via Execution Feed `+` and manage own Personal Templates in Profil.

### 3.10 Réordonnancement des tâches

- `ChecklistTaskTemplate.position` is **required**.
- Stable order: `position` ascending, then `created_at` or `id` as tiebreaker.
- Reordering is MVP scope at API level (reliable order).
- Advanced drag-and-drop UI is not required in the first frontend lot.

### 3.11 Exécutions concurrentes

**Shared:**
- One template may have **multiple** active assignments and **multiple** active executions in parallel.
- Each assignment may target one assignee; each occurrence creates a `ChecklistExecution`.
- Active statuses: `assigned`, `in_progress`.

**Personal:**
- At most **one** active execution per personal `ChecklistTemplate`.
- Active statuses: `assigned`, `in_progress`.
- If an active execution exists, the backend must refuse a new active execution for the same personal template.
- A new execution is allowed only after the previous one is `done` or `canceled`.

### 3.12 Template / Assignment `inactive`

- An `inactive` template **blocks** creation of new assignments and personal executions.
- An `inactive` assignment **blocks** future occurrence materialization.
- Deactivating a template or assignment never modifies existing executions.

### 3.13 `skipped_reason`

- MVP field, **optional** and **nullable**.
- Optional in skip API request.
- Never blocks task or execution completion.

### 3.14 Annulation

**Shared `ChecklistExecution`:**
- Owner and Director may cancel.
- Manager may cancel when execution `business_unit` is covered by their `MembershipScope`.
- Staff may **not** cancel a shared execution.

**Personal `ChecklistExecution`:**
- Creator / assignee may cancel.

### 3.15 Snapshot

Mandatory at execution materialization. Template and assignment edits never affect existing executions.

Snapshot includes:
- template `title` (and `description` if present);
- shared `business_unit` (from template);
- `start_at`, `due_at`, `visible_from` (from assignment occurrence);
- `assigned_to`, `assigned_by`;
- per task: `title`, `instructions` (if any), `position`.

Stored on `ChecklistExecution` and `ChecklistTaskExecution` snapshot fields (normalized rows, not a single opaque JSON blob required).

### 3.16 Checklist vide

- A template **may** exist with zero tasks only while `inactive`.
- Activation (`inactive` → `active`) is **forbidden** without at least one task.
- Assignment creation and personal execution creation are **forbidden** without at least one task on an active template.
- If the last task of an `active` template is deleted, the template automatically becomes `inactive`.

### 3.17 Tri Execution Feed (cible Phase 7)

When checklist items are added to Execution Feed, cross-type MVP sort is:

```txt
last_activity_at desc
created_at desc
```

`due_at` may be shown on shared checklist feed items (including overdue indicator) but does not drive MVP sort and does not remove items from the feed.

**Note:** implemented Action feed sorting today uses additional keys (`requires_me_rank`, overdue, status). Phase 7 integration must not break existing Action feed behavior; checklist items follow the simple sort above unless a dedicated reconciliation ticket explicitly aligns both types.

### 3.18 Notifications

Checklist-related notifications are **out of the initial Checklist implementation lot**.

Depends on Notifications domain (Phase 6). MVP Checklist implementation must not block on notifications.

### 3.19 UX — Profil vs Execution Feed `+`

**Profil → Gérer les checklists** (all active roles):
- Owner/Director: Shared Checklists (establishment) + Mes checklists personnelles
- Manager: Shared Checklists (MembershipScope BU) + Mes checklists personnelles
- Staff: Mes checklists personnelles only

Shared management in Profil: list/create/edit/deactivate templates, manage tasks, create/update/deactivate assignments (`start_at`, `due_at`, `recurrence_days`).

**Execution Feed `+`** (quick terrain create):
- **Personal Checklist only** — label « Checklist personnelle »
- Must **not** create Shared Checklists, assignments, or expose shared catalogue
- Action entry remains for Owner/Director/Manager (unchanged)
- Staff may use `+` for Personal Checklist only

## 4. Hors MVP

- Endpoint `start` for executions.
- Status names `draft`, `archived`, `completed`, `open` for checklist executions.
- Separate `PersonalChecklist` model or domain.
- `operational_domains` or legacy v1 domain arrays for checklist visibility.
- Full RRULE / iCal recurrence, calendar exceptions, complex recurrence end rules.
- Manager validation gate at checklist completion.
- Multi-assignee on a single execution (one assignee per execution/assignment; multiple assignments instead).
- Mandatory photo / proof per task.
- Checklist comments.
- Checklist notifications (assignation, done) — future lot after Notifications Phase 6.
- Shorter Observation text for checklist origin.
- `due_at` on Personal checklists or on templates.
- Staff access to shared template catalogue or assignment management.
- Shared Checklist creation from Execution Feed `+`.
- Metrics dashboard / anomaly detection from checklist data.
- Advanced Execution Feed sort (`requires_me_rank` for checklist items).
- Realtime invalidation for checklist (Phase 8A — separate from Checklist core lot).
- Treating `ChecklistTaskExecution` as an Action.

## 5. Questions non bloquantes post-MVP

- Drag-and-drop task reorder UI vs position-only API forms.
- Checklist feed item progress display format (percentage vs fraction).
- Whether to expose `ChecklistPermissionHints` on feed items (mirror Actions).
- Metrics: `completion_rate`, `observations_created_from_checklist` storage and reporting surfaces.
- Optional `due_at` reminder notifications (requires Notifications domain).
- Composite API for quick Personal Checklist from `+` (single request vs mutation chain).

None of these block Cursor dev plan generation for MVP Checklist.

## 6. Core Invariants

- Template, assignment, and execution are separate concepts.
- Recurrence lives on `ChecklistAssignment`, not on `ChecklistExecution`.
- Checklist is not Action, Signal, or Observation.
- Backend owns all lifecycle transitions via explicit service methods.
- Frontend cannot authoritatively change checklist status.
- Single-assignee per `ChecklistAssignment` and per `ChecklistExecution`; multiple assignees ⇒ multiple assignments/executions.
- Shared executions start as `assigned` when materialized.
- Treated task statuses: `done`, `skipped`, `observation_created`.
- Observation-from-task uses Observation domain; no direct Signal or Action creation.
- No raw Observation text on checklist detail, feed, notification, or realtime surfaces.
- `due_at` never removes an active execution from the feed — only `done`/`canceled` do.
- Notifications and realtime do not grant access and do not carry business truth.
- Establishment scoping is mandatory on all checklist objects.

## 7. Main Objects

### `ChecklistTemplate`

- `checklist_type`: `shared` | `personal`
- `establishment_id`
- `created_by` → `EstablishmentMembership`
- `business_unit` → `BusinessUnit` (required if `shared`; null if `personal`)
- `title`, `description` (optional)
- `status`: `active` | `inactive`

### `ChecklistTaskTemplate`

- `checklist_template_id`
- `title`, `instructions` (optional)
- `position` (required, integer)

### `ChecklistAssignment` (shared only)

- `checklist_template_id`
- `establishment_id`
- `assigned_to` → `EstablishmentMembership`
- `assigned_by` → `EstablishmentMembership`
- `business_unit` (snapshot from template)
- `start_at` (required)
- `due_at` (required; `due_at > start_at`)
- `recurrence_days` (nullable list of weekdays; empty = one-shot)
- `status`: `active` | `inactive`

### `ChecklistExecution`

- `checklist_template_id`
- `checklist_assignment_id` (nullable; null for personal)
- `checklist_type` (copied from template)
- `establishment_id`
- `assigned_to` → `EstablishmentMembership`
- `assigned_by` → `EstablishmentMembership` (nullable; null for personal self-run)
- `business_unit` (snapshot; required if `shared`; null if `personal`)
- `start_at` (snapshot; nullable for personal)
- `visible_from` (snapshot; `start_at - 1h` for shared; null for personal)
- `due_at` (snapshot; nullable for personal)
- `occurrence_date` (nullable; idempotence key for recurring occurrences)
- `status`: `assigned` | `in_progress` | `done` | `canceled`
- Snapshot: `template_title`, `template_description` (optional)
- `last_activity_at` (maintained by backend for feed sort)
- Timestamps: `started_at`, `done_at`, `canceled_at` (nullable as applicable)

### `ChecklistTaskExecution`

- `checklist_execution_id`
- `checklist_task_template_id` (nullable reference to origin template row)
- Snapshot: `title`, `instructions`, `position`
- `status`: `pending` | `done` | `skipped` | `observation_created`
- `observation_id` (nullable FK after handoff)
- `skipped_reason` (nullable)
- Actor/timestamp fields as needed (`completed_at`, `skipped_at`, etc.)

### `ChecklistOriginContext` (Observation handoff)

- Context passed into Observation creation from a task.
- Must not bypass Observation validation or privacy rules.
- Target fields: `checklist_execution_id`, `checklist_task_execution_id`, extended `origin`.

## 8. Lifecycle / Statuses

### Template

| From | To | Trigger |
| --- | --- | --- |
| — | `inactive` | create (default for new template without tasks, or explicit) |
| `inactive` | `active` | activate command (requires ≥1 task) |
| `active` | `inactive` | deactivate command, or last task deleted |
| `active` | `active` | template edit (does not affect existing executions) |

### Assignment (shared)

| From | To | Trigger |
| --- | --- | --- |
| — | `active` | create assignment (template must be `active`) |
| `active` | `inactive` | deactivate assignment command |
| `active` | `active` | update schedule (does not affect existing executions) |

### Execution

| From | To | Trigger |
| --- | --- | --- |
| — | `assigned` | materialize from assignment, or create personal execution |
| `assigned` | `in_progress` | first `mark_done`, `skip`, or `create_observation_from_task` |
| `in_progress` | `done` | all tasks treated |
| `assigned` / `in_progress` | `canceled` | cancel command (authorized actor) |

Active Execution Feed inclusion: `status IN (assigned, in_progress)` AND `(visible_from IS NULL OR now >= visible_from)`.

### Task execution

| From | To | Trigger |
| --- | --- | --- |
| `pending` | `done` | `mark_done` |
| `pending` | `skipped` | `skip` (optional `skipped_reason`) |
| `pending` | `observation_created` | `create_observation_from_task` after valid Observation persisted |

Task transitions are forbidden when execution is `done` or `canceled`.

## 9. Permissions

Establishment-scoped, backend-enforced. Current code has no checklist-specific helpers yet — implement in `houston/checklists/permissions.py`.

| Capability | Owner / Director | Manager | Staff |
| --- | --- | --- | --- |
| Profil — Gérer les checklists (page access) | yes | yes | yes |
| Create shared template | yes | yes, if `business_unit` in scope | no |
| View shared catalogue | yes | yes, scoped BU | **no** |
| Edit / activate / deactivate shared template | yes | yes, scoped BU | no |
| View / manage shared assignments | yes | yes, scoped BU | **no** |
| Create personal template | yes | yes | yes |
| View personal template | own only | own only | own only |
| Create shared assignment | yes | yes, scoped BU | no |
| Create personal execution | own templates | own templates | own templates |
| Execute tasks (assignee) | if assignee | if assignee | if assignee |
| Cancel shared execution | yes | yes, scoped BU | **no** |
| Cancel personal execution | creator / assignee | creator / assignee | creator / assignee |
| Execution Feed `+` — Personal Checklist | yes | yes | yes |
| Execution Feed `+` — Action | yes | yes | no (unchanged Action rule) |
| Execution Feed — personal | assigned shared + own personal | same | assigned shared + own personal |
| Execution Feed — general | all establishment | own + scoped BU shared + own personal | assigned + own personal only |

RBAC reference: [`rbac_permissions_domain.md`](rbac_permissions_domain.md) — `MembershipScope` on BusinessUnit only.

## 10. Events

No implemented checklist event contract in current code or `schema.yml`.

Candidate events (for future Notifications / Realtime lots):
- `ChecklistTemplateCreated`, `ChecklistTemplateUpdated`, `ChecklistTemplateActivated`, `ChecklistTemplateDeactivated`
- `ChecklistAssignmentCreated`, `ChecklistAssignmentUpdated`, `ChecklistAssignmentDeactivated`
- `ChecklistExecutionCreated`, `ChecklistExecutionProgressed`, `ChecklistExecutionDone`, `ChecklistExecutionCanceled`
- `ChecklistTaskCompleted`, `ChecklistTaskSkipped`, `ChecklistTaskObservationCreated`

## 11. API Surface

Current API truth: `apps/api/schema.yml` — **no checklist endpoints implemented**.

Candidate endpoints (establishment-scoped, `/api/v1/establishments/{establishment_id}/`):

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `checklist-templates/?type=shared\|personal` | List (filtered by type / permissions) / create |
| GET, PATCH | `checklist-templates/{id}/` | Detail / update |
| POST | `checklist-templates/{id}/activate/` | Activate (requires ≥1 task) |
| POST | `checklist-templates/{id}/deactivate/` | Deactivate |
| POST | `checklist-templates/{id}/tasks/` | Add task |
| PATCH, DELETE | `checklist-task-templates/{id}/` | Update / delete task |
| POST | `checklist-templates/{id}/tasks/reorder/` | Reorder tasks by position |
| GET | `checklist-assignments/` | List shared assignments (RBAC filtered) |
| POST | `checklist-templates/{id}/assignments/` | Create assignment + materialize first occurrence |
| GET, PATCH | `checklist-assignments/{id}/` | Detail / update schedule |
| POST | `checklist-assignments/{id}/deactivate/` | Deactivate assignment |
| POST | `checklist-templates/{id}/personal-executions/` | Create personal execution (personal templates only) |
| GET | `checklist-executions/{id}/` | Detail with task executions |
| POST | `checklist-task-executions/{id}/mark-done/` | Mark task done |
| POST | `checklist-task-executions/{id}/skip/` | Skip task (optional `skipped_reason`) |
| POST | `checklist-task-executions/{id}/create-observation/` | Observation handoff |
| POST | `checklist-executions/{id}/cancel/` | Cancel execution |

**Not in MVP:** `POST .../start/`, `POST .../executions/` on shared templates (use assignments).

Execution Feed extension (Phase 7): extend existing `GET execution-feed/` with `item_type: "checklist"` items — no separate feed endpoint.

Do not treat any checklist endpoint as implemented until it exists in `schema.yml`.

## 12. Frontend Expectations

- **Profil → Gérer les checklists** for administrative template and assignment management (all roles; content RBAC-filtered).
- **Execution Feed** for terrain execution visibility only.
- **Execution Feed `+`** creates **Personal Checklist only** — never shared templates or assignments.
- Separate template management from execution work.
- Lifecycle changes are backend commands, not local UI authority.
- Use generated OpenAPI clients only for routes in `schema.yml`.
- TanStack Query owns checklist server state when APIs exist.
- Display execution status as `assigned`, `in_progress`, `done`, `canceled`.
- Done/canceled executions excluded from active Execution Feed.
- Overdue shared executions remain visible in feed until done/canceled.
- No Checklist comment UI in MVP.
- Checklist-origin Observation opens reporting flow with context; client must not create Signal or Action.
- No raw Observation text on checklist UI.
- Replace disabled placeholders when APIs exist (`execution-checklist-placeholder-card.tsx`).
- Notifications for assign / done: **future lot** — do not implement in initial Checklist frontend lot.
- Staff: no shared catalogue or assignment UI; Profil shows personal section only.

## 13. Execution Feed integration (Phase 7 target)

Owned by Feed domain for projection rules; Checklist domain owns lifecycle and feed-eligible statuses.

- `ExecutionFeedItem` polymorphism: `item_type: "action" | "checklist"`.
- Checklist feed item exposes safe summary (title, progress, `due_at`, overdue indicator, `business_unit` label, status).
- Visibility: `status IN (assigned, in_progress)` AND `now >= visible_from` (or `visible_from` null) AND RBAC `view_mode` rules (§9).
- `due_at` does not remove items; only `done`/`canceled` exclude from active feed.
- Sort: `last_activity_at desc`, `created_at desc` across Action and Checklist items (see §3.17).
- See [`feed_domain.md`](feed_domain.md).

## 14. AI Agent Notes

- Inspect `apps/api/houston/checklists/` before claiming models, services, or APIs exist.
- Inspect `schema.yml` before claiming checklist endpoints are implemented.
- Inspect [`action_domain.md`](action_domain.md), [`feed_domain.md`](feed_domain.md), [`observation_domain.md`](observation_domain.md), [`rbac_permissions_domain.md`](rbac_permissions_domain.md).
- Do not use archive [`houston_checklist_domain.md`](../../archive/codex/houston_checklist_domain.md) as implementation authority (`completed`, `draft`, `archived`, `operational_domains`, Start endpoint are obsolete).
- Do not create `PersonalChecklist` as a separate model.
- Do not add a `start` endpoint.
- Do not use `operational_domains` for checklist RBAC — use `business_unit` + `MembershipScope`.
- Do not put shared checklist management in Execution Feed `+`.
- `observation_created` **counts** for execution completion.
- Recurrence is weekly simple on `ChecklistAssignment` only — not RRULE.
- When adding checklist APIs: update permissions, OpenAPI, generated clients, tests, and this document together.
