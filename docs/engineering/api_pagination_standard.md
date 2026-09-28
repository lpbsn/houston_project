# API Pagination Standard

Status: authoritative  
Last reviewed: 2026-09-28

## 1. Purpose

Define how Houston list endpoints paginate (or intentionally do not), and how the frontend consumes them.

This document applies to:

- new list endpoints
- pagination fixes on existing endpoints

It defines shared engineering rules. Domain documents and [`apps/api/schema.yml`](../../apps/api/schema.yml) own endpoint-specific filtering, ordering, metadata, and visibility.

## 2. Authority order

1. Current source code
2. [`apps/api/schema.yml`](../../apps/api/schema.yml)
3. [`AGENTS.md`](../../AGENTS.md) files
4. This document

If code and this document conflict, code wins until this document is updated in the same change set.

## 3. Context

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
| Cursor encoding | Opaque, versioned, tied to collection, stable sort keys, filters/view, scope, and effective authorization context |
| Invalid context | HTTP 400, code `cursor_context_mismatch`; restart from page 1 |
| Frontend | Automatic bounded continuation near the end; one continuation in flight; explicit retry/fallback |

The list collection uses this core envelope:

```json
{
  "items": [],
  "next_cursor": "opaque-string-or-null",
  "has_more": true
}
```

First-page metadata may add independent collections and summaries such as `pins`, `counts`, `section_counts`, `scheduled`, `pins_next_cursor`, `pins_has_more`, or `applied_filters`. A continuation returns only `items`, `next_cursor`, and `has_more` unless the endpoint explicitly documents otherwise.

Pins and the main list are disjoint collections. P contains authorized, filter-eligible pinned items; L contains authorized, filter-eligible non-pinned items. P is excluded from L before LIMIT, including pins not yet loaded in a Cross preview. P may be bounded by its domain cap or expose a dedicated cursor endpoint; its cursor is never interchangeable with an L cursor.

| Endpoint family | L | P and first-page metadata |
|---|---|---|
| Signal Feed, establishment and Cross | Flat global page over the selected status | `pins`, `counts`, `applied_filters`; Cross pin continuation uses `GET /api/v1/cross/signal-feed-pins/` |
| Action Plan Execution Feed, establishment | Flat global page over the selected category | First page adds `pins`, `section_counts`, and `scheduled` |
| Action Plan Execution Feed, Cross | Flat global page over the selected category | Main first page adds `section_counts` and `scheduled`; a separate `GET /api/v1/cross/action-plan-execution-feed-pins/` supplies the three-pin preview and its continuations |

The historical `/execution-feed/` path is gone.

Operational Execution Feed contains only `pending_validation` and `in_progress`; terminal executions belong to History. `scheduled` remains outside L and is summarized as `{ count, next }`. The first L cursor freezes `as_of` for the traversal; this value is not a response field.

### Tier B — Chronological streams

Use for message-like lists ordered by time.

| Rule | Value |
|------|-------|
| Mechanism | Cursor on request; prefer server `next_cursor` in response |
| Default `page_size` | 50 (chat messages today) |
| Max `page_size` | 100 (chat messages today) |

**Target envelope:** same as Tier A (`items`, `next_cursor`, `has_more`).

**Exception today:** chat messages return `{ items, has_more }` only; the frontend builds the next cursor from the oldest item (`created_at|uuid`). Align to Tier A or document as a permanent exception.

### Tier C — Configuration / management lists

Use for admin or catalogue lists with slower growth.

| Rule | Value |
|------|-------|
| Default | No pagination if typical volume **< ~50 rows** per establishment |
| When needed | `page`/`limit` acceptable for stable admin lists; cursor only if list is dynamically sorted like a feed |
| Response target | `{ items: [...] }` |

**Raw array migration:** endpoints that today return `Item[]` directly should migrate to `{ items }` **directly**, one endpoint per PR, with no temporary compatibility layer. Same PR must update schema, regenerated types, frontend hooks, and tests.

**Endpoints today (non-paginated):** action plan catalog (filtered list), membership roster.

### Tier D — Search / typeahead / hard-capped lists

Use for autocomplete and scoped search.

| Rule | Value |
|------|-------|
| Mechanism | `limit` with documented default and max |
| Cursor | Not used |
| Frontend | `useQuery` with `enabled: query.length >= minLength` |

**Reference:** catalog suggest endpoints — default `limit` 20, max 200.

**Endpoints today:** `GET /api/v1/catalog/*/suggest/`, `GET .../users/search/` (no limit yet), `GET .../chat/eligible-memberships/` (hard slice `[:100]`).

## 5. Feed cursor and continuation contract

Signal and Execution feeds implement the Tier A contract independently; neither is a universal feed engine.

| File | Role |
|------|------|
| [`apps/api/houston/core/opaque_cursor.py`](../../apps/api/houston/core/opaque_cursor.py) | Shared opaque encoding/decoding only |
| [`apps/api/houston/signals/feed_cursor.py`](../../apps/api/houston/signals/feed_cursor.py) | Signal L/P sort tuples and context validation |
| [`apps/api/houston/signals/signal_feed.py`](../../apps/api/houston/signals/signal_feed.py) | Signal L/P pages and first-page metadata |
| [`apps/api/houston/action_plans/feed_cursor.py`](../../apps/api/houston/action_plans/feed_cursor.py) | Execution L/P sort tuples, frozen `as_of`, and context validation |
| [`apps/api/houston/action_plans/execution_feed.py`](../../apps/api/houston/action_plans/execution_feed.py) | Execution L/P pages and first-page metadata |

Cursor payloads are implementation details. Clients must not decode or construct them. The server validates collection, view/filter context, establishment or Cross scope, and an authorization fingerprint derived from the live contributing memberships, roles, statuses, and BusinessUnit scopes. A cursor from another collection or scope is invalid.

Ordering and continuation predicates must match exactly, including null handling and a unique id tie-breaker. `has_more` comes only from fetching `limit + 1`. At the end, `has_more=false` and `next_cursor=null`.

The client stops automatic continuation and exposes a local retry when:

- a response is empty while `has_more=true`;
- a response announces `has_more=true` without advancing the cursor;
- the server rejects the cursor context;
- authorization or transport fails.

## 6. Frontend consumption and memory

Operational feeds load automatically near the end. The manual continuation control is a fallback for retry, stalled progress, or environments without intersection observation; it is not the nominal journey.

TanStack Query remains the server-state owner, but an operational feed does not retain an unbounded chain of loaded pages. [`apps/web/src/lib/feed-reading-window.ts`](../../apps/web/src/lib/feed-reading-window.ts) keeps:

- page 1 of the current generation;
- at most two focused continuation slots around the viewport, including preloading;
- one replaceable cursor for the evicted page behind;
- deduplication ids only for hydrated slots.

Refresh replaces the generation and first page. A continuation or refresh result from a stale generation is ignored. Return-from-detail memory is O(1): anchor, neighbor, resume cursor, and authorization fingerprint. An evicted zone is fetched again from a retained boundary cursor; the client does not retain a growing sparse index.

This bounded-window rule applies to operational Signal and Execution feeds. History currently uses an infinite query with cursor non-progression protection; it does not share the operational feed reading window.

## 7. Response envelope matrix (current state)

| Envelope | Endpoints |
|----------|-----------|
| `{ items, next_cursor, has_more, ...first_page_metadata }` | Signal and Action Plan Execution feeds |
| `{ items, next_cursor, has_more, undated_count? }` | Signal and Execution History |
| `{ items, has_more }` | Chat messages |
| `{ items }` | Chat conversations, chat eligible memberships |
| Raw `Item[]` | Action plan catalog list, users search, memberships, catalog suggest |
| Nested object | Bootstrap, business-unit tree, action plan / execution detail |

Target over time: paginated lists use Tier A/B envelope; non-paginated lists use `{ items }` (Tier C).

## 8. PR checklist

When changing list pagination or response shape:

1. **Backend** — view/selector/serializer; add or fix tests (`pytest` focused on endpoint).
2. **OpenAPI** — `make schema`; verify `cursor` / `page_size` / response fields in `schema.yml`.
3. **Frontend types** — `make web-api-generate`.
4. **Frontend callers** — feature API, hooks/cache, query keys, generation and invalidation behavior, and affected pages.
5. **Tests** — API tests green (`make backend-test` or focused `pytest`); FE `npm test` + `npm run typecheck`.

One PR = one endpoint (or one coherent group) fully aligned. No dual-format transition period.

## 9. Anti-patterns

| Anti-pattern | Why |
|--------------|-----|
| `queryset.count()` for `has_more` on feeds | Full-scan cost; use `limit + 1` |
| `next_cursor` always `null` while `has_more` is `true` | Broken contract; clients cannot load page 2 |
| DRF `PageNumberPagination` / offset on dynamic feeds | Unstable under realtime updates |
| Raw `Item[]` without documented Tier C/D justification | Inconsistent FE consumption; migrate to `{ items }` |
| Frontend-only pagination (client slice of full list) | Scales poorly; backend must bound or paginate (checklist assignments over-fetch today) |
| Decorative `next_cursor` in OpenAPI without `cursor` query param | Contract lies; fix schema and implementation together |
| Cursor context based only on establishment ids | Misses role, membership-state, view, filter, or BusinessUnit-scope changes |
| Keeping every loaded operational-feed page or every seen id | Session memory grows with traversal depth; use the bounded reading window |
| Treating a Cross pin preview as the whole P collection | Hidden pins can leak back into L or become unreachable |

## 10. No global DRF pagination

Houston does not set `DEFAULT_PAGINATION_CLASS` in DRF settings. Each domain implements explicit helpers in views/selectors.

## 11. Related documents

- Feed domain: [`docs/product/domains/feed_domain.md`](../product/domains/feed_domain.md)

## 12. Open pagination gaps

Inspect current list endpoints before treating this as a roadmap:

- Chat messages envelope vs Tier A
- Chat conversations cursor + N+1
- Users search `limit` cap
- Membership roster `page`/`limit`
- Raw array → `{ items }` where lists grow
- Optional shared backend pagination helpers
