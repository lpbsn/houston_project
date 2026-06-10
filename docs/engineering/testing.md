# Houston testing conventions

Phase build: tests protect product risk, not line coverage.

## Philosophy

- A test must protect a **behavior**, **business rule**, **permission**, **API contract**, or **critical regression**.
- Prefer explicit setup over opaque fixtures.
- Do not use source inspection (`readFileSync` + `toContain`) for behavior.
- Do not chase global coverage percentages.
- Delete weak tests rather than maintaining historical noise.

## Backend (pytest)

### Commands

```bash
# Canonical (Docker stack)
make test

# Local with services running
cd apps/api && uv run pytest

# Profile slow tests
docker compose exec api pytest --durations=50 -q

# Exclude opt-in / slow markers
uv run pytest -m "not openai_observation_smoke and not openai_smoke and not slow" -q
```

### Layout

- Domain tests live in `houston/<domain>/tests/`.
- Shared factories and auth helpers live in `houston/testing/`:
  - `factories.py` — memberships, establishments, users
  - `auth.py` — `login`, `auth_headers`, `build_api_membership`, `TEST_PASSWORD`
  - `taxonomy.py` — business units, activity subjects, restaurant v3 taxonomy
  - `onboarding.py` — manual V2 payloads and onboarding session helpers
  - `pipeline.py` — observation/golden pipeline helpers
- Session-scoped `imported_catalog` fixture: `establishments/tests/conftest.py`

**Do not** import helpers from `test_*.py` modules.

### When to write which layer

| Layer | Use for |
|-------|---------|
| `test_*_services.py` | State transitions, invariants, DB side effects |
| `test_*_api.py` | HTTP status, RBAC, response shape, CSRF where relevant |
| `test_*_selectors.py` | Query scoping, filtering, sorting |
| `test_permissions.py` | Permission functions in isolation |

### Markers

- `openai_observation_smoke`, `openai_smoke` — opt-in live AI (env-gated)
- `slow` — explicit sleep or >1s tests (excluded from fast CI job)

### Product priorities (must stay covered)

- Auth / bootstrap / CSRF / refresh rotation
- RBAC and cross-establishment isolation
- Signal lifecycle (pipeline golden + cancel/resolve)
- Action lifecycle (service + API transitions + permissions)
- Checklist permissions and materialization
- Chat WS ticket auth and message delivery
- Upload validators

### Voluntary debt

- `provisioning` — no tests until product risk is defined
- `organizations` — minimal model coverage only
- Non-critical UI pages — no frontend page tests unless wiring is product-critical

## Frontend (Vitest)

### Commands

```bash
cd apps/web && npm test
cd apps/web && npm run typecheck
make web-test
```

### Layout

- Pure lib helpers: `features/<domain>/lib/*.test.ts` (Node environment)
- Provider/hook integration: `// @vitest-environment jsdom` + `@testing-library/react`
- Shared harness: `src/test-utils/` (`createTestQueryClient`, auth mocks, WebSocket mock)

### Rules

- Lib tests stay in **Node** (fast, no DOM).
- Auth provider, WebSocket hooks, and TanStack Query mutations use **jsdom** + test-utils.
- Do not assert exact Tailwind classes or French copy unless it encodes a business rule in lib code.

## CI

GitHub Actions workflow `.github/workflows/ci.yml` runs:

- Backend: `uv run pytest` with PostgreSQL + Redis services (smoke/slow excluded)
- Frontend: `npm test` + `npm run typecheck`

Full local gate: `make verify` (includes schema, lint, build).
