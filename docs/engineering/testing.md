# Houston testing conventions

Phase build: tests protect **product risk**, not line coverage or implementation details.

## Philosophy

- A test must protect a **behavior**, **business rule**, **permission**, **API contract**, or **critical regression**.
- **Check existing coverage** in the same domain and layer before adding a test — extend a focused test rather than duplicating another layer.
- Prefer explicit setup over opaque fixtures.
- Do not use source inspection (`readFileSync` + `toContain`) for behavior.
- Do not chase global coverage percentages or per-file test quotas.
- Delete weak tests rather than maintaining historical noise.
- During development: run **targeted** tests (`make backend-test ARGS='…'`, `npm test -- path`); before merge: project gates (`make backend-check`, `make verify`, `make web-lint`).

## Risk by layer

Add a test only when the layer owns product risk **not already asserted elsewhere**. Do not re-prove the same rule in permissions, API, hooks, and pages.

### Backend

| Layer | Test when | Avoid |
|-------|-----------|-------|
| `permissions.py` | Role×scope combinations, readable/visible rules, edge cases not trivially exposed by API | Re-testing every boolean already matriced in unit via identical API 403 cases |
| `services.py` | State transitions, invariants, DB side effects, after-commit behavior | Re-asserting permission booleans the service delegates unchanged |
| `selectors.py` | Query scoping, filtering, sorting, tenant isolation in reads | Full HTTP round-trips for pure query logic |
| `test_*_api.py` | HTTP status, response shape, CSRF, tenant isolation at the boundary | Duplicating each permission unit case as a separate API test |
| Celery / WS / producers | Side effects after commit, idempotence, payload allowlist, sensitive-data guards | Mocks that bypass transactional DB without reason |
| `models.py` | DB constraints, normalization, business invariants tied to the schema | Declarative `_meta` (verbose names, ordering) with no runtime behavior |
| Journey / integration | Cross-app product loop (e.g. observation → pipeline → signal feed) when fragmented unit tests miss wiring | Replacing focused unit/API tests with one mega-test |

Shared helpers live in `houston/testing/` or domain `tests/helpers.py` — **never** import from `test_*.py` modules.

### Frontend

| Layer | Test when | Avoid |
|-------|-----------|-------|
| `features/*/lib/*.test.ts` | Algorithms, validation, cache keys, navigation derivation, RBAC display hints | — |
| Hooks / mutations (jsdom) | TanStack Query invalidation, mutation error paths, realtime wiring with real `QueryClient` | Mocking everything except the API boundary |
| Pages / components | Wiring at product risk: auth purge, establishment switch cache, navigation guards, blocked submission | Exact Tailwind classes, French copy, shadcn primitive styling |
| Auth provider | `purgeNonAuthQueries` / `clearAuthenticatedQueryCache` on logout, login, registration, establishment switch | Re-testing query-invalidation lib rules already covered in `query-invalidation.test.ts` |

Reference implementations: `query-invalidation.test.ts`, `profile-switch-establishment-cache.test.tsx`, `auth-provider.test.tsx`.

## Backend (pytest)

### Commands

```bash
# Canonical (Docker stack, local DB only)
make test
make backend-test

# Targeted (preferred while iterating)
make backend-test ARGS='houston/signals/tests/test_pipeline_v4_golden.py -q'
make backend-test ARGS='houston/signals/tests/test_pipeline_v4_golden.py::test_golden_case -q'

# Lint (Docker)
make backend-lint
make lint

# Profile slow tests (diagnostic — see baseline below)
docker compose exec api sh -lc 'cd /app/apps/api && uv run pytest --durations=50 -q'

# Reproduce CI backend test env locally (DJANGO_DEBUG=0, production throttle rates)
docker compose exec api sh -lc 'cd /app/apps/api && DJANGO_DEBUG=0 uv run pytest -m "not openai_observation_smoke and not openai_smoke and not slow" -q'
```

Do not run `cd apps/api && uv run pytest` on the host — use Make targets or `docker compose exec api`.

### Layout

- Domain tests live in `houston/<domain>/tests/`.
- Shared factories and auth helpers live in `houston/testing/`:
  - `factories.py` — memberships, establishments, users
  - `auth.py` — `login`, `auth_headers`, `build_api_membership`, `TEST_PASSWORD`
  - `taxonomy.py` — business units, activity subjects, restaurant v3 taxonomy
  - `onboarding.py` — manual V2 payloads and onboarding session helpers
  - `pipeline.py` — observation/golden pipeline helpers
- Domain-specific shared helpers (Lot 4): `tests/helpers.py`, `tests/ws_helpers.py`, `tests/pipeline_helpers.py`, etc. — import these, not `test_*.py`.
- Catalog fixtures in `establishments/tests/conftest.py`:
  - `imported_catalog` — function-scoped sync via `sync_catalog_from_normalized_rows()` (**do not change** scope or seed strategy for taxonomy contraction work)
  - `requires_empty_catalog` — assert no catalog rows (tests that expect an empty DB)
- **Do not** widen `imported_catalog` to session scope without a measured pilot on a single file; shared catalog state breaks isolation and blocks xdist.
- **Taxonomy contraction / env reset:** when an environment has **no data to retain**, prefer a full DB reset + migrate + `make import-catalog` (local: `make reset-dev-db`) over a complex business backfill. When data **must** be retained, **do not reset** — plan an explicit backfill / data migration. Operator order: [`../deploy/prod_test_runbook.md`](../deploy/prod_test_runbook.md).

### Markers

| Marker | Meaning | CI PR |
|--------|---------|-------|
| *(none)* | Standard fake-provider suite | Yes |
| `slow` | Reserved — requires **explicit justification** in code review: real sleep, sustained >1s runtime, live external API, or heavy concurrency | No (excluded via Makefile/CI filter) |
| `openai_observation_smoke` | Live OpenAI observation pipeline; env `HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1` | No |
| `openai_smoke` | Reserved onboarding live smoke; env `HOUSTON_RUN_OPENAI_SMOKE_TEST=1` — **no tests yet** | No |
| `openai_transcription_smoke` | Reserved transcription live smoke — **no tests yet** | No |
| `auth_throttle` | Real rate-limit behavior (429); excluded from relaxed-throttle autouse fixture | Yes (when not also `slow`) |

#### Fake provider vs live smoke (do not conflate)

| Category | Provider | CI PR |
|----------|----------|-------|
| **Standard suite** (~1 600+ tests) | `FakeObservationPipelineProvider` via autouse `force_fake_observation_pipeline_provider` | Yes |
| **Provider guard tests** | Fake + mocked OpenAI client (`test_observation_pipeline_provider.py`) | Yes (Lot 6: no longer `slow`) |
| **Pipeline validation / legacy / golden split** | Fake provider, DB-heavy | Yes (Lot 6: reintegrated into PR) |
| **Live OpenAI smoke** | Real OpenAI (`test_openai_observation_smoke.py`, `test_openai_observation_pipeline_v4_corpus_smoke.py`) | No — manual / pre-release only |

PR filter (Makefile + CI): `-m "not openai_observation_smoke and not openai_smoke and not slow"`.

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
- Signal lifecycle (pipeline golden G01–G11 + schema/prompt v5 `routing_key` + cancel/resolve)
- Action lifecycle (service + API transitions + permissions)
- Checklist permissions and materialization
- Chat WS ticket auth and message delivery
- Upload validators
- Observation → signal feed journey (`observations/tests/test_observation_signal_feed_journey.py`)
- TanStack Query cache purge on auth/session changes

### Voluntary debt

- `provisioning` — no tests until product risk is defined
- `organizations` — minimal model coverage only
- Non-critical UI pages — no page tests unless wiring is product-critical
- Playwright E2E — proposal only: [`playwright_lot7_proposal.md`](playwright_lot7_proposal.md) (not in PR CI)

## Frontend (Vitest)

### Commands

```bash
make web-test
make web-lint
make web-typecheck
make web-build

cd apps/web && npm test
cd apps/web && npm test -- src/features/auth/pages/profile-switch-establishment-cache.test.tsx
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
- Do not assert exact Tailwind classes, shadcn primitive styling, or French copy unless the string encodes a business rule exported from lib code.
- Do not add page tests for layout or copy when the rule already lives in lib/hook tests.

## CI vs local gates

GitHub Actions (`.github/workflows/ci.yml`):

- **Triggers**: `pull_request` on all branches; `push` on `main` only (avoids double runs when a PR branch pushes).
- **Concurrency**: `cancel-in-progress` per ref.
- **Path filters**: backend / frontend / docs jobs run only when relevant paths change; changes to API schema sources or `schema.yml` / `types.ts` still run **both** backend and frontend jobs.

| Job | Steps |
|-----|-------|
| `backend-tests` | Django check, deploy check, migrations, ruff, OpenAPI regen + diff, pytest (PostgreSQL + Redis; smoke/slow excluded) |
| `frontend-tests` | `npm ci`, `api:generate` + diff, lint, vitest, `typecheck` (`tsc -b` once), `build:bundle` (vite only — no second `tsc -b`) |
| `docs-check` | `scripts/docs_check.py`, `scripts/agent_config_check.py` |

**Runtime note:** CI backend steps run **native `uv`** with GitHub Actions Postgres/Redis services. Local backend validation uses **Make/Docker only** (`make backend-check`, `make verify`) — do not run `cd apps/api && uv run …` on the host. Frontend checks may run natively from `apps/web` or via `make web-*`.

**Lint parity:** CI runs `npm run lint`; `make verify` / `web-check` do not — run `make web-lint` before merge when you need full parity.

### Local validation targets

| Target | What it runs |
|--------|----------------|
| `make backend-check` | Django check, ruff, migrations check, schema diff, pytest |
| `make web-api-generate-check` | regen `types.ts` from committed `schema.yml` + `git diff` |
| `make web-check` | vitest, typecheck, build, `web-api-generate-check` |
| `make local-check` | `backend-check` + `web-check` |
| `make verify` | alias for `local-check` |

Run `make verify && make web-lint` before merging when the Docker stack is up and you need full confidence. For day-to-day backend work, `make backend-test` or `make backend-lint` is enough.

## Baseline (Lot 1 — diagnostic, not targets)

Recorded 2026-07-15 in `.artifacts/lot1-baseline/` (local Docker vs CI run `29397589248`):

| Measure | Local PR suite | CI |
|---------|----------------|-----|
| Backend tests passed | 1614 | — |
| Backend pytest duration | ~361 s | ~639 s (step) |
| Vitest files / tests | 164 / 1060 | ~61 s (step) |
| Cross-imports `test_*.py` | 0 (after Lot 4 helpers extraction) | — |
| `imported_catalog` marginal cost | ~16 s / 65 tests vs ~64 s / 311 tests | not dominant |

Use `--durations=50` and `.artifacts/vitest-results.json` for ongoing profiling — **no arbitrary duration quotas**; optimize only measured bottlenecks.

## Audit decisions (Lots 2–7)

| Lot | Decision |
|-----|----------|
| **2** | Remove trivial `_meta` / Django declarative tests; drop shadcn `input`/`textarea` class tests; **EventEnvelope Option A** — keep scaffolding + 3 regression tests (`houston/core/events.py`, non-runtime); v3 golden mapped to v4 — prefer v4 corpus, delete v3 when overlap confirmed |
| **3** | CI concurrency, path filters, push-on-`main` only, single `tsc -b` in frontend job |
| **4** | Extract shared test helpers to `tests/helpers.py`; zero cross-imports from `test_*.py`; parametrize redundant feed/RBAC API cases where matrix proves duplication |
| **6** | Replace TTL `sleep(1.1)` with deterministic time control; reintegrate former `slow` modules into PR; keep live OpenAI smoke manual-only; preserve reserved `openai_smoke` / `openai_transcription_smoke` markers |
| **7** | Backend observation→signal feed journey; auth-provider cache purge tests; Playwright limited to 3 scenarios — infra proposal only, not PR gate |

Protected areas (do not weaken): auth/CSRF/throttle, tenant isolation, pipeline v4 golden, legacy issue-focus aggregation, fake OpenAI guards, notification producers, query invalidation parity.

## Issue focus aggregation eval

```bash
# Live OpenAI corpus diff (opt-in, not CI)
export HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1
docker compose exec api uv run python manage.py evaluate_observation_pipeline --case-id G01 --case-id G03
docker compose exec api uv run python manage.py evaluate_observation_pipeline --json --fail-on-diff

# Plumbing check without OpenAI
docker compose exec api uv run python manage.py evaluate_observation_pipeline --provider fake --case-id G01

# DB aggregation metrics (pilot monitoring)
docker compose exec api uv run python manage.py report_issue_focus_aggregation_eval --json
make backend-test ARGS='houston/signals/tests/test_pipeline_v4_golden.py houston/signals/tests/test_aggregation_eval.py houston/signals/tests/test_evaluate_observation_pipeline.py -q'
```

Command: `report_issue_focus_aggregation_eval` (see `houston/signals/management/commands/`).

## Agent workflow

- Before adding or expanding tests: read this doc and run the [`test-audit`](../../.cursor/commands/test-audit.md) checklist on the touched scope.
- Cursor rule: [`.cursor/rules/40-testing.mdc`](../../.cursor/rules/40-testing.mdc) (applies when editing test files).
