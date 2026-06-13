# Pagination Audit — 2026-06-13

**Date:** 2026-06-13  
**Ticket:** HOU-BACKLOG-018  
**Status:** advisory  
**Standard (authoritative):** [`api_pagination_standard.md`](../engineering/api_pagination_standard.md)

## 1. Scope

Audit main list endpoints exposed in the Houston app. Classify pagination behavior. Define per-endpoint decisions. Derive implementation tickets.

**This ticket:** documentation only. No API, schema, or frontend code changes.

**Environment:** local dev only; test data. No production metrics. Threshold ~50 rows per establishment is guidance from Phase L, not benchmarked.

## 2. Methodology

| Source | Use |
|--------|-----|
| `apps/api/schema.yml` | Query params and response schemas |
| Backend views/selectors | Pagination logic |
| `apps/web/src/features/*/hooks.ts` | TanStack Query pattern (`useQuery` vs `useInfiniteQuery`) |
| [`code_scalability_s0_2026-06-11.md`](code_scalability_s0_2026-06-11.md) | API-02, API-03, API-04 |
| [`db_scalability_phase_l_2026-06-11.md`](db_scalability_phase_l_2026-06-11.md) | Unbounded list inventory, ~50-row threshold |

**Finding:** Houston does not use DRF `PageNumberPagination`, `LimitOffsetPagination`, or `CursorPagination`. List behavior is bespoke per view.

## 3. Classification legend

| Class | Meaning |
|-------|---------|
| **Cursor-paginated** | `cursor` request param + `next_cursor` response + `has_more`; multi-page works |
| **Pseudo-paginated** | `page_size` / `has_more` present but page 2 not reachable (missing or stub `next_cursor`) |
| **Cursor partial** | Cursor on request; `has_more` in response; no server `next_cursor` |
| **Hard limit** | Fixed or param-capped slice (`limit`, `[:100]`) |
| **Non-paginated** | Full scoped result set returned |
| **Non-priority** | Non-paginated by design; low expected volume |

## 4. Critical endpoints (backlog scope)

### 4.1 Signal Feed — reference

| Field | Value |
|-------|-------|
| Route | `GET /api/v1/establishments/{establishment_id}/signal-feed/` |
| Classification | **Cursor-paginated (reference)** |
| Backend | [`signals/api/views.py`](../../apps/api/houston/signals/api/views.py), [`signals/feed_cursor.py`](../../apps/api/houston/signals/feed_cursor.py) |
| Frontend | [`signals/hooks.ts`](../../apps/web/src/features/signals/hooks.ts) — `useInfiniteQuery` |
| Query params | `view_mode` (required), `cursor`, `page_size`, filters |
| Response | `{ items, next_cursor, has_more, applied_filters }` |
| Decision | **Keep as reference.** Document in standard. |

### 4.2 Execution Feed — **resolved** (HOU-BACKLOG-019 / HOU-PAG-001+002)

| Field | Value |
|-------|-------|
| Route | `GET /api/v1/establishments/{establishment_id}/execution-feed/` |
| Classification | **Cursor-paginated** (was pseudo-paginated) |
| Backend | [`actions/api/views.py`](../../apps/api/houston/actions/api/views.py), [`actions/execution_feed.py`](../../apps/api/houston/actions/execution_feed.py), [`actions/execution_feed_cursor.py`](../../apps/api/houston/actions/execution_feed_cursor.py) |
| Frontend | [`actions/hooks.ts`](../../apps/web/src/features/actions/hooks.ts) — `useInfiniteQuery` + « Charger plus » |
| Query params | `view_mode` (required), `cursor`, `page_size` |
| Response | `{ items, next_cursor, has_more }` — `has_more=true` ⇒ non-null `next_cursor` |
| Merge rule | Checklist-first preserved (not global cross-type sort) |
| Delivered | 2026-06-13 — HOU-BACKLOG-019 |

**Resolution note:** Polymorphic opaque cursor (checklist phase + action phase with `as_of` and `action_phase_start`). Sort tie-breaker `-id`. Invalid cursor → `400 validation_error`.

### 4.3 Checklist templates

| Field | Value |
|-------|-------|
| Route | `GET /api/v1/establishments/{establishment_id}/checklist-templates/` |
| Classification | **Non-paginated** |
| Backend | [`checklists/api/views.py`](../../apps/api/houston/checklists/api/views.py) |
| Frontend | [`checklists/hooks.ts`](../../apps/web/src/features/checklists/hooks.ts) — `useChecklistTemplatesQuery` |
| Response | Raw `ChecklistTemplateListItem[]` |
| Decision | **Non-priority** if catalogue < ~50; else HOU-PAG-006 (`page`/`limit` or cursor). Migrate envelope via HOU-PAG-009. |

### 4.4 Checklist assignments

| Field | Value |
|-------|-------|
| Route | `GET /api/v1/establishments/{establishment_id}/checklist-assignments/` |
| Classification | **Non-paginated** |
| Backend | [`checklists/api/views.py`](../../apps/api/houston/checklists/api/views.py) |
| Frontend | [`checklists/hooks.ts`](../../apps/web/src/features/checklists/hooks.ts); UI filters by `checklist_template_id` client-side |
| Response | Raw `ChecklistAssignment[]` |
| Decision | **Non-priority** at low volume; HOU-PAG-007 if growth or over-fetch hurts. Prefer API filter by template. |

### 4.5 Users search

| Field | Value |
|-------|-------|
| Route | `GET /api/v1/establishments/{establishment_id}/users/search/` |
| Classification | **Non-paginated** |
| Backend | [`establishments/api/views.py`](../../apps/api/houston/establishments/api/views.py), [`establishments/selectors.py`](../../apps/api/houston/establishments/selectors.py) |
| Frontend | [`actions/hooks.ts`](../../apps/web/src/features/actions/hooks.ts) — `useEstablishmentUserSearchQuery` |
| Response | Raw `ScopedUserSearchResult[]` |
| Decision | HOU-PAG-005 — add `limit` cap (Tier D typeahead). No cursor. |

## 5. Other app-exposed lists

### Tier B — Chronological

| Endpoint | Class | Backend | Frontend | Decision |
|----------|-------|---------|----------|----------|
| `GET .../chat/conversations/{id}/messages/` | Cursor partial | [`chat/api/views.py`](../../apps/api/houston/chat/api/views.py) | [`chat/hooks.ts`](../../apps/web/src/features/chat/hooks.ts) `useInfiniteQuery`; client builds cursor | HOU-PAG-003 |
| `GET .../chat/conversations/` | Non-paginated | [`chat/api/views.py`](../../apps/api/houston/chat/api/views.py) | [`chat/hooks.ts`](../../apps/web/src/features/chat/hooks.ts) | HOU-PAG-004 (+ DB-03 N+1) |

### Tier C — Management

| Endpoint | Class | Response | Decision |
|----------|-------|----------|----------|
| `GET .../memberships/` | Non-paginated | Raw array | HOU-PAG-008 if > ~50 |
| `GET .../onboarding-sessions/{id}/proposals/` | Non-paginated | Raw array | **Non-priority** (session-scoped) |
| `GET .../checklist-templates/{id}/` → `tasks[]` | Non-paginated nested | Detail inline | **Non-priority** |
| `GET .../checklist-executions/{id}/` → `task_executions[]` | Non-paginated nested | Detail inline | **Non-priority** |

### Tier D — Trees / bootstrap / suggest

| Endpoint | Class | Pattern | Decision |
|----------|-------|---------|----------|
| `GET .../business-units/` | Non-paginated | `{ business_units: tree[] }` | **Non-priority** |
| `GET /api/v1/auth/bootstrap/` | Non-paginated | `memberships[]` nested | **Non-priority** |
| `GET /api/v1/catalog/*/suggest/` | Hard limit | `limit` default 20, max 200 | Keep; document as Tier D reference |
| `GET .../chat/eligible-memberships/` | Hard limit | `{ items }` slice `[:100]` | HOU-PAG-009 envelope; optional explicit `limit` |

## 6. Response envelope inconsistencies

| Envelope | Endpoints |
|----------|-----------|
| `{ items, next_cursor, has_more }` | Signal feed (complete), Execution feed (complete) |
| `{ items, has_more }` | Chat messages |
| `{ items }` | Chat conversations, chat eligible memberships |
| Raw `Item[]` | Checklist templates/assignments, users search, memberships, catalog suggest, onboarding proposals |
| Nested object | Bootstrap, business-unit tree, checklist/execution detail |

**Frontend impact:** `useInfiniteQuery` only on Signal Feed and Chat messages. No shared pagination hook in `apps/web/src/lib/`.

## 7. Key inconsistencies (FE / BE / OpenAPI)

| ID | Issue | Files |
|----|-------|-------|
| INC-01 | ~~Execution Feed schema promises `next_cursor`; backend always returns `null`; no `cursor` query param~~ | **Resolved** HOU-BACKLOG-019 |
| INC-02 | ~~Execution Feed FE ignores `has_more`; no load-more UI~~ | **Resolved** HOU-BACKLOG-019 |
| INC-03 | Chat messages: two cursor models (server opaque vs client `created_at\|id`) | `chat/api/views.ts`, `chat/hooks.ts` |
| INC-04 | Checklist assignments: establishment-wide fetch, template filter in UI | `checklists/hooks.ts`, `checklist-assignment-section.tsx` |
| INC-05 | Raw arrays vs `{ items }` split across list endpoints | Multiple views/serializers |
| INC-06 | S0 API-02 noted signal `count()` for `has_more` — code now uses `limit+1`; verify if S0 finding is stale | `signals/api/views.py` |

## 8. Per-endpoint decision summary

| Endpoint | Class | Pagination decision |
|----------|-------|---------------------|
| Signal feed | Cursor-paginated | **Reference** — no change |
| Execution feed | Cursor-paginated | **Delivered** — HOU-BACKLOG-019 |
| Checklist templates | Non-paginated | Non-priority; paginate if > ~50 |
| Checklist assignments | Non-paginated | Non-priority; API filter + paginate if needed |
| Users search | Non-paginated | Add `limit` (P1) |
| Chat messages | Cursor partial | Align to standard or document exception (P1) |
| Chat conversations | Non-paginated | Cursor when > ~50 (P1) |
| Memberships | Non-paginated | `page`/`limit` if > ~50 (P2) |
| Catalog suggest | Hard limit | Keep |
| Chat eligible memberships | Hard limit | Document cap (P2) |
| Business units / bootstrap / onboarding proposals | Non-paginated | Non-priority |

## 9. Derived implementation tickets

### HOU-PAG-001 (P0) — Execution Feed cursor backend — **delivered**

**Scope:** Polymorphic cursor (action + checklist merge rules), `cursor` query param, real `next_cursor`, `limit+1` for `has_more`, API tests.

**Acceptance:**

- [x] `cursor` and `page_size` in OpenAPI
- [x] Page 2 reachable when `has_more=true`
- [x] `next_cursor` non-null when `has_more=true`
- [x] Focused pytest green

### HOU-PAG-002 (P0) — Execution Feed frontend — **delivered**

**Scope:** `useInfiniteQuery`, load-more button, optional `page_size`.

**Acceptance:**

- [x] `make web-api-generate` after schema update
- [x] `npm run typecheck` + `npm test` green
- [x] Load more fetches page 2 with server cursor

### HOU-PAG-003 (P1) — Chat messages envelope

**Scope:** Add server `next_cursor` **or** document permanent client-derived cursor exception in standard.

### HOU-PAG-004 (P1) — Chat conversations pagination

**Scope:** Cursor list + address DB-03 N+1 in conversation list serialization.

### HOU-PAG-005 (P1) — Users search limit

**Scope:** `limit` query param (default + max), backend selector cap, FE passes limit.

### HOU-PAG-006 (P1) — Checklist templates pagination

**Scope:** If dev data exceeds ~50 templates, add `page`/`limit` or cursor; wrap in `{ items }` if changing shape.

### HOU-PAG-007 (P1) — Checklist assignments

**Scope:** Optional `checklist_template_id` filter on API; pagination if needed; stop client-side over-fetch.

### HOU-PAG-008 (P2) — Membership roster

**Scope:** `page`/`limit` when roster > ~50.

### HOU-PAG-009 (P2) — Envelope harmonization

**Scope:** Migrate raw `Item[]` → `{ items }` one endpoint per PR; schema + types + FE + tests; no dual format.

### HOU-PAG-010 (P2) — Shared backend helpers

**Scope:** Extract `parse_page_size` and `limit+1` pattern after PAG-001/002.

**Recommended order:** PAG-001 → PAG-002 first (backlog acceptance criterion).

## 10. PR checklist (all implementation tickets)

1. Backend change + tests
2. `make schema`
3. `make web-api-generate`
4. Frontend hooks/pages
5. `make backend-test` (or focused pytest) + `npm test` + `npm run typecheck`

No backward compatibility layer. Breaking changes OK in same PR.

## 11. Cross-references

- Standard: [`docs/engineering/api_pagination_standard.md`](../engineering/api_pagination_standard.md)
- Feed domain: [`docs/product/domains/feed_domain.md`](../product/domains/feed_domain.md)
- S0 audit API-02/03/04: [`code_scalability_s0_2026-06-11.md`](code_scalability_s0_2026-06-11.md)
- Phase L API-04: [`db_scalability_phase_l_2026-06-11.md`](db_scalability_phase_l_2026-06-11.md)

## 12. Risks / not verified

- ~50-row threshold not measured on local fixtures
- Polymorphic Execution Feed cursor under checklist-first merge — **validated** in HOU-BACKLOG-019
- S0 API-02 (`count()` on signal feed) may be stale vs current `limit+1` implementation

## 13. HOU-BACKLOG-018 acceptance

- [x] Critical endpoint inventory documented (this audit)
- [x] Per-endpoint pagination decision documented (§8 + standard)
- [x] Signal Feed marked as existing reference (§4.1)
- [x] Execution Feed marked P0 implementation priority (§4.2, PAG-001/002)
- [x] No functional code changes in this ticket
