# Phase S1 — Debt closure / scalability cleanup

**Date:** 2026-06-11  
**Prerequisite:** Phases A, S0, B, C, D, K, L, M, P, E, F, G, H, I complete  
**Mode:** proven-debt closure only — no speculative refactors, no events, no prod/staging

---

## Implemented (this phase)

| S0 ID | Action | Outcome |
|-------|--------|---------|
| BE-SER03 / D follow-up | Extract `build_bootstrap_permission_hints` to `accounts/permission_hints.py` | Selector no longer lazy-imports chat/establishments permissions |
| DB-03 | Batch latest messages + single participant pass on chat conversation list | 12→9 queries (3 conv); 1→3 Δ **0** |
| BE-RBAC05 | Role constant dedup | `_ADMIN_ROLES` / `_MANAGEMENT_ROLES` in `establishments/role_constants.py`; imported by checklists, signals, actions, chat, membership_scope |
| FE-07 | Deprecated `terrain-card` imports | 12 files migrated to `@/components/ui/terrain`; layout re-export deleted |
| TST-02 | `test_permissions.py` gaps | Added `signals/tests/test_permissions.py`, `chat/tests/test_permissions.py` |
| TST-04 | Slow markers | `@pytest.mark.slow` on golden pipeline / provider / validation tests |

### Query baselines updated

| Endpoint | Before (L) | After (S1) |
|----------|------------|------------|
| `GET .../chat/conversations/` (3 items) | 12 | **10** |
| Same 1→3 Δ | ≤2 | **0** |

---

## Reviewed / deferred with reason

| Item | Decision | Rationale |
|------|----------|-----------|
| FE-08 / entry shell | **Defer** | Entry ~561 kB post-P; no measured gain from further split without product-driven route work |
| PWA precache (50 entries) | **Defer** | Dev-phase acceptable; no offline policy change without reviewed tradeoffs |
| API-04 unbounded list pagination | **Defer** | L inventory documents ~50-row threshold; fixture scale not proven hot |
| API-06 onboarding/auth casts | **Defer** | H residual; no contract change in S1 |
| BE-S01–S05 structural refactors | **Defer** | Not blocking; no profiling evidence |
| `reporter_display` boundary | **No action** | Module remains display-only; no growth beyond Phase E helpers |

---

## Follow-up backlog (post-S1)

- Review `membership-rbac.ts` once backend exposes membership edit hints
- Review remaining `App.tsx` / shared shell size after further route splits
- Audit chat nav hint freshness after `chat_enabled` toggle UX exists
- Continue narrowing invalidations if query tests reveal over-refetch
- Verify clean `bootstrap-dev` from empty local DB after all hardening lots
- Verify shared-dev guard scripts from real local environment
- Keep scheduler startup explicit; do not auto-start Beat from bootstrap
- Revisit read-path materialization only if Celery beat is always guaranteed

---

## Commands run

```bash
make verify
make shared-dev-check   # when .env.shared-dev present
```

## Rollback

Per-item revert; query baselines in `houston/testing/query_baseline.py` can be restored independently.
