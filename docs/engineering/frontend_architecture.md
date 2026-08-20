# Frontend architecture

Status: authoritative  
Last reviewed: 2026-08-20

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
- Native HTTPS deep links (`getLaunchUrl` / `appUrlOpen`) parse the public origin then `parseAppRoute`; `establishment_id` is a sibling of the product href through login / select-establishment. See [`apps/web/src/lib/app-open-target.ts`](../../apps/web/src/lib/app-open-target.ts).
- `terrain-routes.ts` — shell config per route (`mainScroll`, topbar, bottom nav)
- Terrain back path is semantic (`resolveTerrainBackPath` / topbar « Retour »), not `history.back`. Android hardware back uses that path (overlay first, then `minimizeApp` on hubs). iOS has no system back listener.

Lazy pages: [`lazy-terrain-pages.tsx`](../../apps/web/src/app/lazy-terrain-pages.tsx).

## Layout

- **Terrain shell** — `TerrainShell` (`fixed inset-x-0 top-0`, `h-dvh`, topbar, scrollable main, optional bottom nav). Safe-area token `--app-safe-top/bottom` = `var(--safe-area-inset-*, env(safe-area-inset-*, 0px))` (Capacitor Android polyfill + iOS `env()`).
- **App shell** — desktop/management shell for non-terrain routes (`/organization*`, `/app/operational-config`, onboarding, auth pages)

## Server state

- Generated OpenAPI types → API wrappers → TanStack Query hooks
- HTTP and WebSocket hosts are resolved only in [`apps/web/src/lib/runtime.ts`](../../apps/web/src/lib/runtime.ts) (`VITE_API_BASE_URL`, `VITE_APP_RUNTIME`). Public invitation copy links use `VITE_PUBLIC_APP_URL` from the same module. Features must not compute the API host.
- Query key roots: feature-scoped (`signals`, `action-plans`, `chat`, `notifications`, `auth`, …)
- Establishment switch / login: purge non-`auth` queries (`@/lib/query-invalidation`)

## Authentication

- `UserSession` remains the single backend session model for both runtimes.
- Access tokens are opaque Bearer credentials kept only in frontend memory.
- Refresh persistence is isolated under `features/auth`: Web uses an HttpOnly cookie + CSRF; Native injects a Keychain/Keystore body-token store from the composition root before session restore.
- `refresh_token_transport` selects credential transport only. Features and business domains never branch on cookie/body.
- Body transport sends `credentials: omit`, then commits a session in the order refresh persistence → in-memory access token → bootstrap cache; persistence failures fail closed before best-effort network cleanup.
- Cookie session-creation/replacement requests are serialized inside Auth so out-of-order `Set-Cookie` responses cannot replace a newer session. Any cookie response made stale by logout fails closed and triggers best-effort cookie-session cleanup.
- Native refresh persistence uses `@aparajita/capacitor-secure-storage` only when `VITE_APP_RUNTIME=native` and `Capacitor.isNativePlatform()`; iCloud Keychain sync is off. The plugin is never used on web (it would write `localStorage`).

## Realtime

| Channel | Provider | Scope |
|---------|----------|-------|
| Operational invalidation | `OperationalRealtimeProvider` | Terrain routes (not chat conversation wiring) |
| Chat messages | `ChatRealtimeProvider` | Chat pages |

Invalidation only — backend remains source of truth.

Network banner (`navigator.onLine` on Web; `@capacitor/network` on Native) and WS reconnect on `visibilitychange` / native `appStateChange` share runtime lifecycle and a single `isOnline` source. Query resync after pause is the existing WS `onReconnect` catalogue plus `refetchOnReconnect` when that network signal flaps — not a global foreground invalidate.

## Builds Web / Native

One React tree, two Vite pipelines in [`vite.config.ts`](../../apps/web/vite.config.ts):

- **Web** (`npm run build`): `VITE_APP_RUNTIME=web`, `base: '/'`, `dist/`. Classic hashed assets; `index.html` revalidated by nginx/CDN. No service worker, no web app manifest. Boot unregisters leftover service-worker registrations from pre–Capacitor Lot 4 installs.
- **Native** (`npm run build:native`): `VITE_APP_RUNTIME=native`, `base: './'`, `dist-native/`. Capacitor `webDir` is `dist-native`. `VITE_API_BASE_URL` and `VITE_PUBLIC_APP_URL` (absolute http(s) origin) are required at Vite startup (dev and build).

`tsc -b` stays in `build` and `build:native`. The runtime pin is on the Vite process only (`tsc -b && VITE_APP_RUNTIME=… vite build`). Native projects live in [`apps/web/ios`](../../apps/web/ios) and [`apps/web/android`](../../apps/web/android); sync with `npm run cap:sync`. Committed `capacitor.config.ts` keeps `allowMixedContent: false` and no `server.cleartext`; Android debug Gradle overlays local HTTP mixed content for the emulator.

## Commands

```bash
cd apps/web && npm run typecheck
cd apps/web && npm run lint
cd apps/web && npm test
cd apps/web && npm run build
cd apps/web && npm run build:native   # requires VITE_API_BASE_URL and VITE_PUBLIC_APP_URL
cd apps/web && npm run cap:sync
make web-api-generate   # after make schema
```

## Agent entry

[`apps/web/AGENTS.md`](../../apps/web/AGENTS.md) — ownership, cache isolation, and surface identification.
