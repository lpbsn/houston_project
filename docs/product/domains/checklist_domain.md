# Checklist Domain

Status: authoritative
Last reviewed: 2026-06-09
Implementation status: implemented

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
- Shared scheduling via `ChecklistAssignment`: required period (`start_date`, `end_date`), required daily times (`start_at`, `end_at` with `end_at > start_at` on the same day — no overnight slots), optional weekly `recurrence_days`.
- Execution materialization from assignments; `visible_from = execution.start_at - 1 hour` on shared executions.
- Personal: no `ChecklistAssignment`, no recurrence, no required `end_at`; one active execution per personal template.
- Snapshot at execution materialization (template + tasks + assignment fields).
- Backend-authorized task transitions: `mark_done`, `skip`, `create_observation_from_task`.
- No `start` endpoint — automatic `assigned` → `in_progress` on first user task event.
- Task-triggered Observation through the normal Observation domain flow (min 10 characters, no shortcut).
- `skipped_reason` optional and nullable on skip.
- Concurrent execution rules: multiple active shared executions allowed; one active personal execution per personal template.
- Inactive template blocks new assignments/executions; existing executions unchanged.
- Empty checklist rules: no activation or execution without at least one task.
- Checklist executions in Execution Feed (polymorphic `item_type: checklist`).
- **Profil → Gérer les checklists** for template/assignment management; **Execution Feed `+`** for quick Personal Checklist creation only.
- No Checklist comments in MVP.

Current code truth:
- Backend: [`apps/api/houston/checklists/`](../../../apps/api/houston/checklists/) (models, services, selectors, materialization, permissions, `permission_hints`, REST API).
- OpenAPI: checklist endpoints implemented in [`apps/api/schema.yml`](../../../apps/api/schema.yml).
- Execution Feed merges actions and checklist executions.
- Frontend: [`apps/web/src/features/checklists/`](../../../apps/web/src/features/checklists/) (hub, template detail, assignment sheets, execution detail); feed card: [`execution-checklist-card.tsx`](../../../apps/web/src/features/execution/components/execution-checklist-card.tsx).
- Profil entry: « Gérer les checklists » on [`profile-page.tsx`](../../../apps/web/src/features/auth/pages/profile-page.tsx).

## 3. Décisions définitives MVP

### 3.1 Statuts

| Object | MVP statuses | Forbidden names |
| --- | --- | --- |
| `ChecklistTemplate` | `active`, `inactive` | `draft`, `archived` |
| `ChecklistAssignment` | `active`, `inactive` | `draft`, `archived` |
| `ChecklistExecution` | `assigned`, `in_progress`, `done`, `canceled` | `open`, `completed`, `inactive`, `archived` |
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
  start_date                 # required; period start (DateField)
  end_date                   # required; period end (DateField); end_date >= start_date
  start_at                   # required; daily start time (TimeField)
  end_at                     # required; daily end time (TimeField); end_at > start_at (no overnight)
  recurrence_days            # nullable list; empty/null = one-shot (end_date = start_date)
  status = active | inactive

ChecklistExecution
  checklist_template
  checklist_assignment       # nullable; null for personal
  checklist_type
  assigned_to
  assigned_by                # nullable (null for personal self-run)
  business_unit              # snapshot: required if shared; null if personal
  occurrence_date            # nullable; idempotence key for recurring occurrences
  start_at                   # snapshot datetime; nullable for personal
  end_at                     # snapshot datetime; nullable for personal
  visible_from               # snapshot; shared = start_at - 1h; null for personal (= visible immediately)
```

### 3.5 BusinessUnit / RBAC

Use `MembershipScope` on **BusinessUnit** only. Do not use `operational_domains` or legacy domain arrays.

**Shared checklist:**
- `ChecklistTemplate.business_unit` is **required**.
- `ChecklistAssignment.business_unit` and `ChecklistExecution.business_unit` are copied from the template (snapshot).
- Owner and Director: see and manage all shared templates, assignments, and executions in the establishment.
- Manager: see and manage shared templates, assignments, and executions only when `business_unit` is covered by their `MembershipScope`.
- Staff: do **not** see shared template catalogue, assignments, or management UI; may only see and execute shared `ChecklistExecution` items assigned to them.

**Who manages assignments vs who can be assigned (distinct rules):**

| Concern | Owner / Director | Manager | Staff |
|--------|------------------|---------|-------|
| Create or update a shared `ChecklistAssignment` | yes (all BUs) | yes, if template `business_unit` is in their `MembershipScope` | no |
| Be selected as `assigned_to` on a shared assignment | yes (implicit all-BU access in establishment) | yes, if template `business_unit` is in their `MembershipScope` | yes, if template `business_unit` is in their `MembershipScope` |

- Backend enforces assignee eligibility on create and when `assigned_to` changes on update (`400` if the member does not cover the template BU).
- User search for assignee pickers may pass `business_unit_id` on `GET /api/v1/establishments/{establishment_id}/users/search/` to list only active members covering that BU (generic establishments filter; not checklist-specific naming).
- **Legacy tolerance (not the normal target rule):** an existing assignment may still display an assignee who no longer covers the BU, and schedule-only updates without changing `assigned_to` remain allowed. Any new assignment or assignee change must satisfy BU coverage.

**Personal checklist:**
- `ChecklistTemplate.business_unit` is **null**.
- `ChecklistExecution.business_unit` is **null**.
- Visible and manageable only by `created_by` / `assigned_to` (same member in MVP).
- A member never sees another member's Personal Checklist Templates.

### 3.6 Scheduling — period, daily times, `visible_from`

**Establishment timezone (MVP):**
- `Establishment.timezone` stores an IANA identifier (default `Europe/Paris` for the Mama Shelter Nice pilot).
- `start_date`, `end_date`, `start_at`, and `end_at` on shared assignments are **establishment-local** calendar values.
- `start_at` / `end_at` remain naive `TimeField` wall-clock times in the establishment timezone (not UTC, not user-browser offset).
- Materialization combines `occurrence_date + start_at/end_at` in `Establishment.timezone`, producing aware `DateTimeField` snapshots stored in UTC by Django.
- Lazy materialization and horizon windows use the **establishment-local calendar date** derived from `timezone.now()`, not raw UTC `date()`.

**Shared `ChecklistAssignment` (schedule definition):**
- **Period:** `start_date` and `end_date` (`DateField`) bound when occurrences may be materialized. `end_date >= start_date`.
- **Daily times:** `start_at` and `end_at` (`TimeField`) define the per-occurrence window on each eligible day in establishment-local time. `end_at > start_at` on the same calendar day — **overnight slots are not supported** in MVP (e.g. `22:00 → 02:00` is rejected).
- **Recurrence:** `recurrence_days` selects weekdays within the period. Empty or null ⇒ **one-shot** on `start_date` (`end_date` defaults to `start_date`).
- Recurrence is **not** stored on `ChecklistExecution` — only on `ChecklistAssignment`.
- An assignment is **not** auto-deleted after `end_date`; it remains `active` until explicitly retirée (`inactive`). Materialization simply stops producing new occurrences beyond `end_date`.

**Shared `ChecklistExecution` (materialized occurrence):**
- `occurrence_date` identifies the calendar day (establishment-local).
- `start_at = combine(occurrence_date, assignment.start_at)` in `Establishment.timezone`; same for `end_at`.
- `visible_from = execution.start_at - 1 hour`.
- Appears in Execution Feed when `now >= visible_from` AND `status IN (assigned, in_progress)`.
- **Overdue rule:** `end_at` does **not** remove an execution from the feed. An overdue execution remains visible while `assigned` or `in_progress`.
- Feed active exclusion: only `done` and `canceled`.

**Personal:**
- No `ChecklistAssignment`.
- No required `end_at` in MVP.
- `visible_from` is **null** (visible immediately on creation).
- `start_at` is **null** (immediate execution).

### 3.7 Récurrence hebdomadaire simple (MVP)

- `recurrence_days` on `ChecklistAssignment`: one or more weekday values (`monday` … `sunday`).
- Empty or null `recurrence_days` ⇒ **one-shot** assignment.
- Non-empty `recurrence_days` ⇒ **weekly simple recurrence** on selected days.
- Each occurrence is a separate materialized `ChecklistExecution` linked to the assignment.
- Retirer une affectation (`inactive` via `POST .../deactivate/`) stoppe la matérialisation future.

**Hors MVP:** full RRULE, calendar exceptions, overnight time windows, advanced pause.

**Materialization strategy (MVP):** short-horizon materialization (14 days) via:

1. **Eager** — first occurrence on assignment create;
2. **Lazy** — `ensure_visible_executions_materialized` on execution-feed read (primary safety net);
3. **Celery Beat** (optional `celery-beat` service) — daily `materialize_checklist_assignments_horizon_task` for all active assignments.

Occurrences are idempotent, capped by assignment `end_date`, and never created after `end_date`. No complex planning engine.

### 3.8 Observation depuis tâche

- A checklist task may create a contextualized Observation.
- Observation text validation remains **10–1,000 characters** (same as direct report). No shorter-text exception for checklist origin in MVP.
- The Observation follows the existing async pipeline (Observation → CandidateSignal → Signal). Checklist never creates Signal or Action directly.
- After valid Observation creation, the task becomes `observation_created`.
- `observation_created` counts as treated for execution completion.
- Raw Observation text must not appear on checklist surfaces.

Handoff implemented: `Observation.origin = checklist_task` with links to `checklist_execution_id` / `checklist_task_execution_id`.

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
- An `inactive` assignment (**retirée** in UX) **blocks** future occurrence materialization.
- The standard assignment management list (`GET checklist-assignments/`) returns **active** assignments only; withdrawn (`inactive`) rows remain in the database for execution/observation history but are not shown in the current management UI.
- `GET checklist-assignments/{id}/` may still return an `inactive` assignment (e.g. for API consistency); `PATCH` on an inactive assignment is refused with `400`.
- `ChecklistExecution` has **no** `inactive` status — use `assigned`, `in_progress`, `done`, or `canceled` only.

**Modifier une affectation** (`PATCH checklist-assignments/{id}/`):
- Updates the `ChecklistAssignment` schedule fields (`assigned_to`, `start_date`, `end_date`, `start_at`, `end_at`, `recurrence_days`).
- Propagates schedule/assignee snapshots to linked executions still in status `assigned` **and still valid** under the new schedule (`occurrence_date` within `[start_date, end_date]` and weekday in `recurrence_days`).
- Automatically cancels (`canceled`) `assigned` executions whose `occurrence_date` no longer matches the new schedule.
- Does **not** modify executions in `in_progress`, `done`, or `canceled`.
- Daily `start_at`/`end_at` define the per-occurrence time window but do **not** filter eligible `occurrence_date` values (period + `recurrence_days` do).
- Does **not** immediately materialize new occurrences when recurrence is expanded (horizon materialization handles that later).
- Refused when assignment is already `inactive`.

**Retirer une affectation** (`POST checklist-assignments/{id}/deactivate/`):
- Blocked with `409` + `active_execution_id` if an `in_progress` execution exists on the assignment.
- Cancels (`canceled`) all `assigned` executions on that assignment.
- Preserves `done` / `canceled` history, task executions, and observations.
- Hard-deletes the assignment row when no execution was ever created; otherwise sets `inactive`.

**Supprimer une Shared Template** (`DELETE checklist-templates/{id}/`, Owner/Director only):
- Allowed when no linked execution is `assigned` or `in_progress`.
- Blocked with `409` + `active_execution_id` otherwise.
- Terminal history (`done` / `canceled`) is detached (`checklist_template = null`) and preserved with snapshots.

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

Mandatory at execution materialization. Template edits never affect existing executions. Assignment `PATCH` updates snapshots on `assigned` executions only; `in_progress` and terminal executions keep their snapshots.

Snapshot includes:
- template `title` (and `description` if present);
- shared `business_unit` (from template);
- `start_at`, `end_at`, `visible_from` (from assignment occurrence);
- `assigned_to`, `assigned_by`;
- per task: `task`, `position`.

Stored on `ChecklistExecution` and `ChecklistTaskExecution` snapshot fields (normalized rows, not a single opaque JSON blob required).

### 3.16 Checklist vide

- A template **may** exist with zero tasks only while `inactive`.
- Activation (`inactive` → `active`) is **forbidden** without at least one task.
- Assignment creation and personal execution creation are **forbidden** without at least one task on an active template.
- If the last task of an `active` template is deleted, the template automatically becomes `inactive`.

### 3.17 Tri Execution Feed (implémenté)

Checklist items in Execution Feed are sorted among themselves by `last_activity_at desc` (then `created_at desc` as tiebreaker in selectors).

**Page merge (implemented in [`execution_feed.py`](../../../apps/api/houston/actions/execution_feed.py)):** visible checklist items are **prioritized** — up to `page_size` checklists appear first; Actions fill the remaining slots using existing Action sort keys (`requires_me_rank`, overdue, status, etc.). This is **not** a single global interleaved sort across both types.

`end_at` may be shown on shared checklist feed items (including `is_overdue` when `now > end_at`) but does not drive sort and does not remove items from the feed.

Frontend: checklist cards render flat above grouped Action sections (see [`execution-feed-sections.ts`](../../../apps/web/src/features/execution/lib/execution-feed-sections.ts)).

### 3.18 Notifications

Checklist-related notifications are **out of the initial Checklist implementation lot**.

Depends on Notifications domain (Phase 6). MVP Checklist implementation must not block on notifications.

### 3.19 UX — Profil vs Execution Feed `+`

**Profil → Gérer les checklists** (all active roles):
- Owner/Director: Shared Checklists (establishment) + Mes checklists personnelles
- Manager: Shared Checklists (MembershipScope BU) + Mes checklists personnelles
- Staff: Mes checklists personnelles only

Shared management in Profil: list/create/edit/deactivate templates, manage tasks, create/update/retirer **active** assignments (`start_date`, `end_date`, `start_at`, `end_at`, `recurrence_days`); withdrawn assignments disappear from the list but are retained when execution history exists.

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
- `end_at` on Personal checklists or on templates.
- Staff access to shared template catalogue or assignment management.
- Shared Checklist creation from Execution Feed `+`.
- Metrics dashboard / anomaly detection from checklist data.
- Advanced Execution Feed sort (`requires_me_rank` for checklist items).
- Realtime invalidation for checklist (Phase 8C global realtime — separate from Checklist core lot).
- Treating `ChecklistTaskExecution` as an Action.

## 5. Questions non bloquantes post-MVP

- Drag-and-drop task reorder UI vs position-only API forms.
- Checklist feed item progress display format (percentage vs fraction).
- Whether to expose `ChecklistPermissionHints` on feed items (mirror Actions).
- Metrics: `completion_rate`, `observations_created_from_checklist` storage and reporting surfaces.
- Optional `end_at` reminder notifications (requires Notifications domain).
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
- `end_at` never removes an active execution from the feed — only `done`/`canceled` do.
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
- `task` (required, max 500 characters)
- `position` (required, integer)

### `ChecklistAssignment` (shared only)

- `checklist_template_id`
- `establishment_id`
- `assigned_to` → `EstablishmentMembership`
- `assigned_by` → `EstablishmentMembership`
- `business_unit` (snapshot from template)
- `start_date` (required; `DateField`)
- `end_date` (required; `DateField`; `end_date >= start_date`)
- `start_at` (required; daily `TimeField`)
- `end_at` (required; daily `TimeField`; `end_at > start_at`, no overnight)
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
- `occurrence_date` (nullable; idempotence key for recurring occurrences)
- `start_at` (snapshot datetime; nullable for personal)
- `end_at` (snapshot datetime; nullable for personal)
- `visible_from` (snapshot; `start_at - 1h` for shared; null for personal)
- `status`: `assigned` | `in_progress` | `done` | `canceled`
- Snapshot: `template_title`, `template_description` (optional)
- `last_activity_at` (maintained by backend for feed sort)
- Timestamps: `started_at`, `done_at`, `canceled_at` (nullable as applicable)

### `ChecklistTaskExecution`

- `checklist_execution_id`
- `checklist_task_template_id` (nullable reference to origin template row)
- Snapshot: `task`, `position`
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
| `active` | `active` | update schedule (`PATCH`): syncs `assigned` executions still valid under new schedule; cancels `assigned` executions outside new schedule; does not modify `in_progress`, `done`, or `canceled` executions (see §3.12) |

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

Establishment-scoped, backend-enforced. RBAC helpers live in [`permissions.py`](../../../apps/api/houston/checklists/permissions.py). UX hints (`can_update`, `can_delete`, `can_execute_tasks`, etc.) are derived in [`permission_hints.py`](../../../apps/api/houston/checklists/permission_hints.py) and exposed on template, assignment, and execution API responses — hints are not authorization authority.

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

### 9.1 Permission hints (UX helpers)

Backend exposes `permission_hints` on template (list + detail), assignment, and execution API responses. **Hints are not authorization authority** — the backend still enforces permissions and may return `403` / `409`.

| Resource | Hint keys | Notes |
| --- | --- | --- |
| Template | `can_update`, `can_manage_tasks`, `can_activate`, `can_deactivate`, `can_delete`, `can_create_assignment`, `can_create_personal_execution` (detail only) | List omits `can_create_personal_execution` |
| Assignment | `can_update`, `can_deactivate` | `can_deactivate` is `false` when an `in_progress` execution exists on the assignment (deactivate returns `409`) |
| Execution | `can_execute_tasks`, `can_cancel` | Task execution requires assignee; cancel rules per matrix above |

**Delete template (`can_delete`):**

- **Detail:** `false` when an active execution (`assigned` or `in_progress`) exists — matches `409` + `active_execution_id` on `DELETE`.
- **List:** RBAC only (may still be `true` with active execution); UI delete flow must handle `409`.

**Assignee eligibility:** enforced on assignment create/update when `assigned_to` changes — assignee must cover template `business_unit` via `MembershipScope` (`400` if not). User search may filter by `business_unit_id` (see §3.5).

## 10. Events

No implemented checklist event contract in current code or `schema.yml`.

Candidate events (for future Notifications / Realtime lots):
- `ChecklistTemplateCreated`, `ChecklistTemplateUpdated`, `ChecklistTemplateActivated`, `ChecklistTemplateDeactivated`
- `ChecklistAssignmentCreated`, `ChecklistAssignmentUpdated`, `ChecklistAssignmentDeactivated`
- `ChecklistExecutionCreated`, `ChecklistExecutionProgressed`, `ChecklistExecutionDone`, `ChecklistExecutionCanceled`
- `ChecklistTaskCompleted`, `ChecklistTaskSkipped`, `ChecklistTaskObservationCreated`

## 11. API Surface

Current API truth: [`apps/api/schema.yml`](../../../apps/api/schema.yml) — checklist endpoints are **implemented** (establishment-scoped, `/api/v1/establishments/{establishment_id}/`).

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `checklist-templates/?type=shared\|personal` | List (filtered by type / permissions) / create |
| GET, PATCH, DELETE | `checklist-templates/{id}/` | Detail / update / delete |
| POST | `checklist-templates/{id}/activate/` | Activate (requires ≥1 task) |
| POST | `checklist-templates/{id}/deactivate/` | Deactivate |
| POST | `checklist-templates/{id}/tasks/` | Add task |
| PATCH, DELETE | `checklist-task-templates/{id}/` | Update / delete task |
| POST | `checklist-templates/{id}/tasks/reorder/` | Reorder tasks by position |
| GET | `checklist-assignments/` | List shared **active** assignments (RBAC filtered) |
| POST | `checklist-templates/{id}/assignments/` | Create assignment + materialize first occurrence |
| GET, PATCH | `checklist-assignments/{id}/` | Detail / update schedule |
| POST | `checklist-assignments/{id}/deactivate/` | Deactivate assignment |
| POST | `checklist-templates/{id}/personal-executions/` | Create personal execution (personal templates only) |
| GET | `checklist-executions/{id}/` | Detail with task executions + `permission_hints` |
| POST | `checklist-task-executions/{id}/mark-done/` | Mark task done |
| POST | `checklist-task-executions/{id}/skip/` | Skip task (optional `skipped_reason`) |
| POST | `checklist-task-executions/{id}/create-observation/` | Observation handoff |
| POST | `checklist-executions/{id}/cancel/` | Cancel execution |

**Not in MVP:** `POST .../start/`, `POST .../executions/` on shared templates (use assignments).

Execution Feed: existing `GET execution-feed/` returns polymorphic items with `item_type: "action" | "checklist"` — no separate checklist feed endpoint.

Inspect `schema.yml` before claiming any additional checklist endpoint exists.

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
- Execution Feed renders checklist items via [`ExecutionChecklistCard`](../../../apps/web/src/features/execution/components/execution-checklist-card.tsx) (polymorphic `item_type: checklist`).
- Notifications for assign / done: **future lot** — do not implement in initial Checklist frontend lot.
- Staff: no shared catalogue or assignment UI; Profil shows personal section only.

## 13. Execution Feed integration (implemented)

Owned by Feed domain for projection rules; Checklist domain owns lifecycle and feed-eligible statuses.

- `ExecutionFeedItem` polymorphism: `item_type: "action" | "checklist"`.
- Checklist feed item exposes safe summary (title, progress, `end_at`, `is_overdue`, `business_unit` label, status).
- Visibility: `status IN (assigned, in_progress)` AND `now >= visible_from` (or `visible_from` null) AND RBAC `view_mode` rules (§9).
- `end_at` does not remove items; only `done`/`canceled` exclude from active feed.
- Page merge: checklists prioritized, Actions fill remaining slots (see §3.17).
- Orchestration: [`actions/execution_feed.py`](../../../apps/api/houston/actions/execution_feed.py) triggers lazy materialization then merges querysets.
- See [`feed_domain.md`](feed_domain.md).

## 14. Backend module architecture

| Module | Path | Responsibility |
| --- | --- | --- |
| `selectors.py` | [`checklists/selectors.py`](../../../apps/api/houston/checklists/selectors.py) | Read-only query composition: catalogues, feed querysets, detail prefetch, overdue helper. No writes, no materialization. |
| `materialization.py` | [`checklists/materialization.py`](../../../apps/api/houston/checklists/materialization.py) | Occurrence math, eager/lazy/horizon materialization, `visible_from = start_at - 1h`, idempotent execution create. |
| `services.py` | [`checklists/services.py`](../../../apps/api/houston/checklists/services.py) | Business commands: template/task/assignment CRUD, execution transitions, observation handoff, assignment schedule sync. |
| `permissions.py` | [`checklists/permissions.py`](../../../apps/api/houston/checklists/permissions.py) | RBAC pure: establishment-scoped authorization helpers. |
| `permission_hints.py` | [`checklists/permission_hints.py`](../../../apps/api/houston/checklists/permission_hints.py) | UX hints derived from permissions (+ conflict checks where applicable); exposed on API responses, not authorization authority. |
| `execution_feed.py` | [`actions/execution_feed.py`](../../../apps/api/houston/actions/execution_feed.py) | Thin polymorphic feed orchestrator: lazy materialization trigger, checklist-first page merge, Action fill. |

## 15. AI Agent Notes

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
