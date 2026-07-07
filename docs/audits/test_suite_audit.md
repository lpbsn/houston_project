# Test suite audit — Houston

**Date:** 2026-07-07  
**Scope:** 3 échecs `make verify`, RBAC manager/scopes, drift `scope_label`, couverture critique auth/chat/membership.  
**Reference:** plan minimal post-analyse statique + validation ciblée.

---

## 1. Files inspected

- `apps/api/houston/establishments/membership_scope.py`
- `apps/api/houston/establishments/services.py`
- `apps/api/houston/accounts/selectors.py`
- `apps/api/houston/accounts/api/serializers.py`
- `apps/api/houston/testing/taxonomy.py`
- `apps/api/schema.yml`

## 2. Tests inspected

- `apps/api/houston/accounts/tests/test_auth_api.py`
- `apps/api/houston/chat/tests/test_membership_deactivation.py`
- `apps/api/houston/establishments/tests/test_membership_api.py`
- `apps/api/houston/establishments/tests/test_membership_scope.py`
- `apps/api/houston/accounts/tests/test_bootstrap_permission_hints.py`
- Échantillon suite globale (~170 modules backend, 121 fichiers Vitest)

## 3. Docs / rules inspected

- `AGENTS.md`, `apps/api/AGENTS.md`
- `docs/audits/phase_2_test_strategy_audit.md`
- `docs/audits/README.md`

## 4. Assumptions / unknowns

- Frontend `make verify` hors scope des 3 échecs backend initiaux.
- Megafiles action_plans/chat non audités en profondeur (dette structurelle, pas bloquante CI).

---

## Executive summary

Les 3 échecs `make verify` ne sont **pas** des bugs fonctionnels prod : tests mal alignés avec `scope_label` additif et RBAC manager par périmètre BU. Dette principale : factories `create_membership` dupliquées et absence de tests API `deactivate` manager scoped.

---

## Findings

### F1 — Tests auth obsolètes sur `scopes`

- **Severity:** P0 | **Category:** tests / API contract
- **Evidence:** `test_login_with_csrf_succeeds_for_valid_email`, `test_bootstrap_with_valid_bearer_returns_authenticated_payload` in `test_auth_api.py`
- **Problem:** strict equality without `scope_label`; runtime emits `scope_label: "Housekeeping"`
- **Why it matters now:** `make verify` red
- **Why it will hurt later:** every payload enrichment breaks CI
- **Recommended fix:** reuse `assert_business_unit_scope_response` from `houston/testing/taxonomy.py`
- **Tests to add/update:** fix 2 existing auth tests
- **Size:** S

### F2 — Chat deactivation test: manager without scopes

- **Severity:** P0 | **Category:** tests / security
- **Evidence:** `test_membership_deactivation_removes_group_participant`; `can_actor_manage_target_membership` in `services.py`
- **Problem:** MANAGER without BU scope → `MembershipManagementForbiddenError` before chat side effects
- **Why it matters now:** test fails; does not validate intended behavior
- **Why it will hurt later:** false confidence on group participant removal on deactivation
- **Recommended fix:** add `create_business_unit` + `create_membership_with_business_unit_scope` on manager and staff
- **Tests to add/update:** fix existing chat deactivation test
- **Size:** S

### F3 — No API deactivate tests for scoped manager

- **Severity:** P1 | **Category:** tests / security
- **Evidence:** `test_membership_api.py` has `test_manager_can_patch_staff_in_scope` but zero `test_manager_*_deactivate_*`
- **Problem:** RBAC deactivate not covered at HTTP level while patch is
- **Why it matters now:** regression on deactivate possible without signal
- **Why it will hurt later:** team/membership feature evolution
- **Recommended fix:** add `test_manager_can_deactivate_staff_in_scope` and `test_manager_cannot_deactivate_staff_out_of_scope`
- **Tests to add/update:** 2 new tests in `test_membership_api.py`
- **Size:** S

### F4 — OpenAPI auth vs runtime contract drift

- **Severity:** P1 | **Category:** API contract
- **Evidence:** `AuthMembershipScopeItem` in `schema.yml` without `scope_label`; establishment serializer has it; runtime auth emits it
- **Problem:** documented contract ≠ actual behavior
- **Why it matters now:** generated frontend types may be incomplete for auth scopes
- **Why it will hurt later:** integration confusion, divergent assertions
- **Recommended fix:** add `scope_label` to `MembershipScopeItemSerializer` auth + regen schema/types
- **Tests to add/update:** auth tests + unit test for `membership_scope_rows_for_membership`
- **Size:** M

### F5 — Duplicate `create_membership` factories

- **Severity:** P1 | **Category:** maintainability / tests
- **Evidence:** `houston/testing/factories.py`, local in `test_auth_api.py`, local in `test_membership_api.py`
- **Problem:** copy-paste manager without scope → mutation tests silently wrong
- **Why it matters now:** direct cause of F2
- **Why it will hurt later:** growing debt per membership feature
- **Recommended fix:** extend shared factory with `business_unit_keys`; migrate progressively
- **Tests to add/update:** none (helper refactor)
- **Size:** M

### F6 — Cross-import `test_auth_api` from bootstrap hints

- **Severity:** P2 | **Category:** structure / tests
- **Evidence:** `test_bootstrap_permission_hints.py` imports from `test_auth_api`
- **Problem:** fragile coupling
- **Recommended fix:** import from `houston/testing/` only
- **Size:** S

### F7 — Redundant normalize dedupe tests

- **Severity:** P3 | **Category:** tests
- **Evidence:** `test_membership_scope.py` — two identical dedupe tests
- **Recommended fix:** delete one
- **Size:** S

### F8 — Quasi-duplicate WS `access_revoked` tests

- **Severity:** P3 | **Category:** tests
- **Evidence:** `test_ws_hardening.py` vs `test_ws_access_revocation.py`
- **Recommended fix:** merge assertions; remove smoke mock
- **Size:** S

### F9 — Misplaced test in deactivation file

- **Severity:** P3 | **Category:** structure
- **Evidence:** `test_group_promotes_new_admin_when_last_admin_leaves` in `test_membership_deactivation.py`
- **Problem:** tests leave API, not deactivation
- **Recommended fix:** move to `test_rest_api.py`
- **Size:** S

### F10 — `membership_is_assignable_by_actor` untested

- **Severity:** P2 | **Category:** tests / ambiguity
- **Evidence:** function in `membership_scope.py` used by user-search; differs from `can_actor_manage_target_membership`
- **Recommended fix:** 1–2 unit tests in `test_membership_scope_coverage.py`
- **Size:** S

---

## Top 3 fixes to do first

1. **F1** — Auth scope assertions via shared helper
2. **F2** — Chat deactivation test with scoped manager
3. **F3** — Manager deactivate API tests

## Quick wins

- `assert_business_unit_scope_response` in auth tests
- 2 manager deactivate API tests mirroring patch tests
- `test_membership_deactivation_forbidden_leaves_chat_unchanged`

## Structural issues to plan later

- F5 unified `create_membership` factory
- F6 bootstrap hints import decoupling
- Megafiles: `test_execution_feed_api.py` (1157 lines), `test_rest_api.py` (849 lines)

## Things not worth fixing now

- Split mega test files
- `organizations` domain (2 tests only)
- WS `conversation.access_revoked` on deactivation E2E (non-blocking)

---

## Implementation status (this pass)

### Deleted
- None (Lot 3 optional, not in scope)

### Refactored
- `test_auth_api.py` — scope assertions via `assert_business_unit_scope_response`
- `test_membership_deactivation.py` — scoped manager + staff setup

### Added
- `test_manager_can_deactivate_staff_in_scope`
- `test_manager_cannot_deactivate_staff_out_of_scope`
- `test_membership_deactivation_forbidden_leaves_chat_unchanged`
- `test_membership_scope_rows_for_membership_includes_scope_label`
- `scope_label` on `AuthMembershipScopeItem` serializer + schema regen

### Validated
- Targeted `make backend-test` on touched modules
- Full `make verify` when stack available

### Remaining test debt
- F5 factories unification
- F6–F10 optional cleanup
- Frontend observations/onboarding gaps (cf. phase_2 audit)
