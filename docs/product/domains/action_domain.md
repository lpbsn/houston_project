# Action Domain

Status: authoritative  
Last reviewed: 2026-06-18  
Implementation status: implemented — Phase 1 multi-assignee (backend)

## 1. Purpose

Action owns concrete operational execution work: assignable, executable, and validatable tasks.

An Action is classified by **BusinessUnit / ActivitySubject** (v2, authoritative).

## 2. MVP Scope — two creation modes

### Linked Action (from Signal)

- `POST .../actions/` with `signal` UUID
- Backend copies from Signal:
  - `affected_business_unit`
  - `responsible_business_unit`
  - `activity_subject`
- Client must **not** send `module_key`, `domain_key`, `subject_key` (rejected with validation error)
- Client must **not** send `responsible_business_unit_id` when `signal` is set

### Free Action (no Signal)

- `POST .../actions/` with `signal: null` and `responsible_business_unit_id`
- `activity_subject` and `affected_business_unit` remain null
- No ActivitySubject required
- Owner/Director: any establishment BusinessUnit
- Manager: BusinessUnit in `MembershipScope` only
- Staff: BusinessUnit in `MembershipScope` only; **self-assign only** (`assignee_ids` must be exactly the creator's membership id); cannot create linked Actions from Signals

### Assignees (multi-assignee, Phase 1)

- Create with `assignee_ids` (1 to N membership UUIDs, `minItems: 1`)
- Duplicate IDs forbidden (request validation + service)
- Assignees must be **active** memberships of the same establishment
- Optional `requires_validation` at create (default `true`)
- **Staff:** exactly one assignee — themselves only (no multi-assignee create)

### Shared lifecycle

- While `open` or `reopened`: any assignee may **accept**; the first available assignee who accepts becomes `accepted_by` and moves the Action to `in_progress` (row lock; one winner under concurrency)
- Only `accepted_by` may **mark done**
- If `requires_validation=true` (default): `mark_done` → `pending_validation` → `validate` → `done`
- If `requires_validation=false`: `mark_done` → `done` directly; linked Signal sync when applicable; `can_validate=false`
- `reopened`, `canceled`, `reassign`, `update_action_due_at`
- Execution Feed projection (`GET .../execution-feed/`)
- Signal side effects for linked Actions only

### Reassign (Phase 1)

- `POST .../reassign/` with `assignee_ids` replacing the **entire** list
- Allowed from `open` (stays `open`), `reopened` (stays `reopened`), `in_progress` (resets to `open`, clears `accepted_by` / `accepted_at`)
- Refused from `pending_validation`, `done`, `canceled`

## 3. Out of Scope

- AI-created Actions
- Generic status PATCH
- ActivitySubject on free Actions
- Historical data backfill
- **Recurrence** (independent occurrences — later phase)
- **Validator groups** in V1 (validation uses existing RBAC only)
- Frontend Phase 1 (API contract changed; regenerate types in a later phase)

Checklist executions in the polymorphic Execution Feed are **in scope** — see [`checklist_domain.md`](checklist_domain.md) §5.6 and [`feed_domain.md`](feed_domain.md) §7.

## 4. Core Invariants

- Backend owns all transitions via dedicated services with `select_for_update` re-lock per `action_id`
- An Action must have at least one assignee (`ActionAssignee` rows)
- Assignees are active memberships of the same establishment; no duplicates
- All assignees see the Action in their personal feed; the creator sees it even when not assigned
- `accepted_by` is the effective responsible member after acceptance; only they may mark done
- Linked Actions: first on `open` Signal → `in_progress` + unpin; resolve blocked if active linked Actions; auto-resolve when all terminal with ≥1 `done`
- Free Actions: no Signal side effects
- Legacy `operational_*` compatibility is removed from product behavior.
- **Visibility ≠ actionability** for Manager scope (see §6)
- Feed visibility for assignees uses `Exists` subquery (no M2M join duplication)

### Classification invariants

| `signal_id` | `affected_business_unit` | `responsible_business_unit` | `activity_subject` |
| --- | --- | --- | --- |
| set | required (from Signal) | required (from Signal) | required (from Signal) |
| null | null | required (from request) | null |

### Canonical responsible BusinessUnit (validation)

Helper: `resolve_action_responsible_business_unit(action)` in `action_classification.py`

- **Free Action:** `action.responsible_business_unit`
- **Linked Action:** `action.responsible_business_unit` (copied from Signal at create); fallback `signal.responsible_business_unit` if null
- If no responsible BU can be determined: Manager validation denied; Owner/Director may still validate

## 5. API Surface (implemented)

Under `/api/v1/establishments/{establishment_id}/` — see `apps/api/schema.yml`

- `POST actions/` — `ActionCreateRequest`: `assignee_ids[]`, `requires_validation?`, dual-mode create (see §2)
- `GET actions/{action_id}/` — `ActionDetail`
- `POST actions/{id}/accept|mark-done|validate|reopen|cancel|reassign/` — `ActionReassignRequest` uses `assignee_ids[]`
- `PATCH actions/{id}/due-at/`
- `GET execution-feed/?view_mode=personal|general` → `{ items, next_cursor, has_more }`

**ActionFeedItem / ActionDetail** expose:

- `assignees[]` — `ActionMembershipRef`: `{ membership_id, display_name, role }`
- `accepted_by` — `ActionAcceptedBy | null`: `{ membership_id, display_name }`
- `requires_validation` (boolean)
- `accepted_at`, `marked_done_at`, `validated_at` (detail)
- Classification + `signal_summary` (unchanged shape)
- `permission_hints` — see §6

Signal: `POST signals/{id}/resolve/` returns **409** `business_conflict` when linked Actions are active.

## 6. Permissions (summary)

| Role | Create linked | Create free | Validate | Cancel/reopen | Reassign | Feed Ma vue (`personal`) | Feed Vue globale (`general`) |
|------|---------------|-------------|----------|---------------|----------|------------------------|------------------------------|
| Owner/Director | all | all BU | all when `requires_validation` + `pending_validation` | all | all | `created_by` or any assignee | all establishment |
| Manager | responsible BU actionable on Signal | BU in scope | canonical responsible BU in scope | own `created_by` | responsible BU actionable | `created_by` or any assignee | personal + scope visibility |
| Staff | no | BU in scope, self-assign only | no | no | no | `created_by` or any assignee | same as personal |

**Validate V1:** Owner/Director always (when `requires_validation` and `pending_validation`). Manager only when canonical responsible BU is in `MembershipScope`. No validator group.

**Accept:** any assignee while `open`/`reopened`.

**Mark done:** `accepted_by` only while `in_progress`.

### Permission hints (`ActionPermissionHints`)

| Hint | Rule (UX only) |
|------|----------------|
| `can_accept` | assignee + `open`/`reopened` |
| `can_mark_done` | `accepted_by` + `in_progress` |
| `can_validate` | `requires_validation` + validate permission |
| `can_reopen` / `can_cancel` / `can_reassign` / `can_update_due_at` | unchanged manager/creator rules; reassign blocked on terminal/pending_validation |
| `is_assignee` | membership in `assignees` |
| `accepted_by_me` | `accepted_by.membership_id == actor` |

### Manager visibility vs actionability

**Linked Action:**

- **Visibility** (general feed, detail): `affected_business_unit` OR `responsible_business_unit` in scopes
- **Actionability** (create linked, reassign scope): `responsible_business_unit` in scopes only

**Free Action:**

- **Visibility** and **actionability**: `responsible_business_unit` in scopes

Detail: Action **detail** visibility follows `action_visible_to_membership`. `done`/`canceled` readable in detail without feed-active status filter.

## 7. AI Agent Notes

- Inspect `apps/api/schema.yml` before claiming endpoints
- Do not add `completed_at`; use `marked_done_at`
- Reject legacy taxonomy keys on create — do not ignore silently
- Use `assignee_ids` on create/reassign; single `assigned_to` removed
- Regenerate frontend types with `make web-api-generate` when starting frontend Phase 2
