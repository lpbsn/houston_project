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
# Canonical (Docker stack, local DB only)
make test
make backend-test

# Lint (Docker)
make backend-lint
make lint

# Local with services running — prefer Make targets above
docker compose exec api sh -lc 'cd /app/apps/api && uv run pytest -m "not openai_observation_smoke and not openai_smoke and not slow" -q'

# Profile slow tests
docker compose exec api pytest --durations=50 -q

# Reproduce CI backend test env locally (DJANGO_DEBUG=0, production throttle rates)
docker compose exec api sh -lc 'cd /app/apps/api && DJANGO_DEBUG=0 uv run pytest -m "not openai_observation_smoke and not openai_smoke and not slow" -q'
```

### Layout

- Domain tests live in `houston/<domain>/tests/`.
- Shared factories and auth helpers live in `houston/testing/`:
  - `factories.py` — memberships, establishments, users
  - `auth.py` — `login`, `auth_headers`, `build_api_membership`, `TEST_PASSWORD`
  - `taxonomy.py` — business units, activity subjects, restaurant v3 taxonomy
  - `onboarding.py` — manual V2 payloads and onboarding session helpers
  - `pipeline.py` — observation/golden pipeline helpers
- Catalog fixtures in `establishments/tests/conftest.py`:
  - `imported_catalog` — function-scoped sync via `sync_catalog_from_normalized_rows()`
  - `requires_empty_catalog` — assert no catalog rows (tests that expect an empty DB)

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
- `auth_throttle` — tests that assert real rate-limit behavior (429). Excluded from the global relaxed-throttle fixture in `houston/conftest.py`. Use this marker plus local low-rate overrides when adding new throttle tests.

### Auth throttling in pytest

CI runs with `DJANGO_DEBUG=0`, which enables production auth throttle quotas and Redis-backed counters. The standard test suite calls `/auth/login/` hundreds of times from the same IP, so unguarded runs hit 429 and cascade into auth/RBAC failures.

`houston/conftest.py` applies an autouse fixture (`relaxed_auth_throttling_for_standard_tests`) for all tests **except** those marked `auth_throttle`:

- LocMem cache with a unique `LOCATION` per test
- relaxed quotas (`1000/minute`, mirroring DEBUG settings)
- skip via `yield; return` when `@pytest.mark.auth_throttle` is present (never bare `return` in this yield fixture)

Dedicated throttle tests (`test_auth_throttling_api.py`, invitation accept over-limit, etc.) must use `@pytest.mark.auth_throttle` and their own low-rate cache isolation. Production rates in `config/settings.py` are unchanged.

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
make web-test
make web-lint
make web-typecheck
make web-build

cd apps/web && npm test
cd apps/web && npm run lint
cd apps/web && npm run typecheck
```

### Layout

- Pure lib helpers: `features/<domain>/lib/*.test.ts` (Node environment)
- Provider/hook integration: `// @vitest-environment jsdom` + `@testing-library/react`
- Shared harness: `src/test-utils/` (`createTestQueryClient`, auth mocks, WebSocket mock)

### Rules

- Lib tests stay in **Node** (fast, no DOM).
- Auth provider, WebSocket hooks, and TanStack Query mutations use **jsdom** + test-utils.
- Do not assert exact Tailwind classes or French copy unless it encodes a business rule in lib code.

## CI vs local gates

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR:

| Job | Steps |
|-----|-------|
| `backend-tests` | `manage.py check`, `makemigrations --check --dry-run`, `ruff check .`, OpenAPI regen + `git diff schema.yml`, `pytest` (PostgreSQL + Redis; smoke/slow excluded) |
| `frontend-tests` | `npm run lint`, `npm test`, `npm run typecheck`, `npm run build` |

**Runtime note:** CI backend steps run **native `uv`** with GitHub Actions Postgres/Redis services. Local backend validation uses **Make/Docker only** (`make backend-check`, `make verify`) — do not run `cd apps/api && uv run …` on the host. Frontend checks may run natively from `apps/web` or via `make web-*`.

**Still ungated in CI and `make verify`:** generated `types.ts` freshness (follow-up CI-E8). CI runs `npm run lint`; `make verify` / `web-check` do not — run `make web-lint` before merge if you need lint parity.

### Local validation targets

| Target | What it runs |
|--------|----------------|
| `make backend-check` | Django check, ruff, migrations check, schema diff, pytest |
| `make web-check` | vitest, typecheck, build |
| `make local-check` | `backend-check` + `web-check` |
| `make verify` | alias for `local-check` |

Run `make verify && make web-lint` before merging when the Docker stack is up and you need full confidence. For day-to-day backend work, `make backend-test` or `make backend-lint` is enough.

### Issue focus aggregation eval (Lot 5)

```bash
# Live OpenAI corpus diff (opt-in, not CI)
export HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1
docker compose exec api uv run python manage.py evaluate_observation_pipeline --case-id G01 --case-id G03
docker compose exec api uv run python manage.py evaluate_observation_pipeline --json --fail-on-diff

# Plumbing check without OpenAI
docker compose exec api uv run python manage.py evaluate_observation_pipeline --provider fake --case-id G01

# DB aggregation metrics (pilot monitoring)
docker compose exec api uv run python manage.py report_issue_focus_aggregation_eval --json
make backend-test PYTEST_ARGS='houston/signals/tests/test_pipeline_v4_golden.py houston/signals/tests/test_aggregation_eval.py houston/signals/tests/test_evaluate_observation_pipeline.py -q'
```

See [`issue_focus_aggregation_eval_lot5.md`](issue_focus_aggregation_eval_lot5.md).
