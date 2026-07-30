# Test audit

Audit and refactor the test suite for the requested scope.

Mode:
- destructive cleanup allowed when justified by risk analysis
- prefer fewer stronger tests over many weak tests
- no arbitrary test-count quotas

Read first:
- [`docs/engineering/testing.md`](../../docs/engineering/testing.md)
- [`.cursor/rules/40-testing.mdc`](../rules/40-testing.mdc)
- nearest `AGENTS.md` and existing tests in the domain

## Pre-merge checklist (scope under review)

### Coverage discipline
- [ ] Existing tests searched at the correct layer before any addition
- [ ] New test protects product risk (behavior, rule, permission, contract, regression) — not implementation or coverage %
- [ ] No duplicate assertion of the same rule across permissions / API / hooks / pages without layer-specific reason

### Backend
- [ ] Helpers imported from `houston/testing/` or `tests/helpers.py` — **zero** imports from `test_*.py`
- [ ] API tests assert HTTP boundary (status, shape, CSRF, tenant) — not re-proving every permissions unit case
- [ ] Services/Celery/WS tests use transactional DB where side effects matter
- [ ] No trivial model `_meta` or declarative-only tests
- [ ] `slow` marker only with documented justification; live OpenAI only under `openai_observation_smoke`
- [ ] `auth_throttle` on tests that need real 429 behavior

### Frontend
- [ ] Lib rules tested in Node (`*.test.ts`) — not re-tested via page copy/CSS
- [ ] Hooks/mutations use real `QueryClient` for invalidation paths
- [ ] Page tests limited to wiring risk (auth purge, guards, blocked submit) — not layout or Tailwind
- [ ] No shadcn primitive class assertions

### Protected areas (do not weaken)
- Auth / CSRF / refresh / throttle
- Tenant isolation / RBAC API
- Signal pipeline v4 golden + legacy issue-focus aggregation
- Fake OpenAI autouse + provider guard tests
- Notification producers (sensitive payloads)
- Query invalidation / auth-provider cache purge

## Audit scan

- slow or sleep-based tests without `slow` justification
- fragile copy/CSS/class assertions
- redundant cross-layer duplication (RBAC matrix)
- over-mocked frontend pages
- obsolete behavior or scaffolding tests (removed EventEnvelope / dead domains without product plan)
- fixture bloat (`imported_catalog` scope changes need measurement)
- missing critical lifecycle / journey / cache-purge coverage

## Actions

- delete duplicate, obsolete, or implementation-detail tests when lib/service already covers the rule
- replace weak tests with stronger focused coverage at the owning layer
- add only missing **critical** tests (see protected areas + journey gaps)
- extract shared setup to helpers — never leave cross-imports between `test_*.py` files

## Validation

- targeted: `make backend-test ARGS='…'` or `cd apps/web && npm test -- …`
- gates when justified: `make backend-check`, `make verify`, `make web-lint`

Final report:
- Deleted
- Refactored
- Added
- Validated
- Remaining test debt
