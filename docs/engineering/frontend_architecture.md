# Frontend architecture

Status: authoritative  
Last reviewed: 2026-08-17

## Stack

React, TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query, Framer Motion (terrain transitions). Two Vite pipelines from one source tree: Web (`dist/`, `base: '/'`) and Native (`dist-native/`, `base: './'`).

Zustand was removed from the stack — prefer TanStack Query for server state and React state for local UI.

## Routing

Client-side router in [`apps/web/src/app/app-routes.ts`](../../apps/web/src/app/app-routes.ts) — not React Router.

- `AppPath` — static terrain and auth paths (`/signals`, `/execution`, `/chat`, …)
- `AppRoute` — discriminated union for detail routes (`signal-detail`, `action-plan-execution-detail`, `chat-conversation-detail`, …)
- `parseAppRoute` / `serializeAppRoute` — URL ↔ `AppRoute` (query owned by the route, e.g. create `from=execution`)
- `AppHistory` — injectable location store (`getHref`, `subscribe`, `navigate`); Web uses `createBrowserHistory()`, tests use `createMemoryHistory()`
- `AppRouteProvider` — requires `history` from the composition root ([`main.tsx`](../../apps/web/src/main.tsx)); `useAppRoute()` exposes `{ route, search, navigate }`. Search-only URL changes keep the same `route` object (`getAppRouteKey`); `search` still updates.
- Search-only screen state (Analytics filters, comment deep links, onboarding ids) stays in the URL query and is read from `useAppRoute().search` / `useLocationSearch()`
- `terrain-routes.ts` — shell config per route (`mainScroll`, topbar, bottom nav)

Lazy pages: [`lazy-terrain-pages.tsx`](../../apps/web/src/app/lazy-terrain-pages.tsx).

## Layout

- **Terrain shell** — `TerrainShell` (`fixed inset-x-0 top-0`, `h-dvh`, topbar, scrollable main, optional bottom nav)
- **App shell** — desktop/management shell for non-terrain routes (`/organization*`, `/app/operational-config`, onboarding, auth pages)

## Server state

- Generated OpenAPI types → API wrappers → TanStack Query hooks
- HTTP and WebSocket hosts are resolved only in [`apps/web/src/lib/runtime.ts`](../../apps/web/src/lib/runtime.ts) (`VITE_API_BASE_URL`, `VITE_APP_RUNTIME`). Features must not compute the API host.
- Query key roots: feature-scoped (`signals`, `action-plans`, `chat`, `notifications`, `auth`, …)
- Establishment switch / login: purge non-`auth` queries (`@/lib/query-invalidation`)

## Authentication

- `UserSession` remains the single backend session model for both runtimes.
- Access tokens are opaque Bearer credentials kept only in frontend memory.
- Refresh persistence is isolated under `features/auth`: Web uses an HttpOnly cookie + CSRF; the future Native composition injects a secure body-token store.
- `refresh_token_transport` selects credential transport only. Features and business domains never branch on cookie/body.
- Body transport sends `credentials: omit`, then commits a session in the order refresh persistence → in-memory access token → bootstrap cache; persistence failures fail closed before best-effort network cleanup.
- Cookie session-creation/replacement requests are serialized inside Auth so out-of-order `Set-Cookie` responses cannot replace a newer session. Any cookie response made stale by logout fails closed and triggers best-effort cookie-session cleanup.
- Capacitor and the concrete native secure-storage adapter are intentionally deferred to roadmap Lot 5.

## Realtime

| Channel | Provider | Scope |
|---------|----------|-------|
| Operational invalidation | `OperationalRealtimeProvider` | Terrain routes (not chat conversation wiring) |
| Chat messages | `ChatRealtimeProvider` | Chat pages |

Invalidation only — backend remains source of truth.

## Builds Web / Native

One React tree, two Vite pipelines in [`vite.config.ts`](../../apps/web/vite.config.ts):

- **Web** (`npm run build`): `VITE_APP_RUNTIME=web`, `base: '/'`, `dist/`. Classic hashed assets; `index.html` revalidated by nginx/CDN. No service worker, no web app manifest.
- **Native** (`npm run build:native`): `VITE_APP_RUNTIME=native`, `base: './'`, `dist-native/`. Same app without Web-only artifacts. `VITE_API_BASE_URL` is required at Vite startup (dev and build). `base: './'` is a Lot 4 output convention, not a proven Capacitor contract.

`tsc -b` stays in `build` and `build:native`. The runtime pin is on the Vite process only (`tsc -b && VITE_APP_RUNTIME=… vite build`). Capacitor bootstrap is Lot 5.

## Commands

```bash
cd apps/web && npm run typecheck
cd apps/web && npm run lint
cd apps/web && npm test
cd apps/web && npm run build
cd apps/web && npm run build:native   # requires VITE_API_BASE_URL
make web-api-generate   # after make schema
```

## Agent entry

[`apps/web/AGENTS.md`](../../apps/web/AGENTS.md) — ownership rules and cache purge policy.
