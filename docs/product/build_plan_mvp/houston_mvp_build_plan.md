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

### Phase 2 — Runtime config / Onboarding minimal ✅ completed

Add minimal establishment setup and onboarding inputs required before operational use.

See [phase_2_runtime_config_onboarding.md](phase_2_runtime_config_onboarding.md) (closure
section) for deferred items and Phase 3 entry assumptions.

### Phase 3 — Observation / Media / Transcription

Add Observation submission, optional media handling, audio transcription, and cleanup lifecycle.

Current API truth implements this Phase 3 subset: Observation submit, temporary photo uploads (temporary-uploads), and audio transcription (transcriptions). Observation processing starts with `processing_status=queued`, while Signal/Action/Feed APIs remain outside the current schema.

### Phase 4 — AI Pipeline / Signal Feed

Add AI-assisted Observation interpretation, Signal creation or aggregation, and Signal Feed behavior.

Not yet implemented in the current API contract (`apps/api/schema.yml`): Signal Feed and related Signal/Aggregation endpoints are Phase 4 candidate surface.

**Implementation gate:** Phase 4 code starts only after Phase B/C taxonomy and onboarding runtime (modules, domains, subjects) are live.

**Deliverables (code, when Phase 4 starts):**

- Signal model with single categorization triplet (module/domain/subject FKs)
- Observation → CandidateSignal → validated Signal pipeline (Celery + OpenAI provider + fake provider for tests)
- Signal Feed endpoint `signal-feed` with `view_mode=personal|general` (**Ma vue** filters by `MembershipScope`; Owner/Director personal = all active)
- Signal Detail + pin/unpin/urgency commands (no manual Signal CRUD)
- OpenAPI + generated clients + backend tests
- **`MembershipFeedSubscription` is out of scope for Phase 4** (see `feed_subscription_domain.md`)

**Future test scenarios (documentation only until Phase 4 code):**

| Area | Scenarios to cover when implementing |
| --- | --- |
| Signal service | Establishment scope on all FKs; one triplet per Signal; multi-problem Observation → N Signals |
| Feed selectors | `signal_matches_membership_scope`; personal vs general; empty personal without scopes |
| Feed API | `view_mode` query param; active statuses only; cross-tenant 404 |
| Roles | Directeur / Gouvernante / Femme de chambre / Technicien Ma vue vs Vue générale (see `feed_domain.md`) |
| Regression | No raw Observation text in feed items; OpenAPI drift check in CI |

Detailed scenario tables: `signal_domain.md` §12, `feed_domain.md` §12. See [phase_4_ai_pipeline_signal_feed.md](phase_4_ai_pipeline_signal_feed.md).

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
