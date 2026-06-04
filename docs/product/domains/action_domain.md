# Action Domain

Status: authoritative  
Last reviewed: 2026-06-04  
Implementation status: implemented (Phase 5)

## 1. Purpose

Action owns concrete operational execution work: assignable, executable, and validatable tasks.

Action may be **linked** to a Signal (`signal` FK) or **free** (`signal` null). Each Action has its **own** operational taxonomy (module/domain/subject FKs), not inherited from the parent Signal.

## 2. MVP Scope

- Create Action (free or linked) via `POST .../actions/`
- Lifecycle: `open` → `in_progress` → `pending_validation` → `done` (via explicit command endpoints)
- `reopened`, `canceled`, `reassign_action`, `update_action_due_at`
- Execution Feed projection (`GET .../execution-feed/`)
- Signal side effects for linked Actions only
- `marked_done_at` on mark-done; `validated_at` on validate (no `completed_at`)

## 3. Out of Scope

- AI-created Actions
- Generic status PATCH
- Checklists in Execution Feed (Phase 7)
- Comments, mentions, `SignalAccessGrant` table (doc candidate only)
- `MembershipFeedSubscription`

## 4. Core Invariants

- Backend owns all transitions via dedicated services
- Free Actions have no Signal side effects
- Linked Actions: first on `open` Signal → `in_progress` + unpin; resolve blocked if active linked Actions; auto-resolve when all terminal with ≥1 `done`
- Taxonomy on Action row is mandatory and independent of Signal taxonomy
- Execution Feed `view_mode=personal|general` is backend-enforced; Staff never gains scope-only Actions in **general**

## 5. API Surface (implemented)

Under `/api/v1/establishments/{establishment_id}/`:

- `POST actions/`
- `GET actions/{action_id}/`
- `POST actions/{id}/accept|mark-done|validate|reopen|cancel|reassign/`
- `PATCH actions/{id}/due-at/`
- `GET execution-feed/?view_mode=personal|general` → `{ items, next_cursor, has_more }`

Signal: `POST signals/{id}/resolve/` returns **409** `business_conflict` when linked Actions are active.

## 6. Permissions (summary)

| Role | Create | Validate/cancel/reopen | Reassign | update due_at | Feed Ma vue (`personal`) | Feed Vue globale (`general`) |
|------|--------|----------------------|----------|---------------|--------------------------|------------------------------|
| Owner/Director | all | all | all | all | `created_by` or `assigned_to` | all establishment |
| Manager | scope + signal access if linked | own `created_by` | scope | own `created_by` | `created_by` or `assigned_to` | personal + `MembershipScope` |
| Staff | no | no | no | no | `created_by` or `assigned_to` | same as personal |

Detail: Action **detail** visibility follows `action_visible_to_membership` (manager may open scope-only Actions not listed in Ma vue). `done`/`canceled` readable in detail without feed-active status filter.

## 7. AI Agent Notes

- Inspect `apps/api/schema.yml` before claiming endpoints
- Do not add `completed_at`; use `marked_done_at`
- See [`signal_access_grant_domain.md`](signal_access_grant_domain.md) for future mention access
