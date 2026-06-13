# Houston — MVP Build Plan

**Status:** Active MVP build sequence  
**Scope:** Houston MVP for the initial Mama Shelter Nice pilot

## Purpose

This document defines the validated MVP phase order and the active target scope.

It is implementation-adaptive:

- current code and `apps/api/schema.yml` remain the source of truth
- future endpoints are `candidate` unless present in `apps/api/schema.yml`
- backend authority, tenant scoping, and OpenAPI contract rules do not change

## MVP Objective

```txt
Observation → Signal → Action → Execution → Validation → Feed update
```

Houston remains a backend-authoritative operational workflow app.

## Validated Phase Sequence

1. Phase 0 — Full-stack foundation ✅ completed
2. Phase 1 — Identity / Memberships / RBAC ✅ completed
3. Phase 2 — Runtime config / Onboarding ✅ completed
4. Phase 3 — Observation / Media / Transcription ✅ completed
5. Phase 4 — AI Pipeline / Signal Feed ✅ completed
6. Phase 5 — Actions / Execution Feed ✅ core implemented
7. Phase 7 — Checklists ✅ core implemented
8. Phase 8 — Chat V1 (minimal Chat-only realtime) ✅ core implemented
9. Phase 8C — Global realtime invalidation (Signal/Action/Notifications) — **deferred post Chat V1**
10. Phase 6 — Notifications
11. Phase 9 — Hardening
12. Phase 10 — Pilot readiness

Chat V1 ships before generic realtime invalidation. Chat remains independent from the operational loop.

## Scope Rules

- Django remains the business authority.
- PostgreSQL remains the persisted source of truth.
- React remains the UI layer.
- OpenAPI remains the frontend/backend contract.
- Realtime remains invalidation and refetch only.
- Future APIs described here are `candidate` unless present in `apps/api/schema.yml`.

## Phase Summary

### Phase 0 — Full-stack foundation ✅ completed

Foundation baseline is complete and no longer a pending MVP phase.

### Phase 1 — Identity / Memberships / RBAC

Establish authenticated identity, establishment membership, backend authorization, and tenant-scoped visibility.

### Phase 2 — Runtime config / Onboarding minimal ✅ completed

Add minimal establishment setup and onboarding inputs required before operational use.

See [`runtime_config_onboarding_domain.md`](../domains/runtime_config_onboarding_domain.md) for onboarding scope (Manual V2, BU/AS).

### Phase 3 — Observation / Media / Transcription

Add Observation submission, optional media handling, audio transcription, and cleanup lifecycle.

Current API truth implements Phase 3: Observation submit, temporary photo uploads, audio transcription, and observation processing enqueue. Phases 4–5 surfaces are in `schema.yml` (see below).

### Phase 4 — AI Pipeline / Signal Feed ✅ completed

Implemented in `apps/api/schema.yml`:

- Signal with **BusinessUnit / ActivitySubject** classification (`affected_business_unit`, `responsible_business_unit`, `activity_subject`)
- Observation → CandidateSignal → validated Signal pipeline v4 (Celery + OpenAI/fake providers)
- `signal-feed/` with `view_mode=personal|general` (**Ma vue** = `MembershipScope`; Owner/Director personal = all active)
- Signal detail + pin/unpin/urgency/resolve/cancel (no manual Signal CRUD)
- Feed subscription (`MembershipFeedSubscription`) **deferred** — future BU-only, then ActivitySubject subscribe/unsubscribe

See [phase_4_ai_pipeline_signal_feed.md](phase_4_ai_pipeline_signal_feed.md). Acceptance matrices: `signal_domain.md` §12, `feed_domain.md` §12.

### Phase 5 — Actions / Execution Feed ✅ core implemented

Core delivered in `schema.yml`: Action lifecycle commands, `execution-feed/`, Signal-linked and free Actions with BU/AS classification.

**Not in Phase 5 core:** notifications, comments, checklists in Execution Feed, Signal archive, advanced feed pagination/filters, realtime avancé.

See [phase_5_actions_execution_feed.md](phase_5_actions_execution_feed.md).

### Phase 6 — Notifications

Add in-app notifications and Notification Center behavior linked to backend events.

### Phase 7 — Checklists

Add shared and personal checklists, including task-to-Observation handoff where required by the MVP.

### Phase 8 — Chat V1 (minimal Chat-only realtime) ✅ core implemented

Authoritative product spec : [`chat_domain.md`](../domains/chat_domain.md).
Technical debt register : [`chat_v1_technical_debt_2026-06-09.md`](../../audit/chat_v1_technical_debt_2026-06-09.md).

Implementation lots (closed):

| Lot | Scope | Status |
|-----|--------|--------|
| 2 | ASGI + Daphne + ws-ticket + consumer auth | ✅ |
| 3 | Models + REST (no message POST) | ✅ |
| 4 | WS `message.send` / `message.created` + personal-group broadcast | ✅ |
| 5 | Terrain UI `/chat` | ✅ |
| 6 | Purge 7j + membership deactivate + rate limits + `access_revoked` | ✅ |
| 7 | Documentation alignment + acceptance checklist | ✅ |

Delivered scope:

- DM + free groups (not a single establishment general chat)
- membership-centric model (`ChatParticipant.membership`, `ChatMessage.author_membership`)
- text messages only (max 2,000 chars)
- WebSocket-only message send ; REST for structure, history, participants, seen, ws-ticket
- REST one-time WebSocket ticket auth ; no `AuthMiddlewareStack`
- Daphne ASGI server ; `AllowedHostsOriginValidator`
- personal membership channel groups for delivery to connected participants without reconnect
- minimal unread (`last_seen_message_id` UUID non-FK + `last_seen_message_created_at`)
- hard purge messages after 7 days
- `chat_enabled` on establishment (default true on activation ; data migration for existing active establishments)

Exclusions:

- no chat notifications / push / sounds
- no read receipts, delivered status, typing indicators
- no REST message send endpoint
- no attachments, audio, reactions, threads, search, message edit/delete
- no link with Signal, Action, Observation, Checklist, Comments, Feed, AI
- Owner/Director cannot read or delete groups outside participation (product API)

API note:

- Chat REST endpoints are implemented under `/api/v1/establishments/{establishment_id}/chat/` — see `apps/api/schema.yml`
- WebSocket path : `/ws/v1/establishments/{establishment_id}/chat/` (not listed in OpenAPI)
- Post-core gaps (group settings UI, events, bootstrap flag) remain in the debt register ; not blockers for core pilot chat

### Phase 8C — Global realtime invalidation (deferred)

Post Chat V1. Scope:

- lightweight invalidation for Signal Feed, Execution Feed, notifications, detail views
- TanStack Query invalidation and REST refetch
- no websocket business truth
- no business workflow execution in realtime consumers
- does not reuse Chat message WebSocket protocol

See [`realtime_domain.md`](../domains/realtime_domain.md).

### Phase 9 — Hardening

Hardening is technical only:

- security review
- permission review
- realtime review
- cleanup and background job review
- feed correctness review
- operational privacy review

### Phase 10 — Pilot readiness

Pilot readiness is field readiness, not net-new product scope:

- operational QA
- mobile QA
- documentation alignment
- support readiness
- rollout readiness for Mama Shelter Nice

## Acceptance Direction

The MVP is ready for pilot only when:

- the validated phases above are complete in order
- backend-owned business rules remain backend-owned
- tenant and establishment scoping are enforced
- OpenAPI matches implemented APIs
- realtime is still invalidation-only
- chat remains isolated from the operational workflow in MVP
