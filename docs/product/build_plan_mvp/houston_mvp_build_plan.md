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
7. Phase 7 — Checklists
8. Phase 8A — Realtime invalidation foundation
9. Phase 8B — Establishment Chat
10. Phase 6 — Notifications
11. Phase 9 — Hardening
12. Phase 10 — Pilot readiness

Each phase gates the next one. Chat follows the realtime foundation and remains independent from the operational loop in MVP.

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
- Observation → CandidateSignal → validated Signal pipeline v3 (Celery + OpenAI/fake providers)
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

### Phase 8A — Realtime invalidation foundation

Realtime scope in MVP remains narrow:

- websocket authentication and subscription permission checks
- lightweight invalidation events only
- TanStack Query invalidation and REST refetch
- no websocket business truth
- no business workflow execution in realtime consumers

### Phase 8B — Establishment General Chat

Chat is included in MVP scope, but it is intentionally isolated from Observations, Signals, Actions, Checklists, AI, and Notifications.

MVP chat scope:

- one general chat per establishment
- text messages only
- active establishment members can view and send
- paginated message list
- soft delete
- realtime invalidation and refetch only

MVP chat exclusions:

- no direct messages
- no multiple channels
- no attachments
- no audio
- no AI analysis
- no mentions
- no push notifications
- no link with Signal, Action, Observation, or Checklist
- no search
- no reactions
- no message editing

API note:

- any chat endpoint remains `candidate` unless it already exists in `apps/api/schema.yml`
- this document does not claim any concrete chat endpoint is implemented today

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
