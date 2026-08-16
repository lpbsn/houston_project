# Frontend architecture

Status: authoritative  
Last reviewed: 2026-07-23

## Stack

React, TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query, Framer Motion (terrain transitions), PWA via `vite-plugin-pwa`.

Zustand was removed from the stack — prefer TanStack Query for server state and React state for local UI.

## Routing

Client-side router in [`apps/web/src/app/app-routes.ts`](../../apps/web/src/app/app-routes.ts) — not React Router.

- `AppPath` — static terrain and auth paths (`/signals`, `/execution`, `/chat`, …)
- `AppRoute` — discriminated union for detail routes (`signal-detail`, `action-plan-execution-detail`, `chat-conversation-detail`, …)
- `AppRouteProvider` + `useAppRoute()` — `history.pushState` / `popstate`
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

## Realtime

| Channel | Provider | Scope |
|---------|----------|-------|
| Operational invalidation | `OperationalRealtimeProvider` | Terrain routes (not chat conversation wiring) |
| Chat messages | `ChatRealtimeProvider` | Chat pages |

Invalidation only — backend remains source of truth.

## PWA

[`vite.config.ts`](../../apps/web/vite.config.ts):

- `strategies: 'injectManifest'`
- `srcDir: 'src'`, `filename: 'sw.ts'`
- `registerType: 'prompt'`, `injectRegister: false`
- Manifest branding: **Spore**

[`sw.ts`](../../apps/web/src/sw.ts): Workbox precache, SPA navigation fallback, push + `notificationclick` handlers.

Prod registration via `virtual:pwa-register` in [`main.tsx`](../../apps/web/src/main.tsx).

## Commands

```bash
cd apps/web && npm run typecheck
cd apps/web && npm run lint
cd apps/web && npm test
cd apps/web && npm run build
make web-api-generate   # after make schema
```

## Agent entry

[`apps/web/AGENTS.md`](../../apps/web/AGENTS.md) — ownership rules and cache purge policy.
