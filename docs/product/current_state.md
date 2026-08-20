# Houston — Current product state

Status: authoritative  
Last reviewed: 2026-08-20

## Branding

- **Houston** — repository name, backend modules, technical docs, operator workflows.
- **Spore** — product name (UI, Capacitor app, landing, emails).

## Operational loop (live)

```txt
Observation → Signal → Action Plan → Execution → Validation → Feed update
```

Legacy **Action** and **Checklist** domains were removed (Lot 10). The execution surface is **Action Plan** only.

## Backend apps (13 installed)

`core`, `accounts`, `organizations`, `establishments`, `observations`, `signals`, `action_plans`, `comments`, `notifications`, `realtime`, `chat`, `ai`, `uploads`

API contract: [`apps/api/schema.yml`](../../apps/api/schema.yml).

## Implemented surfaces (pilot)

| Area | Status | Notes |
|------|--------|-------|
| Identity / memberships / RBAC | Live | Bootstrap, establishment scoping |
| Runtime config / onboarding | Live | Lot 1: `OnboardingDraft` + `…/draft/` + `…/complete/` additive; legacy `onboarding_proposal_v4` until Lot 3; description 10–5000 in readiness |
| BusinessUnit / ActivitySubject taxonomy | Live | Identity: `specific_name` + internal `routing_key`; catalog FK required (`PROTECT`); public API Lot 5 (no `routing_key`); legacy instance columns removed |
| Observations + media + transcription | Live | Celery pipeline |
| AI observation → Signal | Live | Pipeline **v6** (schema `ai_observation_pipeline_v6`, prompt `ai_observation_pipeline_v6_2`); Fake (CI) / OpenAI (opt-in smoke) |
| Signal feed + lifecycle | Live | Pin, mark interesting, archive (interesting only; not exposed after), resolve, cancel |
| Action Plan catalog + executions + feed | Live | See [`decisions/action_plan.md`](decisions/action_plan.md) |
| Comments (signal + execution threads) | Live | REST + mention picker |
| Notifications in-app | Live | List, preferences, mark read |
| Native push (FCM) | Live | Capacitor Lot 7; membership `push_enabled`; Web Push removed |
| Native HTTPS deep links | Live | Capacitor Lot 8 handler (`getLaunchUrl` / `appUrlOpen`); device QA pending; App Links / Universal Links E2E blocked ops/ADP |
| Operational realtime (invalidation) | Live | WS ticket + `OperationalRealtimeProvider` on terrain routes |
| Chat V1 core | Live | DM + groups, WS messages, Terrain UI `/chat` |
| Upload / private media | Live | Authorized reads only |
| Security / RGPD baseline | Live | See domain doc |

## Notifications

REST (establishment-scoped):

- `GET …/notifications/`
- `GET` / `PATCH …/notifications/preferences/`
- `POST …/notifications/mark-all-read/`
- `POST …/notifications/{id}/mark-read/`

Native push API: `POST/DELETE …/me/push-devices/` (FCM token, user-scoped). Membership `push_enabled` remains establishment-scoped. Web Push / VAPID removed. Web Push desktop is out (Lot 7).

Domain: [`domains/notification_domain.md`](domains/notification_domain.md).

## Realtime

- **Operational invalidation** (signals, action plans, notifications): `POST …/realtime/ws-ticket/`, WebSocket `ws/v1/establishments/{id}/realtime/`. Frontend: `OperationalRealtimeProvider` in `App.tsx` (terrain shell, not chat).
- **Chat** uses a separate WebSocket protocol — see [`domains/chat_domain.md`](domains/chat_domain.md).

Contract: [`contracts/operational-realtime-invalidation.json`](../../contracts/operational-realtime-invalidation.json).

## Chat V1 (core)

Implemented: REST structure/history/seen/presence, WS message send, Terrain pages, 7-day purge, membership hooks.

Lot 1 conversation actions (pin/unpin, hide DM with personal history cutoff, leave/delete group UI): live — see [`domains/chat_domain.md`](domains/chat_domain.md).

Lot 2 group member admin UI (add/remove/promote via detail « Gérer les membres »): live — see [`domains/chat_domain.md`](domains/chat_domain.md).

Post-core gaps (non-blocking pilot): some bootstrap hints, no REST message write.

## Frontend

- Terrain mobile shell (`TerrainShell`, bottom nav, `--app-safe-*` insets).
- Native UX (Capacitor Lot 9): Android system back aligned on `backPath`; iOS keyboard resize native; Observation mic OS declarations.
- Management shell (`AppShell`) for non-terrain routes: `/organization`, `/organization/establishments/{id}`, `/app/operational-config`, onboarding.
- Organization admin (Owners): `/organization` — establishments, members, owners.
- Establishment admin (Owners org-wide + Directors on path): `/organization/establishments/{id}` — overview metrics + memberships; entry to operational config.
- Client router: `apps/web/src/app/app-routes.ts` (not React Router).
- Server state: TanStack Query only (no client global store library).
- Builds: Web `dist/` (`base: '/'`) and Native `dist-native/` (`base: './'`); Capacitor shells in `apps/web/ios` and `apps/web/android`; no service worker.

Details: [`../engineering/frontend_architecture.md`](../engineering/frontend_architecture.md).

## Lot 11 stabilization (preserved contracts)

Completed 2026-07-05 — test hygiene + doc alignment, **no API contract change**.

Preserved names (do not rename without explicit decision):

- `can_create_action()` — establishment permission alias for action plan creation hints.
- Realtime events `comment.execution.*` for action plan execution comment threads.

## Pilot gaps (known)

- Production-grade polish on all terrain screens.
- Chat post-core UI (group admin, settings).
- Push notifications: native FCM live (Capacitor Lot 7). Device QA (foreground / background / terminated, physical iOS + Android) is manual. Web Push desktop is out.
- Native HTTPS deep links: handler live (Capacitor Lot 8). Device QA pending (Android `adb` VIEW intent → app → navigation, physical iOS). App Links / Universal Links E2E blocked until association files are published and Apple Developer Program (same bar as Lot 7 APNs).
- Observation compose today is memory-only (`/reporting` React state) with immediate photo upload. Capacitor Lot 10 must protect Observation **while the process is alive** (checkpoint Offline capture, done). That protection is a **prerequisite before real field usage or a terrain pilot under intermittent connectivity**. Survival after process kill is not in that lot.
- Native refresh: body-transport `performRefresh` can clear a still-valid Keychain refresh token on network error — [issue #181](https://github.com/lpbsn/houston_project/issues/181), not Offline capture and not Lot 10. See [`../architecture/authentication_charter.md`](../architecture/authentication_charter.md).
- Full device QA matrix not automated in CI.

## BusinessUnit / ActivitySubject (summary)

- Catalogue generics + concrete instances (`specific_name`, immutable internal `routing_key`).
- Public API exposes UUID + `specific_name` + nested `generic` — never `routing_key`.
- Legacy instance columns removed; Signal summary `*_key` / `*_label` kept as display compatibility only (`normalized_specific_name` / `specific_name`).
- Import policy and seed: [`../catalogue/README.md`](../catalogue/README.md).
- Domain detail: [`domains/business_unit_taxonomy_domain.md`](domains/business_unit_taxonomy_domain.md).
- Local reset / deploy contraction order: [`../engineering/local_development.md`](../engineering/local_development.md), [`../deploy/prod_test_runbook.md`](../deploy/prod_test_runbook.md).

## Reading order

1. [`mvp_scope.md`](mvp_scope.md) — pilot boundaries  
2. Domain docs under [`domains/`](domains/) — start with [`domains/business_unit_taxonomy_domain.md`](domains/business_unit_taxonomy_domain.md) for BU/AS
3. [`decisions/action_plan.md`](decisions/action_plan.md) — action plan RBAC and schedules  
4. [`../engineering/local_development.md`](../engineering/local_development.md) — daily workflow
