# Action Domain

Status: authoritative  
Last reviewed: 2026-06-12  
Implementation status: implemented (BE-ACTION-V2)

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
- Staff: cannot create

### Shared lifecycle

- Lifecycle: `open` → `in_progress` → `pending_validation` → `done` (explicit command endpoints)
- `reopened`, `canceled`, `reassign_action`, `update_action_due_at`
- Execution Feed projection (`GET .../execution-feed/`)
- Signal side effects for linked Actions only

## 3. Out of Scope

- AI-created Actions
- Generic status PATCH
- ActivitySubject on free Actions
- Historical data backfill

Checklist executions in the polymorphic Execution Feed are **in scope** — see [`checklist_domain.md`](checklist_domain.md) §5.6 and [`feed_domain.md`](feed_domain.md) §7.

## 4. Core Invariants

- Backend owns all transitions via dedicated services
- Linked Actions: first on `open` Signal → `in_progress` + unpin; resolve blocked if active linked Actions; auto-resolve when all terminal with ≥1 `done`
- Free Actions: no Signal side effects
- Legacy `operational_*` compatibility is removed from product behavior.
- **Visibility ≠ actionability** for Manager scope (see §6)

### Classification invariants

| `signal_id` | `affected_business_unit` | `responsible_business_unit` | `activity_subject` |
| --- | --- | --- | --- |
| set | required (from Signal) | required (from Signal) | required (from Signal) |
| null | null | required (from request) | null |

## 5. API Surface (implemented)

Under `/api/v1/establishments/{establishment_id}/`:

- `POST actions/` — dual-mode create (see §2)
- `GET actions/{action_id}/`
- `POST actions/{id}/accept|mark-done|validate|reopen|cancel|reassign/`
- `PATCH actions/{id}/due-at/`
- `GET execution-feed/?view_mode=personal|general` → `{ items, next_cursor, has_more }`

**ActionFeedItem / ActionDetail** expose:

- `affected_business_unit_key`, `affected_business_unit_label` (nullable)
- `responsible_business_unit_key`, `responsible_business_unit_label`
- `activity_subject_normalized_name`, `activity_subject_label` (nullable)
- `signal_summary` (if linked) with `location_text` and Signal BU/AS context

Signal: `POST signals/{id}/resolve/` returns **409** `business_conflict` when linked Actions are active.

## 6. Permissions (summary)

| Role | Create linked | Create free | Validate/cancel/reopen | Reassign | Feed Ma vue (`personal`) | Feed Vue globale (`general`) |
|------|---------------|-------------|------------------------|----------|------------------------|------------------------------|
| Owner/Director | all | all BU | all | all | `created_by` or `assigned_to` | all establishment |
| Manager | responsible BU actionable on Signal | BU in scope | own `created_by` | responsible BU actionable | `created_by` or `assigned_to` | personal + scope visibility |
| Staff | no | no | no | no | `created_by` or `assigned_to` | same as personal |

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
- Do not expose `_pipeline_db_shim` / placeholder / noop values in API responses
