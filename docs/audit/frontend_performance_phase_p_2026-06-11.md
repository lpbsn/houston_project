# Frontend Performance — Phase P Bundle Budget

**Date:** 2026-06-11  
**Phase:** P (lazy terrain routes + bundle baseline)  
**Prerequisite:** Phases A, S0, B, C, D, K, L, M complete  
**Parent:** [`code_scalability_s0_2026-06-11.md`](code_scalability_s0_2026-06-11.md)

Phase P documents the production JS bundle baseline and splits terrain route pages into lazy-loaded chunks. No `chunkSizeWarningLimit` change, no service-worker changes, no TanStack invalidation refactor (deferred to **H**).

---

## 1. S0 findings addressed

| ID | Priority | Action | Outcome |
|----|----------|--------|---------|
| FE-01 | P1 | Lazy-load terrain route groups | 15 terrain pages + `ChatRealtimeProvider` moved to `React.lazy` in `apps/web/src/app/lazy-terrain-pages.tsx` |
| FE-02 | P1 | Document 733 kB baseline; track post-split | Main entry chunk **733 → 561 kB** (−23%); see §2 |
| FE-03 | P1 | Narrow invalidation | **Deferred to H** — no mutation/invalidation changes in P |

---

## 2. Measured bundle sizes (`npm run build`, Vite 8)

### Before (static imports, S0 baseline)

| Asset | Minified | Gzip |
|-------|----------|------|
| `dist/assets/index-*.js` (single entry) | **732.98 kB** | 203.49 kB |
| JS chunks | 1 | — |

Vite warned: chunk > 500 kB.

### After (lazy terrain routes)

| Asset | Minified | Gzip |
|-------|----------|------|
| `dist/assets/index-*.js` (shell + auth/onboarding) | **561.17 kB** | 162.96 kB |
| Lazy terrain chunks (largest) | | |
| `signal-feed-page-*.js` | 26.35 kB | 8.54 kB |
| `checklist-template-detail-page-*.js` | 24.36 kB | 6.69 kB |
| `report-page-*.js` | 15.02 kB | 5.65 kB |
| `execution-feed-page-*.js` | 12.80 kB | 4.03 kB |
| `chat-page-*.js` | 7.08 kB | 2.43 kB |
| `signal-detail-page-*.js` | 6.79 kB | 2.63 kB |
| `chat-conversation-page-*.js` | 6.68 kB | 2.68 kB |
| `action-create-page-*.js` | 6.10 kB | 2.45 kB |
| `action-detail-page-*.js` | 5.93 kB | 2.41 kB |
| `checklist-execution-detail-page-*.js` | 5.73 kB | 2.12 kB |
| `checklist-hub-page-*.js` | 5.72 kB | 2.34 kB |
| `chat-realtime-provider-*.js` | 4.86 kB | 1.87 kB |
| Remaining lazy chunks | < 5 kB each | — |
| **Total JS chunks** | **49** | — |

**Initial load delta:** main entry −172 kB minified (−40 kB gzip). Terrain feature code loads on first navigation to the matching route.

**Residual warning:** entry chunk still > 500 kB (auth shell, shared UI, TanStack Query, Framer Motion, onboarding). Further splitting is **H** / **S1** scope (`App.tsx` decomposition, FE-08).

---

## 3. Implementation notes

| Item | Detail |
|------|--------|
| Lazy module | `apps/web/src/app/lazy-terrain-pages.tsx` |
| Suspense fallback | `apps/web/src/app/route-page-loading.tsx` |
| Eager routes | Login, onboarding, invitation, `/app` management, operational config, team invite |
| Lazy routes | Terrain hubs (`/reporting`, `/signals`, `/execution`, `/chat`, `/profile`), all terrain detail routes, checklist management |
| `manualChunks` | Not added — route-level `import()` produced sufficient splits without custom Rollup grouping |

---

## 4. Follow-up routing

| Item | Phase |
|------|-------|
| TanStack broad invalidation (`actions/hooks.ts` → `signalsQueryKeys.all`) | **H** (FE-03) |
| `App.tsx` decomposition, deprecated terrain imports | **H** / **S1** |
| Further entry-chunk reduction (shared deps, motion) | **S1** if latency proven |
| Lighthouse / prod perf gates | Out of scope (dev phase) |

---

## 5. Validation

```bash
cd apps/web && npm run typecheck
cd apps/web && npm test
cd apps/web && npm run build
```

- Typecheck, 315 tests, and production build green on 2026-06-11.
- CI `web-build` (Phase A) unchanged — build step only.

---

## 6. Rollback

Revert `lazy-terrain-pages.tsx`, `route-page-loading.tsx`, and `App.tsx` lazy/Suspense wiring. Main bundle returns to ~733 kB single chunk.
