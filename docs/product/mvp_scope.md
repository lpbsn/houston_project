# MVP Scope

Status: authoritative
Last reviewed: 2026-06-22

## 1. MVP Objective

The MVP objective is simple: a field team can report, structure, assign, execute, validate, and follow operational situations in real conditions.

## 2. Validated Build Phases

1. Phase 0 — Full-stack foundation ✅ completed
2. Phase 1 — Identity / Memberships / RBAC
3. Phase 2 — Runtime config / Onboarding minimal
4. Phase 3 — Observation / Media / Transcription
5. Phase 4 — AI Pipeline / Signal Feed
6. Phase 5 — Actions / Execution Feed
7. Phase 6 — Notifications
8. Phase 7 — Checklists
9. Phase 8 — Chat V1 (minimal Chat-only realtime) ✅ core implemented
10. Phase 8C — Global realtime invalidation ✅ completed
11. Phase 9 — Hardening
12. Phase 10 — Pilot readiness

## 3. P0 Functional Loop

```txt
Observation → Signal → Action → Execution → Validation → Feed update
```

## 4. Included MVP Domains

- Identity / Memberships / RBAC
- Runtime config / Onboarding minimal
- Observation
- Upload / Media
- Transcription
- AI Pipeline
- Signals
- Actions
- Feeds
- Notifications
- Checklists
- Chat V1 (DM + free groups, WebSocket messages)
- Global realtime invalidation (operational invalidation/refetch)
- Security/RGPD baseline

## 5. Explicit MVP Exclusions

- Billing
- SSO
- MFA unless already implemented
- Advanced analytics
- Advanced AI review UI
- Recommended assignees
- Direct-to-storage uploads unless already validated
- Single establishment-wide general chat room (replaced by Chat V1 DM + groups)
- Chat notifications, read receipts, typing indicators
- REST message send for chat (WebSocket only in V1)
- AI analysis of Chat
- Chat-to-signal conversion
- Native mobile app
- Complex offline mode
- Arbitrary admin console browsing raw data

## 6. API Scope Rule

`apps/api/schema.yml` is the current API truth.

Endpoint lists in product docs are candidate unless present in `apps/api/schema.yml`.

## 7. AI Agent Notes

Before implementing a phase, the agent must inspect current code, tests, `AGENTS.md`, `apps/api/schema.yml`, and the relevant domain docs.
