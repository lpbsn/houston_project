# Houston — Current product state

Status: authoritative  
Last reviewed: 2026-07-13

## Branding

- **Houston** — repository name, backend modules, technical docs, operator workflows.
- **Spore** — PWA / mobile UI branding (`index.html`, manifest `name` / `short_name`, `apple-mobile-web-app-title`).

## Operational loop (live)

```txt
Observation → Signal → Action Plan → Execution → Validation → Feed update
```

Legacy **Action** and **Checklist** domains were removed (Lot 10). The execution surface is **Action Plan** only.

## Backend apps (14 installed)

`core`, `accounts`, `organizations`, `establishments`, `observations`, `signals`, `action_plans`, `comments`, `notifications`, `realtime`, `chat`, `ai`, `events`, `uploads`

API contract: [`apps/api/schema.yml`](../../apps/api/schema.yml).

## Implemented surfaces (pilot)

| Area | Status | Notes |
|------|--------|-------|
| Identity / memberships / RBAC | Live | Bootstrap, establishment scoping |
| Runtime config / onboarding v2 | Live | BusinessUnit / ActivitySubject |
| Observations + media + transcription | Live | Celery pipeline |
| AI observation → Signal | Live | Fake (tests) / OpenAI (manual) |
| Signal feed + lifecycle | Live | Pin, urgency, resolve, cancel |
| Action Plan catalog + executions + feed | Live | See [`decisions/action_plan.md`](decisions/action_plan.md) |
| Comments (signal + execution threads) | Live | REST + mention picker |
| Notifications in-app | Live | List, preferences, mark read/archive |
| Web Push (VAPID + subscriptions) | Live | Optional; requires browser permission |
| Operational realtime (invalidation) | Live | WS ticket + `OperationalRealtimeProvider` on terrain routes |
| Chat V1 core | Live | DM + groups, WS messages, Terrain UI `/chat` |
| Upload / private media | Live | Authorized reads only |
| Security / RGPD baseline | Live | See domain doc |

## Notifications

REST (establishment-scoped):

- `GET …/notifications/`
- `PATCH …/notifications/preferences/`
- `POST …/notifications/mark-all-read/`
- `POST …/notifications/{id}/mark-read/`
- `POST …/notifications/{id}/archive/`

Web Push: `GET /api/v1/push/vapid-public-key/`, `POST/DELETE …/me/web-push-subscriptions/`.

Domain: [`domains/notification_domain.md`](domains/notification_domain.md).

## Realtime

- **Operational invalidation** (signals, action plans, notifications): `POST …/realtime/ws-ticket/`, WebSocket `ws/v1/establishments/{id}/realtime/`. Frontend: `OperationalRealtimeProvider` in `App.tsx` (terrain shell, not chat).
- **Chat** uses a separate WebSocket protocol — see [`domains/chat_domain.md`](domains/chat_domain.md).

Contract: [`contracts/operational-realtime-invalidation.json`](../../contracts/operational-realtime-invalidation.json).

## Chat V1 (core)

Implemented: REST structure/history/seen/presence, WS message send, Terrain pages, 7-day purge, membership hooks.

Post-core gaps (non-blocking pilot): group settings UI, some bootstrap hints, no REST message write.

## Frontend

- Terrain mobile shell (`TerrainShell`, bottom nav, safe areas).
- Client router: `apps/web/src/app/app-routes.ts` (not React Router).
- Server state: TanStack Query only. Zustand is listed in stack docs but **not imported** in `apps/web/src` today.
- PWA: `vite-plugin-pwa` `injectManifest`, `src/sw.ts`, register on prod build.

Details: [`../engineering/frontend_architecture.md`](../engineering/frontend_architecture.md).

## Lot 11 stabilization (preserved contracts)

Completed 2026-07-05 — test hygiene + doc alignment, **no API contract change**.

Preserved names (do not rename without explicit decision):

- `can_create_action()` — establishment permission alias for action plan creation hints.
- Realtime events `comment.execution.*` for action plan execution comment threads.

## Pilot gaps (known)

- Production-grade polish on all terrain screens.
- Chat post-core UI (group admin, settings).
- Push notifications depend on user opt-in and VAPID config.
- Full device QA matrix not automated in CI.

## Reading order

1. [`mvp_scope.md`](mvp_scope.md) — pilot boundaries  
2. Domain docs under [`domains/`](domains/)  
3. [`decisions/action_plan.md`](decisions/action_plan.md) — action plan RBAC and schedules  
4. [`../engineering/local_development.md`](../engineering/local_development.md) — daily workflow
