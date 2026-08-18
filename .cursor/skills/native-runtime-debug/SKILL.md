---
name: native-runtime-debug
description: Diagnose Spore Web vs Native/Capacitor runtime issues — iOS keyboard, visualViewport, safe areas, auth transport, compile-time runtime pin. Not a generic mobile frontend skill.
---

# Native runtime debug

Expertise only. Respect the active Command’s permissions and scope. Measure before patching. Do not expand into product-surface layout policy (`responsive-surfaces`).

## Purpose

Diagnose Web vs Native/Capacitor failures: iOS keyboard and `visualViewport`, safe areas, auth transport, compile-time runtime pin, host resolution.

## Diagnostic order

1. Confirm runtime: `getAppRuntime()` in [`apps/web/src/lib/runtime.ts`](../../../apps/web/src/lib/runtime.ts) (`VITE_APP_RUNTIME`), plus `Capacitor.isNativePlatform()` when native plugins are involved.
2. Identify the scroll owner (document vs `TerrainShell` `main`) before changing overflow or `position`.
3. For keyboard/layout bugs: capture T0 (idle), T1 (focused / broken), T2 (blur restored) using `visualViewport` and shell/topbar `getBoundingClientRect`. Do not apply global `position: fixed`, overflow locks, or height hacks without that evidence.
4. Preserve `h-dvh`, flex `min-h-0`, and `env(safe-area-inset-*)` on topbar, bottom nav, composer, and sticky footers.

## Spore traps

- **Not a PWA.** Boot unregisters leftover service workers. Do not add `sw.js`, workbox, or a web app manifest.
- **Hosts** are resolved only in `runtime.ts`. Features must not compute API/WS URLs.
- **`make web-dev-native` / `VITE_APP_RUNTIME=native` is a compile-time pin, not authentication.** Native Vite off-device does not configure Keychain.
- **Auth transport:** Web = HttpOnly cookie + CSRF; Native = `refresh_token_transport: body` + injected secure store. Never `localStorage` / `sessionStorage` for refresh tokens. Native store configures only when runtime is `native` **and** `Capacitor.isNativePlatform()`.
- Safe-area insets are real and widespread; do not invent a parallel shell.

## Where to inspect

- [`apps/web/src/lib/runtime.ts`](../../../apps/web/src/lib/runtime.ts)
- [`apps/web/src/features/auth/refresh-token-transport.ts`](../../../apps/web/src/features/auth/refresh-token-transport.ts)
- [`apps/web/src/features/auth/native-refresh-token-store.ts`](../../../apps/web/src/features/auth/native-refresh-token-store.ts)
- Terrain shell / topbar / bottom nav / chat composer / sticky footer
- [`docs/engineering/frontend_architecture.md`](../../../docs/engineering/frontend_architecture.md)

## Canonical commands

- `make web-cap-sync` after native web build
- `make web-dev-native` — compile-time pin only
- `cd apps/web && npm run build:native` — requires `VITE_API_BASE_URL` and `VITE_PUBLIC_APP_URL`

## Output

Diagnosis · Evidence (T0/T1/T2 when layout) · Proposed fix (if any) · What still needs a physical device
