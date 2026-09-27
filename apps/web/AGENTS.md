# Frontend AGENTS.md

Applies to `apps/web/**`.

Spore has one shared React product tree serving Native/Capacitor mobile and Web desktop surfaces. It is not a PWA.

## Ownership and state

- React components own rendering, interaction, and composition.
- TanStack Query owns server state, caching, refetching, and invalidation.
- Backend remains authoritative for business rules, authorization, lifecycle, visibility, and validation.
- Local UI state belongs to the narrowest client owner that matches its lifecycle.
- Durable client persistence is explicit, scoped, and justified; it is not a default state-management tool.

Do not duplicate server-owned data into parallel client state without a demonstrated need.

## Shared product, surface-specific presentation

Spore is one frontend product, not separate mobile and desktop applications.

Share behavior before markup. Data access, mutations, validation, navigation semantics, and reusable domain logic should remain shared when they own the same responsibility.

Do not duplicate an entire feature because its layout differs between mobile and desktop.

When behavior is shared but presentation genuinely differs, prefer shared logic with separate surface-specific presentation components.

Factor shared responsibility, not shared appearance. Do not force reuse through components filled with runtime, viewport, or surface branches.

A feature change should ideally modify its owning logic once, then only the presentation layers that genuinely differ.

Desktop is not stretched mobile. Native is not desktop at a large viewport.

Determine product behavior from the relevant runtime, route, shell, and viewport. Do not infer the product surface from viewport alone.

Use responsive CSS for visual adaptation. Use runtime or surface branching only when interaction or product behavior genuinely differs.

Do not scatter Native/Desktop/viewport checks across feature trees. Concentrate surface divergence at clear runtime, shell, navigation, or narrowly owned presentation boundaries.

## Data flow and performance

Keep API access behind established feature or domain data-access owners. Generated contracts remain the source for API shapes; TanStack Query owns server-state orchestration.

Do not hand-edit generated API artifacts or introduce feature-level ad hoc requests when an existing