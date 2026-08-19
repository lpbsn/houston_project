# MVP Scope — Pilot

Status: authoritative  
Last reviewed: 2026-08-19

## Objective

A field team can report, structure, assign, execute, validate, and follow operational situations on mobile-first terrain UI.

Development until Capacitor Lot 10 assumes **connected conditions**. **Observation process-alive protection** (Capacitor Lot 10 — do not lose in-progress Observation text and local photos while the JS/WebView process is still alive; do not require photo upload in order to compose) is a **prerequisite before real field usage or a terrain pilot under intermittent connectivity**. It is not post-launch comfort. Survival after process kill / cold start is **not** that prerequisite and is not in MVP.

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
- In-app notifications; native FCM push on iOS/Android (Capacitor Lot 7). Web Push desktop/mobile out.
- Capacitor iOS/Android shells (pilot feasibility; same React tree)
- Operational realtime invalidation (refetch, not business truth in WS)
- Chat V1 core (DM + groups, WebSocket messages)
- Private media uploads with authorized access
- Security / RGPD baseline

## Explicit exclusions

- Billing, SSO, MFA (unless already present)
- Legacy Action / Checklist domains (removed)
- App Store / Play Store release and CI `cap sync` (Capacitor Lot 11)
- Durable offline mutation queue (universal mutation outbox / sync). Distinct from Capacitor Lot 10, which protects **Observation compose while the process is alive** only — not a queue, not post-kill restore.
- Observation survival after process kill / cold start (requires durable persistence + security policy exception + possibly offline auth)
- Offline capture of chat, comments, audio, signal/task/plan lifecycle commands, or feed reads
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
