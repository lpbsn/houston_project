# Mobile PWA debug

Diagnose iOS Safari / PWA layout issues (keyboard, topbar, scroll). **No fix before measurement.**

Read [`20-mobile-pwa-shell.mdc`](../rules/20-mobile-pwa-shell.mdc) and [`apps/web/AGENTS.md`](../../apps/web/AGENTS.md).

Before proposing code changes:
1. Identify scroll owner: document (`html`/`body`) vs `TerrainShell` `main`
2. Capture T0 (idle), T1 (keyboard focused / bug), T2 (blur restored) using `visualViewport` and shell/topbar `getBoundingClientRect`
3. Log: `scrollY`, `innerHeight`, `vv.height`, `vv.offsetTop`, `shell.top`, `shell.height`

Constraints:
- Do not apply global `position: fixed`, overflow locks, or height hacks without T0/T1/T2 evidence
- Preserve `h-dvh`, flex `min-h-0` chain, safe-area insets
- For implementation after diagnosis, use `implement-change` with minimal diff

Final: Diagnosis · Evidence · Proposed fix (if any) · Validation on iPhone/PWA
