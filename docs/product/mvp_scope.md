# MVP Scope — Pilot

Status: authoritative  
Last reviewed: 2026-08-17

## Objective

A field team can report, structure, assign, execute, validate, and follow operational situations on mobile-first terrain UI in connected conditions.

## Core loop

```txt
Observation → Signal → Action Plan → Execution → Validation → Feed update
```

## In scope (pilot)

- Identity, memberships, establishment isolation, RBAC
- Manual onboarding v2 (BusinessUnit / ActivitySubject)
- Observation submission (text, optional photo, audio transcription)
- AI pipeline → Signal feed and detail
- Action Plan catalog, executions, execution feed, lifecycle commands
- Comments on signals and action plan executions
- In-app notifications; Web Push **API/backend only** (frontend client removed in Capacitor Lot 4; delivery is Capacitor Lot 7)
- Capacitor iOS/Android shells (pilot feasibility; same React tree)
- Operational realtime invalidation (refetch, not business truth in WS)
- Chat V1 core (DM + groups, WebSocket messages)
- Private media uploads with authorized access
- Security / RGPD baseline

## Explicit exclusions

- Billing, SSO, MFA (unless already present)
- Legacy Action / Checklist domains (removed)
- App Store / Play Store release and CI `cap sync` (Capacitor Lot 11)
- Native push (Capacitor Lot 7)
- Durable offline mutation queue
- Chat: REST message send, read receipts, typing, AI on chat, chat-to-signal
- Feed subscriptions (deferred — see `feed_subscription_domain.md`)
- Arbitrary admin console browsing raw tables
- Advanced analytics and AI review UI

## API truth

[`apps/api/schema.yml`](../../apps/api/schema.yml) is the HTTP contract. Product docs describe intent; endpoints not in OpenAPI are not implemented.

## Implementation snapshot

See [`current_state.md`](current_state.md) for what is live today.

## Agent notes

Before implementing: read nearest `AGENTS.md`, relevant domain doc, `schema.yml`, and tests for the area.
