# Frontend AGENTS.md

Applies to `apps/web/**`.

## Stack

React, TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query, Framer Motion.

One source tree, two Vite pipelines: Web and Native/Capacitor. Not a PWA — do not reintroduce a service worker or web app manifest.

Do not upgrade frontend framework versions unless explicitly requested.

Architecture reference: [`docs/engineering/frontend_architecture.md`](../../docs/engineering/frontend_architecture.md).

## Ownership

- React renders UI and user interactions.
- Backend owns business rules, permissions, lifecycle, visibility, and validation.
- OpenAPI/generated types own API data contracts.
- TanStack Query owns server state.
- React state owns local UI (drawers, tabs, modals). Do not persist server-owned data in client stores.

Do not move business workflows to React. Frontend permission checks are UX only; unauthorized data must not be fetched and hidden locally.

## API flow

generated client → API wrapper/hook → TanStack Query → component

Do not call `fetch` in feature components, duplicate or hand-edit generated API types, or use endpoints absent from OpenAPI. If generated types are wrong, fix the backend schema and regenerate.

HTTP and WebSocket hosts are resolved only in [`apps/web/src/lib/runtime.ts`](src/lib/runtime.ts).

## Surfaces

Identify the actual product surface and shell from the repository before changing UI. Mobile-first is not mobile-only; do not force phone-style layouts onto desktop-oriented surfaces. Reuse existing shells. No hover-only critical actions.

Current operational patterns (not a closed taxonomy — inspect routing and shells):

- Terrain operational (`TerrainShell`, bottom-nav hubs): mobile-primary, desktop-supported
- Analytics (`TerrainShell`, not in mobile bottom nav): desktop-primary, remain coherent on small screens
- Organization / admin / config / onboarding / auth (`AppShell`): desktop-primary, existing shell conventions

Public landing is a separate marketing tree and must not inherit Terrain phone-shell rules.

Native keyboard, safe-area, and Web vs Native auth diagnosis: Skill `native-runtime-debug`.

## State and cache

TanStack Query for reads, mutations, cache, invalidation, and server-derived loading/error. React state for local UI.

`auth` is the only query root that may survive login, registration, or establishment switch. Never store operational or tenant-scoped data under `auth`. Logout clears the full query cache; login, registration, and establishment switch purge non-auth queries before hydrating bootstrap. Implementation: `@/lib/query-invalidation`.

Do not casually cache authenticated operational data in durable client storage. No durable offline mutation queue unless explicitly implemented. Access tokens stay in memory; do not put refresh credentials in `localStorage` / `sessionStorage`.

## Components and realtime

Components may render UI, handle interactions, call focused hooks, and display loading/empty/error/unauthorized/offline states when relevant. They must not fetch directly, compute real permissions, encode lifecycle transitions, or duplicate backend state.

Generic realtime is invalidation or a safe Query patch. Backend remains source of truth. Chat is the exception: dedicated WebSocket for messages; REST remains source for history, structure, and permissions; the ws-ticket is REST-issued and not persisted.

Use existing shadcn/ui and domain components first. Prefer readable Tailwind. Use Framer Motion sparingly.

## Tests and commands

Procedure: [`docs/engineering/testing.md`](../../docs/engineering/testing.md).

Test product risk at the owning layer: lib (Node) → hooks/mutations with a real `QueryClient` → page tests only for wiring risk. Do not assert Tailwind/shadcn classes or French copy unless exported as a lib rule.

Run from repo root unless needed:

- `cd apps/web && npm run typecheck`
- `cd apps/web && npm run lint`
- `cd apps/web && npm test -- path/to/file.test.ts`
- `cd apps/web && npm run build`
- `cd apps/web && npm run build:native` (requires `VITE_API_BASE_URL` and `VITE_PUBLIC_APP_URL`)
- `make web-cap-sync` / `make web-dev-native` (`web-dev-native` is a compile-time runtime pin, not authentication)
- `make web-api-generate` after `make schema`
