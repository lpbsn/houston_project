# Houston — Current product state

Status: authoritative  
Last reviewed: 2026-09-21

Snapshot of what is live, plus remaining **pilot** exclusions. HTTP: [`apps/api/schema.yml`](../../apps/api/schema.yml). Identity map: [`domains/identity_membership_domain.md`](domains/identity_membership_domain.md).

## Branding

- **Houston** — repository name, backend modules, technical docs, operator workflows.
- **Spore** — product name (UI, Capacitor app, landing, emails).

## Operational loop (live)

```txt
Observation → Signal → Action Plan → Execution → Validation → Feed update
```

The execution surface is **Action Plan** only.

## Backend apps (14 installed)

`core`, `accounts`, `organizations`, `establishments`, `platform`, `observations`, `signals`, `action_plans`, `comments`, `notifications`, `realtime`, `chat`, `ai`, `uploads`

## Implemented surfaces (pilot)

| Area | Status | Notes |
|------|--------|-------|
| Identity / memberships / RBAC | Live | Bootstrap, establishment scoping. Tenant ≠ Platform — see identity domain |
| Account deletion | Live | Profil `/general` + public `https://spore-os.com/supprimer-compte/`; last-owner org closure; [`data_inventory.md`](data_inventory.md) |
| Privacy Policy / CGU | Live | `https://spore-os.com/politique-de-confidentialite/` · `https://spore-os.com/conditions-d-utilisation/`; UGC gate + OpenAI consent in-app |
| Public support | Live | `https://spore-os.com/support/` |
| Store listing / review pack | Prepared | [`store_listing.md`](store_listing.md) · [`store_review.md`](store_review.md) · [`store_assets/`](store_assets/). Console paste, screenshots of the app in use, Play/App Store identities, and Closed Testing remain operator work |
| Runtime config / onboarding | Live | Wizard **Platform** only (`/api/v1/platform/onboardings/`, desktop Web). Invited Owner/Director: accept invitation then waiting |
| Platform control plane | Live | `houston.platform`, desktop `/platform`. Independent operator grant |
| BusinessUnit / ActivitySubject taxonomy | Live | Identity: `specific_name` + internal `routing_key`; catalog FK required (`PROTECT`); public API omits `routing_key` |
| Observations + media + transcription | Live | Celery pipeline |
| AI observation → Signal | Live | Pipeline **v6** (schema `ai_observation_pipeline_v6`, prompt `ai_observation_pipeline_v6_2`); Fake (CI) / OpenAI (opt-in smoke) |
| Signal feed + lifecycle | Live | Pin, mark interesting, cancel (open and interesting), resolve (open), qualify merge absorb+delete |
| Action Plan catalog + executions + feed | Live | [`domains/action_plan_domain.md`](domains/action_plan_domain.md) |
| Comments (signal + execution threads) | Live | REST + mention picker |
| Notifications in-app | Live | List, preferences, mark read |
| Native push (FCM) | Live | Membership `push_enabled`; Web Push removed |
| Native HTTPS deep links | Live | Handler (`getLaunchUrl` / `appUrlOpen`). **Play** `assetlinks.json` and **App Store** AASA wait on store identities |
| Operational realtime (invalidation) | Live | WS ticket + `OperationalRealtimeProvider` on terrain routes |
| Chat V1 core | Live | DM + groups, HTTP send, WS fan-out, attachments, Terrain UI `/chat`; conversation pin/hide/leave and group member admin live |
| Upload / private media | Live | Authorized reads only |
| Security / RGPD baseline | Live | See domain doc |

## Notifications / realtime / chat

REST and WebSocket paths: `schema.yml`. Native push: `POST/DELETE …/me/push-devices/` (FCM, user-scoped). Membership `push_enabled` remains establishment-scoped.

- Operational invalidation: `POST …/realtime/ws-ticket/`, WebSocket `ws/v1/establishments/{id}/realtime/`. Frontend: `OperationalRealtimeProvider` (terrain shell, not chat). Contract: [`contracts/operational-realtime-invalidation.json`](../../contracts/operational-realtime-invalidation.json).
- Chat uses a separate WebSocket protocol — [`domains/chat_domain.md`](domains/chat_domain.md).

Post-core chat gaps (non-blocking pilot): some bootstrap hints. Chat send is HTTP.

## Frontend

- Terrain mobile shell (`TerrainShell`, bottom nav, `--app-safe-*` insets). Native UX: Android system back aligned on `backPath`; iOS keyboard resize native; Observation mic OS declarations.
- Management shell (`AppShell`) for pending onboarding, select-establishment, no-establishment, invitations, auth pages. Not the Platform wizard.
- Platform shell (`/platform`, desktop Web only) for operator onboarding and control-plane lists.
- Organization owner invite: `/team/invite` (Owner option when bootstrap shows an owner membership on the current establishment’s organization) via `POST /api/v1/organizations/{id}/owner-invitations/`. Membership invites stay on the same page.
- Operational config: `/e/{id}/operational-config` (desktop sidebar). Team: `/team*`.
- Client router: `apps/web/src/app/app-routes.ts` (not React Router). Server state: TanStack Query only.
- Builds: Web `dist/` (`base: '/'`) and Native `dist-native/` (`base: './'`); Capacitor shells in `apps/web/ios` and `apps/web/android`; no service worker.

Details: [`../engineering/frontend_architecture.md`](../engineering/frontend_architecture.md).

CI `cap sync` / publication pipeline is **deferred**. Local Play AAB: [`../deploy/native_release.md`](../deploy/native_release.md). Remaining store console and identity work: [`store_review.md`](store_review.md), [`../deploy/native_release.md`](../deploy/native_release.md).

Do not rename without an explicit decision: `can_create_action()` (establishment permission alias for action plan creation hints); realtime events `comment.execution.*` for action plan execution comment threads.

## Pilot exclusions (still true)

- Billing, SSO, MFA.
- Durable offline mutation queue (universal mutation outbox / sync). Observation compose is process-memory only while the JS/WebView process is alive; photos upload at Envoyer; Envoyer is disabled while offline. Survival after process kill / cold start is out.
- Offline capture of chat, comments, audio, signal/task/plan lifecycle commands, or feed reads.
- Feed subscriptions (deferred — [`domains/feed_subscription_domain.md`](domains/feed_subscription_domain.md)).
- Chat: read receipts, typing, AI on chat, chat-to-signal. Chat send is HTTP (in scope).
- Arbitrary admin console browsing raw tables.
- Native CI `cap sync` (deferred — [`../deploy/native_release.md`](../deploy/native_release.md)).

## Pilot gaps (known)

- Production-grade polish on all terrain screens.
- Push: native FCM live. Physical iOS APNs QA waits on the Apple Developer Program. Web Push desktop is out.
- Native HTTPS deep links: handler live. Play-verified App Links wait on Play App Signing SHA-256 in `assetlinks.json`. iOS Universal Links wait on the App Store Team ID (not Personal Team AASA).
- Observation compose leftovers that do not reopen a capture lot: iOS Simulator avion → reconnect not tested; iPhone physical offline → reconnect still open.
- Native refresh: body-transport `performRefresh` can clear a still-valid Keychain refresh token on network error — [issue #181](https://github.com/lpbsn/houston_project/issues/181). See [`../architecture/authentication_charter.md`](../architecture/authentication_charter.md).
- Full device QA matrix not automated in CI.

## BusinessUnit / ActivitySubject (summary)

- Catalogue generics + concrete instances (`specific_name`, immutable internal `routing_key`).
- Public API exposes UUID + `specific_name` + nested `generic` — never `routing_key`.
- Signal summary `*_key` / `*_label` kept as display compatibility only (`normalized_specific_name` / `specific_name`).
- Import policy and seed: [`../catalogue/README.md`](../catalogue/README.md).
- Domain: [`domains/business_unit_taxonomy_domain.md`](domains/business_unit_taxonomy_domain.md).
- Local reset / deploy contraction order: [`../engineering/local_development.md`](../engineering/local_development.md), [`../deploy/prod_test_runbook.md`](../deploy/prod_test_runbook.md).

## Reading order

1. This file — live surfaces and remaining exclusions
2. [`domains/identity_membership_domain.md`](domains/identity_membership_domain.md) — Authentication vs Tenant vs Platform
3. The domain you are changing
4. [`apps/api/schema.yml`](../../apps/api/schema.yml)
5. [`../engineering/local_development.md`](../engineering/local_development.md) — daily workflow
