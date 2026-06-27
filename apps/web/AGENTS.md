# Frontend AGENTS.md

Applies to `apps/web/**`.

## Stack

React, TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query, minimal Zustand, minimal Framer Motion, PWA-ready.

Do not upgrade frontend framework versions unless explicitly requested.

## Ownership

- React renders UI and user interactions.
- Backend owns business rules, permissions, lifecycle, visibility, and validation.
- OpenAPI/generated types own API data contracts.
- TanStack Query owns server state.
- Zustand owns local UI/client state only.

Do not move business workflows to React.

## API flow

Use:

generated client -> API wrapper/hook -> TanStack Query -> component

Do not:
- call `fetch` directly in feature components
- manually duplicate generated API types
- manually edit generated API files
- use endpoints not present in OpenAPI
- store server-owned data in Zustand

If generated types are wrong, fix backend schema and regenerate.

## Mobile-first / PWA

Houston is phone-first for field teams.

- build mobile layout first
- no desktop-only or hover-only UX
- no horizontal page scroll
- critical actions must be reachable on phone
- loading, empty, error, unauthorized, and offline states must be explicit
- no casual caching of authenticated operational data
- no durable offline mutation queue unless explicitly implemented
- no persistent storage of sensitive business data

## State

Use TanStack Query for reads, mutations, cache, invalidation, and server-derived loading/error state.

Use Zustand only for UI state:
- drawer/sidebar
- selected tab/view mode
- modal state
- short-lived form helpers

Forbidden in Zustand:
- feed data
- permissions
- workflow statuses
- backend-derived visibility
- API response caches

TanStack Query cache isolation: `auth` is the only root preserved on establishment switch, login, and registration. Never store operational, tenant-scoped, workspace, onboarding, reporting, or feature data under `auth`. Logout must clear the full query cache; login, registration, and establishment switch must purge all non-auth queries before hydrating bootstrap.

Establishment-scoped cache purge (`@/lib/query-invalidation`):
- Logout / invalidated session: `clearAuthenticatedQueryCache` — `cancelQueries()` then `queryClient.clear()`.
- Login / registration: `purgeNonAuthQueries` — `cancelQueries` then `removeQueries` with predicate `queryKey[0] !== 'auth'`, then rewrite `['auth', 'bootstrap']`.
- Establishment switch: same as login/registration — `purgeNonAuthQueries`, then rewrite `['auth', 'bootstrap']`.
- Default-safe: any non-`auth` query root is treated as tenant-scoped and removed automatically — no manual whitelist to update per feature.
- Only queries under the `auth` root may survive an establishment switch (today: bootstrap). Do not store operational data under `auth`.

## Components

Components may render UI, handle interactions, call focused hooks, and display states.

Components must not:
- perform direct fetch calls
- compute real permissions
- encode lifecycle transitions
- orchestrate complex API workflows
- duplicate backend state

## Permissions

Frontend may display backend permission hints.
Frontend must not enforce security.
Unauthorized data must not be sent and hidden locally.

## Realtime

Generic realtime is invalidation/refetch only.
Backend remains source of truth.
On realtime event, invalidate or safely patch TanStack Query.

Chat V1 exception:
- WebSocket sends messages
- REST remains source for history/structure/permissions
- ws-ticket is REST-issued and not persisted

## UI conventions

Use shadcn/ui primitives and existing Houston domain components first.
Prefer simple, readable Tailwind.
Use Framer Motion sparingly; operational clarity beats polish.
Respect accessibility basics: labels, accessible icon buttons, reduced motion.

## Tests

Add/update tests for:
- API hooks
- mutations
- routing
- permission-based UI
- mobile states
- loading/error/empty states
- query invalidation/realtime behavior

## Commands

Run from repo root unless needed:

- typecheck: `cd apps/web && npm run typecheck`
- lint: `cd apps/web && npm run lint`
- tests: `cd apps/web && npm test`
- build: `cd apps/web && npm run build`

Use project-defined API generation command if it exists. Do not invent missing commands.