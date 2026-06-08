# Phase 5 — Actions / Execution Feed

Status: **Phase 5 core implemented**  
Scope: Action lifecycle core, Execution Feed core, Signal side effects for linked Actions

## Deliverables (core — in `schema.yml`)

- `Action` model with **BusinessUnit / ActivitySubject** classification (`affected_business_unit`, `responsible_business_unit`, `activity_subject`)
- Free Actions (`signal` null) and Signal-linked Actions
- Explicit transition services (no generic status PATCH)
- `GET execution-feed/` with `{ items, next_cursor, has_more }`
- Action APIs under `/establishments/{id}/actions/`
- Signal `resolve` returns **409** `business_conflict` when linked Actions are active
- Frontend: Execution Feed, Action detail, create from Signal Detail and Execution Feed

## Out of scope (not Phase 5 core)

- Checklists in Execution Feed
- Comments and mentions
- `SignalAccessGrant` table
- Notifications
- Realtime avancé
- Advanced feed filters and pagination beyond cursor envelope
- Signal archive

See [`action_domain.md`](../domains/action_domain.md) and [`feed_domain.md`](../domains/feed_domain.md).
