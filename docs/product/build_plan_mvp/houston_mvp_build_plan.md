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
3. Phase 2 — Runtime config / Onboarding
4. Phase 3 — Observation / Media / Transcription
5. Phase 4 — AI Pipeline / Signal Feed
6. Phase 5 — Actions / Execution Feed
7. Phase 6 — Notifications
8. Phase 7 — Checklists
9. Phase 8A — Realtime invalidation foundation
10. Phase 8B — Establishment General Chat
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

### Phase 2 — Runtime config / Onboarding minimal

Add minimal establishment setup and onboarding inputs required before operational use.

### Phase 3 — Observation / Media / Transcription

Add Observation submission, optional media handling, audio transcription, and cleanup lifecycle.

### Phase 4 — AI Pipeline / Signal Feed

Add AI-assisted Observation interpretation, Signal creation or aggregation, and Signal Feed behavior.

### Phase 5 — Actions / Execution Feed

Add Action lifecycle, assignment, execution, validation, and Execution Feed updates.

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
