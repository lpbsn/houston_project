## Frontend stack:

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- TanStack Query
- minimal Zustand
- Framer Motion, minimal usage only
- PWA-ready

Do not upgrade frontend framework versions unless explicitly requested.

------

## Frontend principles

React is the UI layer.

The backend owns business rules.

OpenAPI owns API contracts.

TanStack Query owns server state.

Zustand owns UI/client state only.

The frontend must remain API-driven and thin.

Do not move business workflows to React.

Do not compute real permissions in React.

Do not duplicate backend business state in client stores.

------

## Frontend structure

Expected structure:

```
src/
  api/
    generated/
  app/
  components/
    ui/
    domain/
    layout/
  features/
  stores/
  lib/
```

Use:

- `src/api/generated/` for generated OpenAPI client files
- `src/app/` for app bootstrap, providers, routing, layout shell
- `src/components/ui/` for generic shadcn/ui-style primitives
- `src/components/domain/` for reusable Houston domain components
- `src/components/layout/` for layout primitives
- `src/features/` for feature-level screens and flows
- `src/stores/` for minimal UI/client state stores
- `src/lib/` for small frontend utilities

Do not create new top-level folders unless clearly justified.

------

## API usage rules

Use the generated OpenAPI TypeScript client.

Do not call `fetch` directly inside feature components.

Do not manually duplicate generated API types.

Do not manually edit generated API client files.

If generated API types are wrong, fix the backend schema/source and regenerate.

No frontend endpoint usage without OpenAPI.

API usage should flow through:

```
generated client -> API wrapper/hook -> TanStack Query -> component
```

Auth retry + multipart upload guidance:
- Prefer the shared `withAuthRetry` helper from `src/api/client.ts` for 401 -> refresh retry flows.
- For multipart submission (e.g. observations media), use `FormData` and do not manually force the `Content-Type` header; let the browser set the multipart boundary (see `src/features/observations/api.ts`).
- For the invitation accept flow, do not clear/purge auth state before the API request succeeds; update auth state only after success (see `src/features/invitations/api.ts`).
------

## Server state vs UI state

Use TanStack Query for:

- API reads
- API mutations
- caching
- refetching
- invalidation
- loading/error/success state tied to server data

Use Zustand only for:

- local UI state
- temporary client state
- drawer/sidebar state
- selected tab/view mode when not persisted by backend
- modal state
- short-lived form UI helpers

Do not store server-owned data in Zustand.

Forbidden in Zustand:

- Signals feed data
- Actions feed data
- current permissions
- establishment business truth
- workflow statuses
- backend-derived visibility
- duplicated API response caches

------

## React component rules

React components should remain presentation-oriented whenever possible.

Components may:

- render UI
- handle user interaction
- call focused hooks
- display loading/error/empty/success states
- compose domain components

Components must not:

- perform direct fetch calls
- contain business workflow decisions
- compute real permissions
- duplicate backend state
- perform complex API orchestration
- encode status transition rules

Custom hooks must stay small and focused.

Split hooks by intent:

- read hooks
- mutation hooks
- UI-only hooks

------

## Feature structure rules

Feature folders may contain:

```
components/
hooks/
pages/
forms/
types.ts
```

Keep feature code close to the workflow it supports.

Promote reusable UI to `components/domain/` only when it is reused or clearly generic across Houston domains.

Avoid over-abstracting early.

Prefer readable duplication over premature generic components.

------

## UI rules

Prioritize:

- mobile-first layouts
- touch-friendly interactions
- responsive behavior
- clear hierarchy
- fast execution flows
- readable operational screens
- clear loading/error/empty/success states

Every data-driven screen must handle relevant states:

- loading
- error
- empty
- success

Use reusable Houston domain components before creating one-off screen UI.

Prefer simple UI over clever UI.

Avoid dense desktop-first layouts.

Avoid hidden critical actions.

Avoid business-critical actions without clear feedback.

------

## shadcn/ui and Tailwind rules

Use shadcn/ui primitives as base components.

Keep styling local and readable.

Prefer Tailwind utility composition over custom CSS unless repeated patterns justify extraction.

Do not create heavy design abstractions too early.

Use domain components for Houston-specific UI patterns.

------

## Framer Motion rules

Use Framer Motion sparingly.

Allowed:

- micro-interactions
- mobile transitions
- small feedback animations
- panel/drawer transitions

Avoid:

- animation-heavy UI
- decorative animations that slow operational use
- complex animation state machines
- motion that hides latency or state changes

Operational clarity is more important than visual polish.

------

## Permission and visibility rules

The backend owns permissions.

Frontend may display backend-provided permission flags.

Frontend must not calculate real permissions from raw role/domain data.

Frontend must not receive unauthorized data and hide it locally.

If a backend response says an action is forbidden, the UI must handle it gracefully.

Do not implement security boundaries in React.

------

## Realtime frontend rules

Realtime messages are invalidation/refetch triggers only.

On realtime event:

1. inspect event type
2. invalidate relevant TanStack Query keys
3. refetch through REST API if needed
4. update UI from server response

Do not use websocket payloads as business truth.

Do not store full websocket payloads as domain state.

Do not bypass REST API after realtime events.

------

## Forms rules

Forms should validate UI-level constraints only.

Backend remains responsible for business validation.

Frontend validation may cover:

- required visible fields
- primitive format checks
- basic length checks
- immediate UX feedback

Frontend validation must not replace backend validation.

When backend returns validation errors, display them clearly.
Backend error responses follow the standardized `{ code, detail, errors? }` contract documented in [`api_error_contract.md`](../../docs/architecture/api_error_contract.md).

------

## Error handling rules

User-facing errors should be clear and actionable.

Do not expose raw technical errors directly to users.

Preserve enough technical detail for debugging in developer logs when appropriate.

Handle:

- network errors
- validation errors
- permission errors
- business conflict errors
- empty results
- expired sessions

------

## PWA and offline rules

PWA-ready does not mean offline business workflows by default.

Forbidden unless explicitly implemented:

- durable offline storage of sensitive business data
- offline mutation queue for operational workflows
- storing raw Observation text persistently
- storing media locally beyond temporary browser handling

Text drafts may be frontend-only if explicitly scoped and non-durable.

------

## Frontend commands

Run from repository root unless stated otherwise.

Install dependencies:

```
cd apps/web && npm install
```

Typecheck:

```
cd apps/web && npm run typecheck
```

Lint:

```
cd apps/web && npm run lint
```

Build:

```
cd apps/web && npm run build
```

Test:

```
cd apps/web && npm test
cd apps/web && npm run test:watch
```

Generate API client:

```
Use the project-defined API client generation command if it exists.
If missing, do not invent it.
```

------

## Frontend testing rules

Add or update tests when changing:

- reusable domain components
- critical forms
- API hooks
- mutation flows
- routing behavior
- permission-based UI display
- error/empty/loading states

Frontend tests should verify:

- loading state
- error state
- empty state
- success state
- user interaction
- mutation behavior
- query invalidation when applicable

Prefer behavior-focused tests.

Avoid tests that only check implementation details.

------

## TypeScript rules

Do not use `any` unless explicitly justified.

Prefer generated API types.

Avoid duplicating backend DTO types manually.

Use narrow local types only for UI-specific state.

If a type comes from the API, use the generated type.

If generated types are wrong, fix the backend schema and regenerate.

------

## Frontend Definition of Done

Frontend work is done only when:

- generated API types are used when applicable
- no direct fetch is added inside feature components
- TanStack Query handles server state
- Zustand is limited to UI/client state
- React does not contain business workflows
- loading/error/empty/success states are handled when relevant
- mobile-first behavior is preserved
- permissions are backend-driven
- relevant frontend commands were run or a reason is given
- tests are added/updated when behavior changes
- risks/debt are stated