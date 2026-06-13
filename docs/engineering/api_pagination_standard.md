# API Pagination Standard

Status: authoritative  
Last reviewed: 2026-06-13  
Ticket: HOU-BACKLOG-018

## 1. Purpose

Define how Houston list endpoints paginate (or intentionally do not), and how the frontend consumes them.

This document applies to:

- new list endpoints
- pagination fixes on existing endpoints (see derived tickets in [`pagination_audit_2026-06-13.md`](../audit/pagination_audit_2026-06-13.md))

## 2. Authority order

1. Current source code
2. [`apps/api/schema.yml`](../../apps/api/schema.yml)
3. [`AGENTS.md`](../../AGENTS.md) files
4. This document
5. Archived docs (historical only)

If code and this document conflict, code wins until this document is updated in the same change set.

## 3. Context

**Environment:** local dev only. No staging/prod deployment. Test data only.

**Change policy:**

- No backward compatibility period, API versioning, feature flags, or temporary dual response formats.
- Breaking API shape changes are acceptable when the frontend is adapted in the **same PR**.
- Contractual rigor per PR: update `schema.yml`, regenerate TypeScript types, adapt frontend callers, keep API and frontend tests green.

Commands (from repo root):

```bash
make schema && make web-api-generate   # after API shape change
make backend-test                      # API tests
cd apps/web && npm test && npm run typecheck   # FE tests + types
```

## 4. Tiers

### Tier A — Dynamic feeds (cursor required)

Use for operational feeds that change frequently (realtime invalidation, sort buckets, priority).

| Rule | Value |
|------|-------|
| Mechanism | Cursor-based only (no offset) |
| Query params | `cursor` (opaque, optional on page 1), `page_size` |
| Default `page_size` | 25 |
| Max `page_size` | 50 |
| `has_more` | `limit + 1` pattern — **not** full `queryset.count()` |
| Cursor encoding | Opaque, server-side, tied to stable feed sort keys |
| Frontend | `useInfiniteQuery`; manual « Charger plus » button (no implicit infinite scroll) |

**Response envelope:**

```json
{
  "items": [],
  "next_cursor": "opaque-string-or-null",
  "has_more": true
}
```

Optional endpoint-specific fields (e.g. `applied_filters` on Signal Feed) are documented per endpoint, not part of the shared envelope.

**Endpoints today:**

| Endpoint | Status |
|----------|--------|
| `GET .../signal-feed/` | **Reference** — full cursor round-trip |
| `GET .../execution-feed/` | **Complete** — polymorphic cursor (checklist-first merge preserved) |

Execution Feed cursor specifics (HOU-BACKLOG-019):

- Opaque server cursor with checklist phase and action phase (`action_phase_start` = action phase without item position).
- Sort tie-breaker `-id` on checklist and action lists.
- Action cursor encodes `as_of` to stabilize `is_overdue_rank` across paginated requests (mid-pagination rank drift possible if status changes between pages; mutations invalidate the feed).

### Tier B — Chronological streams

Use for message-like lists ordered by time.

| Rule | Value |
|------|-------|
| Mechanism | Cursor on request; prefer server `next_cursor` in response |
| Default `page_size` | 50 (chat messages today) |
| Max `page_size` | 100 (chat messages today) |

**Target envelope:** same as Tier A (`items`, `next_cursor`, `has_more`).

**Exception today:** chat messages return `{ items, has_more }` only; the frontend builds the next cursor from the oldest item (`created_at|uuid`). Align to Tier A in HOU-PAG-003 or document as a permanent exception.

### Tier C — Configuration / management lists

Use for admin or catalogue lists with slower growth.

| Rule | Value |
|------|-------|
| Default | No pagination if typical volume **< ~50 rows** per establishment (guidance from Phase L audit) |
| When needed | `page`/`limit` acceptable for stable admin lists; cursor only if list is dynamically sorted like a feed |
| Response target | `{ items: [...] }` |

**Raw array migration:** endpoints that today return `Item[]` directly should migrate to `{ items }` **directly**, one endpoint per PR, with no temporary compatibility layer. Same PR must update schema, regenerated types, frontend hooks, and tests.

**Endpoints today (non-paginated):** checklist templates, checklist assignments, membership roster, onboarding proposals (session-scoped).

### Tier D — Search / typeahead / hard-capped lists

Use for autocomplete and scoped search.

| Rule | Value |
|------|-------|
| Mechanism | `limit` with documented default and max |
| Cursor | Not used |
| Frontend | `useQuery` with `enabled: query.length >= minLength` |

**Reference:** catalog suggest endpoints — default `limit` 20, max 200.

**Endpoints today:** `GET /api/v1/catalog/*/suggest/`, `GET .../users/search/` (no limit yet — HOU-PAG-005), `GET .../chat/eligible-memberships/` (hard slice `[:100]`).

## 5. Reference implementation — Signal Feed

Signal Feed is the **existing reference** for Tier A (backend + frontend).

### Backend

| File | Role |
|------|------|
| [`apps/api/houston/signals/api/views.py`](../../apps/api/houston/signals/api/views.py) | `SignalFeedView` — parses `cursor`, `page_size`, `limit+1`, returns `next_cursor` |
| [`apps/api/houston/signals/feed_cursor.py`](../../apps/api/houston/signals/feed_cursor.py) | Encode/decode opaque cursor from stable sort keys |
| [`apps/api/houston/signals/selectors.py`](../../apps/api/houston/signals/selectors.py) | `signal_feed_queryset`, `apply_feed_sorting` |
| [`apps/api/houston/signals/api/serializers.py`](../../apps/api/houston/signals/api/serializers.py) | `SignalFeedResponseSerializer` |

### Frontend

| File | Role |
|------|------|
| [`apps/web/src/features/signals/hooks.ts`](../../apps/web/src/features/signals/hooks.ts) | `useSignalFeedQuery` — `useInfiniteQuery`, `getNextPageParam` from `next_cursor` |
| [`apps/web/src/features/signals/api.ts`](../../apps/web/src/features/signals/api.ts) | `fetchSignalFeed` — passes `cursor` query param |
| [`apps/web/src/features/signals/pages/signal-feed-page.tsx`](../../apps/web/src/features/signals/pages/signal-feed-page.tsx) | Merges `data.pages`, « Charger plus » via `fetchNextPage()` |

### OpenAPI

- `GET .../signal-feed/` exposes `cursor` and `page_size` query params.
- `SignalFeedResponse`: `items`, `next_cursor`, `has_more`, `applied_filters`.

## 6. Response envelope matrix (current state)

| Envelope | Endpoints |
|----------|-----------|
| `{ items, next_cursor, has_more }` | Signal feed (complete), Execution feed (complete) |
| `{ items, has_more }` | Chat messages |
| `{ items }` | Chat conversations, chat eligible memberships |
| Raw `Item[]` | Checklist templates, checklist assignments, users search, memberships, catalog suggest, onboarding proposals |
| Nested object | Bootstrap, business-unit tree, checklist/execution detail |

Target over time: paginated lists use Tier A/B envelope; non-paginated lists use `{ items }` (Tier C).

## 7. PR checklist (implementation tickets)

When changing list pagination or response shape:

1. **Backend** — view/selector/serializer; add or fix tests (`pytest` focused on endpoint).
2. **OpenAPI** — `make schema`; verify `cursor` / `page_size` / response fields in `schema.yml`.
3. **Frontend types** — `make web-api-generate`.
4. **Frontend callers** — hooks (`useInfiniteQuery` for Tier A), pages, query keys / invalidation.
5. **Tests** — API tests green (`make backend-test` or focused `pytest`); FE `npm test` + `npm run typecheck`.

One PR = one endpoint (or one coherent group) fully aligned. No dual-format transition period.

## 8. Anti-patterns

| Anti-pattern | Why |
|--------------|-----|
| `queryset.count()` for `has_more` on feeds | Full-scan cost; use `limit + 1` |
| `next_cursor` always `null` while `has_more` is `true` | Broken contract; clients cannot load page 2 |
| DRF `PageNumberPagination` / offset on dynamic feeds | Unstable under realtime updates |
| Raw `Item[]` without documented Tier C/D justification | Inconsistent FE consumption; migrate to `{ items }` |
| Frontend-only pagination (client slice of full list) | Scales poorly; backend must bound or paginate (checklist assignments over-fetch today) |
| Decorative `next_cursor` in OpenAPI without `cursor` query param | Contract lies; fix schema and implementation together |

## 9. No global DRF pagination

Houston does not set `DEFAULT_PAGINATION_CLASS` in DRF settings. Each domain implements explicit helpers in views/selectors. Shared extraction (`parse_page_size`, `paginate_limit_plus_one`) is optional future work (HOU-PAG-010).

## 10. Related documents

- Audit inventory: [`docs/audit/pagination_audit_2026-06-13.md`](../audit/pagination_audit_2026-06-13.md)
- Feed domain: [`docs/product/domains/feed_domain.md`](../product/domains/feed_domain.md)
- Phase L unbounded lists: [`docs/audit/db_scalability_phase_l_2026-06-11.md`](../audit/db_scalability_phase_l_2026-06-11.md) (API-04)
- S0 feed gaps: [`docs/audit/code_scalability_s0_2026-06-11.md`](../audit/code_scalability_s0_2026-06-11.md) (API-02, API-03)

## 11. Derived implementation tickets

| ID | Priority | Summary |
|----|----------|---------|
| HOU-PAG-001 | P0 | Execution Feed — cursor backend (**delivered** HOU-BACKLOG-019) |
| HOU-PAG-002 | P0 | Execution Feed — frontend `useInfiniteQuery` (**delivered** HOU-BACKLOG-019) |
| HOU-PAG-003 | P1 | Chat messages — align envelope or document exception |
| HOU-PAG-004 | P1 | Chat conversations — cursor pagination + N+1 fix |
| HOU-PAG-005 | P1 | Users search — `limit` cap |
| HOU-PAG-006 | P1 | Checklist templates — pagination if > ~50 |
| HOU-PAG-007 | P1 | Checklist assignments — pagination + API filter |
| HOU-PAG-008 | P2 | Membership roster — `page`/`limit` |
| HOU-PAG-009 | P2 | Raw array → `{ items }` harmonization |
| HOU-PAG-010 | P2 | Shared backend pagination helpers |

Details and acceptance criteria: [`pagination_audit_2026-06-13.md`](../audit/pagination_audit_2026-06-13.md).
