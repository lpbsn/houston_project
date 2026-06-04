# Phase 5 — Actions / Execution Feed

Status: implemented (code)  
Scope: Action lifecycle, Execution Feed, Signal side effects

## Deliverables

- `Action` model with own operational taxonomy (module/domain/subject FKs)
- Free Actions (`signal` null) and Signal-linked Actions
- Explicit transition services (no generic status PATCH)
- `GET execution-feed/` with `{ items, next_cursor, has_more }`
- Action APIs under `/establishments/{id}/actions/`
- Signal `resolve` returns **409** `business_conflict` when linked Actions are active
- Frontend: Execution Feed, Action detail, create from Signal Detail and Execution Feed

## Out of scope

- Checklists in Execution Feed, comments, mentions, `SignalAccessGrant` table, notifications, realtime, feed filters

See [`action_domain.md`](../domains/action_domain.md) and [`feed_domain.md`](../domains/feed_domain.md).
